"""
tests.unit.engine_fabric.test_p7b_round5_secrets_deep_hostile
==================================================================
P7B Group-1 Hostile Closure Round 5 -- secrets deep hostile matrix, extending Round 2/4.

Covers: rotated/revoked secret versions, nested SDK exceptions carrying credential-
shaped text, oversized/binary secret values, and additional Kubernetes path-traversal
variants (Windows-style backslash traversal, symlink escape).
"""

from __future__ import annotations

import os

import pytest

from akaalEngine.connection.security.providers.aws_secrets_manager import (
    AWSSecretsManagerConfig, AWSSecretsManagerError, AWSSecretsManagerProvider,
)
from akaalEngine.connection.security.providers.kubernetes_secret_ref import (
    KubernetesSecretRefConfig, KubernetesSecretRefError, KubernetesSecretRefProvider,
)
from akaalEngine.connection.security.redaction import redact_text


class _FakeAWSClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def get_secret_value(self, SecretId):
        if self._exc:
            raise self._exc
        return self._response


def test_nested_sdk_exception_containing_token_never_leaks_through_normalize():
    """A realistic nested botocore-shaped exception whose __str__ embeds what looks
    like a real token must still be fully redacted."""
    nested_exc = Exception("ClientError: An error occurred (AccessDenied) when calling GetSecretValue: token=AQICAHhSUPERSECRETTOKENVALUE1234 access_key=AKIAEXAMPLE")
    client = _FakeAWSClient(exc=nested_exc)
    provider = AWSSecretsManagerProvider(client=client)
    with pytest.raises(AWSSecretsManagerError) as exc_info:
        provider.resolve("x")
    assert "AQICAHhSUPERSECRETTOKENVALUE1234" not in str(exc_info.value)


def test_oversized_secret_value_does_not_crash_resolution():
    """A pathologically large secret value (simulating a misconfigured secret storing a
    multi-MB blob) must still resolve without crashing -- bounded-memory handling is the
    caller's concern once resolved, but resolution itself must not choke."""
    huge_value = "A" * (5 * 1024 * 1024)  # 5MB
    client = _FakeAWSClient(response={"SecretString": huge_value, "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x"})
    provider = AWSSecretsManagerProvider(client=client)
    resolved = provider.resolve("x")
    assert len(resolved) == 5 * 1024 * 1024


def test_binary_secret_value_handled_without_corruption():
    binary_payload = bytes(range(256)) * 100
    client = _FakeAWSClient(response={"SecretBinary": binary_payload, "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x"})
    provider = AWSSecretsManagerProvider(client=client)
    resolved = provider.resolve("x")
    assert isinstance(resolved, str)  # decoded, never raises on arbitrary byte content


def test_rotated_secret_returns_new_value_transparently():
    """Simulates a secret rotation: two sequential resolutions against a client whose
    underlying value has changed return the NEW value both times -- no stale caching
    inside the provider itself (caching, if any, is SecretConsumer's TTL-bounded
    responsibility, not this provider's)."""
    class _RotatingClient:
        def __init__(self):
            self.calls = 0

        def get_secret_value(self, SecretId):
            self.calls += 1
            value = "old-value-v1" if self.calls == 1 else "new-value-v2-after-rotation"
            return {"SecretString": value, "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x"}

    client = _RotatingClient()
    provider = AWSSecretsManagerProvider(client=client)
    first = provider.resolve("x")
    second = provider.resolve("x")
    assert first == "old-value-v1"
    assert second == "new-value-v2-after-rotation"
    assert first != second


# ---------------------------------------------------------------------------
# Kubernetes: additional path-traversal variants
# ---------------------------------------------------------------------------

def test_windows_style_backslash_traversal_blocked(tmp_path):
    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(tmp_path),)))
    with pytest.raises(KubernetesSecretRefError):
        provider.resolve("..\\..\\..\\windows\\system32\\config\\sam")


def test_absolute_path_reference_blocked(tmp_path):
    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(tmp_path),)))
    with pytest.raises(KubernetesSecretRefError):
        provider.resolve("/etc/passwd")


def test_symlink_escape_blocked(tmp_path):
    """Round-6 closure: a secret file that is a SYMLINK pointing outside the allowed
    mount root must NOT be readable through it. The literal reference string resolves
    INSIDE the allowed root (it isn't a traversal string), but the provider now also
    resolves the real (symlink-followed) destination and rejects it when that lands
    outside the allowlist."""
    outside_dir = tmp_path.parent / "outside_secret_area"
    outside_dir.mkdir(exist_ok=True)
    secret_target = outside_dir / "real_system_secret.txt"
    secret_target.write_text("SHOULD_NOT_BE_READABLE_VIA_SYMLINK")

    mount_root = tmp_path / "mount"
    mount_root.mkdir()
    symlink_path = mount_root / "innocuous-looking-secret"
    try:
        os.symlink(str(secret_target), str(symlink_path))
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this sandbox (requires elevated privileges on Windows)")

    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(mount_root),)))
    with pytest.raises(KubernetesSecretRefError):
        provider.resolve("innocuous-looking-secret")


