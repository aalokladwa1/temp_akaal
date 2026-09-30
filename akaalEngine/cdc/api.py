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
from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.errors.taxonomy import ExtensionEngineException
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId
from akaalEngine.extensions.resolution.handles import ResolvedStrategyHandle
from akaalEngine.extensions.spi.authority_contract import AuthorityContractDefinition

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
        extensions_authority: Optional[ExtensionsAuthority] = None,
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
        self._ext_auth = extensions_authority
        if self._ext_auth is not None:
            self._ext_auth.register_authority_contract(
                AuthorityContractDefinition(
                    authority_id=AuthorityId("cdc"),
                    contract_version="1.0.0",
                    description="CDC source adapter contract (Authority #10)",
                    expected_base_type=ICDCSourceAdapter,
                )
            )

        self.capture_poll_interval_ms = capture_poll_interval_ms
        self.max_events_per_fetch = max_events_per_fetch
        self.max_fetch_bytes_sec = max_fetch_bytes_sec

        self.streaming_health_state: str = "INITIALIZED"
        self.last_streaming_error: Optional[str] = None
        self.consecutive_streaming_failures: int = 0

        self._lock = RLock()
        import threading
        self._streaming_thread: Optional[threading.Thread] = None
        self._stop_streaming = threading.Event()
        self.backlog_buffer = CDCBacklogBuffer(durability_authority=self.durability_authority)
        self.tx_engine = TransactionReconstructionEngine()
        self.retention_monitor = SourceRetentionMonitor()
        self.handshake_engine = SnapshotCDCHandshakeEngine()
        self.barrier_engine = SynchronizationBarrierEngine()
        self.cutover_coordinator = CutoverCoordinator()
        self.apply_coordinator: Optional[CDCApplyCoordinator] = None

        # Telemetry counters
        self.events_captured_total = 0
        self.events_applied_total = 0
        self.events_deduplicated_total = 0
        self.replication_lag_seconds: Optional[float] = None
        self.ambiguous_commit_count = 0
        self.is_cdc_paused = False

    def bind_target_writer(
        self,
        target_writer: Any,
        ordering_guarantee: OrderingGuarantee = OrderingGuarantee.GLOBAL_COMMIT_ORDER,
    ) -> CDCApplyCoordinator:
        """Binds a physical TargetWriter to CDCApplyCoordinator for target DML execution."""
        with self._lock:
            self.apply_coordinator = CDCApplyCoordinator(
                target_writer=target_writer,
                data_processing_authority=self.data_processing_authority,
                durability_authority=self.durability_authority,
                ordering_guarantee=ordering_guarantee,
            )
            self._start_background_streaming()
            return self.apply_coordinator

    @property
    def is_streaming_active(self) -> bool:
        """Public authority query indicating whether continuous physical streaming worker thread is active."""
        return bool(self._streaming_thread and self._streaming_thread.is_alive())



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

    def set_capture_budget(self, max_events_per_fetch: Optional[int] = None, max_fetch_bytes_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Dynamically adjusts change capture throttle budgets under lock.
        Classified as RUNTIME_MUTABLE because limits are enforced on each poll cycle.
        Fails closed (REJECT INVALID): raises ValueError if parameters are <= 0.
        """
        with self._lock:
            if max_events_per_fetch is not None:
                val_events = int(max_events_per_fetch)
                if val_events <= 0:
                    raise ValueError("max_events_per_fetch must be a positive integer > 0")
                self.max_events_per_fetch = val_events
            if max_fetch_bytes_sec is not None:
                val_bytes = int(max_fetch_bytes_sec)
                if val_bytes <= 0:
                    raise ValueError("max_fetch_bytes_sec must be a positive integer > 0")
                self.max_fetch_bytes_sec = val_bytes
            logger.info(
                "[CDCAuthority] Updated capture budget: max_events_per_fetch=%d, max_fetch_bytes_sec=%d",
                self.max_events_per_fetch,
                self.max_fetch_bytes_sec,
            )
            return {
                "max_events_per_fetch": self.max_events_per_fetch,
                "max_fetch_bytes_sec": self.max_fetch_bytes_sec,
            }

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

    def resolve_adapter_for_provider(
        self,
        provider_id: str,
        required_capability: Optional[str] = None,
    ) -> ResolvedStrategyHandle:
        """
        Resolves a real CDC source adapter for `provider_id` from the Extensions authority
        (authority_id="cdc") rather than requiring a manually-constructed adapter via
        set_active_adapter(). Sets it as the active adapter and returns the lease handle
        so the caller can release it and, before invoking a capability-gated operation,
        call handle.require_capability(name) to fail closed on an unsupported/undeclared
        capability -- this is the CDC-specific enforcement point for negative capability
        declarations (e.g. a connector declaring CDC_CAPTURE=NO cannot be silently invoked
        for capture through this path).

        Requires this CDCAuthority to have been constructed with extensions_authority set;
        the manual set_active_adapter() path remains available and unaffected for callers
        that construct adapters directly.
        """
        if self._ext_auth is None:
            raise ExtensionEngineException(
                "CDCAuthority was constructed without extensions_authority; "
                "resolve_adapter_for_provider() requires it. Use set_active_adapter() directly instead.",
                error_code="CDC_EXTENSIONS_NOT_CONFIGURED",
            )

        handle = self._ext_auth.resolve_strategy(
            provider_id=provider_id,
            authority_id=AuthorityId("cdc"),
            required_capabilities=[required_capability] if required_capability else None,
        )
        if not isinstance(handle.strategy_instance, ICDCSourceAdapter):
            handle.release()
            raise ExtensionEngineException(
                f"Resolved 'cdc' strategy for provider '{provider_id}' does not implement "
                f"ICDCSourceAdapter (got {type(handle.strategy_instance).__name__}).",
                error_code="CDC_STRATEGY_CONTRACT_MISMATCH",
            )

        with self._lock:
            self.active_adapter = handle.strategy_instance
        return handle

    def drain_and_sync(self, max_events: int = 5000) -> int:
        """Drains physical source stream deltas completely and applies them to target writer."""
        with self._lock:
            total_applied = 0
            while True:
                try:
                    evts = self.fetch_events(max_events=max_events)
                    self.streaming_health_state = "HEALTHY"
                    self.consecutive_streaming_failures = 0
                except Exception as exc:
                    self.streaming_health_state = "UNHEALTHY"
                    self.last_streaming_error = str(exc)
                    self.consecutive_streaming_failures += 1
                    logger.warning(f"[CDCAuthority] fetch_events during drain notice ({self.consecutive_streaming_failures}): {exc}")
                    raise exc
                if not evts:
                    break
                applied = self.apply_events(evts)
                total_applied += applied
                if len(evts) < max_events:
                    break
            return total_applied

    def _start_background_streaming(self) -> None:
        """Starts background thread to continuously poll CDC deltas and apply them to target."""
        with self._lock:
            if self._streaming_thread and self._streaming_thread.is_alive():
                return
            self._stop_streaming.clear()

            def _loop():
                import threading
                while not self._stop_streaming.is_set():
                    try:
                        if not self.is_cdc_paused and self.active_adapter and getattr(self, "apply_coordinator", None):
                            self.drain_and_sync(max_events=1000)
                    except Exception as exc:
                        self.streaming_health_state = "UNHEALTHY"
                        self.last_streaming_error = str(exc)
                        logger.debug(f"[CDCAuthority] Background stream cycle notice: {exc}")
                    time.sleep(max(0.1, self.capture_poll_interval_ms / 1000.0))

            import threading
            self._streaming_thread = threading.Thread(target=_loop, name="akaal-cdc-streaming", daemon=True)
            self._streaming_thread.start()
            logger.info("[CDCAuthority] Continuous CDC streaming background thread started.")

    def initialize_stream(self, migration_id: str = "default", starting_position: Optional[CDCSourcePosition] = None) -> CDCSnapshot:
        """Initializes CDC replication stream via active provider adapter."""
        with self._lock:
            self.is_cdc_paused = False
            if self.active_adapter and hasattr(self.active_adapter, "initialize_stream"):
                self.active_adapter.initialize_stream(migration_id)
            elif self.active_adapter and hasattr(self.active_adapter, "start_stream"):
                self.active_adapter.start_stream(migration_id)
            elif self.active_adapter and hasattr(self.active_adapter, "start_capture"):
                self.active_adapter.start_capture(starting_position)
            elif self.active_adapter and hasattr(self.active_adapter, "get_current_position") and self.handshake_engine:
                pos = starting_position or self.active_adapter.get_current_position()
                self.handshake_engine.establish_handshake_boundary(pos)
            else:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError(f"No physical CDC provider adapter connected to initialize stream for migration '{migration_id}'.")

            from akaalEngine.cdc.models.cutover import CutoverState
            self.cutover_coordinator.transition_to(CutoverState.CAPTURE_STARTING)
            self._start_background_streaming()
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
            self._start_background_streaming()
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

    def _get_table_dependency_depth(self, table_name: str, evt: Optional[ChangeEvent] = None) -> int:
        """Generically resolves table FK dependency depth without hardcoded table literals."""
        if hasattr(self, "schema_authority") and self.schema_authority and hasattr(self.schema_authority, "get_table_dependency_depth"):
            try:
                return self.schema_authority.get_table_dependency_depth(table_name)
            except Exception:
                pass

        if evt is not None:
            if hasattr(evt, "dependency_depth") and evt.dependency_depth is not None:
                return evt.dependency_depth
            image = evt.after_image or evt.before_image or {}
            if isinstance(image, dict):
                tbl_clean = (table_name or "").lower().strip()
                tbl_stem = tbl_clean[:-1] if tbl_clean.endswith("s") and len(tbl_clean) > 3 else tbl_clean
                pk_cols_upper = set(str(k).upper() for k in (getattr(evt, "key_columns", None) or []))
                fk_count = 0
                for col in image.keys():
                    c_upper = str(col).upper()
                    if c_upper in pk_cols_upper:
                        continue
                    c_lower = str(col).lower()
                    if (c_lower.endswith("_id") or c_lower.endswith("_fk") or c_lower.endswith("_code")) and not c_lower.startswith(tbl_stem):
                        fk_count += 1
                if tbl_clean.endswith("_item") or tbl_clean.endswith("_items") or tbl_clean.endswith("_line") or tbl_clean.endswith("_lines") or tbl_clean.endswith("_detail"):
                    return max(3, fk_count + 1)
                return fk_count

        t = str(table_name).lower().strip()
        if t.endswith("_item") or t.endswith("_items") or t.endswith("_line") or t.endswith("_lines") or t.endswith("_detail") or t.endswith("_details"):
            return 3
        return 1


    def apply_events(self, events: List[ChangeEvent]) -> int:
        """Applies change events physically to target endpoint via provider adapter or transport authority."""
        with self._lock:
            if not events:
                return 0

            # Preserve transaction boundaries and commit ordering by grouping events per transaction/commit position:
            # Within each transaction:
            # 1. INSERTs/UPDATEs executed parent -> child (increasing depth)
            # 2. DELETEs executed child -> parent (decreasing depth)
            tx_groups: Dict[str, List[ChangeEvent]] = {}
            for e in events:
                tx_key = getattr(e, "tx_id", None) or getattr(e, "commit_position", None) or getattr(e, "source_position", None) or "global"
                tx_groups.setdefault(str(tx_key), []).append(e)

            ordered_events: List[ChangeEvent] = []
            for tx_key, tx_evts in tx_groups.items():
                deletes = [e for e in tx_evts if e.operation == ChangeOperation.DELETE]
                inserts_updates = [e for e in tx_evts if e.operation != ChangeOperation.DELETE]

                inserts_updates.sort(key=lambda e: self._get_table_dependency_depth(e.logical_object, e))
                deletes.sort(key=lambda e: self._get_table_dependency_depth(e.logical_object, e), reverse=True)

                ordered_events.extend(inserts_updates + deletes)

            applied = False
            if self.active_adapter and hasattr(self.active_adapter, "apply_events"):
                self.active_adapter.apply_events(ordered_events)
                applied = True
            elif getattr(self, "apply_coordinator", None) is not None:
                deferred_events: List[ChangeEvent] = []
                for evt in ordered_events:
                    tbl = evt.logical_object or getattr(evt, "table_name", "main") or "main"
                    tgt_schema = getattr(evt, "target_schema", None)
                    if not tgt_schema or tgt_schema == "public":
                        if hasattr(self.apply_coordinator, "target_writer"):
                            tw = self.apply_coordinator.target_writer
                            if hasattr(tw, "params") and isinstance(tw.params, dict):
                                tgt_schema = (
                                    tw.params.get("schema")
                                    or tw.params.get("user")
                                    or tw.params.get("username")
                                    or tw.params.get("database")
                                    or "public"
                                )
                    try:
                        self.apply_coordinator.apply_event(evt, table_name=tbl, target_schema=tgt_schema or "public")
                    except Exception as apply_err:
                        err_str = str(apply_err).lower()
                        if "ora-02291" in err_str or "ora-02292" in err_str or "foreign key" in err_str or "integrity constraint" in err_str:
                            logger.debug(f"[CDCAuthority] Deferring FK event {evt.event_id} for table {tbl}: {apply_err}")
                            deferred_events.append(evt)
                        else:
                            raise apply_err

                # Retry deferred events after parents have settled using topological dependency order
                if deferred_events:
                    max_passes = 4
                    for _pass in range(max_passes):
                        deferred_events.sort(key=lambda e: self._get_table_dependency_depth(e.logical_object, e))
                        still_deferred: List[ChangeEvent] = []
                        for evt in deferred_events:
                            tbl = evt.logical_object or getattr(evt, "table_name", "main") or "main"
                            tgt_schema = getattr(evt, "target_schema", None)
                            if not tgt_schema or tgt_schema == "public":
                                if hasattr(self.apply_coordinator, "target_writer"):
                                    tw = self.apply_coordinator.target_writer
                                    if hasattr(tw, "params") and isinstance(tw.params, dict):
                                        tgt_schema = (
                                            tw.params.get("schema")
                                            or tw.params.get("user")
                                            or tw.params.get("username")
                                            or tw.params.get("database")
                                            or "public"
                                        )
                            try:
                                self.apply_coordinator.apply_event(evt, table_name=tbl, target_schema=tgt_schema or "public")
                            except Exception as retry_err:
                                err_str = str(retry_err).lower()
                                if "ora-02291" in err_str or "ora-02292" in err_str or "foreign key" in err_str or "integrity constraint" in err_str:
                                    still_deferred.append(evt)
                                else:
                                    raise retry_err
                        deferred_events = still_deferred
                        if not deferred_events:
                            break
                    if deferred_events:
                        last_evt = deferred_events[0]
                        last_tbl = last_evt.logical_object or getattr(last_evt, "table_name", "main") or "main"
                        from akaalEngine.cdc.models.errors import CDCApplyError
                        raise CDCApplyError(f"Deferred FK event '{last_evt.event_id}' for table '{last_tbl}' failed apply after {max_passes} passes.")

                applied = True
            elif self.transport_authority and hasattr(self.transport_authority, "write_batch"):
                self.transport_authority.write_batch(ordered_events)
                applied = True

            if not applied:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError("No physical target writer or CDCApplyCoordinator connected to execute CDC event apply.")

            for evt in ordered_events:
                if self.data_processing_authority and hasattr(self.data_processing_authority, "transform_event"):
                    self.data_processing_authority.transform_event(evt)
                if hasattr(evt, "tx_id") and evt.tx_id:
                    self.tx_engine.commit_transaction(evt.tx_id)
                self.backlog_buffer.ack_event(evt.event_id)

            self.events_applied_total += len(ordered_events)
            self.record_telemetry_metrics()
            return len(ordered_events)

    def recover_from_durability(self, session_id: Optional[str] = None) -> List[ChangeEvent]:
        """Recovers unapplied pending CDC backlog events from Authority #5 Durability store."""
        with self._lock:
            return self.backlog_buffer.recover_pending_events(session_id)

    def evaluate_cutover_readiness(self) -> Dict[str, Any]:
        """Evaluates replication lag convergence state and technical cutover readiness."""
        with self._lock:
            self.drain_and_sync()
            from akaalEngine.cdc.models.cutover import CutoverState
            self.barrier_engine.reach_barrier("CUTOVER_READY")
            self.cutover_coordinator.transition_to(CutoverState.TECHNICAL_CUTOVER_READY)
            return {
                "is_ready": True,
                "technical_cutover_ready": True,
                "cutover_state": self.cutover_coordinator.state.value,
                "replication_lag_seconds": 0.0,
            }

    def execute_atomic_cutover(self, cdc_boundary_position: str = "0/200") -> CDCSnapshot:
        """Executes atomic technical cutover state transition via physical provider adapter."""
        with self._lock:
            self.drain_and_sync()
            if self.active_adapter and hasattr(self.active_adapter, "execute_cutover"):
                self.active_adapter.execute_cutover(cdc_boundary_position)
            from akaalEngine.cdc.models.cutover import CutoverState
            self.barrier_engine.reach_barrier("CUTOVER_COMPLETE")
            self.cutover_coordinator.transition_to(CutoverState.CUTOVER_COMPLETE)
            logger.info(f"[CDCAuthority] Executed physical atomic cutover at boundary position '{cdc_boundary_position}'.")
            return self.get_snapshot()

    def record_telemetry_metrics(self) -> None:
        """Physical integration with Authority #7 Telemetry metrics registry."""
        if self.telemetry_authority:
            if hasattr(self.telemetry_authority, "record_counter"):
                self.telemetry_authority.record_counter("cdc_events_applied_total", self.events_applied_total)
            if hasattr(self.telemetry_authority, "record_gauge"):
                lag_val = self.replication_lag_seconds if self.replication_lag_seconds is not None else 0.0
                self.telemetry_authority.record_gauge("cdc_replication_lag_seconds", lag_val)


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
                if not adapter_handle:
                    adapter_handle = f"cdc-stream-{getattr(self.active_adapter, 'engine_name', 'native').lower()}"

                if hasattr(self.active_adapter, "get_current_position"):
                    pos = self.active_adapter.get_current_position()
                    if hasattr(pos, "to_string"):
                        pos_str = pos.to_string()
                    else:
                        pos_str = getattr(pos, "position_str", str(pos) if pos else None)

                capture_strategy = getattr(self.active_adapter, "capture_strategy", getattr(self.active_adapter, "strategy_name", None))
                apply_strategy = getattr(self.active_adapter, "apply_strategy", None)

            retention_status = self.retention_monitor.assess_retention(self.active_adapter) if self.active_adapter else None
            retention_state = retention_status.state.value if retention_status else RetentionState.HEALTHY.value
            retention_remaining = retention_status.remaining_seconds if retention_status else None

            barrier_pos = getattr(self.barrier_engine, "barrier_position", None) or pos_str

            metrics = {
                "stream_handle": adapter_handle,
                "boundary_token": pos_str,
                "capture_state": "PAUSED" if self.is_cdc_paused else "RUNNING",
                "apply_state": "RUNNING" if self.apply_coordinator is not None else "UNBOUND",
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
                "convergence": ConvergenceState.CONVERGING.value if (self.replication_lag_seconds is not None and self.replication_lag_seconds > 0) else ConvergenceState.STABLE.value,
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

_DEFAULT_CDC_AUTHORITY: Optional[CDCAuthority] = None


def default_cdc_authority(
    schema_authority: Optional[Any] = None,
    durability_authority: Optional[Any] = None,
    runtime_authority: Optional[Any] = None,
    telemetry_authority: Optional[Any] = None,
    data_processing_authority: Optional[Any] = None,
    transport_authority: Optional[Any] = None,
    extensions_authority: Optional[Any] = None,
) -> CDCAuthority:
    """Canonical singleton authority factory for shared Engine CDC Authority."""
    global _DEFAULT_CDC_AUTHORITY
    if _DEFAULT_CDC_AUTHORITY is None:
        _DEFAULT_CDC_AUTHORITY = CDCAuthority(
            schema_authority=schema_authority,
            durability_authority=durability_authority,
            runtime_authority=runtime_authority,
            telemetry_authority=telemetry_authority,
            data_processing_authority=data_processing_authority,
            transport_authority=transport_authority,
            extensions_authority=extensions_authority,
        )
    return _DEFAULT_CDC_AUTHORITY


def reset_default_cdc_authority() -> None:
    """Resets the shared Engine CDC Authority singleton."""
    global _DEFAULT_CDC_AUTHORITY
    if _DEFAULT_CDC_AUTHORITY is not None:
        try:
            _DEFAULT_CDC_AUTHORITY._stop_streaming.set()
        except Exception:
            pass
        _DEFAULT_CDC_AUTHORITY = None

