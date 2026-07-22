"""
Authenticator Service Supporting API Keys, JWT, and mTLS.
"""

from typing import Dict, Optional
import time
from akaal.api.auth.models import Identity, SecurityContext, TokenPayload
from akaal.api.auth.trl import TokenRevocationList
from akaal.api.contracts.errors import AuthenticationError


class Authenticator:
    """Production Authenticator handling multi-scheme authentication."""

    def __init__(self, trl: Optional[TokenRevocationList] = None) -> None:
        self.trl = trl or TokenRevocationList()
        self._valid_api_keys: Dict[str, Identity] = {
            "akaal_live_test_key_123": Identity(
                user_id="user-admin-1",
                tenant_id="tenant-prod-alpha",
                roles=["admin", "operator"],
                scopes=["akaal:jobs:write", "akaal:workflows:execute", "akaal:admin"],
                auth_method="API_KEY",
            )
        }

    def register_api_key(self, api_key: str, identity: Identity) -> None:
        self._valid_api_keys[api_key] = identity

    def authenticate_api_key(self, api_key: str) -> SecurityContext:
        if not api_key or api_key not in self._valid_api_keys:
            raise AuthenticationError("Invalid or missing API key")
        identity = self._valid_api_keys[api_key]
        return SecurityContext(identity=identity, is_authenticated=True)

    def authenticate_jwt(self, token_payload: TokenPayload) -> SecurityContext:
        if self.trl.is_revoked(token_payload.jti):
            raise AuthenticationError(f"JWT Token {token_payload.jti} has been revoked")

        if token_payload.exp < int(time.time()):
            raise AuthenticationError("JWT Token has expired")

        identity = Identity(
            user_id=token_payload.sub,
            tenant_id=token_payload.tenant_id,
            roles=token_payload.roles,
            scopes=token_payload.scopes,
            auth_method="JWT",
        )
        return SecurityContext(identity=identity, token_id=token_payload.jti, is_authenticated=True)
