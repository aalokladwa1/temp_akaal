"""
AKAAL Universal Connector Taxonomy & Capability Classifications (P4.1).
========================================================================
Defines canonical connector families, roles, authentication mechanisms,
proof levels, capability support states, error categories, and semantic compatibility.
"""

from enum import Enum


class ConnectorFamily(str, Enum):
    """Canonical classification of enterprise connector technology families."""
    RELATIONAL_DATABASE         = "RELATIONAL_DATABASE"
    CLOUD_DATA_WAREHOUSE        = "CLOUD_DATA_WAREHOUSE"
    DOCUMENT_DATABASE           = "DOCUMENT_DATABASE"
    WIDE_COLUMN_DATABASE        = "WIDE_COLUMN_DATABASE"
    GRAPH_DATABASE              = "GRAPH_DATABASE"
    KEY_VALUE_STORE             = "KEY_VALUE_STORE"
    SEARCH_ENGINE               = "SEARCH_ENGINE"
    STREAM_EVENT_PLATFORM       = "STREAM_EVENT_PLATFORM"
    DISTRIBUTED_FILESYSTEM      = "DISTRIBUTED_FILESYSTEM"
    OBJECT_STORAGE              = "OBJECT_STORAGE"
    FILE_DATASET                = "FILE_DATASET"
    LAKEHOUSE_ANALYTICS         = "LAKEHOUSE_ANALYTICS"
    CLOUD_PROVIDER              = "CLOUD_PROVIDER"
    CONTAINER_ORCHESTRATION     = "CONTAINER_ORCHESTRATION"
    CONNECTIVITY_INFRASTRUCTURE = "CONNECTIVITY_INFRASTRUCTURE"


class ConnectorRole(str, Enum):
    """Functional role declarations for universal connectors."""
    SOURCE               = "SOURCE"
    TARGET               = "TARGET"
    BOTH                 = "BOTH"
    INFRASTRUCTURE_ONLY  = "INFRASTRUCTURE_ONLY"


class AuthenticationMechanism(str, Enum):
    """Standardized authentication mechanisms supported by connectors."""
    USERNAME_PASSWORD        = "USERNAME_PASSWORD"
    TLS_CERTIFICATE          = "TLS_CERTIFICATE"
    ORACLE_WALLET            = "ORACLE_WALLET"
    BEARER_TOKEN             = "BEARER_TOKEN"
    API_KEY                  = "API_KEY"
    OAUTH2                   = "OAUTH2"
    AWS_IAM                  = "AWS_IAM"
    AZURE_MANAGED_IDENTITY   = "AZURE_MANAGED_IDENTITY"
    GCP_SERVICE_ACCOUNT      = "GCP_SERVICE_ACCOUNT"
    KERBEROS                 = "KERBEROS"
    ANONYMOUS                = "ANONYMOUS"


class ProofLevel(str, Enum):
    """Truthful, evidence-backed proof levels for connectors and capabilities."""
    UNIMPLEMENTED            = "UNIMPLEMENTED"
    STATIC_INSPECTION_ONLY   = "STATIC_INSPECTION_ONLY"
    UNIT_PROVEN              = "UNIT_PROVEN"
    MOCK_PROVEN              = "MOCK_PROVEN"
    EMULATOR_PROVEN          = "EMULATOR_PROVEN"
    CONTAINER_PROVEN         = "CONTAINER_PROVEN"
    REAL_SYSTEM_PROVEN       = "REAL_SYSTEM_PROVEN"
    MANAGED_CLOUD_PROVEN     = "MANAGED_CLOUD_PROVEN"
    PRODUCTION_SCALE_PROVEN  = "PRODUCTION_SCALE_PROVEN"


class ProofState(str, Enum):
    """Independent proof state dimension."""
    UNPROVEN                 = "UNPROVEN"
    UNIT_PROVEN              = "UNIT_PROVEN"
    SYNTHETIC_PROVEN         = "SYNTHETIC_PROVEN"
    INTEGRATION_PROVEN       = "INTEGRATION_PROVEN"
    REAL_SYSTEM_PROVEN       = "REAL_SYSTEM_PROVEN"
    REAL_CLOUD_PROVEN        = "REAL_CLOUD_PROVEN"
    PERFORMANCE_PROVEN       = "PERFORMANCE_PROVEN"
    PRODUCTION_CERTIFIED     = "PRODUCTION_CERTIFIED"


class ImplementationState(str, Enum):
    """Independent implementation state dimension."""
    ABSENT                   = "ABSENT"
    STUB                     = "STUB"
    PARTIAL                  = "PARTIAL"
    IMPLEMENTED              = "IMPLEMENTED"
    MANAGED_PROFILE          = "MANAGED_PROFILE"  # Managed/distribution alias reusing a canonical physical connector


class RegistrationState(str, Enum):
    """Independent registration state dimension."""
    UNREGISTERED             = "UNREGISTERED"
    REGISTERED               = "REGISTERED"


class PipelineState(str, Enum):
    """Independent pipeline reachability dimension."""
    UNREACHABLE              = "UNREACHABLE"
    REACHABLE                = "REACHABLE"


class SupportState(str, Enum):
    """Independent operational support state dimension."""
    UNSUPPORTED              = "UNSUPPORTED"
    EXPERIMENTAL             = "EXPERIMENTAL"
    PARTIAL                  = "PARTIAL"
    SUPPORTED                = "SUPPORTED"
    CERTIFIED                = "CERTIFIED"


class CapabilitySupportStatus(str, Enum):
    """Machine-readable support classification for specific connector capabilities."""
    SUPPORTED                  = "SUPPORTED"
    SUPPORTED_WITH_LIMITATIONS = "SUPPORTED_WITH_LIMITATIONS"
    SUPPORTED_WITH_MAPPING     = "SUPPORTED_WITH_MAPPING"
    LOSSY                      = "LOSSY"
    UNSUPPORTED                = "UNSUPPORTED"
    UNKNOWN_NOT_PROVEN         = "UNKNOWN_NOT_PROVEN"


class ConnectorErrorCategory(str, Enum):
    """Canonical classification for connector error handling and retries."""
    RETRYABLE            = "RETRYABLE"
    NON_RETRYABLE        = "NON_RETRYABLE"
    AUTHENTICATION       = "AUTHENTICATION"
    AUTHORIZATION        = "AUTHORIZATION"
    CONNECTIVITY         = "CONNECTIVITY"
    THROTTLED            = "THROTTLED"
    RESOURCE_EXHAUSTED   = "RESOURCE_EXHAUSTED"
    UNSUPPORTED          = "UNSUPPORTED"
    DATA_ERROR           = "DATA_ERROR"
    SCHEMA_ERROR         = "SCHEMA_ERROR"
    GOVERNANCE_REQUIRED  = "GOVERNANCE_REQUIRED"
    UNKNOWN_FAIL_CLOSED  = "UNKNOWN_FAIL_CLOSED"


class SemanticCompatibility(str, Enum):
    """Cross-engine semantic compatibility classification."""
    SUPPORTED                  = "SUPPORTED"
    SUPPORTED_WITH_MAPPING     = "SUPPORTED_WITH_MAPPING"
    SUPPORTED_WITH_LIMITATIONS  = "SUPPORTED_WITH_LIMITATIONS"
    LOSSY_REQUIRES_APPROVAL    = "LOSSY_REQUIRES_APPROVAL"
    UNSUPPORTED                = "UNSUPPORTED"
    NOT_YET_PROVEN             = "NOT_YET_PROVEN"
