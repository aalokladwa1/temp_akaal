"""akaalPipeline.operations.gateway
=================================
Final P6 Operations Gateway.
Thin canonical Northbound facade unifying P6.1 through P6.7.
Dynamically resolves capabilities, preserves complete P5 actor context,
and routes requests to authoritative Pipeline subsystems without duplicating domain logic.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error
from akaalIPC.transport.ports import CallerResult, CallerResultStatus
from akaalPipeline.contracts.enums import (
    AlertLifecycleState,
    AlertSeverity,
    IncidentSeverity,
    IncidentStatus,
    NotificationChannel,
    PipelineErrorCode,
    ResourceType,
)
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.security.context import PipelineActorContext

if TYPE_CHECKING:
    from akaalPipeline.application.unified_caller import PipelineUnifiedCaller

logger = logging.getLogger("akaalPipeline.operations.gateway")


@dataclass(frozen=True)
class GatewayCapabilities:
    """Dynamically discovered P6 operational capabilities."""
    gateway_version: str
    tenant_id: str
    control_plane_available: bool
    observability_available: bool
    health_diagnostics_available: bool
    fleet_management_available: bool
    scheduling_retention_available: bool
    capacity_intelligence_available: bool
    alerts_incidents_available: bool
    supported_commands: List[str]
    supported_queries: List[str]
    timestamp_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_version": self.gateway_version,
            "tenant_id": self.tenant_id,
            "control_plane_available": self.control_plane_available,
            "observability_available": self.observability_available,
            "health_diagnostics_available": self.health_diagnostics_available,
            "fleet_management_available": self.fleet_management_available,
            "scheduling_retention_available": self.scheduling_retention_available,
            "capacity_intelligence_available": self.capacity_intelligence_available,
            "alerts_incidents_available": self.alerts_incidents_available,
            "supported_commands": self.supported_commands,
            "supported_queries": self.supported_queries,
            "timestamp_iso": self.timestamp_iso,
        }


class OperationsGateway:
    """Canonical Northbound Gateway for Whole P6 Operations."""

    def __init__(self, unified_caller: PipelineUnifiedCaller) -> None:
        self.caller = unified_caller

    def discover_capabilities(self, actor: PipelineActorContext) -> GatewayCapabilities:
        """Dynamically discovers active capabilities from real registered pipeline authorities."""
        commands = [
            "migration.create", "migration.configure", "migration.plan", "migration.initialize",
            "migration.approve", "migration.start", "migration.cancel", "migration.recover",
            "migration.pause", "migration.resume", "migration.throttle_cdc",
            "fleet.drain_node", "fleet.undrain_node",
            "schedule.create", "schedule.update", "schedule.arm", "schedule.disable",
            "schedule.enable", "schedule.cancel", "schedule.delete", "retention.execute",
            "capacity.sample",
            "alert.rule.create", "alert.evaluate", "alert.acknowledge", "alert.resolve", "alert.suppress",
            "incident.create", "incident.alert.attach", "incident.status.update",
            "notification.send",
        ]
        queries = [
            "migration.get", "migration.list", "operation.get", "mutability.evaluate",
            "observability.get", "health.get_explainable", "diagnostics.capture",
            "fleet.status", "metrics.export_prometheus",
            "schedule.get", "schedule.list", "schedule.occurrence.get", "schedule.occurrence.list",
            "retention.preview", "retention.operation.get", "retention.operation.list",
            "capacity.report", "capacity.history", "capacity.forecast",
            "alert.list", "alert.get",
            "incident.list", "incident.get", "incident.timeline",
            "notification.list",
        ]

        return GatewayCapabilities(
            gateway_version="6.0.0",
            tenant_id=actor.organization_id,
            control_plane_available=bool(self.caller.operation_service is not None),
            observability_available=bool(self.caller.binding_registry is not None),
            health_diagnostics_available=True,
            fleet_management_available=True,
            scheduling_retention_available=bool(self.caller.schedule_service is not None),
            capacity_intelligence_available=bool(self.caller.capacity_service is not None),
            alerts_incidents_available=bool(self.caller.alert_service is not None),
            supported_commands=commands,
            supported_queries=queries,
        )

    # -------------------------------------------------------------------------
    # Northbound Command & Query Dispatch
    # -------------------------------------------------------------------------

    def execute_command(self, envelope: CommandEnvelope) -> CallerResult:
        """Dispatches an IPC command envelope through the unified pipeline caller."""
        return self.caller.handle_command(envelope)

    def execute_query(self, envelope: QueryEnvelope) -> CallerResult:
        """Dispatches an IPC query envelope through the unified pipeline caller."""
        return self.caller.handle_query(envelope)

    # -------------------------------------------------------------------------
    # High-level P6 Convenience Facade Methods (Thin Routing)
    # -------------------------------------------------------------------------

    def get_capacity_overview(self, actor: PipelineActorContext) -> Dict[str, Any]:
        """P6.6: Retrieves capacity snapshot and recommendations."""
        uow = self.caller._create_uow()
        with uow:
            return self.caller.query_service.get_capacity_report(
                actor=actor,
                conn=uow.connection,
                db_path=self.caller.db_path,
            )

    def get_active_alerts(self, actor: PipelineActorContext, limit: int = 50) -> List[Dict[str, Any]]:
        """P6.7: Retrieves active OPEN or ACKNOWLEDGED alerts for the tenant."""
        uow = self.caller._create_uow()
        with uow:
            open_alerts = self.caller.query_service.list_alerts(actor, uow.connection, lifecycle_state="OPEN", limit=limit)
            ack_alerts = self.caller.query_service.list_alerts(actor, uow.connection, lifecycle_state="ACKNOWLEDGED", limit=limit)
            return open_alerts + ack_alerts

    def get_incident_summary(self, incident_id: str, actor: PipelineActorContext) -> Dict[str, Any]:
        """P6.7: Retrieves incident details along with attached alerts and durable timeline."""
        uow = self.caller._create_uow()
        with uow:
            inc = self.caller.query_service.get_incident(incident_id, actor, uow.connection)
            timeline = self.caller.query_service.get_incident_timeline(incident_id, actor, uow.connection)
            attached_alerts = self.caller.command_handlers.incident_service.get_attached_alerts(incident_id, uow.connection)
            return {
                "incident": inc,
                "timeline": timeline,
                "attached_alerts": attached_alerts,
            }
