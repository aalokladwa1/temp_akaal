"""tests.security.test_p7_campaign_b_c4_aws_kms_adapter
======================================================
C4 hostile review: exercises akaalPipeline.security.kms_provider.AWSKMSProvider's real
request-construction / response-mapping / error-translation logic against a scripted
SDK-interface-shaped test double (NOT a live AWS account). This proves the ADAPTER logic
(algorithm mapping, KeyReference field mapping, CMK origin classification, error
propagation) beyond the dependency-missing check alone -- without pretending the double
is a live provider (never asserted as LIVE_PROVEN anywhere in this file or its results).
"""

from __future__ import annotations

import pytest

from akaalPipeline.contracts.enums import KeyAlgorithm, KeyPurpose
from akaalPipeline.security.kms_provider import AWSKMSProvider, KeyOrigin, KeyReference


class FakeAWSKMSError(Exception):
    """Minimal stand-in for botocore.exceptions.ClientError -- avoids a hard dependency on
    botocore just to model an error shape, while still exercising AWSKMSProvider's own
    exception-propagation behavior (it does not catch/translate boto3 exceptions itself,
    so this proves they propagate untouched -- no silent swallowing)."""
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.response = {"Error": {"Code": code, "Message": message}}


class FakeBoto3KMSClient:
    """Scripted double matching the subset of the real boto3 KMS client surface
    AWSKMSProvider actually calls (create_key/describe_key/get_key_rotation_status/
    sign/verify/encrypt/decrypt/disable_key)."""

    def __init__(self) -> None:
        self.keys: dict = {}
        self.calls: list = []
        self.next_error: Exception | None = None

    def _maybe_raise(self):
        if self.next_error is not None:
            err = self.next_error
            self.next_error = None
            raise err

    def create_key(self, **kwargs):
        self.calls.append(("create_key", kwargs))
        self._maybe_raise()
        key_id = f"key-{len(self.keys) + 1}"
        arn = f"arn:aws:kms:us-east-1:111122223333:key/{key_id}"
        self.keys[key_id] = {"KeyState": "Enabled", "KeyUsage": kwargs.get("KeyUsage")}
        return {"KeyMetadata": {"KeyId": key_id, "Arn": arn, "AWSAccountId": "111122223333", "KeyState": "Enabled"}}

    def describe_key(self, KeyId, **kwargs):
        self.calls.append(("describe_key", {"KeyId": KeyId}))
        self._maybe_raise()
        state = self.keys.get(KeyId, {}).get("KeyState", "Enabled")
        return {"KeyMetadata": {"KeyId": KeyId, "KeyState": state, "Arn": f"arn:aws:kms:us-east-1:111122223333:key/{KeyId}"}}

    def get_key_rotation_status(self, KeyId, **kwargs):
        self.calls.append(("get_key_rotation_status", {"KeyId": KeyId}))
        self._maybe_raise()
        return {"KeyRotationEnabled": True}

    def sign(self, **kwargs):
        self.calls.append(("sign", kwargs))
        self._maybe_raise()
        return {"Signature": b"fake-signature-bytes"}

    def verify(self, **kwargs):
        self.calls.append(("verify", kwargs))
        self._maybe_raise()
        return {"SignatureValid": kwargs.get("Signature") == b"fake-signature-bytes"}

    def encrypt(self, **kwargs):
        self.calls.append(("encrypt", kwargs))
        self._maybe_raise()
        return {"CiphertextBlob": b"ENC[" + kwargs["Plaintext"] + b"]"}

    def decrypt(self, **kwargs):
        self.calls.append(("decrypt", kwargs))
        self._maybe_raise()
        blob = kwargs["CiphertextBlob"]
        assert blob.startswith(b"ENC[") and blob.endswith(b"]")
        return {"Plaintext": blob[4:-1]}

    def disable_key(self, KeyId, **kwargs):
        self.calls.append(("disable_key", {"KeyId": KeyId}))
        self._maybe_raise()
        self.keys.setdefault(KeyId, {})["KeyState"] = "Disabled"


def _provider() -> tuple[AWSKMSProvider, FakeBoto3KMSClient]:
    client = FakeBoto3KMSClient()
    provider = AWSKMSProvider(region_name="us-east-1", account_id="111122223333", client=client)
    return provider, client


