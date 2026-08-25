"""
akaalEngine.gateway.models.errors
=================================
Canonical typed Exception Hierarchy for EngineGateway.
"""


class GatewayError(Exception):
    """Base exception for all EngineGateway failures."""
    pass


class GatewayConfigurationError(GatewayError):
    """Raised when Gateway configuration, signing keys, or cryptographic secrets are missing, invalid, or insecure."""
    pass


class GatewaySecurityError(GatewayError):
    """Raised when Gateway authentication, authorization, or boundary verification fails."""
    pass


class GatewayAdmissionError(GatewayError):
    """Raised when a request is rejected during Gateway pre-admission checks."""
    pass
