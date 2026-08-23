"""
akaalEngine.gateway.api
=======================
Single Canonical Public Engine Façade: EngineGateway.
External production orchestration consumers require ONLY this module:
    from akaalEngine.gateway import EngineGateway
"""

import logging
from typing import Any, Dict, Optional

from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import (
    CompileSchemaMappingRequest,
    DiscoverCatalogRequest,
    EvaluateCutoverRequest,
    ExecuteBulkMigrationRequest,
    ExecuteCDCSyncRequest,
    GatewayRequest,
    PackageEvidenceRequest,
    PrepareMigrationRequest,
    ResolveCapabilitiesRequest,
    RunValidationRequest,
    EndpointTestConnectionRequest,
    VerifyEvidenceRequest,
)
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator
from akaalEngine.gateway.routing.dispatcher import GatewayDispatcher

logger = logging.getLogger("akaalEngine.gateway.api")


class EngineGateway:
    """Single Canonical External Entry Point into akaalEngine for production orchestration consumers."""

    def __init__(
        self,
        coordinator: Optional[GatewayCoordinator] = None,
        dispatcher: Optional[GatewayDispatcher] = None,
    ) -> None:
        self.coordinator = coordinator or GatewayCoordinator()
        self.dispatcher = dispatcher or GatewayDispatcher(coordinator=self.coordinator)

    def execute(self, request: Any) -> GatewayResponse[Any]:
        """Single primary entry point for executing any semantic Gateway request."""
        ctx = getattr(request, "context", None)
        mig_id = ctx.migration_id if ctx else "none"
        op_val = getattr(request, "operation", getattr(request, "__class__", "unknown"))
        logger.info("EngineGateway executing request: operation=%s migration_id=%s", op_val, mig_id)
        return self.dispatcher.dispatch(request)

    def dispatch(self, request: GatewayRequest) -> GatewayResponse[Any]:
        """Alias for execute() to support semantic dispatch patterns."""
        return self.execute(request)

    # -------------------------------------------------------------------------
    # Strongly-Typed Semantic Helper Methods
    # -------------------------------------------------------------------------

    def test_connection(self, req: EndpointTestConnectionRequest) -> GatewayResponse[Dict[str, Any]]:
        """Tests endpoint connectivity & authentication."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.TEST_CONNECTION,
            context=req.context,
            payload={
                "endpoint_spec": req.endpoint_spec,
                "auth_spec": req.auth_spec,
                "session_purpose": req.session_purpose,
            },
        )
        return self.execute(gw_req)

    def resolve_capabilities(self, req: ResolveCapabilitiesRequest) -> GatewayResponse[Dict[str, Any]]:
        """Resolves provider capability support."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.RESOLVE_CAPABILITIES,
            context=req.context,
            payload={
                "provider_id": req.provider_id,
                "required_capabilities": req.required_capabilities,
            },
        )
        return self.execute(gw_req)

    def discover_catalog(self, req: DiscoverCatalogRequest) -> GatewayResponse[Dict[str, Any]]:
        """Discovers database topology and metadata."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.DISCOVER_CATALOG,
            context=req.context,
            payload={
                "endpoint_spec": req.endpoint_spec,
                "auth_spec": req.auth_spec,
                "depth": req.depth,
                "scope_schemas": req.scope_schemas,
            },
        )
        return self.execute(gw_req)

    def compile_schema(self, req: CompileSchemaMappingRequest) -> GatewayResponse[Dict[str, Any]]:
        """Compiles schema DDL and type conversions."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.COMPILE_SCHEMA_MAPPING,
            context=req.context,
            payload={
                "source_discovery_snapshot": req.source_discovery_snapshot,
                "target_dialect": req.target_dialect,
                "type_overrides": req.type_overrides,
            },
        )
        return self.execute(gw_req)

    def prepare_migration(self, req: PrepareMigrationRequest) -> GatewayResponse[Dict[str, Any]]:
        """Prepares runtime resources, tables, and durability checkpoints."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.PREPARE_MIGRATION_EXECUTION,
            context=req.context,
            payload={
                "source_endpoint": req.source_endpoint,
                "target_endpoint": req.target_endpoint,
                "schema_mapping": req.schema_mapping,
            },
        )
        return self.execute(gw_req)

    def execute_bulk_migration(self, req: ExecuteBulkMigrationRequest) -> GatewayResponse[Dict[str, Any]]:
        """Orchestrates parallel bulk data transport."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.EXECUTE_BULK_MIGRATION,
            context=req.context,
            payload={
                "source_endpoint": req.source_endpoint,
                "target_endpoint": req.target_endpoint,
                "table_mappings": req.table_mappings,
                "parallelism": req.parallelism,
                "batch_size": req.batch_size,
            },
        )
        return self.execute(gw_req)

    def execute_cdc_sync(self, req: ExecuteCDCSyncRequest) -> GatewayResponse[Dict[str, Any]]:
        """Orchestrates continuous CDC delta stream sync."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.EXECUTE_CDC_SYNC,
            context=req.context,
            payload={
                "source_endpoint": req.source_endpoint,
                "target_endpoint": req.target_endpoint,
                "batch_size": req.batch_size,
            },
        )
        return self.execute(gw_req)

    def evaluate_cutover(self, req: EvaluateCutoverRequest) -> GatewayResponse[Dict[str, Any]]:
        """Evaluates 17-gate cutover readiness."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.EVALUATE_CUTOVER_READINESS,
            context=req.context,
            payload={
                "cdc_boundary_position": req.cdc_boundary_position,
                "required_proof_categories": req.required_proof_categories,
            },
        )
        return self.execute(gw_req)

    def run_validation(self, req: RunValidationRequest) -> GatewayResponse[Dict[str, Any]]:
        """Runs row-level validation and reconciliation."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.RUN_FINAL_VALIDATION,
            context=req.context,
            payload={
                "source_endpoint": req.source_endpoint,
                "target_endpoint": req.target_endpoint,
                "validation_mode": req.validation_mode,
                "required_cdc_boundary": req.required_cdc_boundary,
            },
        )
        return self.execute(gw_req)

    def package_evidence(self, req: PackageEvidenceRequest) -> GatewayResponse[Dict[str, Any]]:
        """Packages machine execution evidence into a SHA-256 manifest."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.PACKAGE_MACHINE_EVIDENCE,
            context=req.context,
            payload={"artifacts": req.artifacts},
        )
        return self.execute(gw_req)

    def verify_evidence(self, req: VerifyEvidenceRequest) -> GatewayResponse[Dict[str, Any]]:
        """Verifies evidence manifest tamper detection and proof sufficiency."""
        gw_req = GatewayRequest(
            operation=SemanticOperation.VERIFY_EVIDENCE_INTEGRITY,
            context=req.context,
            payload={
                "manifest": req.manifest,
                "required_proof_categories": req.required_proof_categories,
            },
        )
        return self.execute(gw_req)


_default_gateway_instance: Optional[EngineGateway] = None


def default_engine_gateway() -> EngineGateway:
    """Returns singleton instance of EngineGateway."""
    global _default_gateway_instance
    if _default_gateway_instance is None:
        _default_gateway_instance = EngineGateway()
    return _default_gateway_instance
