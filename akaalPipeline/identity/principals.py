"""akaalPipeline.identity.principals
==================================
Canonical principal management authority handling lifecycle, lockout counters, and authentication.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import PrincipalType
from akaalPipeline.identity.passwords import PasswordAuthenticationEngine
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import (
    SQLiteCredentialRepository,
    SQLitePrincipalRepository,
)


class PrincipalNotFoundError(ValueError):
    pass


class PrincipalDisabledError(ValueError):
    pass


class PrincipalLockedError(ValueError):
    pass


class AuthenticationFailedError(ValueError):
    pass


class PrincipalManager:
    """Canonical authority managing enterprise principal lifecycles and authentication."""

    def __init__(
        self,
        principal_repo: SQLitePrincipalRepository,
        credential_repo: SQLiteCredentialRepository,
        config: Optional[SecurityBaselineConfig] = None,
        password_engine: Optional[PasswordAuthenticationEngine] = None,
    ) -> None:
        self.principal_repo = principal_repo
        self.credential_repo = credential_repo
        self.config = config or SecurityBaselineConfig()
        self.password_engine = password_engine or PasswordAuthenticationEngine(self.config)

    def create_principal(
        self,
        tenant_id: str,
        username: str,
        principal_type: PrincipalType = PrincipalType.HUMAN,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new durable enterprise principal with optional password credential."""
        if not tenant_id or not username:
            raise ValueError("tenant_id and username are required")

        existing = self.principal_repo.get_by_username(tenant_id, username)
        if existing:
            raise ValueError(f"Principal with username {username!r} already exists in tenant {tenant_id!r}")

        principal_id = generate_secure_id("usr")
        now_iso = TimeAuthority.utc_iso_now()
        ptype_str = principal_type.value if hasattr(principal_type, "value") else str(principal_type)

        created = self.principal_repo.create(
            tenant_id=tenant_id,
            principal_id=principal_id,
            principal_type=ptype_str,
            username=username,
            display_name=display_name,
            email=email,
            metadata=metadata,
            created_at=now_iso,
        )

        if password and ptype_str == PrincipalType.HUMAN.value:
            self.set_password(tenant_id, principal_id, password)

        return created

    def set_password(self, tenant_id: str, principal_id: str, password: str) -> None:
        """Hash and persist password credential envelope."""
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal:
            raise PrincipalNotFoundError(f"Principal {principal_id!r} not found in tenant {tenant_id!r}")

        algo, kdf_params, salt_hex, pwd_hash = self.password_engine.hash_password(password)
        cred_id = generate_secure_id("crd")
        now_iso = TimeAuthority.utc_iso_now()

        self.credential_repo.save_credential(
            credential_id=cred_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            kdf_algorithm=algo,
            kdf_params=kdf_params,
            salt_hex=salt_hex,
            password_hash_hex=pwd_hash,
            version=1,
            created_at=now_iso,
        )
        self.principal_repo.bump_security_revision(tenant_id, principal_id, now_iso)

    def disable_principal(self, tenant_id: str, principal_id: str) -> None:
        """Administratively disable a principal."""
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal:
            raise PrincipalNotFoundError(f"Principal {principal_id!r} not found in tenant {tenant_id!r}")
        now_iso = TimeAuthority.utc_iso_now()
        self.principal_repo.disable(tenant_id, principal_id, now_iso)

    def authenticate_human(self, tenant_id: str, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a human principal against durable credentials.
        Enforces abuse lockout counters, timing-safe checks, and fail-closed errors.
        """
        principal = self.principal_repo.get_by_username(tenant_id, username)
        if not principal:
            # Timing equalizing synthetic baseline check
            self.password_engine.verify_password(password, "PBKDF2_SHA256", {"iterations": 600000}, "00" * 16, "00" * 32)
            raise AuthenticationFailedError("Invalid username or password")

        principal_id = principal["principal_id"]

        if not principal["is_active"]:
            raise PrincipalDisabledError(f"Principal {username!r} is disabled")

        now = TimeAuthority.utc_now()

        # Check lockout
        if principal["is_locked"]:
            locked_until_str = principal.get("locked_until")
            if locked_until_str:
                locked_until = TimeAuthority.parse_iso(locked_until_str)
                if now < locked_until:
                    raise PrincipalLockedError(f"Account locked until {locked_until_str} due to excessive failed attempts")

        cred = self.credential_repo.get_active_credential(tenant_id, principal_id)
        if not cred:
            raise AuthenticationFailedError("No active credentials configured for principal")

        is_valid = self.password_engine.verify_password(
            password=password,
            algorithm=cred["kdf_algorithm"],
            kdf_params=cred["kdf_params"],
            salt_hex=cred["salt_hex"],
            stored_hash=cred["password_hash_hex"],
        )

        now_iso = now.isoformat()

        if is_valid:
            self.principal_repo.record_successful_login(tenant_id, principal_id, now_iso)
            return self.principal_repo.get_by_id(tenant_id, principal_id)  # type: ignore

        # Failed login
        lockout_until_dt = now + timedelta(seconds=self.config.lockout_duration_seconds)
        fails = self.principal_repo.record_failed_login(
            tenant_id=tenant_id,
            principal_id=principal_id,
            max_failures=self.config.max_failed_logins,
            lockout_until_iso=lockout_until_dt.isoformat(),
            updated_at=now_iso,
        )

        if fails >= self.config.max_failed_logins:
            raise PrincipalLockedError(
                f"Account locked until {lockout_until_dt.isoformat()} after {fails} consecutive failed attempts"
            )

        raise AuthenticationFailedError("Invalid username or password")

    authenticate = authenticate_human
