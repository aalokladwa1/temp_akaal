"""
akaalEngine.gateway.models.requests
===================================
Canonical Gateway request DTOs.
Strongly typed semantic request wrappers for callers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation


import re

def _sanitize_secret_value(obj: Any) -> Any:
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(secret_kw in k_lower for secret_kw in ("pass", "secret", "token", "key", "auth", "cred", "password", "private")):
                res[k] = "***REDACTED***"
            else:
                res[k] = _sanitize_secret_value(v)
        return res
    elif isinstance(obj, list):
        return [_sanitize_secret_value(x) for x in obj]
    elif isinstance(obj, str):
        lower_str = obj.lower()
        if any(secret_kw in lower_str for secret_kw in ("password=", "secret=", "token=", "key=")):
            return re.sub(r'(password|secret|token|key)=[^;&\s]+', r'\1=***REDACTED***', obj, flags=re.IGNORECASE)
    return obj


class SecretSafeDTO:
    """Base mixin ensuring safe string/repr representations for all Gateway request DTOs."""
    def __repr__(self) -> str:
        fields = []
        for k, v in getattr(self, "__dict__", {}).items():
            fields.append(f"{k}={_sanitize_secret_value(v)!r}")
        return f"{self.__class__.__name__}({', '.join(fields)})"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(repr=False)
class GatewayRequest(SecretSafeDTO):
    """Generic base Gateway request wrapper carrying semantic operation and context."""
    operation: SemanticOperation
    context: GatewayRequestContext
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(repr=False)
class EndpointTestConnectionRequest(SecretSafeDTO):
    """Semantic request to test endpoint connectivity & credentials."""
    context: GatewayRequestContext
    endpoint_spec: Dict[str, Any]
    auth_spec: Dict[str, Any]
    session_purpose: str = "HEALTH_PROBE"


@dataclass(repr=False)
class ResolveCapabilitiesRequest(SecretSafeDTO):
    """Semantic request to resolve connector capability support."""
    context: GatewayRequestContext
    provider_id: str
    required_capabilities: List[str] = field(default_factory=list)


@dataclass(repr=False)
class DiscoverCatalogRequest(SecretSafeDTO):
    """Semantic request to discover source/target catalog and metadata."""
    context: GatewayRequestContext
    endpoint_spec: Dict[str, Any]
    auth_spec: Dict[str, Any]
    depth: str = "STANDARD"
    scope_schemas: Optional[List[str]] = None


@dataclass(repr=False)
class CompileSchemaMappingRequest(SecretSafeDTO):
    """Semantic request to compile source-to-target schema mapping and DDL."""
    context: GatewayRequestContext
    source_discovery_snapshot: Dict[str, Any]
    target_dialect: str
    type_overrides: Dict[str, str] = field(default_factory=dict)


@dataclass(repr=False)
class ValidateSchemaCompatibilityRequest(SecretSafeDTO):
    """Semantic request to validate schema compatibility between source and target."""
    context: GatewayRequestContext
    source_schema_model: Dict[str, Any]
    target_schema_model: Dict[str, Any]


@dataclass(repr=False)
class PrepareMigrationRequest(SecretSafeDTO):
    """Semantic request to prepare execution resources, tables, and durability checkpoints."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    schema_mapping: Dict[str, Any]


@dataclass(repr=False)
class ExecuteBulkMigrationRequest(SecretSafeDTO):
    """Semantic request to execute historical parallel bulk data transport."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    table_mappings: List[Dict[str, Any]]
    parallelism: int = 4
    batch_size: int = 5000


@dataclass(repr=False)
class InitializeCDCRequest(SecretSafeDTO):
    """Semantic request to initialize real-time Change Data Capture stream."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    starting_position: Optional[Dict[str, Any]] = None


