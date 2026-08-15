"""
AKAAL CDC Apply Orchestration Manager.
=======================================
Orchestrates target apply workers, manages apply sessions, handles pause/resume/stop,
computes backlog catch-up metrics, and publishes CentralStateStore telemetry via EngineGateway.
"""

from typing import Dict, Any, Optional, List
import time
import logging

from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position
from akaal.cdc.domain.durability import CDCCheckpoint
from akaal.cdc.domain.lifecycle import CDCAckState, CDCSessionState, CDCSessionStateMachine
from akaal.cdc.domain.telemetry import CDCMonitoringDTO
from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory, CDCFailureType, CDCExecutionError

from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer
from akaal.cdc.apply.engine import CDCApplyWorker
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger(__name__)


class CDCApplyCoordinator:
    """
    Central Controller for CDC Target Apply & Backlog Management.
    Coordinates DurableCDCBuffer, CDCApplyWorker instances, fencing tokens, and EngineGateway operations.
    """

    def __init__(
        self,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
    ) -> None:
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()
        self.active_buffers: Dict[str, DurableCDCBuffer] = {}
        self.active_workers: Dict[str, CDCApplyWorker] = {}
        self.active_epochs: Dict[str, int] = {}
        self.apply_statuses: Dict[str, str] = {}
        self.apply_counts: Dict[str, int] = {}
        self.start_times: Dict[str, float] = {}

    def get_or_create_buffer(self, identity: CDCEventIdentity) -> DurableCDCBuffer:
        sess_id = identity.cdc_session_id
        if sess_id not in self.active_buffers:
            self.active_buffers[sess_id] = DurableCDCBuffer(identity=identity)
        return self.active_buffers[sess_id]

    def start_cdc_apply(
        self,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        fencing_epoch: Optional[int] = None,
    ) -> Dict[str, Any]:
        epoch = fencing_epoch or self.recovery_coordinator.issue_epoch(migration_id)
        identity = CDCEventIdentity(
            migration_id=migration_id,
            job_id=job_id,
            run_id=run_id,
            cdc_session_id=cdc_session_id,
        )
        buf = self.get_or_create_buffer(identity)
        worker = CDCApplyWorker(
            identity=identity,
            durable_buffer=buf,
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
        )
        self.active_workers[cdc_session_id] = worker
        self.active_epochs[cdc_session_id] = epoch
        self.apply_statuses[cdc_session_id] = "APPLYING"
        self.apply_counts[cdc_session_id] = 0
        self.start_times[cdc_session_id] = time.time()

        self._publish_apply_telemetry(cdc_session_id)

        return {
            "cdc_session_id": cdc_session_id,
            "status": "APPLYING",
            "fencing_epoch": epoch,
        }

    def process_apply_batch(self, cdc_session_id: str, batch_size: int = 10, target_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Applies up to batch_size transactions from durable buffer to target."""
        if cdc_session_id not in self.active_workers:
            raise ValueError(f"CDC apply session '{cdc_session_id}' is not active.")

        worker = self.active_workers[cdc_session_id]
        epoch = self.active_epochs[cdc_session_id]

        applied_count = 0
        events_count = 0
        for _ in range(batch_size):
            res = worker.apply_next_transaction(current_fencing_epoch=epoch, target_config=target_config)
            if not res["applied"]:
                break
            applied_count += 1
            events_count += res.get("events_applied", 0)

        self.apply_counts[cdc_session_id] = self.apply_counts.get(cdc_session_id, 0) + events_count
        self._publish_apply_telemetry(cdc_session_id)

        return {
            "cdc_session_id": cdc_session_id,
            "status": self.apply_statuses.get(cdc_session_id, "APPLYING"),
            "transactions_applied": applied_count,
            "events_applied": events_count,
        }

    def pause_cdc_apply(self, cdc_session_id: str) -> Dict[str, Any]:
        self.apply_statuses[cdc_session_id] = "PAUSED"
        self._publish_apply_telemetry(cdc_session_id)
        return {"cdc_session_id": cdc_session_id, "status": "PAUSED"}

    def resume_cdc_apply(self, cdc_session_id: str) -> Dict[str, Any]:
        self.apply_statuses[cdc_session_id] = "APPLYING"
        self._publish_apply_telemetry(cdc_session_id)
        return {"cdc_session_id": cdc_session_id, "status": "APPLYING"}

    def stop_cdc_apply(self, cdc_session_id: str) -> Dict[str, Any]:
        self.apply_statuses[cdc_session_id] = "TERMINATED"
        self._publish_apply_telemetry(cdc_session_id)
        return {"cdc_session_id": cdc_session_id, "status": "TERMINATED"}

    def get_cdc_backlog_status(self, cdc_session_id: str) -> Dict[str, Any]:
        if cdc_session_id not in self.active_buffers:
            return {"cdc_session_id": cdc_session_id, "status": "UNKNOWN"}

        buf = self.active_buffers[cdc_session_id]
        worker = self.active_workers.get(cdc_session_id)
        metrics = buf.get_backlog_metrics()

        elapsed = max(0.1, time.time() - self.start_times.get(cdc_session_id, time.time()))
        events_applied = self.apply_counts.get(cdc_session_id, 0)
        apply_rate = round(events_applied / elapsed, 2)
        catchup_time = round(metrics["buffered_events"] / max(0.01, apply_rate), 2) if apply_rate > 0 else 0.0

        return {
            "cdc_session_id": cdc_session_id,
            "status": self.apply_statuses.get(cdc_session_id, "UNKNOWN"),
            "fencing_epoch": self.active_epochs.get(cdc_session_id, 0),
            "buffered_transactions": metrics["buffered_transactions"],
            "buffered_events": metrics["buffered_events"],
            "buffered_bytes": metrics["buffered_bytes"],
            "buffer_utilization": metrics["buffer_utilization"],
            "backpressure_state": metrics["backpressure_state"],
            "apply_rate_events_per_sec": apply_rate,
            "estimated_catchup_time_sec": catchup_time,
            "last_applied_position": worker.last_applied_position.to_dict() if worker and worker.last_applied_position else None,
            "last_acknowledged_position": worker.last_acknowledged_position.to_dict() if worker and worker.last_acknowledged_position else None,
        }

    def recover_cdc_session(self, migration_id: str, cdc_session_id: str) -> Dict[str, Any]:
        """Recovers session, issuing a new fencing epoch and replaying disk WAL buffer."""
        rec_info = self.recovery_coordinator.recover_migration_state(migration_id)
        new_epoch = rec_info["epoch"]
        self.active_epochs[cdc_session_id] = new_epoch

        if cdc_session_id in self.active_buffers:
            buf = self.active_buffers[cdc_session_id]
            recovered_count = buf.recover_from_wal()
        else:
            recovered_count = 0

        self.apply_statuses[cdc_session_id] = "RECOVERED"
        self._publish_apply_telemetry(cdc_session_id)

        return {
            "cdc_session_id": cdc_session_id,
            "status": "RECOVERED",
            "new_fencing_epoch": new_epoch,
            "recovered_transactions": recovered_count,
        }

    def _publish_apply_telemetry(self, cdc_session_id: str) -> None:
        worker = self.active_workers.get(cdc_session_id)
        buf = self.active_buffers.get(cdc_session_id)

        dto = CDCMonitoringDTO(
            cdc_session_id=cdc_session_id,
            migration_id=worker.identity.migration_id if worker else "unknown",
            job_id=worker.identity.job_id if worker else "unknown",
            run_id=worker.identity.run_id if worker else "unknown",
            status=self.apply_statuses.get(cdc_session_id, "UNKNOWN"),
            capture_status="CAPTURING",
            events_applied_total=self.apply_counts.get(cdc_session_id, 0),
            applied_position=worker.last_applied_position.to_string() if worker and worker.last_applied_position else None,
            acknowledged_position=worker.last_acknowledged_position.to_string() if worker and worker.last_acknowledged_position else None,
        )
        self.state_store.update_cdc_telemetry(cdc_session_id, dto.to_dict())
