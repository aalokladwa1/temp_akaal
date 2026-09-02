"""akaalPipeline.security.federation
===================================
P7.4 Enterprise Identity Federation Package.
"""

from akaalPipeline.security.federation.ldap import LDAPAuthError, LDAPClient, LDAPConnectionError
from akaalPipeline.security.federation.manager import FederationManager
from akaalPipeline.security.federation.models import FederatedIdentityResult, FederationProviderConfig
from akaalPipeline.security.federation.oidc import OIDCExpiredError, OIDCValidationError, OIDCValidator
from akaalPipeline.security.federation.saml import (
    SAMLExpiredError,
    SAMLReplayError,
    SAMLValidationError,
    SAMLValidator,
)

__all__ = [
    "FederatedIdentityResult",
    "FederationManager",
    "FederationProviderConfig",
    "LDAPAuthError",
    "LDAPClient",
    "LDAPConnectionError",
    "OIDCExpiredError",
    "OIDCValidationError",
    "OIDCValidator",
    "SAMLExpiredError",
    "SAMLReplayError",
    "SAMLValidationError",
    "SAMLValidator",
]