@dataclass(repr=False)
class ExecuteCDCSyncRequest(SecretSafeDTO):
    """Semantic request to execute continuous CDC change polling and delta application."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    batch_size: int = 1000


@dataclass(repr=False)
class EvaluateCutoverRequest(SecretSafeDTO):
    """Semantic request to evaluate 17-gate cutover readiness."""
    context: GatewayRequestContext
    cdc_boundary_position: str
    required_proof_categories: List[str] = field(default_factory=lambda: ["execution", "validation", "cdc"])


@dataclass(repr=False)
class RunValidationRequest(SecretSafeDTO):
    """Semantic request to execute row-level reconciliation and Merkle validation."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    validation_mode: str = "FULL"
    required_cdc_boundary: Optional[str] = None


@dataclass(repr=False)
class PackageEvidenceRequest(SecretSafeDTO):
    """Semantic request to package machine execution, validation, and CDC proof into an evidence manifest."""
    context: GatewayRequestContext
    artifacts: List[Any] = field(default_factory=list)


@dataclass(repr=False)
class VerifyEvidenceRequest(SecretSafeDTO):
    """Semantic request to verify evidence manifest integrity and contextual proof sufficiency."""
    context: GatewayRequestContext
    manifest: Any
    required_proof_categories: Optional[List[str]] = None


@dataclass(repr=False)
class ExecuteAtomicCutoverRequest(SecretSafeDTO):
    """Semantic request to perform final atomic cutover commit."""
    context: GatewayRequestContext
    cdc_boundary_position: str
    cutover_token: str


@dataclass(repr=False)
class TriggerCheckpointRequest(SecretSafeDTO):
    """Semantic request to force an explicit durable checkpoint flush."""
    context: GatewayRequestContext
    checkpoint_id: str


@dataclass(repr=False)
class RecoverFromCheckpointRequest(SecretSafeDTO):
    """Semantic request to inspect and recover execution state from a durable checkpoint."""
    context: GatewayRequestContext
    checkpoint_id: str


@dataclass(repr=False)
class PauseExecutionRequest(SecretSafeDTO):
    """Semantic request to pause active streaming or CDC operations."""
    context: GatewayRequestContext


@dataclass(repr=False)
class ResumeExecutionRequest(SecretSafeDTO):
    """Semantic request to resume paused operations from durable state."""
    context: GatewayRequestContext


@dataclass(repr=False)
class CancelExecutionRequest(SecretSafeDTO):
    """Semantic request to cancel active background tasks."""
    context: GatewayRequestContext


@dataclass(repr=False)
class GetProgressRequest(SecretSafeDTO):
    """Semantic request to query real-time migration progress metrics."""
    context: GatewayRequestContext


@dataclass(repr=False)
class GetHealthDiagnosticsRequest(SecretSafeDTO):
    """Semantic request to query connection and platform health diagnostics."""
    context: GatewayRequestContext


@dataclass(repr=False)
class ExecuteDataCleansingRequest(SecretSafeDTO):
    """Semantic request to execute data cleansing rules on record batches."""
    context: GatewayRequestContext
    records: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]


@dataclass(repr=False)
class ApplyPrivacyMaskingRequest(SecretSafeDTO):
    """Semantic request to apply privacy masking and tokenization rules."""
    context: GatewayRequestContext
    records: List[Dict[str, Any]]
    privacy_rules: List[Dict[str, Any]]


@dataclass(repr=False)
class ReconcileDisputedRecordsRequest(SecretSafeDTO):
    """Semantic request to reconcile disputed records identified by validation."""
    context: GatewayRequestContext
    disputed_records: List[Dict[str, Any]]


@dataclass(repr=False)
class RollbackTransactionBatchRequest(SecretSafeDTO):
    """Semantic request to rollback an uncommitted or poisoned transaction batch."""
    context: GatewayRequestContext
    batch_id: str


@dataclass(repr=False)
class FinalizeMigrationRunRequest(SecretSafeDTO):
    """Semantic request to finalize a migration run and seal machine evidence."""
    context: GatewayRequestContext
    final_status: str = "COMPLETED"