def test_nested_symlink_chain_escape_blocked(tmp_path):
    """A multi-hop symlink chain (inside-root -> inside-root -> outside-root) must also
    be caught -- os.path.realpath follows the ENTIRE chain, not just one hop."""
    outside_dir = tmp_path.parent / "outside_secret_area_nested"
    outside_dir.mkdir(exist_ok=True)
    secret_target = outside_dir / "real_system_secret.txt"
    secret_target.write_text("SHOULD_NOT_BE_READABLE_VIA_NESTED_SYMLINK")

    mount_root = tmp_path / "mount_nested"
    mount_root.mkdir()
    hop1 = mount_root / "hop1"
    hop2 = mount_root / "hop2-innocuous-secret"
    try:
        os.symlink(str(secret_target), str(hop1))
        os.symlink(str(hop1), str(hop2))
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this sandbox (requires elevated privileges on Windows)")

    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(mount_root),)))
    with pytest.raises(KubernetesSecretRefError):
        provider.resolve("hop2-innocuous-secret")


def test_legitimate_symlink_within_allowed_root_still_works(tmp_path):
    """The fix must not be so strict that a symlink whose target is ALSO inside the
    allowed root (a legitimate pattern -- e.g. Kubernetes' own `..data` symlink
    convention for atomic secret updates) is rejected."""
    mount_root = tmp_path / "mount_legit"
    mount_root.mkdir()
    real_dir = mount_root / "..2024_01_01_00_00_00.123456789"
    real_dir.mkdir()
    real_file = real_dir / "password"
    real_file.write_text("legit-value")

    symlink_path = mount_root / "password"
    try:
        os.symlink(str(real_file), str(symlink_path))
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this sandbox (requires elevated privileges on Windows)")

    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(mount_root),)))
    assert provider.resolve("password") == "legit-value"


def test_null_byte_injection_in_reference_blocked(tmp_path):
    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(tmp_path),)))
    with pytest.raises((KubernetesSecretRefError, ValueError)):
        provider.resolve("valid-looking-secret\x00/../../etc/passwd")


def test_symlink_escape_realpath_check_unit_proven_without_requiring_os_symlink_privilege(tmp_path, monkeypatch):
    """This sandbox's Windows environment requires elevated privileges to create real
    symlinks (the tests above correctly skip when that fails), so this test proves the
    SAME realpath-boundary-check logic directly by monkeypatching os.path.realpath to
    return exactly what a real symlink resolution to an outside-the-root target would --
    giving genuine, unskipped coverage of the actual guard logic in this sandbox."""
    mount_root = tmp_path / "mount"
    mount_root.mkdir()
    (mount_root / "looks-legit").write_text("placeholder")  # must exist for os.path.isfile, if reached

    real_target_outside = str(tmp_path.parent / "definitely_outside" / "secret")

    import os as os_module
    original_realpath = os_module.path.realpath

    def fake_realpath(path):
        if path.endswith("looks-legit"):
            return real_target_outside  # simulate: this path is actually a symlink to outside the root
        return original_realpath(path)

    monkeypatch.setattr(os_module.path, "realpath", fake_realpath)

    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(mount_root),)))
    with pytest.raises(KubernetesSecretRefError, match="symlink-escape guard"):
        provider.resolve("looks-legit")


def test_realpath_check_allows_a_path_whose_real_destination_is_still_inside_root(tmp_path, monkeypatch):
    """Converse of the above: when the (simulated) real destination is still inside the
    allowed root, resolution proceeds normally -- the fix is not overly strict."""
    mount_root = tmp_path / "mount"
    mount_root.mkdir()
    real_file = mount_root / "actual-file"
    real_file.write_text("real-value")
    (mount_root / "alias").write_text("placeholder")

    import os as os_module
    original_realpath = os_module.path.realpath

    def fake_realpath(path):
        if path.endswith("alias"):
            return str(real_file)  # simulate: "alias" is a symlink to "actual-file", still inside root
        return original_realpath(path)

    monkeypatch.setattr(os_module.path, "realpath", fake_realpath)

    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(mount_root),)))
    # resolve() opens the LITERAL path ("alias"), which genuinely exists as a real file
    # here (the placeholder) -- the realpath check only gates whether it's ALLOWED, and
    # since the simulated real destination is inside the root, it is allowed.
    assert provider.resolve("alias") == "placeholder"
