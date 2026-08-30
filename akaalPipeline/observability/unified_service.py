"""akaalPipeline.observability.unified_service
==============================================
Canonical Unified Observability Query Projection Service.
Aggregates live operational telemetry, CDC backlog/lag, runtime worker utilization,
and durable lifecycle history without acting as a duplicate metric producer or store.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.observability")


@dataclass(frozen=True)
class CorrelatedTelemetrySnapshot:
    """Correlated operational telemetry projection."""
    tenant_id: str
    workspace_id: str
    project_id: Optional[str]
    migration_id: str
    execution_id: Optional[str]
    captured_at: str
    runtime_metrics: Dict[str, Any]
    cdc_metrics: Dict[str, Any]
    engine_metrics: Dict[str, Any]
    historical_events_count: int
    data_range_start: Optional[str]
    data_range_end: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "execution_id": self.execution_id,
            "captured_at": self.captured_at,
            "runtime_metrics": self.runtime_metrics,
            "cdc_metrics": self.cdc_metrics,
            "engine_metrics": self.engine_metrics,
            "historical_events_count": self.historical_events_count,
            "data_range_start": self.data_range_start,
            "data_range_end": self.data_range_end,
        }


class UnifiedObservabilityService:
    """
    Unified query projection service aggregating live authoritative telemetry
    from TelemetryAuthority, CDCAuthority, RuntimeAuthority, and SQLite history.
    """

    def __init__(self, binding_registry: Optional[Any] = None) -> None:
        self.binding_registry = binding_registry

    def query_telemetry(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        start_time_iso: Optional[str] = None,
        end_time_iso: Optional[str] = None,
    ) -> CorrelatedTelemetrySnapshot:
        """Queries correlated telemetry snapshot with strict tenant isolation and historical truth."""
        # 1. Verify migration existence and tenant ownership
        cur = conn.execute(
            "SELECT tenant_id, workspace_id, project_id, active_attempt_id FROM migrations WHERE migration_id = ?",
            (migration_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        mig_tenant = row["tenant_id"]
        mig_ws = row["workspace_id"]
        mig_proj = row["project_id"]
        active_attempt = row["active_attempt_id"]

        if mig_tenant != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} unauthorized for tenant.")
        if actor.workspace_id and mig_ws and mig_ws != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and mig_proj and mig_proj != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

        now_str = datetime.now(timezone.utc).isoformat()

        # 2. Sample live authorities via engine binding if connected
        runtime_snap: Dict[str, Any] = {}
        cdc_snap: Dict[str, Any] = {}
        engine_snap: Dict[str, Any] = {}

        if self.binding_registry:
            binding = self.binding_registry.get("gateway_engine_binding")
            if not binding:
                for b in self.binding_registry.list_all():
                    if hasattr(b, "engine_gateway"):
                        binding = b
                        break

            if binding and hasattr(binding, "engine_gateway"):
                gw = getattr(binding, "engine_gateway", None)
                if gw and hasattr(gw, "coordinator"):
                    coord = gw.coordinator
                    if hasattr(coord, "runtime_authority") and coord.runtime_authority:
                        try:
                            runtime_snap = coord.runtime_authority.get_runtime_snapshot()
                        except Exception as exc:
                            logger.warning("Failed to sample RuntimeAuthority: %s", exc)
                    if hasattr(coord, "cdc_authority") and coord.cdc_authority:
                        try:
                            cdc_raw = coord.cdc_authority.get_snapshot()
                            cdc_snap = cdc_raw.to_dict() if hasattr(cdc_raw, "to_dict") else dict(getattr(cdc_raw, "__dict__", {}))
                        except Exception as exc:
                            logger.warning("Failed to sample CDCAuthority: %s", exc)
                    if hasattr(coord, "telemetry_authority") and coord.telemetry_authority:
                        try:
                            m_raw = coord.telemetry_authority.get_metric_snapshot()
                            engine_snap = m_raw.to_dict() if hasattr(m_raw, "to_dict") else {}
                        except Exception as exc:
                            logger.warning("Failed to sample TelemetryAuthority: %s", exc)

        # 3. Query durable history range truth
        hist_cur = conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM lifecycle_history WHERE migration_id = ?",
            (migration_id,),
        )
        hist_row = hist_cur.fetchone()
        hist_count = hist_row[0] if hist_row else 0
        min_ts = hist_row[1] if hist_row and hist_row[1] else None
        max_ts = hist_row[2] if hist_row and hist_row[2] else now_str

        return CorrelatedTelemetrySnapshot(
            tenant_id=mig_tenant,
            workspace_id=mig_ws or "default-workspace",
            project_id=mig_proj,
            migration_id=migration_id,
            execution_id=active_attempt,
            captured_at=now_str,
            runtime_metrics=runtime_snap,
            cdc_metrics=cdc_snap,
            engine_metrics=engine_snap,
            historical_events_count=hist_count,
            data_range_start=min_ts,
            data_range_end=max_ts,
        )

    def export_prometheus_metrics(self) -> str:
        """Fetches standard Prometheus exposition format from Engine TelemetryAuthority."""
        if self.binding_registry:
            binding = self.binding_registry.get("gateway_engine_binding")
            if not binding:
                for b in self.binding_registry.list_all():
                    if hasattr(b, "engine_gateway"):
                        binding = b
                        break

            if binding and hasattr(binding, "engine_gateway"):
                gw = getattr(binding, "engine_gateway", None)
                if gw and hasattr(gw, "coordinator") and hasattr(gw.coordinator, "telemetry_authority"):
                    ta = gw.coordinator.telemetry_authority
                    if hasattr(ta, "export_prometheus_text"):
                        return ta.export_prometheus_text()
        return "# HELP akaal_up AKAAL service status\n# TYPE akaal_up gauge\nakaal_up 1.0\n"
