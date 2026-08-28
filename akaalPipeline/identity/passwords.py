"""akaalPipeline.identity.passwords
================================
Salted adaptive password authentication engine supporting Argon2id and PBKDF2-SHA256.
Enforces constant-time verification, versioned credential envelopes, and strict fail-closed dependency checks.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict, Optional, Tuple
from akaal.core.crypto_random import generate_salt, generate_salt_hex
from akaalPipeline.contracts.enums import KDFAlgorithm
from akaalPipeline.security.config import SecurityBaselineConfig

try:
    import argon2
    import argon2.exceptions
    HAS_ARGON2 = True
except ImportError:
    HAS_ARGON2 = False


class CryptographicDependencyError(RuntimeError):
    """Raised when a configured cryptographic algorithm library is missing."""
    pass


class PasswordAuthenticationEngine:
    """Canonical password hashing, verification, and upgrade evaluator."""

    def __init__(self, config: Optional[SecurityBaselineConfig] = None) -> None:
        self.config = config or SecurityBaselineConfig()

    def hash_password(
        self,
        password: str,
        algorithm: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any], str, str]:
        """
        Hash password according to algorithm and baseline floors.
        Returns: (algorithm, kdf_params, salt_hex, password_hash_hex)
        """
        if not password:
            raise ValueError("Password cannot be empty")

        algo = algorithm or self.config.kdf_default_algorithm

        if algo == KDFAlgorithm.ARGON2ID.value:
            if not HAS_ARGON2:
                raise CryptographicDependencyError("argon2-cffi library is required for ARGON2ID hashing")

            time_cost = (custom_params or {}).get("time_cost", self.config.argon2_time_cost)
            memory_cost = (custom_params or {}).get("memory_cost", self.config.argon2_memory_cost_kib)
            parallelism = (custom_params or {}).get("parallelism", self.config.argon2_parallelism)

            if time_cost < 3 or memory_cost < 65536 or parallelism < 1:
                raise ValueError("Argon2id parameters below immutable security floors")

            salt = generate_salt(16)
            ph = argon2.PasswordHasher(
                time_cost=time_cost,
                memory_cost=memory_cost,
                parallelism=parallelism,
                hash_len=32,
                salt_len=16,
                type=argon2.Type.ID,
            )
            # Hash directly with argon2
            raw_hash = ph.hash(password)
            kdf_params = {
                "time_cost": time_cost,
                "memory_cost_kib": memory_cost,
                "parallelism": parallelism,
                "hash_len": 32,
            }
            return (KDFAlgorithm.ARGON2ID.value, kdf_params, salt.hex(), raw_hash)

        elif algo == KDFAlgorithm.PBKDF2_SHA256.value:
            iterations = (custom_params or {}).get("iterations", self.config.pbkdf2_iterations)
            if iterations < 600000:
                raise ValueError("PBKDF2 iterations below immutable floor of 600,000")

            salt = generate_salt(16)
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations,
                dklen=32,
            )
            kdf_params = {"iterations": iterations, "hash_algorithm": "sha256", "dklen": 32}
            return (KDFAlgorithm.PBKDF2_SHA256.value, kdf_params, salt.hex(), derived.hex())

        else:
            raise ValueError(f"Unsupported KDF algorithm: {algo!r}")

    def verify_password(
        self,
        password: str,
        algorithm: str,
        kdf_params: Dict[str, Any],
        salt_hex: str,
        stored_hash: str,
    ) -> bool:
        """
        Verify password against stored parameters using constant-time comparisons.
        Fails closed on any dependency error or parameter mismatch.
        """
        if not password:
            return False

        if algorithm == KDFAlgorithm.ARGON2ID.value:
            if not HAS_ARGON2:
                raise CryptographicDependencyError("argon2-cffi library is required for ARGON2ID verification")
            try:
                time_cost = kdf_params.get("time_cost", self.config.argon2_time_cost)
                memory_cost = kdf_params.get("memory_cost_kib", self.config.argon2_memory_cost_kib)
                parallelism = kdf_params.get("parallelism", self.config.argon2_parallelism)
                ph = argon2.PasswordHasher(
                    time_cost=time_cost,
                    memory_cost=memory_cost,
                    parallelism=parallelism,
                    hash_len=32,
                    salt_len=16,
                    type=argon2.Type.ID,
                )
                return ph.verify(stored_hash, password)
            except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
                return False
            except Exception as exc:
                raise CryptographicDependencyError(f"Argon2 verification failed: {exc}") from exc

        elif algorithm == KDFAlgorithm.PBKDF2_SHA256.value:
            try:
                salt = bytes.fromhex(salt_hex)
                iterations = kdf_params.get("iterations", self.config.pbkdf2_iterations)
                derived = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt,
                    iterations,
                    dklen=32,
                )
                return hmac.compare_digest(derived.hex(), stored_hash)
            except Exception:
                return False

        else:
            raise ValueError(f"Unrecognized algorithm in credential envelope: {algorithm!r}")
