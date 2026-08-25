"""
akaalEngine.gateway
===================
Final Engine Convergence & Multi-Authority Orchestration Gateway.
Single Canonical External Entry Point into akaalEngine for production orchestration consumers.
Exposes EngineGateway, default_engine_gateway, request DTOs, response DTOs, and semantic enums.
"""

from akaalEngine.gateway.api import EngineGateway, default_engine_gateway
from akaalEngine.gateway.failure.translator import FailureTranslator
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.requests import (
    ApplyPrivacyMaskingRequest,
    CancelExecutionRequest,
    CompileSchemaMappingRequest,
    DiscoverCatalogRequest,
    EvaluateCutoverRequest,
    ExecuteAtomicCutoverRequest,
    ExecuteBulkMigrationRequest,
    ExecuteCDCSyncRequest,
    ExecuteDataCleansingRequest,
    FinalizeMigrationRunRequest,
    GatewayRequest,
    GetHealthDiagnosticsRequest,
    GetProgressRequest,
    InitializeCDCRequest,
    PackageEvidenceRequest,
    PauseExecutionRequest,
    PrepareMigrationRequest,
    ReconcileDisputedRecordsRequest,
    RecoverFromCheckpointRequest,
    ResolveCapabilitiesRequest,
    ResumeExecutionRequest,
    RollbackTransactionBatchRequest,
    RunValidationRequest,
    EndpointTestConnectionRequest,
    TriggerCheckpointRequest,
    ValidateSchemaCompatibilityRequest,
    VerifyEvidenceRequest,
)
from akaalEngine.gateway.models.errors import (
    GatewayAdmissionError,
    GatewayConfigurationError,
    GatewayError,
    GatewaySecurityError,
)
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator
from akaalEngine.gateway.routing.dispatcher import GatewayDispatcher

__all__ = [
    # Single Canonical Engine Façade
    "EngineGateway",
    "default_engine_gateway",
    # Gateway Core Components
    "GatewayDispatcher",
    "GatewayCoordinator",
    "FailureTranslator",
    # Gateway Exceptions
    "GatewayError",
    "GatewayConfigurationError",
    "GatewaySecurityError",
    "GatewayAdmissionError",
    # Models & Enums
    "SemanticOperation",
    "GatewayFailureCategory",
    "GatewayRequestContext",
    "GatewayRequest",
    "GatewayResponse",
    # Semantic Request DTOs
    "EndpointTestConnectionRequest",
    "ResolveCapabilitiesRequest",
    "DiscoverCatalogRequest",
    "CompileSchemaMappingRequest",
    "ValidateSchemaCompatibilityRequest",
    "PrepareMigrationRequest",
    "ExecuteBulkMigrationRequest",
    "InitializeCDCRequest",
    "ExecuteCDCSyncRequest",
    "EvaluateCutoverRequest",
    "RunValidationRequest",
    "PackageEvidenceRequest",
    "VerifyEvidenceRequest",
    "ExecuteAtomicCutoverRequest",
    "TriggerCheckpointRequest",
    "RecoverFromCheckpointRequest",
    "PauseExecutionRequest",
    "ResumeExecutionRequest",
    "CancelExecutionRequest",
    "GetProgressRequest",
    "GetHealthDiagnosticsRequest",
    "ExecuteDataCleansingRequest",
    "ApplyPrivacyMaskingRequest",
    "ReconcileDisputedRecordsRequest",
    "RollbackTransactionBatchRequest",
    "FinalizeMigrationRunRequest",
]
