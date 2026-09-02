"""tests.security.test_p7_campaign_b_c4_azure_gcp_pkcs11_adapters
================================================================
C4 hostile review: deep local contract verification for AzureKeyVaultKMSProvider,
GCPCloudKMSProvider, and PKCS11HSMProvider against scripted SDK-interface-shaped test
doubles (never a live provider; never represented as LIVE_PROVEN).
"""

from __future__ import annotations

import pytest

from akaalPipeline.contracts.enums import KeyAlgorithm, KeyPurpose
from akaalPipeline.security.kms_provider import (
    AzureKeyVaultKMSProvider,
    GCPCloudKMSProvider,
    KeyNotFoundError,
    KeyOrigin,
    KMSProviderUnavailableError,
    PKCS11HSMProvider,
)


# ===========================================================================
# Azure Key Vault
# ===========================================================================

class FakeAzureKeyProps:
    def __init__(self, version="v1", enabled=True):
        self.version = version
        self.enabled = enabled


class FakeAzureKey:
    def __init__(self, key_id, version="v1", enabled=True):
        self.id = key_id
        self.properties = FakeAzureKeyProps(version, enabled)


class FakeAzureKeyClient:
    def __init__(self):
        self.keys = {}
        self.next_error = None

    def create_key(self, name, key_type):
        if self.next_error:
            err, self.next_error = self.next_error, None
            raise err
        key_id = f"https://vault.example.net/keys/{name}/v1"
        key = FakeAzureKey(key_id)
        self.keys[name] = key
        return key

    def begin_delete_key(self, name):
        if self.next_error:
            err, self.next_error = self.next_error, None
            raise err
        if name in self.keys:
            self.keys[name].properties.enabled = False


class FakeAzureSignResult:
    def __init__(self, signature): self.signature = signature


class FakeAzureVerifyResult:
    def __init__(self, is_valid): self.is_valid = is_valid


class FakeAzureEncResult:
    def __init__(self, ciphertext): self.ciphertext = ciphertext


class FakeAzureDecResult:
    def __init__(self, plaintext): self.plaintext = plaintext


class FakeAzureCryptoClient:
    def __init__(self):
        self.next_error = None

    def _raise_if_scheduled(self):
        if self.next_error:
            err, self.next_error = self.next_error, None
            raise err

    def sign(self, alg, digest):
        self._raise_if_scheduled()
        return FakeAzureSignResult(b"fake-sig:" + digest)

    def verify(self, alg, digest, signature):
        self._raise_if_scheduled()
        return FakeAzureVerifyResult(signature == b"fake-sig:" + digest)

    def encrypt(self, alg, plaintext):
        self._raise_if_scheduled()
        return FakeAzureEncResult(b"ENC[" + plaintext + b"]")

    def decrypt(self, alg, ciphertext):
        self._raise_if_scheduled()
        return FakeAzureDecResult(ciphertext[4:-1])


class FakeAzureHttpError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


def _azure_provider():
    client = FakeAzureKeyClient()
    crypto_client = FakeAzureCryptoClient()
    provider = AzureKeyVaultKMSProvider(
        vault_url="https://vault.example.net",
        client=client,
        crypto_client_factory=lambda key_id: crypto_client,
    )
    return provider, client, crypto_client


def test_c4_azure_generate_key_reports_provider_generated_cmk_and_dynamic_url():
    provider, client, _ = _azure_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    assert ref.provider == "AZURE_KEY_VAULT"
    assert ref.origin == KeyOrigin.PROVIDER_GENERATED_CMK
    assert ref.resource_id.startswith("https://vault.example.net/keys/")
    assert provider.vault_url == "https://vault.example.net"  # no hardcoded vault URL


def test_c4_azure_no_hardcoded_vault_url_required():
    with pytest.raises(ValueError):
        AzureKeyVaultKMSProvider(vault_url="")


