"""akaalPipeline.application.query_service
========================================
Pipeline side-effect-free query service.
"""

from __future__ import annotations

import sqlite3
from typing import Any, List, Mapping, Optional
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.service import OperationService
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import MigrationRepositoryPort


from akaalPipeline.security.context import PipelineActorContext


class PipelineQueryService:
    def __init__(
        self,
        repository: MigrationRepositoryPort,
        operation_service: OperationService,
    ) -> None:
        self.repository = repository
        self.operation_service = operation_service

    def get_migration(
        self,
        migration_id: str,
        actor: Optional[PipelineActorContext] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> MigrationAggregate:
        agg = self.repository.get_by_id(migration_id, connection=conn)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        if actor is not None:
            if agg.tenant_id and agg.tenant_id != actor.organization_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
            if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
            if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

        return agg

    def list_migrations(
        self,
        actor: Optional[PipelineActorContext] = None,
        tenant_id: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[MigrationAggregate]:
        effective_tenant = actor.organization_id if actor else tenant_id
        migrations = self.repository.list_all(tenant_id=effective_tenant, connection=conn)
        if actor and actor.workspace_id:
            migrations = [m for m in migrations if not m.workspace_id or m.workspace_id == actor.workspace_id]
        if actor and actor.project_id:
            migrations = [m for m in migrations if not m.project_id or m.project_id == actor.project_id]
        return migrations


    def get_operation(
        self,
        operation_id: str,
        actor: Optional[PipelineActorContext] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> OperationRecord:
        if conn is None:
            raise PipelineError(PipelineErrorCode.INTERNAL_ERROR, "Database connection required for get_operation.")
        op = self.operation_service.get_by_id(operation_id, conn)
        if op is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Operation {operation_id!r} not found.")

        if actor is not None:
            op_org = getattr(op.actor, "organization_id", None)
            if op_org and op_org != actor.organization_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Operation {operation_id!r} not found or unauthorized for tenant.")
            op_ws = getattr(op.actor, "workspace_id", None)
            if actor.workspace_id and op_ws and op_ws != actor.workspace_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Operation {operation_id!r} belongs to a different workspace.")
            op_proj = getattr(op.actor, "project_id", None)
            if actor.project_id and op_proj and op_proj != actor.project_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Operation {operation_id!r} belongs to a different project.")
        return op

    def evaluate_mutability(
        self,
        parameter_name: str,
        migration_id: Optional[str] = None,
        actor: Optional[PipelineActorContext] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """P6.1 Query: Evaluate operational parameter mutability truth dynamically."""
        from akaalPipeline.operations.mutability import OperationalMutabilityResolver
        state = None
        mode = None
        if migration_id and conn:
            agg = self.repository.get_by_id(migration_id, connection=conn)
            if agg:
                if actor and agg.tenant_id != actor.organization_id:
                    raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} unauthorized for tenant.")
                state = agg.state
                mode = agg.mode
        res = OperationalMutabilityResolver.evaluate(parameter_name, current_state=state, mode=mode)
        return res.to_dict()

    def get_observability(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        binding_registry: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """P6.2 Query: Get correlated operational telemetry snapshot."""
        from akaalPipeline.observability.unified_service import UnifiedObservabilityService
        service = UnifiedObservabilityService(binding_registry=binding_registry)
        snap = service.query_telemetry(migration_id, actor, conn)
        return snap.to_dict()

    def get_explainable_health(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        binding_registry: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """P6.3 Query: Get explainable health with causal root-cause derivation."""
        from akaalPipeline.observability.unified_service import UnifiedObservabilityService
        from akaalPipeline.health.explainable import ExplainableHealthService
        obs_service = UnifiedObservabilityService(binding_registry=binding_registry)
        snap = obs_service.query_telemetry(migration_id, actor, conn)
        report = ExplainableHealthService.evaluate(
            migration_id=migration_id,
            migration_state=snap.runtime_metrics.get("is_running", "ACTIVE"),
            cdc_snapshot=snap.cdc_metrics,
            runtime_snapshot=snap.runtime_metrics,
            engine_health_snapshot=snap.engine_metrics,
        )
        return report.to_dict()

    def capture_diagnostics(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        binding_registry: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """P6.3 Query: Capture complete sanitized forensic diagnostic snapshot."""
        from akaalPipeline.health.diagnostics import DiagnosticSnapshotService
        diag_service = DiagnosticSnapshotService(binding_registry=binding_registry)
        snap = diag_service.capture_snapshot(migration_id, actor, conn)
        return snap.to_dict()

    def get_fleet_status(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        binding_registry: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """P6.4 Query: Get registered fleet nodes with liveness and active workloads."""
        from akaalPipeline.fleet.fleet_service import FleetOperationalService
        fleet_service = FleetOperationalService(binding_registry=binding_registry)
        nodes = fleet_service.list_fleet_nodes(conn, actor=actor)
        return [n.to_dict() for n in nodes]

    def export_prometheus(
        self,
        binding_registry: Optional[Any] = None,
    ) -> str:
        """P6.2 Query: Export Prometheus text format metrics from Engine."""
        from akaalPipeline.observability.unified_service import UnifiedObservabilityService
        obs_service = UnifiedObservabilityService(binding_registry=binding_registry)
        return obs_service.export_prometheus_metrics()

    # =========================================================================
    # P6.5 ENTERPRISE SCHEDULING & RETENTION QUERIES
    # =========================================================================

    def get_schedule(
        self,
        schedule_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """P6.5 Query: Get schedule by ID with tenant security check."""
        from akaalPipeline.operations.schedules import ScheduleService
        service = ScheduleService()
        sch = service.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if actor and sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        return sch.to_dict()

    def list_schedules(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        tenant_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """P6.5 Query: List schedules within tenant/workspace/project scope."""
        from akaalPipeline.operations.schedules import ScheduleService
        service = ScheduleService()
        effective_tenant = actor.organization_id if actor else (tenant_id or "default-tenant")
        effective_ws = actor.workspace_id if actor else workspace_id
        effective_proj = actor.project_id if actor else project_id
        schedules = service.list_schedules(effective_tenant, conn, workspace_id=effective_ws, project_id=effective_proj)
        return [s.to_dict() for s in schedules]

    def get_schedule_occurrence(
        self,
        occurrence_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """P6.5 Query: Get specific occurrence details by ID."""
        from akaalPipeline.operations.schedules import ScheduleService
        service = ScheduleService()
        occ = service.get_occurrence_by_id(occurrence_id, conn)
        if occ is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Occurrence {occurrence_id!r} not found.")

        if actor and occ.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Occurrence {occurrence_id!r} unauthorized for tenant.")

        return occ.to_dict()

    def list_schedule_occurrences(
        self,
        schedule_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """P6.5 Query: List historical and pending occurrences for a schedule."""
        from akaalPipeline.operations.schedules import ScheduleService
        service = ScheduleService()
        sch = service.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if actor and sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        occs = service.list_occurrences(schedule_id, conn, limit=limit)
        return [o.to_dict() for o in occs]

    def preview_retention(
        self,
        policy_payload: Mapping[str, Any],
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """P6.5 Query: Non-destructively preview retention candidate numbers and protection reasons."""
        from akaalPipeline.operations.retention import OperationalRetentionService, RetentionPolicy
        cutoff_time = policy_payload.get("cutoff_time")
        if not cutoff_time:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "cutoff_time is required for retention preview.")

        data_classes = policy_payload.get("data_classes") or [
            "operation_journal",
            "idempotency_records",
            "lifecycle_history",
            "outbox_events",
            "checkpoints",
            "immutable_artifacts",
            "audit_trail",
            "schedule_occurrences",
        ]

        policy = RetentionPolicy(
            cutoff_time=cutoff_time,
            tenant_id=actor.organization_id if actor else "default-tenant",
            workspace_id=actor.workspace_id if actor else "default-workspace",
            project_id=actor.project_id if actor else None,
            data_classes=data_classes,
        )
        service = OperationalRetentionService()
        preview_res = service.preview(policy, conn, actor=actor)
        return preview_res.to_dict()

    def get_retention_operation(
        self,
        retention_op_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """P6.5 Query: Get retention operation result by ID."""
        from akaalPipeline.operations.retention import OperationalRetentionService
        service = OperationalRetentionService()
        op = service.get_operation_by_id(retention_op_id, conn)
        if op is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Retention operation {retention_op_id!r} not found.")

        if actor and op.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Retention operation {retention_op_id!r} unauthorized for tenant.")

        return op.to_dict()

    def list_retention_operations(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """P6.5 Query: List historical retention operations for tenant."""
        from akaalPipeline.operations.retention import OperationalRetentionService
        service = OperationalRetentionService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        ops = service.list_operations(effective_tenant, conn, limit=limit)
        return [o.to_dict() for o in ops]

    # =========================================================================
    # P6.6 Capacity & Resource Queries
    # =========================================================================

    def get_capacity_report(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        db_path: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
        staging_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """P6.6 Query: Get comprehensive capacity, storage, and resource report."""
        from akaalPipeline.operations.capacity import CapacityIntelligenceService
        service = CapacityIntelligenceService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        report = service.get_capacity_report(
            tenant_id=effective_tenant,
            conn=conn,
            db_path=db_path,
            checkpoint_dir=checkpoint_dir,
            staging_dir=staging_dir,
        )
        return report.to_dict()

    def get_capacity_history(
        self,
        resource_type_str: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """P6.6 Query: Retrieve historical observations for a resource type."""
        from akaalPipeline.contracts.enums import ResourceType
        from akaalPipeline.operations.capacity import CapacityIntelligenceService
        service = CapacityIntelligenceService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        try:
            rtype = ResourceType(resource_type_str.upper())
        except ValueError:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unknown resource type: {resource_type_str!r}")
        history = service.get_history(effective_tenant, rtype, conn, limit=limit)
        return [h.to_dict() for h in history]

    def get_capacity_forecast(
        self,
        resource_type_str: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        target_capacity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """P6.6 Query: Generate exhaustion forecast for a resource type."""
        from akaalPipeline.contracts.enums import ResourceType
        from akaalPipeline.operations.capacity import CapacityIntelligenceService
        service = CapacityIntelligenceService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        try:
            rtype = ResourceType(resource_type_str.upper())
        except ValueError:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unknown resource type: {resource_type_str!r}")
        fcst = service.generate_forecast(effective_tenant, rtype, conn, target_capacity=target_capacity)
        return fcst.to_dict()

    # =========================================================================
    # P6.7 Alerts, Incidents & Notification Queries
    # =========================================================================

    def list_alerts(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        lifecycle_state: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """P6.7 Query: List operational alerts."""
        from akaalPipeline.contracts.enums import AlertLifecycleState
        from akaalPipeline.operations.alerts import AlertService
        service = AlertService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        state_enum = AlertLifecycleState(lifecycle_state.upper()) if lifecycle_state else None
        alerts = service.list_alerts(effective_tenant, conn, lifecycle_state=state_enum, limit=limit)
        return [a.to_dict() for a in alerts]

    def get_alert(
        self,
        alert_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """P6.7 Query: Get alert by ID."""
        from akaalPipeline.operations.alerts import AlertService
        service = AlertService()
        alert = service.get_alert_by_id(alert_id, conn)
        if not alert:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Alert {alert_id!r} not found.")
        if actor and alert.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Alert {alert_id!r} unauthorized for tenant.")
        return alert.to_dict()

    def list_incidents(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """P6.7 Query: List operational incidents."""
        from akaalPipeline.contracts.enums import IncidentStatus
        from akaalPipeline.operations.incidents import IncidentService
        service = IncidentService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        status_enum = IncidentStatus(status.upper()) if status else None
        incidents = service.list_incidents(effective_tenant, conn, status=status_enum, limit=limit)
        return [i.to_dict() for i in incidents]

    def get_incident(
        self,
        incident_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """P6.7 Query: Get incident by ID."""
        from akaalPipeline.operations.incidents import IncidentService
        service = IncidentService()
        incident = service.get_incident(incident_id, conn)
        if not incident:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Incident {incident_id!r} not found.")
        if actor and incident.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Incident {incident_id!r} unauthorized for tenant.")
        return incident.to_dict()

    def get_incident_timeline(
        self,
        incident_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> List[Dict[str, Any]]:
        """P6.7 Query: Get durable timeline for an incident."""
        from akaalPipeline.operations.incidents import IncidentService
        service = IncidentService()
        incident = service.get_incident(incident_id, conn)
        if not incident:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Incident {incident_id!r} not found.")
        if actor and incident.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Incident {incident_id!r} unauthorized for tenant.")
        timeline = service.get_timeline(incident_id, conn)
        return [t.to_dict() for t in timeline]

    def list_notification_deliveries(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """P6.7 Query: List notification delivery records."""
        from akaalPipeline.operations.notifications import NotificationService
        service = NotificationService()
        effective_tenant = actor.organization_id if actor else "default-tenant"
        deliveries = service.list_deliveries(effective_tenant, conn, limit=limit)
        return [d.to_dict() for d in deliveries]



