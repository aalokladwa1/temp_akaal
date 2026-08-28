"""akaalPipeline.security.config
==============================
Versioned Security Baseline Configuration with immutable security floors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


class SecurityConfigValidationError(ValueError):
    """Raised when security configuration violates immutable baseline floors."""
    pass


@dataclass(frozen=True)
class SecurityBaselineConfig:
    """Configurable security baseline with immutable minimum floors."""

    version: str = "1.0.0"

    # Password / KDF Floors
    kdf_default_algorithm: str = "ARGON2ID"
    pbkdf2_iterations: int = 600000  # Floor: 600,000
    argon2_time_cost: int = 3        # Floor: 3
    argon2_memory_cost_kib: int = 65536  # Floor: 64MB (65536 KiB)
    argon2_parallelism: int = 4      # Floor: 4

    # Authentication & Lockout
    max_failed_logins: int = 5       # Bounds: 3 - 10
    lockout_duration_seconds: int = 900  # Bounds: 60s - 86400s (15m default)

    # Sessions
    session_idle_timeout_seconds: int = 1800      # Bounds: 300s - 7200s (30m default)
    session_absolute_timeout_seconds: int = 28800  # Bounds: 3600s - 86400s (8h default)

    # JIT Privilege & Tokens
    jit_max_duration_seconds: int = 14400         # Bounds: 300s - 28800s (4h default)
    execution_authorization_ttl_seconds: int = 3600  # Bounds: 60s - 86400s (1h default)

    # Key Lifecycle
    execution_key_rotation_days: int = 90         # Bounds: 1d - 365d
    audit_key_rotation_days: int = 180            # Bounds: 30d - 730d

    # Maximum Role Inheritance Depth (Cycle Protection)
    max_role_inheritance_depth: int = 10

    # Clock Skew & Rollback Floor
    clock_skew_threshold_seconds: float = 5.0  # Bounds: 0.1s - 60.0s

    def __post_init__(self) -> None:
        """Enforce immutable security floors and valid bounds."""
        if self.pbkdf2_iterations < 600000:
            raise SecurityConfigValidationError(
                f"pbkdf2_iterations={self.pbkdf2_iterations} is below immutable security floor of 600,000"
            )
        if self.argon2_time_cost < 3:
            raise SecurityConfigValidationError(
                f"argon2_time_cost={self.argon2_time_cost} is below immutable security floor of 3"
            )
        if self.argon2_memory_cost_kib < 65536:
            raise SecurityConfigValidationError(
                f"argon2_memory_cost_kib={self.argon2_memory_cost_kib} is below immutable floor of 64MB"
            )
        if self.argon2_parallelism < 1:
            raise SecurityConfigValidationError("argon2_parallelism must be >= 1")

        if not (1 <= self.max_failed_logins <= 20):
            raise SecurityConfigValidationError("max_failed_logins must be between 1 and 20")
        if not (10 <= self.lockout_duration_seconds <= 86400):
            raise SecurityConfigValidationError("lockout_duration_seconds must be between 10s and 86400s")
        if not (60 <= self.session_idle_timeout_seconds <= 86400):
            raise SecurityConfigValidationError("session_idle_timeout_seconds must be between 60s and 86400s")
        if not (60 <= self.session_absolute_timeout_seconds <= 604800):
            raise SecurityConfigValidationError("session_absolute_timeout_seconds must be between 60s and 604800s")
        if self.session_idle_timeout_seconds > self.session_absolute_timeout_seconds:
            raise SecurityConfigValidationError("session_idle_timeout cannot exceed session_absolute_timeout")

        if not (60 <= self.jit_max_duration_seconds <= 86400):
            raise SecurityConfigValidationError("jit_max_duration_seconds must be between 60s and 86400s")
        if not (10 <= self.execution_authorization_ttl_seconds <= 86400):
            raise SecurityConfigValidationError("execution_authorization_ttl_seconds must be between 10s and 86400s")

        if not (1 <= self.execution_key_rotation_days <= 365):
            raise SecurityConfigValidationError("execution_key_rotation_days must be between 1 and 365")
        if not (1 <= self.audit_key_rotation_days <= 730):
            raise SecurityConfigValidationError("audit_key_rotation_days must be between 1 and 730")
        if not (1 <= self.max_role_inheritance_depth <= 50):
            raise SecurityConfigValidationError("max_role_inheritance_depth must be between 1 and 50")
        if not (0.1 <= self.clock_skew_threshold_seconds <= 60.0):
            raise SecurityConfigValidationError("clock_skew_threshold_seconds must be between 0.1s and 60.0s")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "version": self.version,
            "kdf_default_algorithm": self.kdf_default_algorithm,
            "pbkdf2_iterations": self.pbkdf2_iterations,
            "argon2_time_cost": self.argon2_time_cost,
            "argon2_memory_cost_kib": self.argon2_memory_cost_kib,
            "argon2_parallelism": self.argon2_parallelism,
            "max_failed_logins": self.max_failed_logins,
            "lockout_duration_seconds": self.lockout_duration_seconds,
            "session_idle_timeout_seconds": self.session_idle_timeout_seconds,
            "session_absolute_timeout_seconds": self.session_absolute_timeout_seconds,
            "jit_max_duration_seconds": self.jit_max_duration_seconds,
            "execution_authorization_ttl_seconds": self.execution_authorization_ttl_seconds,
            "execution_key_rotation_days": self.execution_key_rotation_days,
            "audit_key_rotation_days": self.audit_key_rotation_days,
            "max_role_inheritance_depth": self.max_role_inheritance_depth,
            "clock_skew_threshold_seconds": self.clock_skew_threshold_seconds,
        }
