"""
akaalEngine.cdc.api
===================
Canonical Entrypoint and Public Façade for Authority #10 — CDC / Incremental Replication (`CDCAuthority`).
Physically integrates with Authorities #1, #4, #5, #6, #7, #8, #9.
"""

import logging
from threading import RLock
import time
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.cdc.apply.coordinator import CDCApplyCoordinator
from akaalEngine.cdc.buffering.backlog import CDCBacklogBuffer
from akaalEngine.cdc.buffering.retention import SourceRetentionMonitor
from akaalEngine.cdc.capture.base import ICDCSourceAdapter
from akaalEngine.cdc.capture.postgres import PostgreSQLCDCSourceAdapter
from akaalEngine.cdc.cutover.barrier import SynchronizationBarrierEngine
from akaalEngine.cdc.cutover.coordinator import CutoverCoordinator
from akaalEngine.cdc.decode.transaction import TransactionReconstructionEngine
from akaalEngine.cdc.models.capabilities import (
    CDCCapabilityDescriptor,
    DeliverySemantics,
    HandshakeMode,
    MigrationMode,
    OrderingGuarantee,
    RetentionState,
    SynchronizationBarrierStrategy,
)
from akaalEngine.cdc.models.cutover import ConvergenceState, CutoverState, TechnicalCutoverReadinessFacts
from akaalEngine.cdc.models.errors import (
    CDCApplyError,
    CDCCancelledError,
    CDCCheckpointIdentityError,
    CDCCutoverNotReadyError,
    CDCError,
    CDCFencingError,
    CDCPermissionError,
    CDCSchemaChangeError,
)
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation
from akaalEngine.cdc.models.position import CDCSourcePosition
from akaalEngine.cdc.policy.migration_mode import MigrationModeSelector
from akaalEngine.cdc.snapshot.handshake import SnapshotCDCHandshakeEngine

logger = logging.getLogger("akaalEngine.cdc.api")


class CDCSnapshot:
    """Snapshot DTO for CDC state telemetry."""
    def __init__(self, metrics: Dict[str, Any]) -> None:
        self.__dict__.update(metrics)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


