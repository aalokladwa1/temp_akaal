"""akaalPipeline.identity.sessions
================================
Canonical durable session management authority enforcing absolute and idle timeouts in SQLite.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, Union
from akaal.core.crypto_random import generate_secure_id, generate_secure_token
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import AuthenticationAssurance, AuthenticationState, CredentialMechanism
from akaalPipeline.contracts.errors import UnauthorizedError
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteSessionRepository,
    SQLiteTenantRepository,
)


class SessionNotFoundError(ValueError):
    pass


class SessionRevokedError(ValueError):
    pass


class SessionExpiredError(ValueError):
    pass


class SessionSecurityRevisionMismatchError(ValueError):
    pass


class SessionResult(tuple):
    """Dual tuple/dict wrapper for session creation results."""
    def __new__(cls, session_id: str, raw_token: str):
        return super().__new__(cls, (session_id, raw_token))

    @property
    def session_id(self) -> str:
        return self[0]

    @property
    def token(self) -> str:
        return self[1]

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            if item in ("session_id", "id"):
                return self[0]
            if item in ("token", "raw_token"):
                return self[1]
            raise KeyError(item)
        return super().__getitem__(item)


class SessionManager:
    """Canonical durable session authority."""

    def __init__(
        self,
        session_repo: SQLiteSessionRepository,
        principal_repo: SQLitePrincipalRepository,
        tenant_repo: Optional[SQLiteTenantRepository] = None,
        config: Optional[SecurityBaselineConfig] = None,
    ) -> None:
        self.session_repo = session_repo
        self.principal_repo = principal_repo
        self.tenant_repo = tenant_repo
        self.config = config or SecurityBaselineConfig()

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_session(
        self,
        tenant_id: str,
        principal_id: str,
        ttl_seconds: Optional[int] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        authentication_assurance: AuthenticationAssurance = AuthenticationAssurance.NONE,
        credential_mechanism: Optional[CredentialMechanism] = None,
        trust_domain: Optional[str] = None,
    ) -> SessionResult:
        """
        Create a durable high-entropy session.
        Returns: SessionResult(session_id, raw_bearer_token)

        `authentication_assurance`/`credential_mechanism`/`trust_domain`: captured HERE,
        at session-establishment time, from the caller's ALREADY-VERIFIED authentication
        result (e.g. akaalPipeline.security.federation.manager.FederationManager's
        successful OIDC/SAML/LDAP validation, or akaalPipeline.security.mfa.MFAAuthority's
        successful challenge verification) -- never from a later, untrusted, wire-asserted
        claim. This is what allows resolve_authenticated_context() to later hand back a
        genuinely trustworthy assurance level for HIGH-assurance-gated authorization,
        without re-deriving trust from anything the caller merely asserts on each request.
        """
        # If principal_id is a username, resolve to principal_id
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal:
            principal = self.principal_repo.get_by_username(tenant_id, principal_id)
        if not principal or not principal["is_active"]:
            raise ValueError(f"Cannot create session for inactive principal {principal_id!r}")

        real_principal_id = principal["principal_id"]
        session_id = generate_secure_id("sess")
        raw_token = f"ak_sess_{generate_secure_token(32)}"
        token_hash = self._hash_token(raw_token)

        now = TimeAuthority.utc_now()
        now_iso = now.isoformat()
        abs_ttl = ttl_seconds or self.config.session_absolute_timeout_seconds
        abs_exp_iso = (now + timedelta(seconds=abs_ttl)).isoformat()

        self.session_repo.create_session(
            session_id=session_id,
            tenant_id=tenant_id,
            principal_id=real_principal_id,
            session_token_hash=token_hash,
            issued_at=now_iso,
            last_activity_at=now_iso,
            absolute_expires_at=abs_exp_iso,
            idle_timeout_seconds=self.config.session_idle_timeout_seconds,
            bound_security_revision=principal["security_revision"],
            client_ip=client_ip,
            user_agent=user_agent,
            authentication_assurance=authentication_assurance.value if hasattr(authentication_assurance, "value") else str(authentication_assurance),
            credential_mechanism=(credential_mechanism.value if hasattr(credential_mechanism, "value") else credential_mechanism) if credential_mechanism else None,
            trust_domain=trust_domain,
        )
        return SessionResult(session_id, raw_token)

    def resolve_authenticated_context(self, tenant_id: str, session_id: str, raw_token: str):
        """
        THE trusted bridge: resolves a raw bearer token (never a bare session_id alone --
        that is not secret and would let a caller merely guess/replay an identifier) via
        the existing validate_session() durable session authority, then constructs a
        genuinely trustworthy `PipelineActorContext` using the ASSURANCE/CREDENTIAL/
        TRUST-DOMAIN CAPTURED AT SESSION CREATION TIME (see create_session() above) --
        never from anything the current request's caller merely asserts. Fails closed
        (raises UnauthorizedError) on any invalid/expired/revoked/tampered session,
        exactly like every other session validation failure in this class.
        """
        from akaalPipeline.security.context import PipelineActorContext  # local import: avoids a security->identity import cycle

        session = self.authenticate_session(tenant_id, raw_token)
        if session["session_id"] != session_id:
            # The supplied session_id does not match the session actually bound to this
            # token -- treat as tampered/substituted provenance and fail closed.
            raise UnauthorizedError("Session identity does not match the presented session token; provenance rejected.")

        principal = self.principal_repo.get_by_id(tenant_id, session["principal_id"])
        if not principal or not principal["is_active"]:
            raise UnauthorizedError("Session principal is no longer active.")

        return PipelineActorContext(
            actor_id=session["principal_id"],
            actor_type=principal.get("principal_type", "HUMAN"),
            display_name=principal.get("display_name"),
            email=principal.get("email"),
            organization_id=tenant_id,
            session_id=session["session_id"],
            credential_mechanism=session.get("credential_mechanism") or CredentialMechanism.SESSION_TOKEN.value,
            authentication_state=AuthenticationState.AUTHENTICATED.value,
            authentication_assurance=session.get("authentication_assurance") or AuthenticationAssurance.NONE.value,
            trust_domain=session.get("trust_domain"),
            issued_at=session.get("issued_at"),
        )

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

        # Update last activity. Ownership captured BEFORE this call's first write (this
        # method may run inside an external `with uow:` transaction, or -- as with the
        # HIGH-assurance trusted-session bridge in unified_caller.handle_command(), which
        # calls resolve_authenticated_context()/authenticate_session() before opening its
        # own transaction -- it may be the one opening the connection's transaction. Same
        # composability rule as identity.jit_identity.JITIdentityAuthority._commit_if_owned:
        # self-commit only when this call itself owns the transaction, else the outer owner
        # commits/rolls back later.
        owns_transaction = not self.session_repo.conn.in_transaction
        self.session_repo.update_activity(tenant_id, session_id, now_iso)
        if owns_transaction:
            self.session_repo.conn.commit()
        session["last_activity_at"] = now_iso
        return session

    def authenticate_session(self, tenant_id: str, raw_token: str) -> Dict[str, Any]:
        """Authenticate session directly from raw token string, returning validated session or raising UnauthorizedError."""
        if not raw_token:
            raise UnauthorizedError("Empty session token")
        token_hash = self._hash_token(raw_token)
        session = self.session_repo.get_by_hash(tenant_id, token_hash)
        if not session:
            raise UnauthorizedError("Invalid, revoked, or expired session")
        try:
            return self.validate_session(tenant_id, session["session_id"], raw_token)
        except (SessionNotFoundError, SessionRevokedError, SessionExpiredError, SessionSecurityRevisionMismatchError) as exc:
            raise UnauthorizedError(f"Session validation failure: {exc}") from exc

    def revoke_session(self, tenant_id: str, session_id: str, reason: str = "EXPLICIT_LOGOUT") -> None:
        """Revoke a specific session."""
        self.session_repo.revoke_session(tenant_id, session_id, reason)
