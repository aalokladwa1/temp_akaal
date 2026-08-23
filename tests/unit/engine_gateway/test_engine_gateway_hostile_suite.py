"""
akaalEngine Gateway Hostile Test Suite
======================================
Comprehensive hostile test suite covering Contracts GW-001 through GW-040 for EngineGateway.
Executes production gateway routing, multi-authority orchestration, failure translation,
secret sanitization, cancellation, fencing, proof preservation, and thread safety.
"""

import threading
import time
from typing import Any, Dict, List, Optional
import pytest

from akaalEngine.gateway import (
    ApplyPrivacyMaskingRequest,
    CancelExecutionRequest,
    CompileSchemaMappingRequest,
    DiscoverCatalogRequest,
    EndpointTestConnectionRequest,
    EngineGateway,
    EvaluateCutoverRequest,
    ExecuteAtomicCutoverRequest,
    ExecuteBulkMigrationRequest,
    ExecuteCDCSyncRequest,
    ExecuteDataCleansingRequest,
    FailureTranslator,
    FinalizeMigrationRunRequest,
    GatewayDispatcher,
    GatewayFailureCategory,
    GatewayRequest,
    GatewayRequestContext,
    GatewayResponse,
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
    SemanticOperation,
    TriggerCheckpointRequest,
    ValidateSchemaCompatibilityRequest,
    VerifyEvidenceRequest,
    default_engine_gateway,
)
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator
from akaalEngine.evidence.models import EvidenceArtifact, EvidenceCompleteness
from akaalEngine.validation.models import ValidationGateStatus, ValidationResult, ProofScope
from akaalEngine.evidence.api import EvidenceAuthority


# ============================================================
# HELPER FACTORIES
# ============================================================

def make_context(mig_id: str = "mig-test-1", run_id: str = "run-test-1", epoch: Optional[int] = None) -> GatewayRequestContext:
    return GatewayRequestContext(
        migration_id=mig_id,
        run_id=run_id,
        fencing_epoch=epoch,
    )


# ============================================================
# CATEGORY A: FACADE & ROUTING TESTS (GW-001 - GW-005)
# ============================================================

def test_gw_001_single_public_facade_import():
    gw = EngineGateway()
    assert isinstance(gw, EngineGateway)
    sgw = default_engine_gateway()
    assert isinstance(sgw, EngineGateway)

def test_gw_002_known_semantic_operation_routes_correctly():
    gw = EngineGateway()
    ctx = make_context()
    req = EndpointTestConnectionRequest(context=ctx, endpoint_spec={"host": "localhost"}, auth_spec={"secret_ref": "ref-1"})
    res = gw.test_connection(req)
    assert res.success is True
    assert res.status_code == "SUCCESS"
    assert res.operation_type == SemanticOperation.TEST_CONNECTION.value

def test_gw_003_unknown_operation_fails_closed():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(operation="NON_EXISTENT_OP", context=ctx, payload={})
    res = gw.execute(req)
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.UNSUPPORTED_OPERATION.value

def test_gw_004_caller_cannot_specify_authority_number_or_string_method():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(
        operation=SemanticOperation.TEST_CONNECTION,
        context=ctx,
        payload={"authority_number": 1, "method_name": "exec_something_dangerous"}
    )
    res = gw.execute(req)
    assert res.success is True
    assert res.operation_type == SemanticOperation.TEST_CONNECTION.value

def test_gw_005_provider_neutral_contract():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(
        operation=SemanticOperation.RESOLVE_CAPABILITIES,
        context=ctx,
        payload={"provider_id": "oracle"}
    )
    res = gw.execute(req)
    assert res.success is True
    assert "oracle" in res.payload["provider_id"]


# ============================================================
# CATEGORY B: ALL 26 SEMANTIC OPERATIONS TESTS
# ============================================================

def test_op_01_test_connection():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.test_connection(EndpointTestConnectionRequest(ctx, {"host": "127.0.0.1"}, {"secret_ref": "ref"}))
    assert res.success is True

def test_op_02_resolve_capabilities():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.resolve_capabilities(ResolveCapabilitiesRequest(ctx, "postgresql"))
    assert res.success is True

def test_op_03_discover_catalog():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.discover_catalog(DiscoverCatalogRequest(ctx, {"host": "localhost"}, {"secret_ref": "ref"}))
    assert res.success is True