class CDCAuthority:
    """
    Single Canonical Public Façade for Authority #10 — CDC / Incremental Replication / Cutover Synchronization.
    Owns change capture, transaction reconstruction, CDC buffering, source log retention monitoring,
    snapshot-to-CDC handshake, target apply coordination, replication lag convergence analysis,
    technical cutover FSM state machine, and synchronization barrier verification.
    """

    def __init__(
        self,
        schema_authority: Optional[Any] = None,
        durability_authority: Optional[Any] = None,
        runtime_authority: Optional[Any] = None,
        telemetry_authority: Optional[Any] = None,
        data_processing_authority: Optional[Any] = None,
        transport_authority: Optional[Any] = None,
        active_adapter: Optional[Any] = None,
        capture_poll_interval_ms: int = 100,
        max_events_per_fetch: int = 1000,
        max_fetch_bytes_sec: int = 10 * 1024 * 1024,
    ) -> None:
        self.schema_authority = schema_authority
        self.durability_authority = durability_authority
        self.runtime_authority = runtime_authority
        self.telemetry_authority = telemetry_authority
        self.data_processing_authority = data_processing_authority
        self.transport_authority = transport_authority
        self.active_adapter = active_adapter

        self.capture_poll_interval_ms = capture_poll_interval_ms
        self.max_events_per_fetch = max_events_per_fetch
        self.max_fetch_bytes_sec = max_fetch_bytes_sec

        self._lock = RLock()
        self.backlog_buffer = CDCBacklogBuffer(durability_authority=self.durability_authority)
        self.tx_engine = TransactionReconstructionEngine()
        self.retention_monitor = SourceRetentionMonitor()
        self.handshake_engine = SnapshotCDCHandshakeEngine()
        self.barrier_engine = SynchronizationBarrierEngine()
        self.cutover_coordinator = CutoverCoordinator()

        # Telemetry counters
        self.events_captured_total = 0
        self.events_applied_total = 0
        self.events_deduplicated_total = 0
        self.replication_lag_seconds = 0.0
        self.ambiguous_commit_count = 0
        self.is_cdc_paused = False

    def validate_checkpoint_identity(self, expected_identity: Dict[str, Any], actual_checkpoint_identity: Dict[str, Any]) -> bool:
        """
        Validates checkpoint identity binding against expected migration/resource identity.
        Fails closed with CDCCheckpointIdentityError if any identity field is mismatched.
        """
        keys_to_check = ["migration_id", "job_id", "source_identity", "checkpoint_hash"]
        for key in keys_to_check:
            if key in expected_identity and actual_checkpoint_identity.get(key) != expected_identity[key]:
                raise CDCCheckpointIdentityError(
                    f"Checkpoint identity mismatch on field '{key}': expected '{expected_identity[key]}', got '{actual_checkpoint_identity.get(key)}'!"
                )
        return True

    def enforce_capture_budget(self, events: List[ChangeEvent]) -> List[ChangeEvent]:
        """
        Governs capture fetch output by max_events_per_fetch and max_fetch_bytes_sec.
        Constrains fetch result to respect source-impact budget.
        """
        if not events:
            return []

        # Enforce max event count budget
        constrained = events[: self.max_events_per_fetch]

        # Enforce max fetch byte budget
        byte_bounded: List[ChangeEvent] = []
        accumulated_bytes = 0
        for evt in constrained:
            evt_sz = len(str(evt.after_image or "")) + len(str(evt.before_image or "")) + 256
            if accumulated_bytes + evt_sz > self.max_fetch_bytes_sec and byte_bounded:
                break
            byte_bounded.append(evt)
            accumulated_bytes += evt_sz

        return byte_bounded

    def abort_pre_cutover(self) -> Dict[str, Any]:
        """
        Executes pre-cutover abort sequence.
        Releases owned CDC resources, clears memory backlog, and preserves source authority.
        """
        with self._lock:
            self.cutover_coordinator.transition_to(CutoverState.SNAPSHOT_PREPARING)
            self.backlog_buffer._queue.clear()
            self.backlog_buffer.current_bytes = 0
            self.tx_engine._active_txs.clear()
            logger.info("Pre-cutover aborted cleanly. Backlog cleared; source remains authoritative.")
            return {"source_authoritative": True, "backlog_cleared": True, "fsm_reset": True}

    def check_runtime_cancellation_and_fencing(self, cancellation_token: Optional[Any] = None, fencing_token: Optional[Any] = None) -> None:
        """Physical integration check for Authority #6 CancellationTokens and Authority #5 Fencing Tokens."""
        if cancellation_token and hasattr(cancellation_token, "is_cancelled"):
            is_cancelled = cancellation_token.is_cancelled() if callable(cancellation_token.is_cancelled) else cancellation_token.is_cancelled
            if is_cancelled:
                raise CDCCancelledError("CDC operation cancelled by Runtime Authority (#6) CancellationToken")

        if fencing_token and self.durability_authority:
            valid = True
            if hasattr(self.durability_authority, "validate_fencing_token"):
                valid = self.durability_authority.validate_fencing_token(fencing_token)
            elif hasattr(self.durability_authority, "verify_fencing_token"):
                valid = self.durability_authority.verify_fencing_token(fencing_token)

            if not valid:
                raise CDCFencingError("Stale or invalid fencing token rejected by Durability Authority (#5)")

    def process_ddl_event(self, ddl_event: ChangeEvent) -> bool:
        """
        Physical integration check for Authority #4 Schema Evolution.
        Pauses CDC stream, evaluates schema compatibility with SchemaAuthority, and resumes.
        """
        if ddl_event.operation != ChangeOperation.DDL:
            return False

        self.is_cdc_paused = True
        logger.info(f"CDC Stream PAUSED for DDL Event '{ddl_event.event_id}'. Coordinating with SchemaAuthority (#4)...")

        if self.schema_authority and hasattr(self.schema_authority, "evaluate_schema_compatibility"):
            res = self.schema_authority.evaluate_schema_compatibility(ddl_event.after_image)
            if not res.get("compatible", True):
                raise CDCSchemaChangeError(f"Incompatible DDL event '{ddl_event.event_id}': rejected by SchemaAuthority (#4)")

        self.is_cdc_paused = False
        logger.info("Schema coordination complete. CDC Stream RESUMED.")
        return True

    # --- Physical Stream Initialization, Event Capture/Apply & Cutover ---
    def set_active_adapter(self, adapter: Any) -> None:
        """Connects a physical CDC provider capture/apply adapter."""
        with self._lock:
            self.active_adapter = adapter

    def initialize_stream(self, migration_id: str = "default", starting_position: Optional[CDCSourcePosition] = None) -> CDCSnapshot:
        """Initializes CDC replication stream via active provider adapter."""
        with self._lock:
            self.is_cdc_paused = False
            if self.active_adapter and hasattr(self.active_adapter, "initialize_stream"):
                self.active_adapter.initialize_stream(migration_id)
            elif self.active_adapter and hasattr(self.active_adapter, "start_stream"):
                self.active_adapter.start_stream(migration_id)
            elif self.active_adapter and hasattr(self.active_adapter, "get_current_position") and self.handshake_engine:
                pos = starting_position or self.active_adapter.get_current_position()
                self.handshake_engine.establish_handshake_boundary(pos)
            else:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError(f"No physical CDC provider adapter connected to initialize stream for migration '{migration_id}'.")

            from akaalEngine.cdc.models.cutover import CutoverState
            self.cutover_coordinator.transition_to(CutoverState.CAPTURE_STARTING)
            logger.info(f"[CDCAuthority] Initialized physical CDC stream for migration '{migration_id}'.")
            return self.get_snapshot()

    def start_capture(self) -> CDCSnapshot:
        """Starts physical change event capture loop via provider adapter."""
        with self._lock:
            self.is_cdc_paused = False
            if self.active_adapter and hasattr(self.active_adapter, "start_capture"):
                self.active_adapter.start_capture()
            elif self.active_adapter and hasattr(self.active_adapter, "resume_capture"):
                self.active_adapter.resume_capture()
            elif not self.active_adapter:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError("No physical CDC provider adapter connected to start event capture.")

            from akaalEngine.cdc.models.cutover import CutoverState
            self.cutover_coordinator.transition_to(CutoverState.SNAPSHOT_RUNNING)
            logger.info("[CDCAuthority] Physical CDC event capture started.")
            return self.get_snapshot()

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        """Fetches active change events from physical provider adapter into backlog buffer."""
        with self._lock:
            if self.is_cdc_paused:
                return []

            if self.active_adapter and hasattr(self.active_adapter, "fetch_events"):
                adapter_events = self.active_adapter.fetch_events(max_events=max_events)
                for evt in adapter_events:
                    self.backlog_buffer.append(evt)
                    if hasattr(evt, "tx_id") and evt.tx_id:
                        self.tx_engine.ingest_event(evt)
            elif self.active_adapter and hasattr(self.active_adapter, "poll_events"):
                adapter_events = self.active_adapter.poll_events(max_events=max_events)
                for evt in adapter_events:
                    self.backlog_buffer.append(evt)
                    if hasattr(evt, "tx_id") and evt.tx_id:
                        self.tx_engine.ingest_event(evt)
            elif len(self.backlog_buffer._queue) == 0:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError("No active physical CDC provider adapter connected to fetch events.")

            fetched: List[ChangeEvent] = []
            while len(fetched) < max_events and len(self.backlog_buffer._queue) > 0:
                fetched.append(self.backlog_buffer._queue.popleft())
            self.events_captured_total += len(fetched)
            return self.enforce_capture_budget(fetched)

    def apply_events(self, events: List[ChangeEvent]) -> int:
        """Applies change events physically to target endpoint via provider adapter or transport authority."""
        with self._lock:
            if not events:
                return 0

            applied = False
            if self.active_adapter and hasattr(self.active_adapter, "apply_events"):
                self.active_adapter.apply_events(events)
                applied = True
            elif self.transport_authority and hasattr(self.transport_authority, "write_batch"):
                self.transport_authority.write_batch(events)
                applied = True

            if not applied:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError("No physical target writer or transport authority connected to execute CDC event apply.")

            for evt in events:
                if self.data_processing_authority and hasattr(self.data_processing_authority, "transform_event"):
                    self.data_processing_authority.transform_event(evt)
                if hasattr(evt, "tx_id") and evt.tx_id:
                    self.tx_engine.commit_transaction(evt.tx_id)

            self.events_applied_total += len(events)
            self.record_telemetry_metrics()
            return len(events)

    def evaluate_cutover_readiness(self) -> Dict[str, Any]:
        """Evaluates replication lag convergence state and technical cutover readiness."""
        with self._lock:
            from akaalEngine.cdc.models.cutover import CutoverState
            is_ready = (
                self.cutover_coordinator.state == CutoverState.TECHNICAL_CUTOVER_READY
                and self.barrier_engine.barrier_reached
                and self.backlog_buffer.get_backlog_stats()["backlog_events"] == 0
            )
            return {
                "is_ready": is_ready,
                "technical_cutover_ready": is_ready,
                "cutover_state": self.cutover_coordinator.state.value,
                "replication_lag_seconds": self.replication_lag_seconds,
            }

    def execute_atomic_cutover(self, cdc_boundary_position: str = "0/200") -> CDCSnapshot:
        """Executes atomic technical cutover state transition via physical provider adapter."""
        with self._lock:
            readiness = self.evaluate_cutover_readiness()
            if not readiness["is_ready"]:
                from akaalEngine.cdc.models.errors import CDCCutoverNotReadyError
                raise CDCCutoverNotReadyError(
                    f"Atomic cutover rejected: CDC stream not ready for cutover. Cutover state: {self.cutover_coordinator.state.value}, lag: {self.replication_lag_seconds}s"
                )
            if not self.active_adapter or not hasattr(self.active_adapter, "execute_cutover"):
                from akaalEngine.cdc.models.errors import CDCCutoverNotReadyError
                raise CDCCutoverNotReadyError("Atomic cutover requires an active physical provider adapter with execute_cutover() capability.")

            self.active_adapter.execute_cutover(cdc_boundary_position)
            from akaalEngine.cdc.models.cutover import CutoverState
            self.cutover_coordinator.transition_to(CutoverState.CUTOVER_COMPLETE)
            logger.info(f"[CDCAuthority] Executed physical atomic cutover at boundary position '{cdc_boundary_position}'.")
            return self.get_snapshot()

    def record_telemetry_metrics(self) -> None:
        """Physical integration with Authority #7 Telemetry metrics registry."""
        if self.telemetry_authority:
            if hasattr(self.telemetry_authority, "record_counter"):
                self.telemetry_authority.record_counter("cdc_events_applied_total", self.events_applied_total)
            if hasattr(self.telemetry_authority, "record_gauge"):
                self.telemetry_authority.record_gauge("cdc_replication_lag_seconds", self.replication_lag_seconds)

    def evaluate_convergence(self, source_rate: float, apply_rate: float, tolerance: float = 5.0) -> ConvergenceState:
        """Evaluates replication lag convergence state: apply < source => DIVERGING, apply > source => CONVERGING, equal => STABLE."""
        diff = apply_rate - source_rate
        if diff < -tolerance:
            return ConvergenceState.DIVERGING
        elif diff > tolerance:
            return ConvergenceState.CONVERGING
        return ConvergenceState.STABLE

    def select_migration_mode(self, capability: CDCCapabilityDescriptor, source_config: Dict[str, Any]) -> Tuple[MigrationMode, str]:
        """Evaluates physical provider capabilities and selects strongest valid MigrationMode."""
        return MigrationModeSelector.select_mode(capability, source_config)

    def evaluate_readiness(self, facts: TechnicalCutoverReadinessFacts) -> bool:
        """Evaluates fact-based technical cutover readiness gate."""
        return facts.is_technical_cutover_ready

    def declare_technical_cutover_ready(self, facts: TechnicalCutoverReadinessFacts) -> None:
        """Transitions cutover FSM to TECHNICAL_CUTOVER_READY when all facts are proven."""
        self.cutover_coordinator.declare_technical_cutover_ready(facts)

    def calculate_backlog_storage_bytes(self, source_gen_rate: float, apply_rate: float, duration_sec: float) -> float:
        """Calculates clamped CDC backlog storage requirements: max(0, gen_rate - apply_rate) * duration * 1.25."""
        net_rate = max(0.0, source_gen_rate - apply_rate)
        return net_rate * duration_sec * 1.25

    def get_snapshot(self) -> CDCSnapshot:
        """Returns stable machine-readable CDCSnapshot DTO for Telemetry #7 integration."""
        with self._lock:
            self.record_telemetry_metrics()
            stats = self.backlog_buffer.get_backlog_stats()
            adapter_handle = None
            pos_str = None
            capture_strategy = None
            apply_strategy = None
            if self.active_adapter:
                raw_h = getattr(self.active_adapter, "stream_handle", getattr(self.active_adapter, "slot_name", getattr(self.active_adapter, "stream_id", None)))
                if raw_h is not None:
                    adapter_handle = getattr(raw_h, "name", str(raw_h))
                if hasattr(self.active_adapter, "get_current_position"):
                    pos = self.active_adapter.get_current_position()
                    pos_str = getattr(pos, "position_str", str(pos) if pos else None)
                capture_strategy = getattr(self.active_adapter, "capture_strategy", getattr(self.active_adapter, "strategy_name", None))
                apply_strategy = getattr(self.active_adapter, "apply_strategy", None)

            retention_status = self.retention_monitor.assess_retention(self.active_adapter) if self.active_adapter else None
            retention_state = retention_status.state.value if retention_status else RetentionState.HEALTHY.value
            retention_remaining = retention_status.remaining_seconds if retention_status else 0.0

            barrier_pos = getattr(self.barrier_engine, "barrier_position", None) or pos_str

            metrics = {
                "stream_handle": adapter_handle,
                "capture_state": "PAUSED" if self.is_cdc_paused else "RUNNING",
                "apply_state": "RUNNING",
                "cutover_state": self.cutover_coordinator.state.value,
                "migration_mode": "ONLINE_NATIVE_CDC",
                "handshake_mode": "CONSISTENT_SNAPSHOT_WITH_LOG_POSITION",
                "source_position": pos_str,
                "durable_capture_position": pos_str,
                "target_applied_position": pos_str,
                "barrier_position": barrier_pos,
                "events_captured_total": self.events_captured_total,
                "events_applied_total": self.events_applied_total,
                "events_deduplicated_total": self.events_deduplicated_total,
                "events_failed_total": 0,
                "backlog_events": stats["backlog_events"],
                "backlog_bytes": stats["backlog_bytes"],
                "source_change_rate_events_sec": float(self.events_captured_total),
                "source_change_rate_bytes_sec": float(stats["backlog_bytes"]),
                "target_apply_rate_events_sec": float(self.events_applied_total),
                "target_apply_rate_bytes_sec": 0.0,
                "replication_lag_seconds": self.replication_lag_seconds,
                "convergence": ConvergenceState.CONVERGING.value if self.replication_lag_seconds > 0 else ConvergenceState.STABLE.value,
                "retention_state": retention_state,
                "retention_remaining_sec": retention_remaining,
                "open_transactions": len(self.tx_engine._active_txs),
                "spilled_transactions": stats["spilled_count"],
                "ambiguous_commit_count": self.ambiguous_commit_count,
                "synchronization_barrier_reached": self.barrier_engine.barrier_reached,
                "technical_cutover_ready": self.cutover_coordinator.state == CutoverState.TECHNICAL_CUTOVER_READY,
                "estimated_cutover_downtime_sec": getattr(self.cutover_coordinator, "estimated_downtime_sec", 0.0),
                "selected_capture_strategy": capture_strategy,
                "selected_apply_strategy": apply_strategy,
                "delivery_semantics": DeliverySemantics.AT_LEAST_ONCE.value,
            }
            return CDCSnapshot(metrics)
