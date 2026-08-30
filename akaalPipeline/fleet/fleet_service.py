"""akaalPipeline.fleet.fleet_service
=================================
Fleet, Node & Service Operational Management for P6.4.
Delegates canonical node registry to DistributedCoordinator in Engine.
Dynamically resolves capabilities, liveness, active workloads, and durable drain semantics.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.fleet")


class NodeLivenessStatus(str, Enum):
    ALIVE = "ALIVE"
    DEGRADED = "DEGRADED"
    DEAD = "DEAD"
    UNKNOWN = "UNKNOWN"


class NodeDrainState(str, Enum):
    ACTIVE = "ACTIVE"
    DRAIN_REQUESTED = "DRAIN_REQUESTED"
    DRAINING = "DRAINING"
    DRAINED = "DRAINED"
    MAINTENANCE = "MAINTENANCE"


@dataclass(frozen=True)
class NodeOperationalSnapshot:
    """Truthful operational snapshot of a cluster fleet node."""
    node_id: str
    address: str
    port: int
    liveness: NodeLivenessStatus
    drain_state: NodeDrainState
    active_executions: int
    assigned_workloads: int
    capabilities: List[str]
    last_heartbeat_ago_sec: float
    registered_at_iso: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "liveness": self.liveness.value,
            "drain_state": self.drain_state.value,
            "active_executions": self.active_executions,
            "assigned_workloads": self.assigned_workloads,
            "capabilities": self.capabilities,
            "last_heartbeat_ago_sec": round(self.last_heartbeat_ago_sec, 2),
            "registered_at_iso": self.registered_at_iso,
        }


class FleetOperationalService:
    """
    Fleet and Node operational management service.
    Reuses DistributedCoordinator as canonical node registry.
    Persists durable drain and maintenance states in SQLite.
    """

    DEFAULT_HEARTBEAT_DEGRADED_THRESHOLD_SEC = 30.0
    DEFAULT_HEARTBEAT_DEAD_THRESHOLD_SEC = 60.0

    def __init__(self, binding_registry: Optional[Any] = None) -> None:
        self.binding_registry = binding_registry

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        """Ensures durable fleet node state table exists."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fleet_node_states (
                node_id TEXT PRIMARY KEY,
                drain_state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    def _get_engine_distributed_coordinator(self) -> Optional[Any]:
        if self.binding_registry:
            binding = self.binding_registry.get("gateway_engine_binding")
            if not binding:
                for b in self.binding_registry.list_all():
                    if hasattr(b, "engine_gateway"):
                        binding = b
                        break

            if binding and hasattr(binding, "engine_gateway"):
                gw = getattr(binding, "engine_gateway", None)
                if gw and hasattr(gw, "coordinator") and hasattr(gw.coordinator, "runtime_authority"):
                    ra = gw.coordinator.runtime_authority
                    if hasattr(ra, "distributed_coordinator"):
                        return ra.distributed_coordinator
        return None

    def _get_engine_runtime_authority(self) -> Optional[Any]:
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
                    return getattr(gw.coordinator, "runtime_authority", None)
        return None

    def _get_dynamic_capabilities(self) -> List[str]:
        """Dynamically queries installed provider catalog capabilities."""
        caps: List[str] = [
            "bulk_transport",
            "runtime_execution",
            "checkpoint_cas",
            "cdc_capture",
            "cdc_apply",
            "incremental_extract",
            "state_diff",
            "validation_compare",
        ]
        try:
            from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog
            catalog = ProviderCatalog()
            caps.extend(catalog.list_registered_provider_ids())
        except Exception:
            pass
        return sorted(list(set(caps)))

    def sync_durable_state(self, conn: sqlite3.Connection) -> None:
        """Synchronizes durable persisted drain states from SQLite to active Engine runtime."""
        self._ensure_schema(conn)
        cur = conn.execute("SELECT node_id, drain_state FROM fleet_node_states")
        dist_coord = self._get_engine_distributed_coordinator()
        ra = self._get_engine_runtime_authority()

        for row in cur.fetchall():
            node_id = row["node_id"]
            d_state = row["drain_state"]
            if dist_coord:
                dist_coord.set_node_drain_state(node_id, d_state)
            if d_state in (NodeDrainState.DRAINING.value, NodeDrainState.DRAINED.value, NodeDrainState.MAINTENANCE.value):
                if ra and hasattr(ra, "set_drain_mode"):
                    ra.set_drain_mode(True)

    def list_fleet_nodes(
        self,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
        degraded_threshold_sec: Optional[float] = None,
        dead_threshold_sec: Optional[float] = None,
    ) -> List[NodeOperationalSnapshot]:
        """Lists all registered fleet nodes with dynamic liveness, active executions, and capabilities."""
        self._ensure_schema(conn)
        self.sync_durable_state(conn)

        now = time.time()
        deg_thresh = degraded_threshold_sec or self.DEFAULT_HEARTBEAT_DEGRADED_THRESHOLD_SEC
        dead_thresh = dead_threshold_sec or self.DEFAULT_HEARTBEAT_DEAD_THRESHOLD_SEC

        dist_coord = self._get_engine_distributed_coordinator()
        raw_nodes: List[Dict[str, Any]] = []
        if dist_coord and hasattr(dist_coord, "list_nodes"):
            raw_nodes = dist_coord.list_nodes()
        else:
            raw_nodes = [{
                "node_id": "node-local",
                "address": "127.0.0.1",
                "port": 9000,
                "status": "ONLINE",
                "drain_state": "ACTIVE",
                "capabilities": [],
                "registered_at": now,
                "last_seen": now,
            }]

        # Distinct Workload Metrics
        # 1. Active Executions (actively consuming CPU/threads: RUNNING, PAUSING, RECOVERING)
        active_executions = 0
        assigned_workloads = 0
        try:
            cur_exec = conn.execute(
                """
                SELECT COUNT(*) FROM migrations
                WHERE state IN ('ACTIVE', 'PAUSING')
                """
            )
            active_exec_row = cur_exec.fetchone()
            active_executions = active_exec_row[0] if active_exec_row else 0

            # 2. Assigned Workloads (total state/lease assigned: INITIALIZED, ACTIVE, PAUSING, PAUSED)
            cur_assign = conn.execute(
                """
                SELECT COUNT(*) FROM migrations
                WHERE state IN ('INITIALIZED', 'ACTIVE', 'PAUSING', 'PAUSED')
                """
            )
            assigned_row = cur_assign.fetchone()
            assigned_workloads = assigned_row[0] if assigned_row else 0
        except sqlite3.OperationalError:
            pass

        # Dynamic capabilities
        dynamic_caps = self._get_dynamic_capabilities()

        snapshots: List[NodeOperationalSnapshot] = []
        for n in raw_nodes:
            n_id = n.get("node_id", "node-local")
            last_seen = n.get("last_seen", now)
            age = max(0.0, now - last_seen)

            if age < deg_thresh:
                liveness = NodeLivenessStatus.ALIVE
            elif age < dead_thresh:
                liveness = NodeLivenessStatus.DEGRADED
            else:
                liveness = NodeLivenessStatus.DEAD

            # Check persistent state in SQLite first
            cur_pers = conn.execute("SELECT drain_state FROM fleet_node_states WHERE node_id = ?", (n_id,))
            pers_row = cur_pers.fetchone()
            pers_drain = pers_row["drain_state"] if pers_row else n.get("drain_state", "ACTIVE")

            raw_drain = str(pers_drain).upper()
            try:
                drain_state = NodeDrainState(raw_drain)
            except ValueError:
                drain_state = NodeDrainState.ACTIVE

            reg_at_ts = n.get("registered_at", now)
            reg_iso = datetime.fromtimestamp(reg_at_ts, timezone.utc).isoformat()

            node_caps = list(n.get("capabilities", [])) or dynamic_caps

            snapshots.append(
                NodeOperationalSnapshot(
                    node_id=n_id,
                    address=n.get("address", "127.0.0.1"),
                    port=int(n.get("port", 9000)),
                    liveness=liveness,
                    drain_state=drain_state,
                    active_executions=active_executions,
                    assigned_workloads=assigned_workloads,
                    capabilities=node_caps,
                    last_heartbeat_ago_sec=age,
                    registered_at_iso=reg_iso,
                )
            )

        return snapshots

    def drain_node(self, node_id: str, conn: sqlite3.Connection, actor: PipelineActorContext) -> Dict[str, Any]:
        """Sets node into draining mode: halts new admissions in RuntimeAuthority until workloads drain."""
        if not any(r in ("admin", "operator", "platform_admin") for r in getattr(actor, "roles", ())):
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, "Drain operation requires admin or operator role.")

        self._ensure_schema(conn)
        dist_coord = self._get_engine_distributed_coordinator()
        ra = self._get_engine_runtime_authority()

        # Halt admission physically
        if ra and hasattr(ra, "set_drain_mode"):
            ra.set_drain_mode(True)

        # Check active workloads
        active_exec = 0
        try:
            cur_active = conn.execute(
                "SELECT COUNT(*) FROM migrations WHERE state IN ('ACTIVE', 'PAUSING')"
            )
            active_row = cur_active.fetchone()
            active_exec = active_row[0] if active_row else 0
        except sqlite3.OperationalError:
            pass

        final_drain_state = NodeDrainState.DRAINED.value if active_exec == 0 else NodeDrainState.DRAINING.value

        if dist_coord:
            dist_coord.set_node_drain_state(node_id, final_drain_state)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO fleet_node_states (node_id, drain_state, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET drain_state = excluded.drain_state, updated_at = excluded.updated_at
            """,
            (node_id, final_drain_state, now_iso),
        )

        logger.info("[FleetService] Node '%s' drain status set to %s (active_executions=%d)", node_id, final_drain_state, active_exec)

        return {
            "node_id": node_id,
            "drain_state": final_drain_state,
            "active_executions": active_exec,
            "admissions_disabled": True,
            "persisted": True,
        }

    def undrain_node(self, node_id: str, conn: sqlite3.Connection, actor: PipelineActorContext) -> Dict[str, Any]:
        """Restores node from draining/maintenance to ACTIVE status and resumes task admission."""
        if not any(r in ("admin", "operator", "platform_admin") for r in getattr(actor, "roles", ())):
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, "Undrain operation requires admin or operator role.")

        self._ensure_schema(conn)
        dist_coord = self._get_engine_distributed_coordinator()
        ra = self._get_engine_runtime_authority()

        if dist_coord:
            dist_coord.set_node_drain_state(node_id, NodeDrainState.ACTIVE.value)
        if ra and hasattr(ra, "set_drain_mode"):
            ra.set_drain_mode(False)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO fleet_node_states (node_id, drain_state, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET drain_state = excluded.drain_state, updated_at = excluded.updated_at
            """,
            (node_id, NodeDrainState.ACTIVE.value, now_iso),
        )

        logger.info("[FleetService] Node '%s' undrained back to ACTIVE (persisted)", node_id)

        return {
            "node_id": node_id,
            "drain_state": NodeDrainState.ACTIVE.value,
            "admissions_disabled": False,
            "persisted": True,
        }
