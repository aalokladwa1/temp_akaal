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


@dataclass
class GatewayRequest:
    """Generic base Gateway request wrapper carrying semantic operation and context."""
    operation: SemanticOperation
    context: GatewayRequestContext
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointTestConnectionRequest:
    """Semantic request to test endpoint connectivity & credentials."""
    context: GatewayRequestContext
    endpoint_spec: Dict[str, Any]
    auth_spec: Dict[str, Any]
    session_purpose: str = "HEALTH_PROBE"


@dataclass
class ResolveCapabilitiesRequest:
    """Semantic request to resolve connector capability support."""
    context: GatewayRequestContext
    provider_id: str
    required_capabilities: List[str] = field(default_factory=list)


@dataclass
class DiscoverCatalogRequest:
    """Semantic request to discover source/target catalog and metadata."""
    context: GatewayRequestContext
    endpoint_spec: Dict[str, Any]
    auth_spec: Dict[str, Any]
    depth: str = "STANDARD"
    scope_schemas: Optional[List[str]] = None


@dataclass
class CompileSchemaMappingRequest:
    """Semantic request to compile source-to-target schema mapping and DDL."""
    context: GatewayRequestContext
    source_discovery_snapshot: Dict[str, Any]
    target_dialect: str
    type_overrides: Dict[str, str] = field(default_factory=dict)


@dataclass
class ValidateSchemaCompatibilityRequest:
    """Semantic request to validate schema compatibility between source and target."""
    context: GatewayRequestContext
    source_schema_model: Dict[str, Any]
    target_schema_model: Dict[str, Any]


@dataclass
class PrepareMigrationRequest:
    """Semantic request to prepare execution resources, tables, and durability checkpoints."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    schema_mapping: Dict[str, Any]


@dataclass
class ExecuteBulkMigrationRequest:
    """Semantic request to execute historical parallel bulk data transport."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    table_mappings: List[Dict[str, Any]]
    parallelism: int = 4
    batch_size: int = 5000


@dataclass
class InitializeCDCRequest:
    """Semantic request to initialize real-time Change Data Capture stream."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    starting_position: Optional[Dict[str, Any]] = None


@dataclass
class ExecuteCDCSyncRequest:
    """Semantic request to execute continuous CDC change polling and delta application."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    batch_size: int = 1000


@dataclass
class EvaluateCutoverRequest:
    """Semantic request to evaluate 17-gate cutover readiness."""
    context: GatewayRequestContext
    cdc_boundary_position: str
    required_proof_categories: List[str] = field(default_factory=lambda: ["execution", "validation", "cdc"])


@dataclass
class RunValidationRequest:
    """Semantic request to execute row-level reconciliation and Merkle validation."""
    context: GatewayRequestContext
    source_endpoint: Dict[str, Any]
    target_endpoint: Dict[str, Any]
    validation_mode: str = "FULL"
    required_cdc_boundary: Optional[str] = None


@dataclass
class PackageEvidenceRequest:
    """Semantic request to package machine execution, validation, and CDC proof into an evidence manifest."""
    context: GatewayRequestContext
    artifacts: List[Any] = field(default_factory=list)


@dataclass
class VerifyEvidenceRequest:
    """Semantic request to verify evidence manifest integrity and contextual proof sufficiency."""
    context: GatewayRequestContext
    manifest: Any
    required_proof_categories: Optional[List[str]] = None


@dataclass
class ExecuteAtomicCutoverRequest:
    """Semantic request to perform final atomic cutover commit."""
    context: GatewayRequestContext
    cdc_boundary_position: str
    cutover_token: str


@dataclass
class TriggerCheckpointRequest:
    """Semantic request to force an explicit durable checkpoint flush."""
    context: GatewayRequestContext
    checkpoint_id: str


@dataclass
class RecoverFromCheckpointRequest:
    """Semantic request to inspect and recover execution state from a durable checkpoint."""
    context: GatewayRequestContext
    checkpoint_id: str


@dataclass
class PauseExecutionRequest:
    """Semantic request to pause active streaming or CDC operations."""
    context: GatewayRequestContext


@dataclass
class ResumeExecutionRequest:
    """Semantic request to resume paused operations from durable state."""
    context: GatewayRequestContext


@dataclass
class CancelExecutionRequest:
    """Semantic request to cancel active background tasks."""
    context: GatewayRequestContext


@dataclass
class GetProgressRequest:
    """Semantic request to query real-time migration progress metrics."""
    context: GatewayRequestContext


@dataclass
class GetHealthDiagnosticsRequest:
    """Semantic request to query connection and platform health diagnostics."""
    context: GatewayRequestContext


@dataclass
class ExecuteDataCleansingRequest:
    """Semantic request to execute data cleansing rules on record batches."""
    context: GatewayRequestContext
    records: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]


@dataclass
class ApplyPrivacyMaskingRequest:
    """Semantic request to apply privacy masking and tokenization rules."""
    context: GatewayRequestContext
    records: List[Dict[str, Any]]
    privacy_rules: List[Dict[str, Any]]


@dataclass
class ReconcileDisputedRecordsRequest:
    """Semantic request to reconcile disputed records identified by validation."""
    context: GatewayRequestContext
    disputed_records: List[Dict[str, Any]]


@dataclass
class RollbackTransactionBatchRequest:
    """Semantic request to rollback an uncommitted or poisoned transaction batch."""
    context: GatewayRequestContext
    batch_id: str


@dataclass
class FinalizeMigrationRunRequest:
    """Semantic request to finalize a migration run and seal machine evidence."""
    context: GatewayRequestContext
    final_status: str = "COMPLETED"