def test_c4_aws_generate_key_maps_symmetric_and_reports_provider_generated_cmk():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    assert ref.provider == "AWS_KMS"
    assert ref.origin == KeyOrigin.PROVIDER_GENERATED_CMK  # never AKAAL_GENERATED for a cloud-created key
    assert ref.account_or_project == "111122223333"
    assert ref.region_or_location == "us-east-1"
    assert ref.resource_id.startswith("arn:aws:kms:")
    create_kwargs = client.calls[0][1]
    assert create_kwargs["KeySpec"] == "SYMMETRIC_DEFAULT"
    assert create_kwargs["KeyUsage"] == "ENCRYPT_DECRYPT"


def test_c4_aws_generate_key_maps_asymmetric_sign_usage():
    provider, client = _provider()
    provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    create_kwargs = client.calls[0][1]
    assert create_kwargs["KeySpec"] == "ECC_NIST_P256"
    assert create_kwargs["KeyUsage"] == "SIGN_VERIFY"


def test_c4_aws_encrypt_decrypt_roundtrip_through_real_adapter_logic():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    ciphertext = provider.encrypt(ref, b"top-secret")
    assert ciphertext != b"top-secret"
    plaintext = provider.decrypt(ref, ciphertext)
    assert plaintext == b"top-secret"


def test_c4_aws_sign_verify_through_real_adapter_logic():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    sig = provider.sign(ref, b"message")
    assert provider.verify(ref, b"message", sig) is True
    assert provider.verify(ref, b"message", b"wrong-signature") is False


def test_c4_aws_describe_key_reports_real_state_and_rotation():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    state = provider.describe_key(ref)
    assert state["key_state"] == "Enabled"
    assert state["rotation_enabled"] is True


def test_c4_aws_revoke_key_disables_and_describe_reflects_it():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    provider.revoke_key(ref)
    state = provider.describe_key(ref)
    assert state["key_state"] == "Disabled"


def test_c4_aws_permission_denied_propagates_not_swallowed():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    client.next_error = FakeAWSKMSError("AccessDeniedException", "User is not authorized to perform kms:Encrypt")
    with pytest.raises(FakeAWSKMSError):
        provider.encrypt(ref, b"data")


def test_c4_aws_throttling_propagates_not_silently_retried_or_swallowed():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    client.next_error = FakeAWSKMSError("ThrottlingException", "Rate exceeded")
    with pytest.raises(FakeAWSKMSError):
        provider.decrypt(ref, b"ENC[irrelevant]")


def test_c4_aws_verify_genuine_signature_mismatch_via_kms_invalid_signature_exception():
    """Target 5: AWS KMS reports a genuine bad signature via KMSInvalidSignatureException
    (not just SignatureValid=False), and only THIS specific error may become False."""
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    client.next_error = FakeAWSKMSError("KMSInvalidSignatureException", "Signature verification failed")
    assert provider.verify(ref, b"message", b"bad-signature") is False


def test_c4_aws_verify_access_denied_propagates_not_collapsed_to_false():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    client.next_error = FakeAWSKMSError("AccessDeniedException", "not authorized to perform kms:Verify")
    with pytest.raises(FakeAWSKMSError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_aws_verify_throttling_propagates_not_collapsed_to_false():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    client.next_error = FakeAWSKMSError("ThrottlingException", "Rate exceeded")
    with pytest.raises(FakeAWSKMSError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_aws_verify_provider_unavailable_propagates_not_collapsed_to_false():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    client.next_error = FakeAWSKMSError("KMSInternalException", "internal error")
    with pytest.raises(FakeAWSKMSError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_aws_verify_disabled_key_propagates_as_provider_failure_not_false():
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    client.next_error = FakeAWSKMSError("DisabledException", "key is disabled")
    with pytest.raises(FakeAWSKMSError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_aws_verify_malformed_response_fails_closed_not_false():
    """A response missing SignatureValid entirely must not be silently treated as False."""
    from akaalPipeline.security.kms_provider import KMSProviderUnavailableError

    class MalformedVerifyClient(FakeBoto3KMSClient):
        def verify(self, **kwargs):
            return {}  # missing SignatureValid entirely

    provider = AWSKMSProvider(region_name="us-east-1", client=MalformedVerifyClient())
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    with pytest.raises(KMSProviderUnavailableError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_aws_no_local_fallback_on_client_error():
    """A cloud-side failure must never silently substitute local envelope encryption."""
    provider, client = _provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    client.next_error = FakeAWSKMSError("KMSInternalException", "internal error")
    with pytest.raises(FakeAWSKMSError):
        provider.encrypt(ref, b"data")
    # No LocalEnvelopeKMSProvider or keystore reference exists anywhere on AWSKMSProvider.
    assert not hasattr(provider, "keystore")