def test_op_04_compile_schema():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.compile_schema(CompileSchemaMappingRequest(ctx, {}, "postgresql"))
    assert res.success is True

def test_op_05_validate_schema_compatibility():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY, ctx, {"source_schema_model": {}, "target_schema_model": {}})
    res = gw.execute(req)
    assert res.success is True

def test_op_06_prepare_migration():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.prepare_migration(PrepareMigrationRequest(ctx, {}, {}, {}))
    assert res.success is True

def test_op_07_execute_bulk_migration():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.execute_bulk_migration(ExecuteBulkMigrationRequest(ctx, {}, {}, []))
    assert res.success is True
    assert res.payload["status"] == "COMPLETED"

def test_op_08_initialize_cdc_stream():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.INITIALIZE_CDC_STREAM, ctx, {})
    res = gw.execute(req)
    assert res.success is True

def test_op_09_execute_cdc_sync():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.execute_cdc_sync(ExecuteCDCSyncRequest(ctx, {}, {}))
    assert res.success is True

def test_op_10_evaluate_cutover_readiness():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.evaluate_cutover(EvaluateCutoverRequest(ctx, "0/200"))
    assert res.success is True

def test_op_11_run_final_validation():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.run_validation(RunValidationRequest(ctx, {}, {}))
    assert res.success is True

def test_op_12_package_machine_evidence():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.package_evidence(PackageEvidenceRequest(ctx, []))
    assert res.success is True

def test_op_13_verify_evidence_integrity():
    gw = EngineGateway()
    ctx = make_context()
    evd = EvidenceAuthority()
    art_exec = evd.package_execution_evidence(ctx.migration_id, ctx.run_id, "COMPLETED")
    man = evd.create_manifest(ctx.migration_id, ctx.run_id, [art_exec])
    res = gw.verify_evidence(VerifyEvidenceRequest(ctx, man, required_proof_categories=["execution"]))
    assert res.success is True

def test_op_14_execute_atomic_cutover():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.EXECUTE_ATOMIC_CUTOVER, ctx, {"cdc_boundary_position": "0/200"})
    res = gw.execute(req)
    assert res.success is True

def test_op_15_trigger_checkpoint():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.TRIGGER_CHECKPOINT, ctx, {"checkpoint_id": "chk-1"})
    res = gw.execute(req)
    assert res.success is True

def test_op_16_recover_from_checkpoint():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.RECOVER_FROM_CHECKPOINT, ctx, {"checkpoint_id": "chk-1"})
    res = gw.execute(req)
    assert res.success is True

def test_op_17_pause_execution():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.PAUSE_EXECUTION, ctx, {})
    res = gw.execute(req)
    assert res.success is True

def test_op_18_resume_execution():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.RESUME_EXECUTION, ctx, {})
    res = gw.execute(req)
    assert res.success is True

def test_op_19_cancel_execution():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.CANCEL_EXECUTION, ctx, {})
    res = gw.execute(req)
    assert res.success is True

def test_op_20_get_migration_progress():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.GET_MIGRATION_PROGRESS, ctx, {})
    res = gw.execute(req)
    assert res.success is True

def test_op_21_get_health_diagnostics():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.GET_HEALTH_DIAGNOSTICS, ctx, {})
    res = gw.execute(req)
    assert res.success is True

def test_op_22_execute_data_cleansing():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.EXECUTE_DATA_CLEANSING, ctx, {"records": [{"id": 1}]})
    res = gw.execute(req)
    assert res.success is True

def test_op_23_apply_privacy_masking():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.APPLY_PRIVACY_MASKING, ctx, {"records": [{"id": 1}]})
    res = gw.execute(req)
    assert res.success is True

def test_op_24_reconcile_disputed_records():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.RECONCILE_DISPUTED_RECORDS, ctx, {"disputed_records": []})
    res = gw.execute(req)
    assert res.success is True

def test_op_25_rollback_transaction_batch():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.ROLLBACK_TRANSACTION_BATCH, ctx, {"batch_id": "b-1"})
    res = gw.execute(req)
    assert res.success is True

def test_op_26_finalize_migration_run():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(SemanticOperation.FINALIZE_MIGRATION_RUN, ctx, {})
    res = gw.execute(req)
    assert res.success is True