def test_c4_azure_encrypt_decrypt_roundtrip():
    provider, client, _ = _azure_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    ct = provider.encrypt(ref, b"secret-data")
    assert ct != b"secret-data"
    assert provider.decrypt(ref, ct) == b"secret-data"


def test_c4_azure_sign_verify_roundtrip():
    provider, client, _ = _azure_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    sig = provider.sign(ref, b"message")
    assert provider.verify(ref, b"message", sig) is True
    assert provider.verify(ref, b"message", b"wrong") is False


def test_c4_azure_disabled_key_reflected_after_revoke():
    provider, client, _ = _azure_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    provider.revoke_key(ref)
    assert client.keys["akaal-token_encrypt"].properties.enabled is False


def test_c4_azure_permission_and_throttling_errors_propagate_not_swallowed():
    provider, client, crypto = _azure_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    crypto.next_error = FakeAzureHttpError(403, "Forbidden")
    with pytest.raises(FakeAzureHttpError):
        provider.encrypt(ref, b"data")

    crypto.next_error = FakeAzureHttpError(429, "Too Many Requests")
    with pytest.raises(FakeAzureHttpError):
        provider.decrypt(ref, b"ENC[x]")


def test_c4_azure_verify_error_propagates_not_collapsed_to_false():
    """Azure's verify() has no broad except -- proves a provider error during verify is
    never silently reported as an invalid-signature False."""
    provider, client, crypto = _azure_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    crypto.next_error = FakeAzureHttpError(503, "Service Unavailable")
    with pytest.raises(FakeAzureHttpError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_azure_rotate_key_truthfully_unsupported_at_purpose_level():
    provider, client, _ = _azure_provider()
    with pytest.raises(KMSProviderUnavailableError):
        provider.rotate_key(KeyPurpose.TOKEN_ENCRYPT)


def test_c4_azure_no_local_fallback():
    provider, client, _ = _azure_provider()
    assert not hasattr(provider, "keystore")


# ===========================================================================
# GCP Cloud KMS
# ===========================================================================

class FakeGCPCryptoKey:
    def __init__(self, name): self.name = name


class FakeGCPResult:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeGCPError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code  # e.g. "PERMISSION_DENIED", "RESOURCE_EXHAUSTED", "UNAVAILABLE"


class FakeGCPKMSClient:
    def __init__(self):
        self.calls = []
        self.next_error = None
        self.store = {}

    def _maybe_raise(self):
        if self.next_error:
            err, self.next_error = self.next_error, None
            raise err

    def key_ring_path(self, project_id, location_id, key_ring_id):
        return f"projects/{project_id}/locations/{location_id}/keyRings/{key_ring_id}"

    def create_crypto_key(self, request):
        self.calls.append(("create_crypto_key", request))
        self._maybe_raise()
        name = f"{request['parent']}/cryptoKeys/{request['crypto_key_id']}"
        self.store[name] = {"state": "ENABLED"}
        return FakeGCPCryptoKey(name)

    def encrypt(self, request):
        self.calls.append(("encrypt", request))
        self._maybe_raise()
        return FakeGCPResult(ciphertext=b"ENC[" + request["plaintext"] + b"]")

    def decrypt(self, request):
        self.calls.append(("decrypt", request))
        self._maybe_raise()
        ct = request["ciphertext"]
        return FakeGCPResult(plaintext=ct[4:-1])

    def asymmetric_sign(self, request):
        self.calls.append(("asymmetric_sign", request))
        self._maybe_raise()
        return FakeGCPResult(signature=b"fake-gcp-sig")

    def update_crypto_key_primary_version(self, request):
        self.calls.append(("update_crypto_key_primary_version", request))
        self._maybe_raise()
        self.store.setdefault(request["name"], {})["state"] = "DISABLED"


def _gcp_provider():
    client = FakeGCPKMSClient()
    provider = GCPCloudKMSProvider(project_id="akaal-proj", location_id="us-central1", key_ring_id="akaal-ring", client=client)
    return provider, client


def test_c4_gcp_generate_key_constructs_dynamic_resource_name_no_hardcoded_project():
    provider, client = _gcp_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    assert ref.provider == "GCP_KMS"
    assert ref.origin == KeyOrigin.PROVIDER_GENERATED_CMK
    assert ref.account_or_project == "akaal-proj"
    assert ref.region_or_location == "us-central1"
    assert "projects/akaal-proj/locations/us-central1/keyRings/akaal-ring" in ref.resource_id


def test_c4_gcp_no_hardcoded_project_location_keyring():
    with pytest.raises(ValueError):
        GCPCloudKMSProvider(project_id="", location_id="", key_ring_id="")


def test_c4_gcp_encrypt_decrypt_roundtrip():
    provider, client = _gcp_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    ct = provider.encrypt(ref, b"secret")
    assert provider.decrypt(ref, ct) == b"secret"


def test_c4_gcp_sign_issues_real_asymmetric_sign_request():
    provider, client = _gcp_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    sig = provider.sign(ref, b"message")
    assert sig == b"fake-gcp-sig"
    assert client.calls[-1][0] == "asymmetric_sign"


def test_c4_gcp_verify_truthfully_unsupported_not_faked():
    """GCP KMS has no server-side verify RPC for all algorithms -- must fail truthfully,
    never fake a verification result."""
    provider, client = _gcp_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    with pytest.raises(KMSProviderUnavailableError):
        provider.verify(ref, b"message", b"signature")


def test_c4_gcp_permission_denied_and_throttling_propagate():
    provider, client = _gcp_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    client.next_error = FakeGCPError("PERMISSION_DENIED", "denied")
    with pytest.raises(FakeGCPError):
        provider.encrypt(ref, b"data")

    client.next_error = FakeGCPError("RESOURCE_EXHAUSTED", "quota exceeded")
    with pytest.raises(FakeGCPError):
        provider.decrypt(ref, b"ENC[x]")


def test_c4_gcp_revoke_key_updates_state():
    provider, client = _gcp_provider()
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    provider.revoke_key(ref)
    assert client.store[ref.key_id]["state"] == "DISABLED"


def test_c4_gcp_no_local_fallback():
    provider, client = _gcp_provider()
    assert not hasattr(provider, "keystore")


# ===========================================================================
# PKCS#11 HSM
# ===========================================================================

class SignatureInvalid(Exception):
    """
    Deliberately named to match pkcs11.exceptions.SignatureInvalid's class name --
    PKCS11HSMProvider.verify() distinguishes by exception class name (see production
    code comment) so this double exercises the exact same branch a real pkcs11
    SignatureInvalid would.
    """


class FakePKCS11GeneralError(Exception):
    """Models an unrelated HSM/session/mechanism error."""


class FakePKCS11Key:
    def __init__(self, label, secret=b"hsm-key-material"):
        self.label = label
        self._secret = secret  # never exposed via any public accessor
        self.next_verify_error = None
        self.next_sign_error = None

    def sign(self, message):
        if self.next_sign_error:
            err, self.next_sign_error = self.next_sign_error, None
            raise err
        return b"hsm-sig:" + message

    def verify(self, message, signature):
        if self.next_verify_error:
            err, self.next_verify_error = self.next_verify_error, None
            raise err
        if signature != b"hsm-sig:" + message:
            raise SignatureInvalid("signature does not match")
        return True

    def encrypt(self, plaintext):
        return b"HSM_ENC[" + plaintext + b"]"

    def decrypt(self, ciphertext):
        return ciphertext[8:-1]

    def destroy(self):
        pass


class FakePKCS11Session:
    def __init__(self, keys):
        self.keys = keys

    def generate_keypair(self, key_type, bits, label, store):
        key = FakePKCS11Key(label)
        self.keys[label] = key
        return key, key

    def generate_key(self, key_type, bits, label, store):
        key = FakePKCS11Key(label)
        self.keys[label] = key
        return key

    def get_objects(self, attrs):
        label = list(attrs.values())[0]
        return [self.keys[label]] if label in self.keys else []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakePKCS11Token:
    def __init__(self):
        self.keys = {}
        self.next_open_error = None

    def open(self, user_pin):
        if not user_pin:
            raise FakePKCS11GeneralError("missing PIN")
        if self.next_open_error:
            err, self.next_open_error = self.next_open_error, None
            raise err
        return FakePKCS11Session(self.keys)


def _pkcs11_provider(pin="1234"):
    token = FakePKCS11Token()
    provider = PKCS11HSMProvider(
        pkcs11_library_path="/usr/lib/softhsm/libsofthsm2.so",  # dynamic, operator-supplied -- not hardcoded truth
        token_label="akaal-token",
        user_pin_provider=lambda: pin,
        token=token,
    )
    return provider, token


def test_c4_pkcs11_generate_key_reports_hsm_backed_origin_and_dynamic_module_path():
    provider, token = _pkcs11_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    assert ref.origin == KeyOrigin.HSM_BACKED
    assert ref.provider == "PKCS11_HSM"
    assert provider.pkcs11_library_path  # operator-supplied, present, not baked as a fixed constant in source


def test_c4_pkcs11_no_hardcoded_module_or_token_label():
    with pytest.raises(ValueError):
        PKCS11HSMProvider(pkcs11_library_path="", token_label="", user_pin_provider=lambda: "1234")


def test_c4_pkcs11_pin_resolved_dynamically_never_hardcoded():
    provider, token = _pkcs11_provider(pin="")
    with pytest.raises(KMSProviderUnavailableError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)  # empty PIN fails closed


def test_c4_pkcs11_sign_verify_roundtrip_key_never_extracted():
    provider, token = _pkcs11_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    sig = provider.sign(ref, b"message")
    assert provider.verify(ref, b"message", sig) is True
    # No public accessor anywhere on KeyReference or the provider exposes raw key bytes.
    assert not hasattr(ref, "secret") and not hasattr(ref, "key_material")


def test_c4_pkcs11_genuine_signature_mismatch_returns_false():
    provider, token = _pkcs11_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    assert provider.verify(ref, b"message", b"totally-wrong-signature") is False


def test_c4_pkcs11_verify_session_error_propagates_not_collapsed_to_false():
    """Target-5-class fix applied to PKCS11 too: a session/device error during verify
    must not be silently reported as an invalid signature."""
    provider, token = _pkcs11_provider()
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    key = token.keys["akaal-execution_signing"]
    key.next_verify_error = FakePKCS11GeneralError("HSM device error / mechanism failure")
    with pytest.raises(FakePKCS11GeneralError):
        provider.verify(ref, b"message", b"some-signature")


def test_c4_pkcs11_missing_key_fails_closed():
    provider, token = _pkcs11_provider()
    from akaalPipeline.security.kms_provider import KeyReference
    fake_ref = KeyReference(provider="PKCS11_HSM", key_id="nonexistent-label", purpose=KeyPurpose.TOKEN_ENCRYPT)
    with pytest.raises(KeyNotFoundError):
        provider.sign(fake_ref, b"message")


def test_c4_pkcs11_wrong_pin_fails_closed():
    provider, token = _pkcs11_provider(pin="wrong-pin")
    token.next_open_error = FakePKCS11GeneralError("CKR_PIN_INCORRECT")
    with pytest.raises(FakePKCS11GeneralError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)


def test_c4_pkcs11_no_fallback_to_local_envelope_provider():
    provider, token = _pkcs11_provider()
    assert not hasattr(provider, "keystore")
    from akaalPipeline.security.kms_provider import LocalEnvelopeKMSProvider
    assert not isinstance(provider, LocalEnvelopeKMSProvider)
