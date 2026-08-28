"""akaalPipeline.identity.tokens
==============================
Canonical Service API Bearer Token Authority issuing hashed, scoped tokens.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple
from akaal.core.crypto_random import generate_secure_id, generate_secure_token
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteServiceTokenRepository,
)


class ServiceTokenNotFoundError(ValueError):
    pass


class ServiceTokenRevokedError(ValueError):
    pass


class ServiceTokenExpiredError(ValueError):
    pass


class ServiceTokenSecurityRevisionMismatchError(ValueError):
    pass


class ServiceTokenAuthority:
    """Canonical authority for service API token issuance, verification, and revocation."""

    def __init__(
        self,
        token_repo: SQLiteServiceTokenRepository,
        principal_repo: SQLitePrincipalRepository,
        config: Optional[SecurityBaselineConfig] = None,
    ) -> None:
        self.token_repo = token_repo
        self.principal_repo = principal_repo
        self.config = config or SecurityBaselineConfig()

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue_token(
        self,
        tenant_id: str,
        principal_id: str,
        name: str,
        scopes: List[str],
        expires_at_iso: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Issue a high-entropy 256-bit hashed service token.
        Returns: (token_id, raw_bearer_token)
        """
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal or not principal["is_active"]:
            raise ValueError(f"Cannot issue token for inactive principal {principal_id!r}")

        token_id = generate_secure_id("tok")
        token_prefix = "ak_svc"
        raw_secret = generate_secure_token(32)
        raw_token = f"{token_prefix}_{raw_secret}"
        token_hash = self._hash_token(raw_token)

        now_iso = TimeAuthority.utc_iso_now()

        self.token_repo.create_token(
            token_id=token_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            name=name,
            scopes=scopes,
            issued_at=now_iso,
            expires_at=expires_at_iso,
            bound_security_revision=principal["security_revision"],
        )
        return token_id, raw_token

    def validate_token(self, raw_token: str) -> Dict[str, Any]:
        """
        Validate a service bearer token.
        Enforces revocation, expiration, and principal active status.
        """
        if not raw_token:
            raise ServiceTokenNotFoundError("Empty token")

        token_hash = self._hash_token(raw_token)
        token_record = self.token_repo.get_by_hash(token_hash)
        if not token_record:
            raise ServiceTokenNotFoundError("Invalid service token")

        if token_record["is_revoked"]:
            raise ServiceTokenRevokedError("Service token has been revoked")

        if TimeAuthority.is_expired(token_record.get("expires_at")):
            raise ServiceTokenExpiredError("Service token has expired")

        tenant_id = token_record["tenant_id"]
        principal_id = token_record["principal_id"]

        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal or not principal["is_active"]:
            raise ServiceTokenRevokedError("Principal associated with service token is inactive")

        if principal["security_revision"] > token_record["bound_security_revision"]:
            raise ServiceTokenSecurityRevisionMismatchError("Principal security revision advanced; token invalid")

        return {
            "token_id": token_record["token_id"],
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "name": token_record["name"],
            "scopes": token_record["scopes"],
            "principal_type": principal["principal_type"],
            "security_revision": principal["security_revision"],
        }

    def revoke_token(self, tenant_id: str, token_id: str) -> None:
        """Revoke a service token."""
        now_iso = TimeAuthority.utc_iso_now()
        self.token_repo.revoke_token(tenant_id, token_id, now_iso)