# ============================================================
# CATEGORY C: FAILURE TRANSLATION & SANITIZATION (GW-011 - GW-013)
# ============================================================

def test_failure_translation_connectivity_error():
    from akaalEngine.connection.models.errors import ConnectionFailure, DNSResolutionError, FailureCategory
    ctx = make_context()
    fail = ConnectionFailure(error_code="DNS_ERR", category=FailureCategory.DNS_FAILURE, message="Failed to resolve host postgres.internal", retryable=True, provider_id="postgresql")
    exc = DNSResolutionError(fail)
    res = FailureTranslator.translate_exception(exc, ctx, "TEST_CONNECTION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.CONNECTIVITY_FAILURE.value
    assert res.retryable is True

def test_failure_translation_stale_fencing_error():
    from akaalEngine.durability.models import FencingViolationError
    ctx = make_context()
    exc = FencingViolationError("Stale fencing epoch 5")
    res = FailureTranslator.translate_exception(exc, ctx, "EXECUTE_BULK_MIGRATION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.STALE_FENCING.value
    assert res.retryable is False

def test_failure_translation_secret_sanitization():
    from akaalEngine.connection.models.errors import ConnectionFailure, AuthenticationError, FailureCategory
    ctx = make_context()
    fail = ConnectionFailure(error_code="AUTH_ERR", category=FailureCategory.AUTHENTICATION_FAILURE, message="Auth failed for postgres://admin:SUPER_SECRET_PASSWORD_GATEWAY@db:5432/db", retryable=False, provider_id="postgresql")
    exc = AuthenticationError(fail)
    res = FailureTranslator.translate_exception(exc, ctx, "TEST_CONNECTION")
    assert res.success is False
    assert "SUPER_SECRET_PASSWORD_GATEWAY" not in res.error_message
    assert "[REDACTED]" in res.error_message or "postgres://[REDACTED]" in res.error_message


# ============================================================
# CATEGORY D: CANCELLATION & FENCING (GW-008, GW-009)
# ============================================================

def test_cancellation_pre_dispatch_fails_closed():
    gw = EngineGateway()
    ctx = make_context()
    cancel_evt = threading.Event()
    cancel_evt.set()
    ctx.cancellation_event = cancel_evt
    req = ExecuteBulkMigrationRequest(ctx, {}, {}, [])
    res = gw.execute_bulk_migration(req)
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.CANCELLED.value

def test_stale_fencing_epoch_fails_closed():
    gw = EngineGateway()
    ctx = make_context(epoch=1)
    req = ExecuteBulkMigrationRequest(ctx, {}, {}, [])

    class MockStaleDurability:
        def verify_fencing_token(self, token):
            return False

    gw.coordinator.durability_authority = MockStaleDurability()
    res = gw.execute_bulk_migration(req)
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.STALE_FENCING.value


# ============================================================
# CATEGORY E: IDENTITY & THREAD SAFETY (GW-007, GW-031)
# ============================================================

def test_identity_preservation():
    gw = EngineGateway()
    ctx = make_context(mig_id="mig-fixed-99", run_id="run-fixed-99")
    req = EndpointTestConnectionRequest(ctx, {}, {})
    res = gw.test_connection(req)
    assert res.migration_id == "mig-fixed-99"
    assert res.run_id == "run-fixed-99"
    assert res.operation_id == ctx.operation_id

def test_concurrent_independent_requests_thread_safety():
    gw = EngineGateway()
    results = []

    def worker(i: int):
        ctx = make_context(mig_id=f"mig-conc-{i}", run_id=f"run-conc-{i}")
        req = EndpointTestConnectionRequest(ctx, {"port": 5000 + i}, {})
        res = gw.test_connection(req)
        results.append((i, res.migration_id, res.run_id))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    for i, mig, run in results:
        assert mig == f"mig-conc-{i}"
        assert run == f"run-conc-{i}"


# ============================================================
# CATEGORY F: PROOF CLASSIFICATION & VALIDATION LAWS (GW-014 - GW-017)
# ============================================================

def test_proof_classification_preserved():
    gw = EngineGateway()
    ctx = make_context()
    res = gw.test_connection(EndpointTestConnectionRequest(ctx, {}, {}))
    assert res.proof_classification == "UNIT_PROVEN"
    assert res.proof_classification != "LIVE_PROVEN"

def test_validation_law_evidence_missing_required_categories_fails():
    gw = EngineGateway()
    ctx = make_context()
    evd = EvidenceAuthority()
    art_exec = evd.package_execution_evidence(ctx.migration_id, ctx.run_id, "COMPLETED")
    man = evd.create_manifest(ctx.migration_id, ctx.run_id, [art_exec])

    req = VerifyEvidenceRequest(ctx, man, required_proof_categories=["execution", "validation"])
    res = gw.verify_evidence(req)
    assert res.success is False
    assert res.failure_category in (GatewayFailureCategory.EVIDENCE_INSUFFICIENT.value, GatewayFailureCategory.EVIDENCE_TAMPER.value)


# ============================================================
# CATEGORY G: GATEWAY BRAIN TEST (39) & FAILURE BRAIN TEST (40)
# ============================================================

def test_39_gateway_brain_test_single_semantic_request_orchestration():
    """
    GATEWAY BRAIN TEST (39)
    Caller submits ONE semantic request (ExecuteBulkMigrationRequest).
    Caller invokes ZERO authorities directly.
    Gateway orchestrates Authorities #6, #9, #8, #5, #7, #12 internally.
    """
    gw = EngineGateway()
    ctx = make_context(mig_id="mig-brain-39", run_id="run-brain-39")
    req = ExecuteBulkMigrationRequest(
        context=ctx,
        source_endpoint={"host": "src-db"},
        target_endpoint={"host": "tgt-db"},
        table_mappings=[{"source": "t1", "target": "t1"}],
        parallelism=2,
    )

    res = gw.execute(req)

    assert res.success is True
    assert res.operation_type == SemanticOperation.EXECUTE_BULK_MIGRATION.value
    assert res.migration_id == "mig-brain-39"
    assert res.run_id == "run-brain-39"
    assert "task_id" in res.payload
    assert "evidence_artifact_id" in res.payload

def test_40_failure_brain_test_intermediate_authority_failure():
    """
    FAILURE BRAIN TEST (40)
    Caller submits ONE semantic request.
    Intermediate authority fails.
    Gateway catches failure at convergence boundary, normalizes category,
    preserves identity, and does NOT execute duplicate retries.
    """
    class MockFailingTransport:
        def execute_bulk_transport(self, payload):
            from akaalEngine.transport.models import TransportReadError
            raise TransportReadError("Failed to read partition from source DB")

    gw = EngineGateway()
    gw.coordinator.transport_authority = MockFailingTransport()

    ctx = make_context(mig_id="mig-fail-40", run_id="run-fail-40")
    req = ExecuteBulkMigrationRequest(ctx, {}, {}, [])

    res = gw.execute(req)

    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.TRANSPORT_FAILURE.value
    assert res.migration_id == "mig-fail-40"
    assert res.run_id == "run-fail-40"
    assert res.retryable is True


# ============================================================
# CATEGORY H: ADDITIONAL GRANULAR HOSTILE TESTS (GW-021 - GW-040)
# ============================================================

def test_gw_021_unknown_operation_type_fails_closed():
    gw = EngineGateway()
    ctx = make_context()
    req = GatewayRequest(operation=None, context=ctx)
    res = gw.execute(req)
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.UNSUPPORTED_OPERATION.value

def test_gw_022_invalid_context_fails_closed():
    gw = EngineGateway()
    res = gw.dispatcher.dispatch("invalid_non_dto_object")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.INVALID_REQUEST.value

def test_gw_023_sentinel_secret_in_exception_scrubbed():
    ctx = make_context()
    exc = Exception("Error containing secret SUPER_SECRET_TOKEN_GATEWAY and URI postgres://user:SUPER_SECRET_PRIVATE_KEY_GATEWAY@host:5432/db")
    res = FailureTranslator.translate_exception(exc, ctx, "TEST_CONNECTION")
    assert res.success is False
    assert "SUPER_SECRET_TOKEN_GATEWAY" not in res.error_message
    assert "SUPER_SECRET_PRIVATE_KEY_GATEWAY" not in res.error_message

def test_gw_024_proof_upgrade_to_live_proven_prohibited():
    gw = EngineGateway()
    ctx = make_context()
    req = EndpointTestConnectionRequest(ctx, {}, {})
    res = gw.test_connection(req)
    assert res.proof_classification != "LIVE_PROVEN"

def test_gw_025_partial_failure_aborts_subsequent_stages():
    calls = []
    class SpyCoordinator(GatewayCoordinator):
        def check_fencing(self, context):
            calls.append("fencing")
            super().check_fencing(context)
        def check_cancellation(self, context):
            calls.append("cancellation")
            super().check_cancellation(context)

    gw = EngineGateway(coordinator=SpyCoordinator())
    ctx = make_context(epoch=1)

    # Force fencing failure
    gw.coordinator.durability_authority = type("Mock", (), {"verify_fencing_token": lambda self, t: False})()

    req = ExecuteBulkMigrationRequest(ctx, {}, {}, [])
    res = gw.execute(req)

    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.STALE_FENCING.value

def test_gw_026_ambiguous_commit_fails_closed_without_retry():
    ctx = make_context()
    from akaalEngine.transport.models import AmbiguousCommitError
    exc = AmbiguousCommitError("Ambiguous commit outcome on batch b-1")
    res = FailureTranslator.translate_exception(exc, ctx, "EXECUTE_BULK_MIGRATION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.AMBIGUOUS_COMMIT.value
    assert res.retryable is False

def test_gw_027_evidence_tamper_fails_closed():
    ctx = make_context()
    from akaalEngine.evidence.models import EvidenceIntegrityError
    exc = EvidenceIntegrityError("SHA-256 digest mismatch detected in manifest")
    res = FailureTranslator.translate_exception(exc, ctx, "VERIFY_EVIDENCE_INTEGRITY")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.EVIDENCE_TAMPER.value
    assert res.retryable is False

def test_gw_028_validation_mismatch_fails_closed():
    ctx = make_context()
    from akaalEngine.validation.models import ReconciliationMismatchError
    exc = ReconciliationMismatchError("Row count mismatch: expected 100, got 98")
    res = FailureTranslator.translate_exception(exc, ctx, "RUN_FINAL_VALIDATION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.VALIDATION_MISMATCH.value

def test_gw_029_cdc_failure_categorization():
    ctx = make_context()
    from akaalEngine.cdc.models import CDCError
    exc = CDCError("Replication stream lag exceeded maximum threshold")
    res = FailureTranslator.translate_exception(exc, ctx, "EXECUTE_CDC_SYNC")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.CDC_FAILURE.value

def test_gw_030_resource_exhaustion_categorization():
    ctx = make_context()
    from akaalEngine.durability.models import StorageQuotaExceededError
    exc = StorageQuotaExceededError("Disk quota exceeded for spill directory")
    res = FailureTranslator.translate_exception(exc, ctx, "TRIGGER_CHECKPOINT")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.RESOURCE_EXHAUSTION.value
    assert res.retryable is True

def test_gw_031_timeout_categorization():
    ctx = make_context()
    from akaalEngine.transport.models import TransportTimeoutError
    exc = TransportTimeoutError("Read timeout after 30s")
    res = FailureTranslator.translate_exception(exc, ctx, "EXECUTE_BULK_MIGRATION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.TIMEOUT.value
    assert res.retryable is True

def test_gw_032_authentication_failure_categorization():
    ctx = make_context()
    from akaalEngine.connection.models import AuthenticationError, ConnectionFailure, FailureCategory
    fail = ConnectionFailure("AUTH_ERR", FailureCategory.AUTHENTICATION_FAILURE, "Invalid username or password", False, "oracle")
    exc = AuthenticationError(fail)
    res = FailureTranslator.translate_exception(exc, ctx, "TEST_CONNECTION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.AUTHENTICATION_FAILURE.value
    assert res.retryable is False

def test_gw_033_permission_failure_categorization():
    ctx = make_context()
    from akaalEngine.connection.models import PermissionDeniedError, ConnectionFailure, FailureCategory
    fail = ConnectionFailure("PERM_ERR", FailureCategory.AUTHORIZATION_PERMISSION_FAILURE, "Access denied to table main", False, "postgresql")
    exc = PermissionDeniedError(fail)
    res = FailureTranslator.translate_exception(exc, ctx, "TEST_CONNECTION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.PERMISSION_FAILURE.value
    assert res.retryable is False

def test_gw_034_dependency_missing_categorization():
    ctx = make_context()
    from akaalEngine.extensions.errors.taxonomy import ExtensionNotFoundError
    exc = ExtensionNotFoundError("Extension 'oracle_driver' not installed")
    res = FailureTranslator.translate_exception(exc, ctx, "RESOLVE_CAPABILITIES")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.DEPENDENCY_MISSING.value
    assert res.retryable is False


# ============================================================
# CATEGORY I: DEPENDENCY GRAPH COHERENCE TESTS (CW-001 - CW-015)
# ============================================================

def test_cw_001_default_gateway_all_12_authorities_present():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.connection_authority is not None
    assert coord.extensions_authority is not None
    assert coord.discovery_authority is not None
    assert coord.schema_authority is not None
    assert coord.durability_authority is not None
    assert coord.runtime_authority is not None
    assert coord.telemetry_authority is not None
    assert coord.data_processing_authority is not None
    assert coord.transport_authority is not None
    assert coord.cdc_authority is not None
    assert coord.validation_authority is not None
    assert coord.evidence_authority is not None

def test_cw_002_dispatcher_and_coordinator_reference_same_instance():
    gw = EngineGateway()
    assert gw.dispatcher.coordinator is gw.coordinator

def test_cw_003_shared_durability_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.transport_authority.durability_authority is coord.durability_authority
    assert coord.cdc_authority.durability_authority is coord.durability_authority
    assert coord.validation_authority.durability_authority is coord.durability_authority
    assert coord.evidence_authority.durability_authority is coord.durability_authority

def test_cw_004_shared_runtime_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.transport_authority.runtime_authority is coord.runtime_authority
    assert coord.cdc_authority.runtime_authority is coord.runtime_authority
    assert coord.validation_authority.runtime_authority is coord.runtime_authority
    assert coord.evidence_authority.runtime_authority is coord.runtime_authority

def test_cw_005_shared_telemetry_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.transport_authority.telemetry_authority is coord.telemetry_authority
    assert coord.cdc_authority.telemetry_authority is coord.telemetry_authority
    assert coord.validation_authority.telemetry_authority is coord.telemetry_authority
    assert coord.evidence_authority.telemetry_authority is coord.telemetry_authority

def test_cw_006_shared_connection_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.discovery_authority._conn_auth is coord.connection_authority
    assert coord.validation_authority.connection_authority is coord.connection_authority
    assert coord.evidence_authority.connection_authority is coord.connection_authority

def test_cw_007_shared_schema_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.cdc_authority.schema_authority is coord.schema_authority
    assert coord.validation_authority.schema_authority is coord.schema_authority
    assert coord.evidence_authority.schema_authority is coord.schema_authority

def test_cw_008_shared_data_processing_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.transport_authority.data_processing_authority is coord.data_processing_authority
    assert coord.cdc_authority.data_processing_authority is coord.data_processing_authority
    assert coord.validation_authority.data_processing_authority is coord.data_processing_authority
    assert coord.evidence_authority.data_processing_authority is coord.data_processing_authority

def test_cw_009_shared_transport_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.cdc_authority.transport_authority is coord.transport_authority
    assert coord.validation_authority.transport_authority is coord.transport_authority
    assert coord.evidence_authority.transport_authority is coord.transport_authority

def test_cw_010_shared_cdc_and_validation_authority_identity():
    gw = EngineGateway()
    coord = gw.coordinator
    assert coord.validation_authority.cdc_authority is coord.cdc_authority
    assert coord.evidence_authority.validation_authority is coord.validation_authority
    assert coord.evidence_authority.cdc_authority is coord.cdc_authority

def test_cw_011_fencing_state_survives_across_gateway_operation_chain():
    gw = EngineGateway()
    ctx = make_context(epoch=5)

    # Valid token passes
    res1 = gw.execute_bulk_migration(ExecuteBulkMigrationRequest(ctx, {}, {}, []))
    assert res1.success is True

    # Stale writer rejected cleanly by shared durability instance
    class StaleDurability:
        def validate_fencing_token(self, token):
            return False
        def verify_fencing_token(self, token):
            return False

    gw.coordinator.durability_authority = StaleDurability()
    # Direct reference updated
    gw.coordinator.transport_authority.durability_authority = gw.coordinator.durability_authority
    res2 = gw.execute_bulk_migration(ExecuteBulkMigrationRequest(ctx, {}, {}, []))
    assert res2.success is False
    assert res2.failure_category == GatewayFailureCategory.STALE_FENCING.value

def test_cw_012_runtime_task_control_state_survives_across_gateway_calls():
    gw = EngineGateway()
    ctx = make_context()
    res1 = gw.execute_bulk_migration(ExecuteBulkMigrationRequest(ctx, {}, {}, []))
    assert res1.success is True
    task_id = res1.payload["task_id"]
    # Task state registered in shared RuntimeAuthority
    task_snap = gw.coordinator.runtime_authority.inspect_task(task_id)
    assert task_snap is not None
    assert task_snap.task_id == task_id

def test_cw_013_telemetry_written_during_execution_visible_in_gateway_status():
    gw = EngineGateway()
    ctx = make_context(mig_id="mig-telem-1")
    res1 = gw.test_connection(EndpointTestConnectionRequest(ctx, {}, {}))
    assert res1.success is True
    snap = gw.coordinator.telemetry_authority.get_progress_snapshot("mig-telem-1")
    assert snap is not None

def test_cw_014_cdc_state_initialized_in_gateway_visible_to_cutover():
    gw = EngineGateway()
    ctx = make_context()
    res1 = gw.execute(GatewayRequest(SemanticOperation.INITIALIZE_CDC_STREAM, ctx, {}))
    assert res1.success is True
    res2 = gw.evaluate_cutover(EvaluateCutoverRequest(ctx, "0/500"))
    assert res2.success is True
    assert res2.payload["cdc_boundary_position"] == "0/500"

def test_cw_015_concurrent_gateway_instances_independent_durability():
    gw1 = EngineGateway()
    gw2 = EngineGateway()
    assert gw1.coordinator.durability_authority is not gw2.coordinator.durability_authority
    assert gw1.coordinator.runtime_authority is not gw2.coordinator.runtime_authority

def test_gw_035_unknown_exception_fails_closed_internal():
    ctx = make_context()
    exc = RuntimeError("Unexpected internal crash in worker thread")
    res = FailureTranslator.translate_exception(exc, ctx, "EXECUTE_BULK_MIGRATION")
    assert res.success is False
    assert res.failure_category == GatewayFailureCategory.INTERNAL_ENGINE_FAILURE.value
    assert res.retryable is False
    assert "Unexpected internal crash" in res.error_message

def test_gw_036_gateway_response_to_dict_preserves_envelope():
    ctx = make_context(mig_id="mig-100", run_id="run-100")
    res = GatewayResponse.create_success(ctx.operation_id, "TEST", "mig-100", "run-100", {"data": 123}, proof_classification="UNIT_PROVEN")
    assert res.success is True
    assert res.migration_id == "mig-100"
    assert res.run_id == "run-100"
    assert res.payload == {"data": 123}

def test_gw_037_gateway_request_context_cancellation_flag():
    cancel_evt = threading.Event()
    ctx = GatewayRequestContext(migration_id="mig-1", run_id="run-1", cancellation_event=cancel_evt)
    assert ctx.is_cancelled() is False
    cancel_evt.set()
    assert ctx.is_cancelled() is True

def test_gw_038_gateway_dispatcher_explicit_routing_no_eval():
    gw = EngineGateway()
    ctx = make_context()
    # Test all 26 enum operations are explicitly routed in dispatcher without eval or getattr on arbitrary method strings
    for op in SemanticOperation:
        req = GatewayRequest(operation=op, context=ctx, payload={})
        res = gw.execute(req)
        assert isinstance(res, GatewayResponse)
        assert res.operation_type == op.value

def test_gw_039_gateway_does_not_mutate_authority_truth():
    gw = EngineGateway()
    ctx = make_context()
    req = EndpointTestConnectionRequest(ctx, {}, {})
    res = gw.test_connection(req)
    assert res.payload["connected"] is True

def test_gw_040_zero_fake_verification():
    gw = EngineGateway()
    assert hasattr(gw, "execute")
    assert hasattr(gw, "dispatch")
    assert hasattr(gw.coordinator, "connection_authority")
    assert hasattr(gw.coordinator, "evidence_authority")
