"""
Security Models for Authentication & Authorization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Identity(BaseModel):
    user_id: str
    tenant_id: str
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    auth_method: str = "API_KEY"  # API_KEY, JWT, MTLS


class SecurityContext(BaseModel):
    identity: Identity
    token_id: Optional[str] = None
    is_authenticated: bool = True
    correlation_id: Optional[str] = None


class TokenPayload(BaseModel):
    jti: str
    sub: str
    tenant_id: str
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    exp: int
    iat: int
