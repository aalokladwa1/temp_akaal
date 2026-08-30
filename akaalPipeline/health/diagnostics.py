"""akaalPipeline.health.diagnostics
==================================
Diagnostic Snapshot Packaging Service for P6.3.
Bundles complete forensic snapshots from physical authorities without fabricating missing data.
Applies exhaustive secret sanitization across all data structures and error strings.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.diagnostics")

_SECRET_KEY_PATTERN = re.compile(
    r"(password|secret|token|key|credential|auth|dsn|private_key|conn_str|api_key|cert|signature|bearer)",
    re.IGNORECASE,
)
_URI_SECRET_PATTERN = re.compile(r"://([^:]+):([^@]+)@")


def _sanitize_string(val: str) -> str:
    """Masks inline URI credentials and bearer tokens."""
    masked = _URI_SECRET_PATTERN.sub(r"://\1:***REDACTED***@", val)
    if "bearer " in masked.lower():
        masked = re.sub(r"(bearer\s+)[^\s]+", r"\1***REDACTED***", masked, flags=re.IGNORECASE)
    return masked


def _sanitize_data(data: Any) -> Any:
    """Recursively masks secret-bearing keys, values, and structures."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if _SECRET_KEY_PATTERN.search(str(k)):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = _sanitize_data(v)
        return sanitized
    elif isinstance(data, (list, tuple, set)):
        return [_sanitize_data(item) for item in data]
    elif isinstance(data, str):
        return _sanitize_string(data)
    return data


# Backward-compatible alias
_sanitize_dict = _sanitize_data


@dataclass(frozen=True)
class DiagnosticSnapshot:
    """Complete forensic snapshot package for operational diagnostics."""
    snapshot_id: str
    migration_id: str
    tenant_id: str
    captured_at: str
    migration_aggregate: Dict[str, Any]
    active_lease: Optional[Dict[str, Any]]
    runtime_snapshot: Dict[str, Any]
    cdc_snapshot: Dict[str, Any]
    engine_health_snapshot: Dict[str, Any]
    recent_lifecycle_history: List[Dict[str, Any]]
    recent_operations: List[Dict[str, Any]]
    unavailable_sections: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return _sanitize_data({
            "snapshot_id": self.snapshot_id,
            "migration_id": self.migration_id,
            "tenant_id": self.tenant_id,
            "captured_at": self.captured_at,
            "migration_aggregate": self.migration_aggregate,
            "active_lease": self.active_lease,
            "runtime_snapshot": self.runtime_snapshot,
            "cdc_snapshot": self.cdc_snapshot,
            "engine_health_snapshot": self.engine_health_snapshot,
            "recent_lifecycle_history": self.recent_lifecycle_history,
            "recent_operations": self.recent_operations,
            "unavailable_sections": self.unavailable_sections,
        })


class DiagnosticSnapshotService:
    """
    Captures complete diagnostic snapshots across pipeline state and physical engine authorities.
    """

    def __init__(self, binding_registry: Optional[Any] = None) -> None:
        self.binding_registry = binding_registry

    def capture_snapshot(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> DiagnosticSnapshot:
        import uuid
        now_str = datetime.now(timezone.utc).isoformat()
        unavailable: List[str] = []

        # 1. Fetch Migration Aggregate with Tenant Verification
        cur = conn.execute("SELECT * FROM migrations WHERE migration_id = ?", (migration_id,))
        mig_row = cur.fetchone()
        if mig_row is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        tenant_id = mig_row["tenant_id"]
        if tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} unauthorized for tenant.")
        if actor.workspace_id and mig_row["workspace_id"] and mig_row["workspace_id"] != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")

        agg_dict = dict(mig_row)
        active_attempt = mig_row["active_attempt_id"]

        # 2. Fetch Active Lease if any
        active_lease_dict: Optional[Dict[str, Any]] = None
        if active_attempt:
            l_cur = conn.execute("SELECT * FROM leases WHERE attempt_id = ?", (active_attempt,))
            l_row = l_cur.fetchone()
            if l_row:
                active_lease_dict = dict(l_row)

        # 3. Sample Live Engine Authorities
        rt_snap: Dict[str, Any] = {}
        cdc_snap: Dict[str, Any] = {}
        health_snap: Dict[str, Any] = {}

        gw_bound = False
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
                    gw_bound = True
                    coord = gw.coordinator
                    if hasattr(coord, "runtime_authority") and coord.runtime_authority:
                        try:
                            rt_snap = coord.runtime_authority.get_runtime_snapshot()
                        except Exception as exc:
                            unavailable.append(f"RuntimeAuthority: {exc}")
                    else:
                        unavailable.append("RuntimeAuthority: unattached")

                    if hasattr(coord, "cdc_authority") and coord.cdc_authority:
                        try:
                            cdc_raw = coord.cdc_authority.get_snapshot()
                            cdc_snap = cdc_raw.to_dict() if hasattr(cdc_raw, "to_dict") else dict(getattr(cdc_raw, "__dict__", {}))
                        except Exception as exc:
                            unavailable.append(f"CDCAuthority: {exc}")
                    else:
                        unavailable.append("CDCAuthority: unattached")

                    if hasattr(coord, "telemetry_authority") and coord.telemetry_authority:
                        try:
                            h_raw = coord.telemetry_authority.get_health_snapshot()
                            health_snap = h_raw.to_dict() if hasattr(h_raw, "to_dict") else {}
                        except Exception as exc:
                            unavailable.append(f"TelemetryAuthority: {exc}")
                    else:
                        unavailable.append("TelemetryAuthority: unattached")

        if not gw_bound:
            unavailable.append("EngineGateway: no active binding")

        # 4. Fetch Recent Lifecycle History
        hist_cur = conn.execute(
            "SELECT * FROM lifecycle_history WHERE migration_id = ? ORDER BY timestamp DESC LIMIT 20",
            (migration_id,),
        )
        hist_list = [dict(r) for r in hist_cur.fetchall()]

        # 5. Fetch Recent Operations
        op_cur = conn.execute(
            "SELECT * FROM operation_journal WHERE operation_id LIKE ? OR command_id LIKE ? ORDER BY created_at DESC LIMIT 20",
            (f"%{migration_id}%", f"%{migration_id}%"),
        )
        op_list = [dict(r) for r in op_cur.fetchall()]

        return DiagnosticSnapshot(
            snapshot_id=f"diag-snap-{uuid.uuid4().hex[:12]}",
            migration_id=migration_id,
            tenant_id=tenant_id,
            captured_at=now_str,
            migration_aggregate=agg_dict,
            active_lease=active_lease_dict,
            runtime_snapshot=rt_snap,
            cdc_snapshot=cdc_snap,
            engine_health_snapshot=health_snap,
            recent_lifecycle_history=hist_list,
            recent_operations=op_list,
            unavailable_sections=unavailable,
        )
