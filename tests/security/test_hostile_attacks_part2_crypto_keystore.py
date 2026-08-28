"""tests.security.test_hostile_attacks_part2_crypto_keystore
==========================================================
Hostile Security Verification Suite - Part 2: Cryptography & KeyStore Authorities
Contains Hostile Attack Scenarios HOSTILE-ATK-15 through HOSTILE-ATK-26.
"""

import pytest
import time
from datetime import datetime, timezone
from akaal.core.crypto_random import generate_secure_random_bytes, generate_secure_token
from akaal.core.time_authority import TimeAuthority, ClockSkewDetectedError
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.security.keystore import (
    KeyStoreAuthority,
    MasterRootKeyMissingError,
    KeyPurposeMismatchError,
    KeyRevokedError,
    KeyNotFoundError,
)
from akaalPipeline.identity.passwords import PasswordAuthenticationEngine
from akaalPipeline.security.bootstrap import EnterpriseBootstrapCoordinator
from akaalPipeline.contracts.enums import KeyPurpose, KeyStatus, KDFAlgorithm
from akaalPipeline.contracts.errors import ConflictError


@pytest.fixture
def uow(tmp_path):
    db_path = str(tmp_path / "akaal_hostile_crypto.db")
    uow_inst = SQLiteUnitOfWork(db_path)
    uow_inst.initialize_schema()
    return uow_inst


def test_hostile_atk_15_csprng_entropy_output():
    """HOSTILE-ATK-15: Verify OS CSPRNG entropy produces 256-bit distinct non-repeating samples."""
    samples = set()
    for _ in range(100):
        t = generate_secure_token(32)
        assert len(t) == 64
        assert t not in samples
        samples.add(t)


def test_hostile_atk_16_clock_rollback_detection():
    """HOSTILE-ATK-16: Detect backward wall clock step >= 5.0 seconds and raise ClockSkewDetectedError."""
    TimeAuthority._last_wall_utc_ts = 1000000.0
    TimeAuthority._last_monotonic_ts = 100.0
    TimeAuthority.set_clock_skew_threshold(5.0)
    
    # Simulate wall clock rolling backwards by 10 seconds
    try:
        TimeAuthority._last_wall_utc_ts = time.time() + 100.0
        with pytest.raises(ClockSkewDetectedError, match="Wall clock rollback detected"):
            TimeAuthority.utc_now()
    finally:
        TimeAuthority._last_wall_utc_ts = 0.0


def test_hostile_atk_17_missing_or_invalid_master_root_key(uow):
    """HOSTILE-ATK-17: KeyStoreAuthority initialization with missing or malformed MRK must fail closed."""
    with pytest.raises(MasterRootKeyMissingError):
        KeyStoreAuthority(uow.keyring, master_root_key=b"")

    with pytest.raises(MasterRootKeyMissingError, match="Master Root Key must be exactly 32 bytes"):
        KeyStoreAuthority(uow.keyring, master_root_key=b"short_key")


def test_hostile_atk_18_key_purpose_separation_violation(uow):
    """HOSTILE-ATK-18: Attempt to use an EXECUTION_SIGNING key for AUDIT_SEAL or TOKEN_ENCRYPT."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    ks.initialize_purpose_keys_if_missing()
    key_id, _ = ks.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
    
    # Attempting to load an execution key for audit HMAC or token decrypt must fail closed
    with pytest.raises((KeyPurposeMismatchError, ValueError)):
        ks.get_signing_key_ed25519(KeyPurpose.TOKEN_ENCRYPT)


def test_hostile_atk_19_key_rotation_and_old_key_retirement(uow):
    """HOSTILE-ATK-19: Rotate key and verify previous active key is retired."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    ks.initialize_purpose_keys_if_missing()
    key_id_1, _ = ks.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
    
    # Rotate
    key_id_2 = ks.rotate_key(KeyPurpose.EXECUTION_SIGNING)
    assert key_id_1 != key_id_2
    
    # Verify old key is RETIRED
    old_key = uow.keyring.get_key(key_id_1)
    assert old_key["status"] == KeyStatus.RETIRED.value


