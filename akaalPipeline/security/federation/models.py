"""akaalPipeline.security.federation.models
========================================
Enterprise Identity Federation Models and Provider Configurations.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    FederationProviderType,
    PrincipalType,
)


@dataclass(frozen=True)
class FederationProviderConfig:
    """Configuration for an external identity provider (IdP / Directory)."""

    provider_id: str
    provider_type: FederationProviderType
    display_name: str
    issuer: str
    client_id: Optional[str] = None
    client_secret_ref: Optional[str] = None
    jwks_url: Optional[str] = None
    jwks_keys: Optional[Dict[str, Any]] = None  # Pre-configured / cached JWKS
    idp_metadata_xml: Optional[str] = None
    idp_cert_pem: Optional[str] = None
    ldap_server_uri: Optional[str] = None  # e.g. ldaps://ad.corp.com:636
    ldap_base_dn: Optional[str] = None
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password_ref: Optional[str] = None
    default_tenant_id: Optional[str] = None
    tenant_mapping: Dict[str, str] = field(default_factory=dict)  # external claim/group -> tenant_id
    role_mapping: Dict[str, str] = field(default_factory=dict)    # external group -> AKAAL policy input role
    is_active: bool = True


@dataclass(frozen=True)
class FederatedIdentityResult:
    """Normalized, cryptographically verified identity result from an external IdP."""

    provider_id: str
    provider_type: FederationProviderType
    subject: str  # Unique subject identifier within the IdP
    email: Optional[str] = None
    display_name: Optional[str] = None
    groups: Tuple[str, ...] = field(default_factory=tuple)
    claims: Dict[str, Any] = field(default_factory=dict)
    assurance: AuthenticationAssurance = AuthenticationAssurance.MEDIUM
    authenticated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    expires_at: Optional[datetime.datetime] = None

    @property
    def scoped_principal_id(self) -> str:
        """Globally distinct principal ID preventing cross-provider subject collisions."""
        return f"{self.provider_type.value.lower()}:{self.provider_id}:{self.subject}"
