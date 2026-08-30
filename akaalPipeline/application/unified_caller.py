import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

logger = logging.getLogger("akaalPipeline.application.unified_caller")
from akaalIPC.protocol.envelopes import CommandEnvelope, OperationReference, QueryEnvelope
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error, sanitize_unexpected_exception
from akaalIPC.transport.ports import CallerResult, CallerResultStatus, UnifiedCallerPort
from akaalPipeline.application.command_handlers import CommandHandlerRegistry
from akaalPipeline.application.query_service import PipelineQueryService
from akaalPipeline.capabilities.bindings import BindingRegistry, EngineBindingDescriptor
from akaalPipeline.capabilities.catalog import CapabilityCatalog
from akaalPipeline.capabilities.resolver import CapabilityResolver
from akaalPipeline.configuration.invalidation import ConfigurationInvalidator
from akaalPipeline.contracts.enums import CapabilityDimension, MigrationLifecycleState, MigrationMode, OperationStatus
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode, PolicyDeniedError
from akaalPipeline.contracts.serialization import canonical_fingerprint
from akaalPipeline.events.audit import AuditTrailService
from akaalPipeline.events.outbox import OutboxService
from akaalPipeline.events.schemas import DomainEvent
from akaalPipeline.execution.controller import PipelineExecutionController
from akaalPipeline.execution.coordinator import PlanExecutionCoordinator
from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.identity.lineage import LineageTracker
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.service import OperationService
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.policy.contracts import PolicyDecision
from akaalPipeline.policy.gates import PolicyGateEvaluator
from akaalIPC.security.context import ActorContext
from akaalPipeline.ports.engine import (
    EngineInvocationRequest,
    EngineInvocationResult,
    ExecutionPort,
)
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.artifacts import ArtifactRegistry, ImmutableArtifact
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork, UnitOfWorkPort