def test_hostile_atk_20_revoked_key_rejection(uow):
    """HOSTILE-ATK-20: Attempt to use an explicitly revoked cryptographic key."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    ks.initialize_purpose_keys_if_missing()
    key_id, _ = ks.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
    
    # Revoke
    ks.revoke_key(key_id, reason="Compromise suspected")
    
    with pytest.raises((KeyRevokedError, KeyNotFoundError)):
        ks.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)


def test_hostile_atk_21_master_root_key_envelope_tampering(uow):
    """HOSTILE-ATK-21: Tamper with encrypted private key blob in keyring DB."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    ks.initialize_purpose_keys_if_missing()
    key_id, _ = ks.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
    
    # Corrupt private key ciphertext in SQLite directly
    uow.conn.execute(
        "UPDATE security_keyring SET encrypted_private_key_blob = X'DEADBEEFCAFEBABE' WHERE key_id = ?",
        (key_id,),
    )
    
    # Next retrieval must fail closed on AES-GCM decryption
    with pytest.raises(Exception):
        ks_new = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
        ks_new.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)


def test_hostile_atk_22_enterprise_bootstrap_idempotency_and_second_run_blocking(uow):
    """HOSTILE-ATK-22: Execute enterprise bootstrap twice to verify second run is strictly rejected."""
    mrk = b"01234567890123456789012345678901"
    coord = EnterpriseBootstrapCoordinator(uow, master_root_key=mrk)
    
    # First bootstrap
    res1 = coord.bootstrap_enterprise(admin_username="admin", admin_email="admin@corp.com", admin_password="Password123!")
    assert res1["status"] == "BOOTSTRAP_COMPLETED"
    
    # Second bootstrap attempt must raise ConflictError
    with pytest.raises(ConflictError, match="Enterprise security foundation is already bootstrapped"):
        coord.bootstrap_enterprise(admin_username="admin2", admin_email="admin2@corp.com", admin_password="Password123!")


def test_hostile_atk_23_jit_credential_vault_access():
    """HOSTILE-ATK-23: Test canonical InProcessCredentialVault zero-knowledge secret isolation."""
    from akaal.core.credential_vault import InProcessCredentialVault
    vault = InProcessCredentialVault()
    secret_ref = vault.store_secret("pg_password", "SuperSecretPass99!")
    
    # Retrieval
    val = vault.get_secret(secret_ref)
    assert val["password"] == "SuperSecretPass99!"
    
    # Invalid ref must raise RuntimeError in fail_closed mode
    with pytest.raises(RuntimeError):
        vault.get_secret("ref-invalid-random")


def test_hostile_atk_24_jit_credential_vault_eviction():
    """HOSTILE-ATK-24: Evict secret from InProcessCredentialVault and ensure subsequent access fails."""
    from akaal.core.credential_vault import InProcessCredentialVault
    vault = InProcessCredentialVault()
    secret_ref = vault.store_secret("oracle_password", "OraclePass123!")
    vault.evict_secret(secret_ref)
    with pytest.raises(RuntimeError):
        vault.get_secret(secret_ref)


def test_hostile_atk_25_argon2id_high_memory_compliance():
    """HOSTILE-ATK-25: Argon2id hashing must enforce minimum 64MB memory cost."""
    engine = PasswordAuthenticationEngine()
    algo, params, salt, pw_hash = engine.hash_password("ComplexPass123!", algorithm=KDFAlgorithm.ARGON2ID.value)
    assert params["memory_cost_kib"] >= 65536
    assert params["time_cost"] >= 3


def test_hostile_atk_26_pbkdf2_iteration_floor_compliance():
    """HOSTILE-ATK-26: PBKDF2 hashing must enforce minimum 600,000 iterations."""
    engine = PasswordAuthenticationEngine()
    algo, params, salt, pw_hash = engine.hash_password("ComplexPass123!", algorithm=KDFAlgorithm.PBKDF2_SHA256.value)
    assert params["iterations"] >= 600000
