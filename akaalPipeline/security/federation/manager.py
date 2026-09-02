"""akaalPipeline.security.federation.manager
=========================================
P7.4 Unified Enterprise Identity Federation Manager.

Integrates OIDC, OAuth 2.0, SAML 2.0, and LDAP/Active Directory into canonical Zero-Trust Security Contexts.

Strict Invariants:
1. AUTHENTICATED != AUTHORIZED. External directory groups and scopes are policy inputs only.
2. Tenant mappings are derived strictly from trusted provider configuration.
3. Provider subject scoping prevents cross-provider collisions.
4. Preserves human identity as original_actor when propagating downstream.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    FederationProviderType,
    PrincipalType,
)
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.federation.ldap import LDAPClient
from akaalPipeline.security.federation.models import FederatedIdentityResult, FederationProviderConfig
from akaalPipeline.security.federation.oidc import OIDCValidator
from akaalPipeline.security.federation.saml import SAMLValidator

logger = logging.getLogger("akaalPipeline.security.federation.manager")


class FederationManager:
    """
    Unified Manager for Enterprise Identity Federation across OIDC, SAML, and LDAP/AD.
    """

    def __init__(
        self,
        oidc_validator: Optional[OIDCValidator] = None,
        saml_validator: Optional[SAMLValidator] = None,
    ) -> None:
        self.oidc_validator = oidc_validator or OIDCValidator()
        self.saml_validator = saml_validator or SAMLValidator()
        self._providers: Dict[str, FederationProviderConfig] = {}

    def register_provider(self, config: FederationProviderConfig) -> None:
        """Registers an enterprise identity provider configuration."""
        self._providers[config.provider_id] = config
        if config.jwks_keys and config.provider_type in (FederationProviderType.OIDC, FederationProviderType.OAUTH2):
            self.oidc_validator.register_jwks(config.provider_id, config.jwks_keys)

    def get_provider(self, provider_id: str) -> FederationProviderConfig:
        """Retrieves provider configuration or raises KeyError."""
        if provider_id not in self._providers:
            raise KeyError(f"Federation provider '{provider_id}' is not registered")
        return self._providers[provider_id]

    def authenticate_oidc_token(
        self,
        provider_id: str,
        id_token: str,
        expected_audience: Optional[str] = None,
    ) -> PipelineActorContext:
        """
        Authenticates an OIDC ID token and returns a canonical PipelineActorContext.
        """
        config = self.get_provider(provider_id)
        if not config.is_active:
            raise ValueError(f"Federation provider '{provider_id}' is inactive")

        fed_result = self.oidc_validator.validate_id_token(
            token=id_token,
            config=config,
            expected_audience=expected_audience,
        )

        return self._mint_canonical_context(
            fed_result=fed_result,
            config=config,
            mechanism=CredentialMechanism.OIDC_ID_TOKEN,
        )

    def authenticate_saml_assertion(
        self,
        provider_id: str,
        saml_xml_or_b64: str,
        expected_audience: Optional[str] = None,
        expected_in_response_to: Optional[str] = None,
    ) -> PipelineActorContext:
        """
        Authenticates a SAML 2.0 Response/Assertion and returns a canonical PipelineActorContext.
        """
        config = self.get_provider(provider_id)
        if not config.is_active:
            raise ValueError(f"Federation provider '{provider_id}' is inactive")

        fed_result = self.saml_validator.validate_saml_response(
            saml_xml_or_b64=saml_xml_or_b64,
            config=config,
            expected_audience=expected_audience,
            expected_in_response_to=expected_in_response_to,
        )

        return self._mint_canonical_context(
            fed_result=fed_result,
            config=config,
            mechanism=CredentialMechanism.SAML2_ASSERTION,
        )

    def authenticate_ldap_credentials(
        self,
        provider_id: str,
        username: str,
        password: str,
    ) -> PipelineActorContext:
        """
        Authenticates LDAP / Active Directory credentials and returns a canonical PipelineActorContext.
        """
        config = self.get_provider(provider_id)
        if not config.is_active:
            raise ValueError(f"Federation provider '{provider_id}' is inactive")

        ldap_client = LDAPClient(config)
        fed_result = ldap_client.authenticate_user(username=username, password=password)

        return self._mint_canonical_context(
            fed_result=fed_result,
            config=config,
            mechanism=CredentialMechanism.LDAP_BIND_CREDENTIAL,
        )

    def _mint_canonical_context(
        self,
        fed_result: FederatedIdentityResult,
        config: FederationProviderConfig,
        mechanism: CredentialMechanism,
    ) -> PipelineActorContext:
        """
        Constructs canonical PipelineActorContext preserving all Zero-Trust dimensions,
        original actor human provenance, and mapped tenant identity.
        """
        # Resolve Tenant ID from trusted config (never trust self-asserted tenant from client)
        tenant_id = config.default_tenant_id or "default-tenant"
        for group in fed_result.groups:
            if group in config.tenant_mapping:
                tenant_id = config.tenant_mapping[group]
                break

        # Map external directory groups to internal policy input roles
        mapped_roles: List[str] = []
        for group in fed_result.groups:
            if group in config.role_mapping:
                mapped_roles.append(config.role_mapping[group])
            else:
                mapped_roles.append(group)

        # Scoped Principal ID prevents collision between Provider A subject 123 and Provider B subject 123
        scoped_id = fed_result.scoped_principal_id

        # Human identity as original actor
        original_actor_meta = {
            "actor_id": scoped_id,
            "actor_type": PrincipalType.HUMAN.value,
            "display_name": fed_result.display_name,
            "email": fed_result.email,
            "trust_domain": config.issuer,
        }

        provenance_meta = {
            "provider_id": config.provider_id,
            "provider_type": config.provider_type.value,
            "issuer": config.issuer,
            "external_subject": fed_result.subject,
            "auth_time": fed_result.authenticated_at.isoformat(),
        }

        expires_str = fed_result.expires_at.isoformat() if fed_result.expires_at else None

        return PipelineActorContext(
            actor_id=scoped_id,
            actor_type=PrincipalType.HUMAN.value,
            display_name=fed_result.display_name,
            email=fed_result.email,
            organization_id=tenant_id,
            roles=tuple(mapped_roles),
            credential_mechanism=mechanism,
            authentication_state=AuthenticationState.AUTHENTICATED,
            authentication_assurance=fed_result.assurance,
            trust_domain=config.issuer,
            federation_provenance=provenance_meta,
            original_actor=original_actor_meta,
            issued_at=fed_result.authenticated_at.isoformat(),
            expires_at=expires_str,
        )