class PipelineUnifiedCaller(UnifiedCallerPort):
    def __init__(
        self,
        db_path: Optional[str] = None,
        shared_uow: Optional[SQLiteUnitOfWork] = None,
        bind_gateway: bool = False,
        central_authz: Optional[Any] = None,
        threat_detector: Optional[Any] = None,
    ) -> None:
        if db_path is None and shared_uow is None:
            raise ValueError("PipelineUnifiedCaller requires an explicit db_path or shared_uow.")
        self.db_path = db_path or (shared_uow.db_path if shared_uow else None)
        self._shared_uow = shared_uow
        self.central_authz = central_authz
        self.threat_detector = threat_detector

        self.repository = SQLiteMigrationRepository(db_path=self.db_path)

        self.operation_service = OperationService()
        self.idempotency_service = IdempotencyService()
        self.catalog = CapabilityCatalog()
        self.binding_registry = BindingRegistry()
        self._init_catalog()
        if bind_gateway:
            self.bind_engine_gateway()

        self.artifact_registry = ArtifactRegistry()
        self.outbox_service = OutboxService()
        self.audit_service = AuditTrailService()

        self.capability_resolver = CapabilityResolver(self.catalog, self.binding_registry)
        self.catalog_resolver = self.capability_resolver
        self.lease_manager = LeaseManager()
        self.result_reconciler = ResultReconciler(self.lease_manager)
        self.execution_controller = PipelineExecutionController(
            self.capability_resolver,
            self.binding_registry,
            self.lease_manager,
            self.operation_service,
        )
        self.plan_coordinator = PlanExecutionCoordinator(
            self.capability_resolver,
            self.binding_registry,
            self.lease_manager,
            self.operation_service,
            self.result_reconciler,
            self.outbox_service,
            self.audit_service,
            self.repository,
        )
        self.command_handlers = CommandHandlerRegistry(
            self.repository,
            self.operation_service,
            self.idempotency_service,
            self.execution_controller,
            self.outbox_service,
            self.audit_service,
            self.artifact_registry,
            plan_coordinator=self.plan_coordinator,
        )
        self.query_service = PipelineQueryService(
            self.repository,
            self.operation_service,
        )
        self.schedule_service = self.command_handlers.schedule_service
        self.retention_service = self.command_handlers.retention_service
        self.capacity_service = self.command_handlers.capacity_service
        self.alert_service = self.command_handlers.alert_service
        self.incident_service = self.command_handlers.incident_service
        self.notification_service = self.command_handlers.notification_service

    def close(self) -> None:
        """Closes bound EngineGateway resources cleanly."""
        binding = self.binding_registry.get("gateway_engine_binding")
        if binding and hasattr(binding.port_instance, "close"):
            try:
                binding.port_instance.close()
            except Exception:
                pass

    def _init_catalog(self) -> None:
        from akaalPipeline.capabilities.catalog import CapabilityDescriptor
        from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="data_transport",
                name="Data Transport",
                supported_modes={
                    MigrationMode.M1_BULK,
                    MigrationMode.M2_BULK_CDC,
                    MigrationMode.M4_INCREMENTAL,
                    MigrationMode.M5_STATE_SYNC,
                    MigrationMode.M7_DATA_ONLY,
                },
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="schema_prep",
                name="Schema Prep",
                supported_modes={MigrationMode.M1_BULK, MigrationMode.M2_BULK_CDC},
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="schema_extract",
                name="Schema Extract",
                supported_modes={MigrationMode.M6_SCHEMA_ONLY},
                side_effect=SideEffectClassification.READ_ONLY,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="schema_apply",
                name="Schema Apply",
                supported_modes={MigrationMode.M6_SCHEMA_ONLY},
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="cdc_sync",
                name="CDC Sync",
                supported_modes={MigrationMode.M2_BULK_CDC},
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="cdc_capture",
                name="CDC Capture",
                supported_modes={MigrationMode.M2_BULK_CDC, MigrationMode.M3_CDC},
                side_effect=SideEffectClassification.READ_ONLY,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="cdc_apply",
                name="CDC Apply",
                supported_modes={MigrationMode.M2_BULK_CDC, MigrationMode.M3_CDC},
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="incremental_extract",
                name="Incremental Extract",
                supported_modes={MigrationMode.M4_INCREMENTAL},
                side_effect=SideEffectClassification.READ_ONLY,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="incremental_apply",
                name="Incremental Apply",
                supported_modes={MigrationMode.M4_INCREMENTAL},
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="state_diff",
                name="State Diff",
                supported_modes={MigrationMode.M5_STATE_SYNC},
                side_effect=SideEffectClassification.READ_ONLY,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="state_reconcile",
                name="State Reconcile",
                supported_modes={MigrationMode.M5_STATE_SYNC},
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="validation_compare",
                name="Validation Compare",
                supported_modes={MigrationMode.M1_BULK, MigrationMode.M2_BULK_CDC, MigrationMode.M3_CDC, MigrationMode.M5_STATE_SYNC, MigrationMode.M7_DATA_ONLY, MigrationMode.M8_VALIDATION_ONLY},
                side_effect=SideEffectClassification.READ_ONLY,
            )
        )

    def bind_engine_gateway(self, gateway: Optional[Any] = None) -> None:
        from akaalPipeline.adapters.engine_gateway import PipelineEngineGatewayAdapter
        from akaalEngine.gateway.api import EngineGateway
        gw_instance = gateway or EngineGateway()
        adapter = PipelineEngineGatewayAdapter(gateway=gw_instance)
        binding_desc = EngineBindingDescriptor(
            binding_id="gateway_engine_binding",
            engine_name="akaalEngineGateway",
            version="1.0.0",
            port_instance=adapter,
            is_healthy=True,
            supported_capabilities={
                "data_transport",
                "schema_prep",
                "schema_extract",
                "schema_apply",
                "cdc_sync",
                "cdc_capture",
                "cdc_apply",
                "incremental_extract",
                "incremental_apply",
                "state_diff",
                "state_reconcile",
                "validation_compare",
            },
            supported_modes=set(MigrationMode),
        )
        self.binding_registry.register(binding_desc)

    def _create_uow(self) -> SQLiteUnitOfWork:
        if self._shared_uow:
            return self._shared_uow
        return SQLiteUnitOfWork(db_path=self.db_path)

    def handle_command(self, envelope: Any) -> CallerResult:
        if isinstance(envelope, dict):
            from akaalIPC.protocol.envelopes import CommandEnvelope, CorrelationContext
            from akaalIPC.security.context import ActorContext, ActorReference
            from akaalIPC.protocol.schemas import RequestKind
            actor_dict = envelope.get("actor_context") or envelope.get("actor")
            if actor_dict:
                actor_ref = ActorReference(
                    actor_id=actor_dict.get("principal_id") or actor_dict.get("actor_id", "anonymous"),
                    actor_type=actor_dict.get("actor_type", "human"),
                )
                actor_ctx = ActorContext(
                    actor=actor_ref,
                    organization_id=actor_dict.get("tenant_id", "default"),
                    provenance=actor_dict.get("provenance", "external"),
                )
            else:
                actor_ctx = None
            req_id = envelope.get("command_id") or envelope.get("envelope_id", str(uuid.uuid4()))
            req_type = envelope.get("command_type") or envelope.get("request_type") or envelope.get("command_id", "UNKNOWN")
            envelope = CommandEnvelope(
                request_id=req_id,
                protocol_version="1.0",
                schema_version="1.0",
                request_type=req_type,
                kind=RequestKind.COMMAND,
                actor=actor_ctx,
                correlation=CorrelationContext(correlation_id=req_id, request_id=req_id),
                payload=envelope.get("payload", {}),
                command_id=req_id,
                idempotency_key=envelope.get("idempotency_key"),
            )

        correlation_id = envelope.correlation.correlation_id if envelope.correlation else str(uuid.uuid4())
        request_id = envelope.request_id

        # 1. Convert IPC ActorContext to PipelineActorContext & validate authorization
        if envelope.actor is None or envelope.actor.actor is None:
            return CallerResult(
                status=CallerResultStatus.ERROR,
                error=make_error(
                    IPCErrorCategory.UNAUTHORIZED,
                    code="MISSING_ACTOR_CONTEXT",
                    message="Command envelope has no actor context.",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )
        pipeline_actor = PipelineActorContext.from_ipc(envelope.actor)

        # Reject SYSTEM actor spoofing from external envelope
        if pipeline_actor.actor_type.lower() == "system" and envelope.actor.provenance != "internal-core":
            return CallerResult(
                status=CallerResultStatus.ERROR,
                error=make_error(
                    IPCErrorCategory.UNAUTHORIZED,
                    code="SYSTEM_ACTOR_SPOOFING_PROHIBITED",
                    message="External callers are prohibited from asserting system actor identity.",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )

        payload_fp = canonical_fingerprint(envelope.payload)
        uow = self._create_uow()

        try:
            # 2. Idempotency Check (A-01: Same key + same request payload => same semantic response)
            if envelope.idempotency_key:
                with uow:
                    cached_result = self.idempotency_service.get_idempotent_result(
                        idempotency_key=envelope.idempotency_key,
                        tenant_id=pipeline_actor.organization_id,
                        payload_fingerprint=payload_fp,
                        conn=uow.connection,
                        workspace_id=pipeline_actor.workspace_id,
                        project_id=pipeline_actor.project_id,
                        command_name=envelope.request_type,
                    )
                if cached_result is not None:
                    if isinstance(cached_result, Mapping) and "_operation_reference" in cached_result:
                        op_data = cached_result["_operation_reference"]
                        return CallerResult(
                            status=CallerResultStatus.ACCEPTED,
                            operation=OperationReference(
                                operation_id=op_data["operation_id"],
                                accepted_at=op_data["accepted_at"],
                                query_request_type=op_data.get("query_request_type", "operation.get"),
                                correlation_id=op_data.get("correlation_id", correlation_id),
                            ),
                        )
                    if isinstance(cached_result, Mapping) and "_error_category" in cached_result:
                        cat_str = cached_result["_error_category"]
                        cat = getattr(IPCErrorCategory, cat_str, IPCErrorCategory.INTERNAL_ERROR)
                        return CallerResult(
                            status=CallerResultStatus.ERROR,
                            error=make_error(
                                cat,
                                code=cached_result.get("_error_code", "CACHED_ERROR"),
                                message=cached_result.get("_error_message", "Idempotent cached error"),
                                correlation_id=correlation_id,
                                request_id=request_id,
                            ),
                        )
                    return CallerResult(
                        status=CallerResultStatus.OK,
                        result=cached_result,
                    )
            request_type = envelope.request_type

            # Central Authorization Check (Dynamic RBAC + ABAC)
            if getattr(self, "central_authz", None) is not None:
                from akaalPipeline.contracts.errors import ForbiddenError, UnauthorizedError
                from akaalPipeline.security.permission_registry import PermissionRegistry
                from akaalPipeline.contracts.enums import SecurityAlertSeverity
                perm_map = {
                    "migration.create": PermissionRegistry.MIGRATION_CREATE,
                    "create_migration": PermissionRegistry.MIGRATION_CREATE,
                    "migration.configure": PermissionRegistry.MIGRATION_CONFIGURE,
                    "configure_migration": PermissionRegistry.MIGRATION_CONFIGURE,
                    "migration.plan": PermissionRegistry.MIGRATION_PLAN,
                    "plan_migration": PermissionRegistry.MIGRATION_PLAN,
                    "migration.initialize": PermissionRegistry.MIGRATION_PLAN,
                    "initialize_migration": PermissionRegistry.MIGRATION_PLAN,
                    "migration.approve": PermissionRegistry.GOVERNANCE_APPROVAL_SUBMIT,
                    "approve_migration": PermissionRegistry.GOVERNANCE_APPROVAL_SUBMIT,
                    "migration.start": PermissionRegistry.MIGRATION_EXECUTE,
                    "start_migration": PermissionRegistry.MIGRATION_EXECUTE,
                    "migration.cancel": PermissionRegistry.MIGRATION_CANCEL,
                    "cancel_migration": PermissionRegistry.MIGRATION_CANCEL,
                    "migration.recover": PermissionRegistry.MIGRATION_RECOVER,
                    "recover_migration": PermissionRegistry.MIGRATION_RECOVER,
                    "migration.pause": PermissionRegistry.MIGRATION_PAUSE,
                    "pause_migration": PermissionRegistry.MIGRATION_PAUSE,
                    "migration.resume": PermissionRegistry.MIGRATION_RESUME,
                    "resume_migration": PermissionRegistry.MIGRATION_RESUME,
                    "schedule.create": PermissionRegistry.OPERATIONS_SCHEDULE_CREATE,
                    "create_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_CREATE,
                    "schedule.update": PermissionRegistry.OPERATIONS_SCHEDULE_UPDATE,
                    "update_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_UPDATE,
                    "schedule.arm": PermissionRegistry.OPERATIONS_SCHEDULE_ARM,
                    "arm_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_ARM,
                    "schedule.disable": PermissionRegistry.OPERATIONS_SCHEDULE_DISABLE,
                    "disable_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_DISABLE,
                    "schedule.enable": PermissionRegistry.OPERATIONS_SCHEDULE_ARM,
                    "enable_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_ARM,
                    "schedule.cancel": PermissionRegistry.OPERATIONS_SCHEDULE_CANCEL,
                    "cancel_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_CANCEL,
                    "schedule.delete": PermissionRegistry.OPERATIONS_SCHEDULE_DELETE,
                    "delete_schedule": PermissionRegistry.OPERATIONS_SCHEDULE_DELETE,
                    "retention.execute": PermissionRegistry.OPERATIONS_RETENTION_EXECUTE,
                    "execute_retention": PermissionRegistry.OPERATIONS_RETENTION_EXECUTE,
                }
                perm = perm_map.get(request_type, PermissionRegistry.MIGRATION_READ)
                res_id = envelope.payload.get("migration_id", "root") if isinstance(envelope.payload, dict) else "root"
                try:
                    self.central_authz.authorize(
                        actor_context=pipeline_actor,
                        permission_id=perm,
                        resource_type="migration",
                        resource_id=res_id,
                        raise_exceptions=True,
                    )
                except (ForbiddenError, UnauthorizedError) as auth_exc:
                    if getattr(self, "threat_detector", None) is not None:
                        self.threat_detector._emit_alert(
                            tenant_id=pipeline_actor.organization_id,
                            threat_type="UNAUTHORIZED_COMMAND_ATTEMPT",
                            severity=SecurityAlertSeverity.HIGH,
                            description=str(auth_exc),
                            actor_id=pipeline_actor.actor_id,
                            resource_type="migration",
                            resource_id=res_id,
                        )
                    cat = IPCErrorCategory.FORBIDDEN if isinstance(auth_exc, ForbiddenError) else IPCErrorCategory.UNAUTHORIZED
                    return CallerResult(
                        status=CallerResultStatus.ERROR,
                        error=make_error(
                            cat,
                            code=cat.name,
                            message=str(auth_exc),
                            correlation_id=correlation_id,
                            request_id=request_id,
                        ),
                    )

            # 3. Handle synchronous domain commands
            if request_type in ("migration.create", "create_migration"):
                with uow:
                    res = self.command_handlers.handle_create_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.configure", "configure_migration"):
                with uow:
                    res = self.command_handlers.handle_configure_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.cancel", "cancel_migration"):
                with uow:
                    res = self.command_handlers.handle_cancel_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.recover", "recover_migration"):
                with uow:
                    res = self.command_handlers.handle_recover_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.pause", "pause_migration"):
                with uow:
                    res = self.command_handlers.handle_pause_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.resume", "resume_migration"):
                with uow:
                    res = self.command_handlers.handle_resume_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.throttle_cdc", "throttle_cdc"):
                with uow:
                    res = self.command_handlers.handle_throttle_cdc(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("fleet.drain_node", "drain_node"):
                from akaalPipeline.fleet.fleet_service import FleetOperationalService
                with uow:
                    node_id = envelope.payload.get("node_id", "node-local")
                    fleet_svc = FleetOperationalService(binding_registry=self.binding_registry)
                    res = fleet_svc.drain_node(node_id, uow.connection, pipeline_actor)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("fleet.undrain_node", "undrain_node"):
                from akaalPipeline.fleet.fleet_service import FleetOperationalService
                with uow:
                    node_id = envelope.payload.get("node_id", "node-local")
                    fleet_svc = FleetOperationalService(binding_registry=self.binding_registry)
                    res = fleet_svc.undrain_node(node_id, uow.connection, pipeline_actor)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.create", "create_schedule"):
                with uow:
                    res = self.command_handlers.handle_create_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.update", "update_schedule"):
                with uow:
                    res = self.command_handlers.handle_update_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.arm", "arm_schedule"):
                with uow:
                    res = self.command_handlers.handle_arm_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.disable", "disable_schedule"):
                with uow:
                    res = self.command_handlers.handle_disable_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.enable", "enable_schedule"):
                with uow:
                    res = self.command_handlers.handle_enable_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.cancel", "cancel_schedule"):
                with uow:
                    res = self.command_handlers.handle_cancel_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("schedule.delete", "delete_schedule"):
                with uow:
                    res = self.command_handlers.handle_delete_schedule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("retention.execute", "execute_retention"):
                with uow:
                    res = self.command_handlers.handle_execute_retention(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("capacity.sample", "sample_capacity"):
                with uow:
                    res = self.command_handlers.handle_sample_capacity(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("alert.rule.create", "create_alert_rule"):
                with uow:
                    res = self.command_handlers.handle_create_alert_rule(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("alert.evaluate", "evaluate_alert"):
                with uow:
                    res = self.command_handlers.handle_evaluate_alert(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("alert.acknowledge", "acknowledge_alert"):
                with uow:
                    res = self.command_handlers.handle_acknowledge_alert(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("alert.resolve", "resolve_alert"):
                with uow:
                    res = self.command_handlers.handle_resolve_alert(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("alert.suppress", "suppress_alert"):
                with uow:
                    res = self.command_handlers.handle_suppress_alert(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("incident.create", "create_incident"):
                with uow:
                    res = self.command_handlers.handle_create_incident(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("incident.alert.attach", "attach_alert_to_incident"):
                with uow:
                    res = self.command_handlers.handle_attach_alert_to_incident(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("incident.status.update", "update_incident_status"):
                with uow:
                    res = self.command_handlers.handle_update_incident_status(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("notification.send", "send_notification"):
                with uow:
                    res = self.command_handlers.handle_send_notification(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.plan", "plan_migration"):


                with uow:
                    res = self.command_handlers.handle_plan_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.initialize", "initialize_migration"):
                with uow:
                    res = self.command_handlers.handle_initialize_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.approve", "approve_migration"):
                with uow:
                    res = self.command_handlers.handle_approve_migration(envelope.payload, pipeline_actor, uow)
                    if envelope.idempotency_key:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            res,
                            uow.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

            elif request_type in ("migration.start", "start_migration"):
                # A-04, A-06, A-07: Real Start Admission & Durable Acceptance Before Engine Dispatch
                mig_id = envelope.payload.get("migration_id", "mig-1")
                op_id = f"op-{uuid.uuid4().hex}"
                att_id = f"att-{uuid.uuid4().hex}"

                # --- PHASE 1: Durable Admission & Acceptance in UoW (BEFORE Engine Dispatch) ---
                with uow:
                    # 1. Validate migration exists & actor scope (NEVER auto-create missing migration)
                    agg = self.repository.get_by_id(mig_id, connection=uow.connection)
                    if agg is None:
                        raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {mig_id!r} not found.")

                    if agg.tenant_id != pipeline_actor.organization_id:
                        raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {mig_id!r} not found or unauthorized for tenant.")
                    if pipeline_actor.workspace_id and agg.workspace_id and agg.workspace_id != pipeline_actor.workspace_id:
                        raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {mig_id!r} belongs to a different workspace.")
                    if pipeline_actor.project_id and agg.project_id and agg.project_id != pipeline_actor.project_id:
                        raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {mig_id!r} belongs to a different project.")

                    # 2. Validate requested mode against configured migration mode
                    requested_mode_str = envelope.payload.get("mode")
                    if requested_mode_str is not None:
                        mode_val = MigrationMode(requested_mode_str)
                        if mode_val != agg.mode:
                            raise PipelineError(
                                PipelineErrorCode.INVALID_REQUEST,
                                f"Requested mode {mode_val.value!r} does not match configured migration mode {agg.mode.value!r}.",
                            )
                    else:
                        mode_val = agg.mode

                    # 3. Validate lifecycle state
                    if agg.state not in (
                        MigrationLifecycleState.INITIALIZED,
                        MigrationLifecycleState.AUTHORIZED,
                        MigrationLifecycleState.ACTIVE,
                    ):
                        raise PipelineError(
                            PipelineErrorCode.INVALID_TRANSITION,
                            f"Cannot start migration in non-startable state {agg.state.value!r}. Migration must be INITIALIZED or AUTHORIZED before starting.",
                        )



                    # 4. Authoritative Immutable ExecutionPlan (MUST PRE-EXIST, NEVER CREATED IN START)
                    plan_art_id = agg.plan_id or f"art-plan-{mig_id}"
                    try:
                        plan_art = self.artifact_registry.get(plan_art_id, conn=uow.connection)
                    except PipelineError:
                        raise PipelineError(
                            PipelineErrorCode.NOT_READY,
                            f"Authoritative execution plan not found for migration {mig_id!r}. Migration must be planned before start.",
                        )


                    plan = ExecutionPlan.from_dict(plan_art.content)
                    GraphValidator.validate_plan(plan)


                    # 5. Authoritative Immutable Initialization Artifact (MUST PRE-EXIST, NEVER CREATED IN START)
                    if not agg.initialization_id:
                        raise PipelineError(
                            PipelineErrorCode.NOT_READY,
                            f"Migration {mig_id!r} has not been initialized. Migration must be initialized before start.",
                        )

                    try:
                        init_art = self.artifact_registry.get(agg.initialization_id, conn=uow.connection)
                    except PipelineError:
                        raise PipelineError(
                            PipelineErrorCode.NOT_READY,
                            f"Authoritative initialization artifact {agg.initialization_id!r} not found for migration {mig_id!r}.",
                        )

                    if init_art.content.get("plan_fingerprint") not in (plan.fingerprint, plan_art.fingerprint):
                        raise PipelineError(
                            PipelineErrorCode.NOT_READY,
                            "Initialization artifact plan fingerprint mismatch.",
                        )
                    init_fp = init_art.fingerprint

                    # 6. Policy Gate / Governance Approval Evaluation (Authoritative Persisted Authority Only)
                    policy_required = PolicyGateEvaluator.is_approval_required(agg.state, pipeline_actor)
                    approval_id = envelope.payload.get("approval_id") or envelope.payload.get("decision_id")
                    if not approval_id and envelope.payload.get("policy_decision"):
                        decision_data = envelope.payload.get("policy_decision")
                        if isinstance(decision_data, Mapping):
                            approval_id = decision_data.get("approval_id") or decision_data.get("decision_id")

                    if policy_required or approval_id or agg.state == MigrationLifecycleState.GOVERNANCE_PENDING:
                        effective_approval_id = approval_id or f"art-approval-{mig_id}"
                        try:
                            approval_art = self.artifact_registry.get(effective_approval_id, conn=uow.connection)
                        except PipelineError:
                            raise PolicyDeniedError(
                                f"Action requires authoritative governance approval, but persisted approval artifact {effective_approval_id!r} was not found."
                            )
                        decision = PolicyDecision.from_dict(approval_art.content)
                        PolicyGateEvaluator.evaluate_gate(
                            decision,
                            expected_resource_id=mig_id,
                            expected_action=envelope.request_type,
                            target_artifact_fingerprint=init_fp,
                            actor=pipeline_actor,
                        )




                    # 7. Materialize Durable Plan Execution & Initial Node States in UoW
                    plan_exec = self.plan_coordinator.materialize_plan_execution(
                        plan=plan,
                        migration=agg,
                        actor=pipeline_actor,
                        initialization_fingerprint=init_fp,
                        conn=uow.connection,
                        operation_id=op_id,
                    )


                    # 8. Create Accepted Operation Journal Record
                    op_rec = OperationRecord(
                        operation_id=op_id,
                        command_id=envelope.command_id,
                        idempotency_key=envelope.idempotency_key,
                        status=OperationStatus.ACCEPTED,
                        actor=pipeline_actor,
                        payload_fingerprint=payload_fp,
                    )
                    self.operation_service.create_operation(op_rec, uow.connection)

                    # 9. Update Aggregate Revision in UoW
                    agg.revision += 1
                    self.repository.save(agg, connection=uow.connection)

                    # 10. Record Outbox Event & Audit Record in SAME UoW
                    evt = DomainEvent.create(
                        mig_id,
                        "migration.start.accepted",
                        {"operation_id": op_id, "execution_id": plan_exec.execution_id},
                    )
                    self.outbox_service.stage_event(evt, uow.connection)
                    self.audit_service.record_event(
                        pipeline_actor,
                        "migration.start.accepted",
                        mig_id,
                        uow.connection,
                        details={"execution_id": plan_exec.execution_id},
                    )

                    # 11. Establish Operation Reference
                    accepted_at_str = datetime.now(timezone.utc).isoformat()
                    op_ref = OperationReference(
                        operation_id=op_id,
                        accepted_at=accepted_at_str,
                        query_request_type="operation.get",
                        correlation_id=correlation_id,
                    )

                # --- UoW EXITED HERE -> COMMIT COMPLETE! ---

                # --- PHASE 2: Canonical DAG Advancement via PlanExecutionCoordinator ---
                outcome = self.plan_coordinator.advance_plan_execution(
                    execution_id=plan_exec.execution_id,
                    plan=plan,
                    actor=pipeline_actor,
                    operation_id=op_id,
                    correlation_id=correlation_id,
                    request_id=request_id,
                    payload=envelope.payload,
                    uow_factory=self._create_uow,
                )

                if not outcome.is_success and outcome.error_category in (IPCErrorCategory.UNBOUND, IPCErrorCategory.UNAVAILABLE):
                    err = make_error(
                        outcome.error_category,
                        code=outcome.error_code or "UNAVAILABLE",
                        message=outcome.error_message or "Engine dispatch failed",
                        correlation_id=correlation_id,
                        request_id=request_id,
                    )
                    if envelope.idempotency_key:
                        with self._create_uow() as uow_idemp:
                            self.idempotency_service.record_idempotent_result(
                                envelope.idempotency_key,
                                pipeline_actor.organization_id,
                                envelope.command_id,
                                payload_fp,
                                {"_error_category": err.category.value, "_error_code": err.code, "_error_message": err.message},
                                uow_idemp.connection,
                                workspace_id=pipeline_actor.workspace_id,
                                project_id=pipeline_actor.project_id,
                                command_name=envelope.request_type,
                            )
                    return CallerResult(status=CallerResultStatus.ERROR, error=err)

                if envelope.idempotency_key:
                    with self._create_uow() as uow_idemp:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            {"_operation_reference": {"operation_id": op_id, "accepted_at": op_ref.accepted_at, "query_request_type": op_ref.query_request_type, "correlation_id": correlation_id}},
                            uow_idemp.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )

                return CallerResult(status=CallerResultStatus.ACCEPTED, operation=op_ref)







            else:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Unsupported command request_type {request_type!r}",
                    correlation_id=correlation_id,
                )

        except PipelineError as pe:
            ipc_err = pe.to_ipc_error()
            if envelope.idempotency_key:
                try:
                    with self._create_uow() as uow_idemp:
                        self.idempotency_service.record_idempotent_result(
                            envelope.idempotency_key,
                            pipeline_actor.organization_id,
                            envelope.command_id,
                            payload_fp,
                            {"_error_category": ipc_err.category.value, "_error_code": ipc_err.code, "_error_message": ipc_err.message},
                            uow_idemp.connection,
                            workspace_id=pipeline_actor.workspace_id,
                            project_id=pipeline_actor.project_id,
                            command_name=envelope.request_type,
                        )
                except Exception:
                    pass
            return CallerResult(status=CallerResultStatus.ERROR, error=ipc_err)

        except Exception as unexpected:  # noqa: BLE001
            logger.exception("Unexpected exception in handle_command: %s", unexpected)
            sanitized = sanitize_unexpected_exception(unexpected, correlation_id=correlation_id, request_id=request_id)
            return CallerResult(status=CallerResultStatus.ERROR, error=sanitized)

    def handle_query(self, envelope: QueryEnvelope) -> CallerResult:
        correlation_id = envelope.correlation.correlation_id
        request_id = envelope.request_id

        if envelope.actor is None or envelope.actor.actor is None:
            return CallerResult(
                status=CallerResultStatus.ERROR,
                error=make_error(
                    IPCErrorCategory.UNAUTHORIZED,
                    code="MISSING_ACTOR_CONTEXT",
                    message="Query envelope has no actor context.",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )
        pipeline_actor = PipelineActorContext.from_ipc(envelope.actor)

        uow = self._create_uow()
        try:
            with uow:
                request_type = envelope.request_type
                if request_type in ("migration.get", "get_migration"):
                    mig_id = envelope.payload.get("migration_id")
                    agg = self.query_service.get_migration(mig_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=agg.to_dict())
                elif request_type in ("migration.list", "list_migrations"):
                    aggs = self.query_service.list_migrations(actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result={"migrations": [a.to_dict() for a in aggs]})
                elif request_type in ("operation.get", "get_operation"):
                    op_id = envelope.payload.get("operation_id")
                    op = self.query_service.get_operation(op_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=op.to_dict())
                elif request_type in ("mutability.evaluate", "evaluate_mutability"):
                    param_name = envelope.payload.get("parameter_name", "")
                    mig_id = envelope.payload.get("migration_id")
                    res = self.query_service.evaluate_mutability(param_name, migration_id=mig_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("observability.get", "get_observability"):
                    mig_id = envelope.payload.get("migration_id", "")
                    res = self.query_service.get_observability(mig_id, actor=pipeline_actor, conn=uow.connection, binding_registry=self.binding_registry)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("health.get_explainable", "get_explainable_health"):
                    mig_id = envelope.payload.get("migration_id", "")
                    res = self.query_service.get_explainable_health(mig_id, actor=pipeline_actor, conn=uow.connection, binding_registry=self.binding_registry)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("diagnostics.capture", "capture_diagnostics"):
                    mig_id = envelope.payload.get("migration_id", "")
                    res = self.query_service.capture_diagnostics(mig_id, actor=pipeline_actor, conn=uow.connection, binding_registry=self.binding_registry)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("fleet.status", "get_fleet_status"):
                    res = self.query_service.get_fleet_status(actor=pipeline_actor, conn=uow.connection, binding_registry=self.binding_registry)
                    return CallerResult(status=CallerResultStatus.OK, result={"nodes": res})
                elif request_type in ("metrics.export_prometheus", "export_prometheus"):
                    res = self.query_service.export_prometheus(binding_registry=self.binding_registry)
                    return CallerResult(status=CallerResultStatus.OK, result={"prometheus_text": res})
                elif request_type in ("schedule.get", "get_schedule"):
                    sch_id = envelope.payload.get("schedule_id", "")
                    res = self.query_service.get_schedule(sch_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("schedule.list", "list_schedules"):
                    res = self.query_service.list_schedules(
                        actor=pipeline_actor,
                        conn=uow.connection,
                        tenant_id=envelope.payload.get("tenant_id"),
                        workspace_id=envelope.payload.get("workspace_id"),
                        project_id=envelope.payload.get("project_id"),
                    )
                    return CallerResult(status=CallerResultStatus.OK, result={"schedules": res})
                elif request_type in ("schedule.occurrence.get", "get_schedule_occurrence"):
                    occ_id = envelope.payload.get("occurrence_id", "")
                    res = self.query_service.get_schedule_occurrence(occ_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("schedule.occurrence.list", "list_schedule_occurrences"):
                    sch_id = envelope.payload.get("schedule_id", "")
                    limit = int(envelope.payload.get("limit", 50))
                    res = self.query_service.list_schedule_occurrences(sch_id, actor=pipeline_actor, conn=uow.connection, limit=limit)
                    return CallerResult(status=CallerResultStatus.OK, result={"occurrences": res})
                elif request_type in ("retention.preview", "preview_retention"):
                    res = self.query_service.preview_retention(envelope.payload, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("retention.operation.get", "get_retention_operation"):
                    op_id = envelope.payload.get("retention_op_id", "")
                    res = self.query_service.get_retention_operation(op_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("retention.operation.list", "list_retention_operations"):
                    limit = int(envelope.payload.get("limit", 50))
                    res = self.query_service.list_retention_operations(actor=pipeline_actor, conn=uow.connection, limit=limit)
                    return CallerResult(status=CallerResultStatus.OK, result={"operations": res})
                elif request_type in ("capacity.report", "get_capacity_report"):
                    res = self.query_service.get_capacity_report(
                        actor=pipeline_actor,
                        conn=uow.connection,
                        db_path=self.db_path,
                    )
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("capacity.history", "get_capacity_history"):
                    resource_type_str = envelope.payload.get("resource_type", "DISK")
                    limit = int(envelope.payload.get("limit", 100))
                    res = self.query_service.get_capacity_history(resource_type_str, actor=pipeline_actor, conn=uow.connection, limit=limit)
                    return CallerResult(status=CallerResultStatus.OK, result={"history": res})
                elif request_type in ("capacity.forecast", "get_capacity_forecast"):
                    resource_type_str = envelope.payload.get("resource_type", "DISK")
                    target_capacity = envelope.payload.get("target_capacity")
                    res = self.query_service.get_capacity_forecast(resource_type_str, actor=pipeline_actor, conn=uow.connection, target_capacity=target_capacity)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("alert.list", "list_alerts"):
                    lifecycle_state = envelope.payload.get("lifecycle_state")
                    limit = int(envelope.payload.get("limit", 50))
                    res = self.query_service.list_alerts(actor=pipeline_actor, conn=uow.connection, lifecycle_state=lifecycle_state, limit=limit)
                    return CallerResult(status=CallerResultStatus.OK, result={"alerts": res})
                elif request_type in ("alert.get", "get_alert"):
                    alert_id = envelope.payload.get("alert_id", "")
                    res = self.query_service.get_alert(alert_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("incident.list", "list_incidents"):
                    status = envelope.payload.get("status")
                    limit = int(envelope.payload.get("limit", 50))
                    res = self.query_service.list_incidents(actor=pipeline_actor, conn=uow.connection, status=status, limit=limit)
                    return CallerResult(status=CallerResultStatus.OK, result={"incidents": res})
                elif request_type in ("incident.get", "get_incident"):
                    incident_id = envelope.payload.get("incident_id", "")
                    res = self.query_service.get_incident(incident_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result=res)
                elif request_type in ("incident.timeline", "get_incident_timeline"):
                    incident_id = envelope.payload.get("incident_id", "")
                    res = self.query_service.get_incident_timeline(incident_id, actor=pipeline_actor, conn=uow.connection)
                    return CallerResult(status=CallerResultStatus.OK, result={"timeline": res})
                elif request_type in ("notification.list", "list_notification_deliveries"):
                    limit = int(envelope.payload.get("limit", 50))
                    res = self.query_service.list_notification_deliveries(actor=pipeline_actor, conn=uow.connection, limit=limit)
                    return CallerResult(status=CallerResultStatus.OK, result={"deliveries": res})
                else:
                    raise PipelineError(
                        PipelineErrorCode.INVALID_REQUEST,
                        f"Unsupported query request_type {request_type!r}",
                        correlation_id=correlation_id,
                    )
        except PipelineError as pe:
            return CallerResult(status=CallerResultStatus.ERROR, error=pe.to_ipc_error())
        except Exception as unexpected:  # noqa: BLE001
            sanitized = sanitize_unexpected_exception(unexpected, correlation_id=correlation_id, request_id=request_id)
            return CallerResult(status=CallerResultStatus.ERROR, error=sanitized)

    def reconcile_node_completion(
        self,
        result: EngineInvocationResult,
        actor: ActorContext,
    ) -> CallerResult:
        """Asynchronously reconciles a completion posted by an engine worker into the Pipeline DAG."""
        pipeline_actor = PipelineActorContext.from_ipc(actor)
        outcome = self.plan_coordinator.reconcile_node_completion(
            result=result,
            actor=pipeline_actor,
            uow_factory=self._create_uow,
        )
        if outcome.is_success:
            return CallerResult(status=CallerResultStatus.OK, result={"status": outcome.status})
        else:
            err = make_error(
                outcome.error_category or IPCErrorCategory.INTERNAL_ERROR,
                code=outcome.error_code or "RECONCILIATION_FAILED",
                message=outcome.error_message or "Node completion reconciliation failed.",
            )
            return CallerResult(status=CallerResultStatus.ERROR, error=err)
