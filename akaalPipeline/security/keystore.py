"""akaalPipeline.security.keystore
================================
Canonical Cryptographic KeyStore Authority managing Master Root Key, Ed25519, HMAC, and AES keys.
Enforces purpose separation, fail-closed operator recovery ceremonies, and key lifecycles.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple
from akaal.core.crypto_random import generate_secure_id, secure_random_bytes
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import KeyAlgorithm, KeyPurpose, KeyStatus
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import SQLiteKeyringRepository
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class MasterRootKeyMissingError(RuntimeError):
    """Raised when the Master Root Key is missing or invalid."""
    pass


class KeyPurposeMismatchError(ValueError):
    """Raised when an operation attempts to use a key for an unassigned purpose."""
    pass


class KeyNotFoundError(ValueError):
    """Raised when a requested key ID does not exist."""
    pass


class KeyRevokedError(ValueError):
    """Raised when attempting to use a revoked key."""
    pass


class KeyStoreAuthority:
    """Canonical cryptographic authority for key lifecycle and operations."""

    def __init__(
        self,
        keyring_repo: SQLiteKeyringRepository,
        master_root_key: Optional[bytes] = None,
        config: Optional[SecurityBaselineConfig] = None,
    ) -> None:
        self.keyring_repo = keyring_repo
        self.config = config or SecurityBaselineConfig()
        self._mrk = self._resolve_mrk(master_root_key)

    def _resolve_mrk(self, injected_mrk: Optional[bytes]) -> bytes:
        if injected_mrk:
            if len(injected_mrk) != 32:
                raise MasterRootKeyMissingError("Injected Master Root Key must be exactly 32 bytes")
            return injected_mrk

        env_val = os.getenv("AKAAL_MASTER_ROOT_KEY")
        if env_val:
            try:
                mrk_bytes = bytes.fromhex(env_val)
                if len(mrk_bytes) != 32:
                    raise ValueError
                return mrk_bytes
            except Exception as exc:
                raise MasterRootKeyMissingError("AKAAL_MASTER_ROOT_KEY env var must be 64 hex characters (32 bytes)") from exc

        raise MasterRootKeyMissingError(
            "Master Root Key is missing. Refusing silent generation. Provide AKAAL_MASTER_ROOT_KEY or operator recovery key."
        )

    def _encrypt_blob(self, plaintext: bytes) -> bytes:
        """Encrypt private key material using MRK and AES-256-GCM."""
        aesgcm = AESGCM(self._mrk)
        nonce = secure_random_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def _decrypt_blob(self, encrypted_blob: bytes) -> bytes:
        """Decrypt private key material using MRK and AES-256-GCM."""
        if len(encrypted_blob) < 28:
            raise ValueError("Encrypted key blob too short")
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        aesgcm = AESGCM(self._mrk)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def initialize_purpose_keys_if_missing(self) -> None:
        """Initialize missing default keys for each required purpose."""
        for purpose in [KeyPurpose.EXECUTION_SIGNING, KeyPurpose.AUDIT_SEAL]:
            existing = self.keyring_repo.get_active_key(purpose.value)
            if not existing:
                self.generate_and_save_key(purpose, KeyAlgorithm.ED25519)

        for purpose in [KeyPurpose.TOKEN_ENCRYPT]:
            existing = self.keyring_repo.get_active_key(purpose.value)
            if not existing:
                self.generate_and_save_key(purpose, KeyAlgorithm.AES_256_GCM)

        for purpose in [KeyPurpose.RECEIPT_SIGNING]:
            existing = self.keyring_repo.get_active_key(purpose.value)
            if not existing:
                self.generate_and_save_key(purpose, KeyAlgorithm.HMAC_SHA256)

    def generate_and_save_key(
        self,
        purpose: KeyPurpose,
        algorithm: KeyAlgorithm,
    ) -> str:
        """Generate a new purpose-separated key pair and persist encrypted in keyring."""
        key_id = generate_secure_id("key")
        now_iso = TimeAuthority.utc_iso_now()

        if algorithm == KeyAlgorithm.ED25519:
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            encrypted_blob = self._encrypt_blob(private_bytes)

            self.keyring_repo.save_key(
                key_id=key_id,
                purpose=purpose.value,
                algorithm=algorithm.value,
                public_key_pem=public_pem,
                encrypted_private_key_blob=encrypted_blob,
                status=KeyStatus.ACTIVE.value,
                version=1,
                created_at=now_iso,
            )
            return key_id

        elif algorithm in (KeyAlgorithm.AES_256_GCM, KeyAlgorithm.HMAC_SHA256):
            secret_bytes = secure_random_bytes(32)
            encrypted_blob = self._encrypt_blob(secret_bytes)

            self.keyring_repo.save_key(
                key_id=key_id,
                purpose=purpose.value,
                algorithm=algorithm.value,
                public_key_pem=None,
                encrypted_private_key_blob=encrypted_blob,
                status=KeyStatus.ACTIVE.value,
                version=1,
                created_at=now_iso,
            )
            return key_id

        raise ValueError(f"Unsupported key algorithm: {algorithm!r}")

    def get_signing_key_ed25519(self, purpose: KeyPurpose) -> Tuple[str, ed25519.Ed25519PrivateKey]:
        """Get active Ed25519 private signing key for a specific purpose."""
        key_record = self.keyring_repo.get_active_key(purpose.value)
        if not key_record:
            raise KeyNotFoundError(f"No active key found for purpose {purpose.value!r}")

        if key_record["purpose"] != purpose.value:
            raise KeyPurposeMismatchError(f"Key {key_record['key_id']!r} is not for purpose {purpose.value!r}")

        if key_record.get("algorithm") != KeyAlgorithm.ED25519.value:
            raise KeyPurposeMismatchError(f"Key {key_record['key_id']!r} algorithm is {key_record.get('algorithm')!r}, not ED25519")

        if key_record["status"] != KeyStatus.ACTIVE.value:
            raise KeyRevokedError(f"Key {key_record['key_id']!r} is not ACTIVE (status={key_record['status']})")

        raw_private = self._decrypt_blob(key_record["encrypted_private_key_blob"])
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_private)
        return key_record["key_id"], priv_key

    def get_key_for_purpose(self, key_id: str, expected_purpose: KeyPurpose) -> Dict[str, Any]:
        """Fetch a specific key and strictly enforce purpose match."""
        key_record = self.keyring_repo.get_key_by_id(key_id)
        if not key_record:
            raise KeyNotFoundError(f"Key {key_id!r} not found in keyring")
        if key_record["purpose"] != expected_purpose.value:
            raise KeyPurposeMismatchError(
                f"Key {key_id!r} purpose is {key_record['purpose']!r}, expected {expected_purpose.value!r}"
            )
        return key_record

    def get_public_key_pem(self, key_id: str) -> str:
        """Get public key PEM for verification."""
        key_record = self.keyring_repo.get_key_by_id(key_id)
        if not key_record:
            raise KeyNotFoundError(f"Key {key_id!r} not found in keyring")
        if not key_record["public_key_pem"]:
            raise ValueError(f"Key {key_id!r} has no public key PEM")
        return key_record["public_key_pem"]

    def rotate_key(self, purpose: KeyPurpose) -> str:
        """Retire active key and generate a new versioned key."""
        old_active = self.keyring_repo.get_active_key(purpose.value)
        now_iso = TimeAuthority.utc_iso_now()
        if old_active:
            self.keyring_repo.retire_key(old_active["key_id"], now_iso)

        algo = KeyAlgorithm(old_active["algorithm"]) if old_active else KeyAlgorithm.ED25519
        return self.generate_and_save_key(purpose, algo)

    def revoke_key(self, key_id: str, reason: Optional[str] = None) -> None:
        """Revoke a specific key."""
        now_iso = TimeAuthority.utc_iso_now()
        self.keyring_repo.revoke_key(key_id, now_iso)

    def verify_signature_ed25519(self, key_id: str, message: bytes, signature: bytes) -> bool:
        """
        Verify an Ed25519 signature against message bytes using the stored public key.
        Fails closed (raises KeyRevokedError) if the key is not ACTIVE.
        Raises KeyNotFoundError if the key does not exist.
        Raises cryptography.exceptions.InvalidSignature on bad signature.
        """
        from cryptography.exceptions import InvalidSignature
        key_record = self.keyring_repo.get_key_by_id(key_id)
        if not key_record:
            raise KeyNotFoundError(f"Key {key_id!r} not found in keyring")
        if key_record["status"] != KeyStatus.ACTIVE.value:
            raise KeyRevokedError(
                f"Key {key_id!r} is not ACTIVE (status={key_record['status']}). "
                "Signature verification blocked on revoked key."
            )
        public_pem = key_record.get("public_key_pem")
        if not public_pem:
            raise KeyPurposeMismatchError(f"Key {key_id!r} has no public key PEM for Ed25519 verification")
        public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise KeyPurposeMismatchError(f"Key {key_id!r} is not an Ed25519 public key")
        public_key.verify(signature, message)  # raises InvalidSignature if mismatch
        return True
