"""akaalPipeline.identity.sessions
================================
Canonical durable session management authority enforcing absolute and idle timeouts in SQLite.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from akaal.core.crypto_random import generate_secure_id, generate_secure_token
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteSessionRepository,
)


class SessionNotFoundError(ValueError):
    pass


class SessionRevokedError(ValueError):
    pass


class SessionExpiredError(ValueError):
    pass


class SessionSecurityRevisionMismatchError(ValueError):
    pass


class SessionManager:
    """Canonical durable session authority."""

    def __init__(
        self,
        session_repo: SQLiteSessionRepository,
        principal_repo: SQLitePrincipalRepository,
        config: Optional[SecurityBaselineConfig] = None,
    ) -> None:
        self.session_repo = session_repo
        self.principal_repo = principal_repo
        self.config = config or SecurityBaselineConfig()

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_session(
        self,
        tenant_id: str,
        principal_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create a durable high-entropy session.
        Returns: (session_id, raw_bearer_token)
        """
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal or not principal["is_active"]:
            raise ValueError(f"Cannot create session for inactive principal {principal_id!r}")

        session_id = generate_secure_id("sess")
        raw_token = f"ak_sess_{generate_secure_token(32)}"
        token_hash = self._hash_token(raw_token)

        now = TimeAuthority.utc_now()
        now_iso = now.isoformat()
        abs_exp_iso = (now + timedelta(seconds=self.config.session_absolute_timeout_seconds)).isoformat()

        self.session_repo.create_session(
            session_id=session_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            session_token_hash=token_hash,
            issued_at=now_iso,
            last_activity_at=now_iso,
            absolute_expires_at=abs_exp_iso,
            idle_timeout_seconds=self.config.session_idle_timeout_seconds,
            bound_security_revision=principal["security_revision"],
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return session_id, raw_token

    def validate_session(
        self,
        tenant_id: str,
        session_id: str,
        raw_token: str,
    ) -> Dict[str, Any]:
        """
        Validate session token and update last activity.
        Enforces revocation, absolute timeout, and idle timeout.
        """
        session = self.session_repo.get_session(tenant_id, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")

        expected_hash = self._hash_token(raw_token)
        if session["session_token_hash"] != expected_hash:
            raise SessionNotFoundError("Invalid session token")

        if session["is_revoked"]:
            raise SessionRevokedError("Session has been revoked")

        now = TimeAuthority.utc_now()
        now_iso = now.isoformat()

        # Check absolute expiry
        abs_exp = TimeAuthority.parse_iso(session["absolute_expires_at"])
        if now >= abs_exp:
            self.session_repo.revoke_session(tenant_id, session_id, "ABSOLUTE_TIMEOUT")
            raise SessionExpiredError("Session absolute lifetime expired")

        # Check idle timeout
        last_act = TimeAuthority.parse_iso(session["last_activity_at"])
        idle_limit = timedelta(seconds=session["idle_timeout_seconds"])
        if (now - last_act) > idle_limit:
            self.session_repo.revoke_session(tenant_id, session_id, "IDLE_TIMEOUT")
            raise SessionExpiredError("Session idle timeout exceeded")

        # Check principal security revision
        principal = self.principal_repo.get_by_id(tenant_id, session["principal_id"])
        if not principal or not principal["is_active"]:
            self.session_repo.revoke_session(tenant_id, session_id, "PRINCIPAL_DEACTIVATED")
            raise SessionRevokedError("Principal is deactivated or missing")

        if principal["security_revision"] > session["bound_security_revision"]:
            self.session_repo.revoke_session(tenant_id, session_id, "SECURITY_REVISION_ADVANCED")
            raise SessionSecurityRevisionMismatchError("Principal security revision advanced; session invalid")

        # Update last activity
        self.session_repo.update_activity(tenant_id, session_id, now_iso)
        session["last_activity_at"] = now_iso
        return session

    def revoke_session(self, tenant_id: str, session_id: str, reason: str = "EXPLICIT_LOGOUT") -> None:
        """Revoke a specific session."""
        self.session_repo.revoke_session(tenant_id, session_id, reason)
