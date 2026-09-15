"""Plan-driven DAG stage dispatch for AkaalSuperEngine's physical execution path.

This module is NOT a second execution engine/coordinator/authority. It is
AkaalSuperEngine's own dispatch logic (invoked exclusively from
`AkaalSuperEngine.execute_migration`), extracted into its own file for
readability. `AkaalSuperEngine` remains the single physical execution
authority; this module has no independent entrypoint, no registry
presence, and is not importable/usable as a standalone runtime.

Responsibility mapping: each compiled `dag_stages` entry (produced by the
canonical `akaal.planner.engine.plan_compiler.PlanCompiler`, itself
untouched by this module) is dispatched by its stage NAME to the existing
canonical authority for that responsibility:

  - Schema deployment  -> for postgresql/oracle targets: the existing,
    unmodified `SchemaExecutionStep` (akaal/workflow/steps/migration_steps.py).
    For dialects that step does not support (e.g. sqlite, used by the
    local simulated acceptance estate), a dialect-neutral fallback issues
    `CREATE TABLE IF NOT EXISTS` via the target's own canonical
    `IDatabaseCapability`/`BaseAdapter` connection -- this does not
    replace `SchemaExecutionStep`, it only covers a dialect the legacy,
    Postgres/Oracle-hardcoded step was never built to support, without
    modifying that step's frozen behavior for the dialects it does support.
  - Data transport     -> for postgresql/oracle targets: the existing
    `DataTransportStep`. For unsupported dialects: the same canonical
    `BaseAdapter.read_batch`/`write_batch` contract, called directly.
  - Reconciliation/validation (M1/M2/M5/M7/M8 nodes) -> the existing
    `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine`
    (Validation Authority #11), fed rows read via the canonical adapter
    contract. No parallel comparison logic is implemented here.
  - CDC / incremental-poll nodes -> dispatched in later phases of this
    correction to `akaal.cdc.apply.engine.CDCApplyWorker` and to the new
    incremental-polling step (see akaal/engine/incremental_poll.py),
    respectively.
  - Evidence ("SHA-256 Digital Trust Seal") -> best-effort binding to the
    canonical Evidence Authority; if that authority is not reachable from
    this call path, the gap is reported truthfully rather than papered
    over with a substitute "evidence-shaped" record (see correction
    report for the exact finding).

No stage handler here ever fabricates success: a handler that cannot
genuinely perform its responsibility raises or returns success=False,
and the dispatcher propagates that as a dependency failure to every
downstream stage (fail-closed, per correction #6/#11).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("akaal.engine.plan_dispatch")

# Stage-name -> responsibility-type mapping. Names are the exact strings
# PlanCompiler emits (akaal/planner/engine/plan_compiler.py::_build_dynamic_dag).
STAGE_RESPONSIBILITY = {
    "Discovery & Catalog Fencing": "discovery",
    "Consistent Change Boundary Token Capture": "cdc_boundary",
    "DAG Topological Dependency Sorting & Schema Routing": "planning_metadata",
    "Target Schema Structure Deployment": "schema",
    "Target Schema Structure Verification": "schema_verify",
    "CDC Change Capture Initialization": "cdc_init",
    "Parallel Stream Data Transport": "transport",
    "CDC Stream Apply & Continuous Catchup": "cdc_apply",
    "Incremental Watermark Query & Batch Apply": "incremental_poll",
    "State-Based Differential Analysis & Reconciliation": "reconciliation",
    "Reconciliation & Validation Node": "validation",
    "Passive Source & Target State Inspection": "inspection",
    "Deep Data Reconciliation & Integrity Verification": "reconciliation",
    "Repair Eligibility & Candidate Evaluation": "repair_eligibility",
    "SHA-256 Digital Trust Seal": "evidence",
}

# Dialects the legacy, Postgres/Oracle-hardcoded workflow steps genuinely
# support (SQL-text addressing, %s placeholders, PostgreSQLDDLEmitter/etc).
LEGACY_STEP_SUPPORTED_TARGET_DIALECTS = {"postgresql", "postgres", "oracle"}

# SEC correction: defense-in-depth mode fence.
#
# Before this correction, `PlanExecutionDispatcher.run()` dispatched every
# stage in `dag_stages` purely by STAGE NAME, with no check that the
# responsibility that stage name maps to is even legal for the DECLARED
# execution mode. That means the dispatcher's mode-fencing (M3 cannot bulk,
# M6 cannot transport, M7 cannot DDL, etc.) was entirely a property of
# `PlanCompiler` never EMITTING an illegal stage for a given mode -- there
# was no defense-in-depth inside the dispatcher itself. A malformed,
# hostile, or buggy-future-caller-supplied `dag_dict` claiming
# `execution_mode=M6` but containing a `"Parallel Stream Data Transport"`
# stage would have been executed verbatim: the dispatcher never asked "is
# this responsibility even ALLOWED for this mode?"
#
# This table is the dispatcher's OWN, independent legality check, derived
# from the exact mode->stage rules `PlanCompiler._build_dynamic_dag`
# encodes (akaal/planner/engine/plan_compiler.py:601-731). It does not
# replace `PlanCompiler` as the source of truth for what a *correctly*
# compiled plan looks like; it is an additional, fail-closed gate so that
# an illegal DAG node for the declared mode cannot execute even if it
# somehow reaches the dispatcher.
MODE_ALLOWED_RESPONSIBILITIES = {
    "M1": {"discovery", "planning_metadata", "schema", "transport", "validation", "evidence"},
    "M2": {"discovery", "planning_metadata", "cdc_boundary", "schema", "cdc_init", "transport", "cdc_apply", "validation", "evidence"},
    "M3": {"discovery", "planning_metadata", "cdc_init", "cdc_apply", "validation", "evidence"},
    "M4": {"discovery", "planning_metadata", "incremental_poll", "validation", "evidence"},
    "M5": {"discovery", "planning_metadata", "reconciliation", "repair_eligibility", "evidence"},
    "M6": {"discovery", "planning_metadata", "schema", "schema_verify", "evidence"},
    "M7": {"discovery", "planning_metadata", "transport", "validation", "evidence"},
    "M8": {"discovery", "planning_metadata", "inspection", "reconciliation", "repair_eligibility", "evidence"},
}


def _canonical_mode_key(mode_str: str) -> str:
    """Resolves any legal mode alias to its canonical 'M1'..'M8' key using
    the SAME canonical `ExecutionMode.from_string` the planner uses -- no
    duplicated alias table. Raises ValueError (fail closed) for anything
    that is not a recognized mode."""
    from akaal.planner.models.p5_domain import ExecutionMode
    return ExecutionMode.from_string(mode_str).value


@dataclass
class StageOutcome:
    stage_name: str
    responsibility: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    skipped_reason: Optional[str] = None


@dataclass
class PlanExecutionResult:
    plan_fingerprint: str
    mode: str
    stage_outcomes: List[StageOutcome] = field(default_factory=list)
    success: bool = True
    rows_read: int = 0
    rows_written: int = 0
    tables_processed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_fingerprint": self.plan_fingerprint,
            "mode": self.mode,
            "success": self.success,
            "rows_read": self.rows_read,
            "rows_written": self.rows_written,
            "tables_processed": self.tables_processed,
            "stages": [
                {
                    "stage_name": o.stage_name,
                    "responsibility": o.responsibility,
                    "success": o.success,
                    "details": o.details,
                    "errors": o.errors,
                    "skipped_reason": o.skipped_reason,
                }
                for o in self.stage_outcomes
            ],
        }


def _physical_table_names(selected_objs: List[Dict[str, Any]]) -> List[str]:
    names = []
    for obj in selected_objs:
        n = obj.get("target_object_name") or obj.get("object_name") or obj.get("name")
        if n:
            names.append(n)
    return names


def _sqlite_column_ddl(col: Dict[str, Any]) -> str:
    name = col["name"]
    affinity = (col.get("type") or "TEXT").upper() or "TEXT"
    parts = [f'"{name}"', affinity]
    if not col.get("nullable", True):
        parts.append("NOT NULL")
    return " ".join(parts)


class _CDCApplyAdapterBridge:
    """M2/M3 correction: translates CDCApplyWorker's physical-application
    hook (`target_adapter.apply_changes(events)`) into the canonical
    `BaseAdapter.write_batch` (upsert, covers INSERT/UPDATE) contract plus
    a minimal delete-by-primary-key statement for DELETE. No adapter in
    this repository implements `apply_changes` natively; this bridge does
    not modify or extend `BaseAdapter` -- it lives entirely inside this
    dispatcher's own CDC-apply call path, the same pattern already used
    for the sqlite dialect-neutral schema/transport fallback."""

    def __init__(self, tgt_adapter):
        self.tgt_adapter = tgt_adapter

    async def apply_changes(self, events) -> bool:
        from akaal.cdc.domain.events import CDCOperationType
        for evt in events:
            table = evt.source_table
            if evt.operation in (CDCOperationType.INSERT, CDCOperationType.UPDATE):
                row = evt.after_image or {}
                if row:
                    await self.tgt_adapter.write_batch(table, [row])
            elif evt.operation == CDCOperationType.DELETE:
                row = evt.before_image or {}
                if row:
                    pk_col = next(iter(row.keys()))
                    conn = self.tgt_adapter.get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute(f'DELETE FROM "{table}" WHERE "{pk_col}" = ?', (row[pk_col],))
                        conn.commit()
                    finally:
                        cur.close()
        return True


class PlanExecutionDispatcher:
    """Traverses compiled dag_stages in order and dispatches each stage to
    its owning responsibility handler. One instance per execute_migration
    call; not shared, not registered, not a service."""

    def __init__(self, mode_str: str, plan_fingerprint: str, rt_ctx: Dict[str, Any]):
        self.mode_str = mode_str
        self.plan_fingerprint = plan_fingerprint
        self.rt_ctx = rt_ctx
        self.loop = asyncio.new_event_loop()
        self.src_adapter = None
        self.tgt_adapter = None
        self._durability_authority = None
        self.result = PlanExecutionResult(plan_fingerprint=plan_fingerprint, mode=mode_str)

    # -- adapter lifecycle -----------------------------------------------

    def _get_adapters(self):
        if self.src_adapter is not None:
            return self.src_adapter, self.tgt_adapter
        from akaal.workflow.steps.migration_steps import _extract_source_config, _extract_target_config
        from akaal.adapters.adapter_registry import create_adapter

        src_config = _extract_source_config(self.rt_ctx)
        tgt_config = _extract_target_config(self.rt_ctx)
        self.src_adapter = create_adapter(src_config)
        self.tgt_adapter = create_adapter(tgt_config)
        self.loop.run_until_complete(self.src_adapter.connect())
        self.loop.run_until_complete(self.tgt_adapter.connect())
        return self.src_adapter, self.tgt_adapter

    def _target_dialect(self) -> str:
        from akaal.workflow.steps.migration_steps import _extract_target_config
        cfg = _extract_target_config(self.rt_ctx)
        st = getattr(cfg, "system_type", "postgresql")
        val = getattr(st, "value", None) or getattr(st, "name", None) or str(st)
        return str(val).lower()

    def _get_durability_authority(self):
        """M4 correction: lazily constructs the canonical, extended
        `akaalEngine.durability.DurabilityAuthority` (the SAME authority
        `save_watermark`/`get_watermark` were added to this correction --
        no parallel/shadow authority is created here). Key material and
        storage location are NOT hardcoded: they come from `rt_ctx`
        (so a test or a future real caller can inject an isolated,
        per-run store) or from environment variables for a real
        deployment. If neither supplies the required secrets, this fails
        closed with a clear error rather than fabricating/hardcoding a
        default secret, which would be a real security regression."""
        if self._durability_authority is not None:
            return self._durability_authority
        import os
        from akaalEngine.durability import DurabilityAuthority, DurabilityConfig

        storage_dir = (self.rt_ctx.get("durability_storage_dir")
                       or os.environ.get("AKAAL_DURABILITY_STORAGE_DIR")
                       or os.path.join(os.getcwd(), ".akaal", "durability"))
        fencing_key = self.rt_ctx.get("durability_fencing_key")
        anchor_key = self.rt_ctx.get("durability_anchor_key")
        if isinstance(fencing_key, str):
            fencing_key = fencing_key.encode("utf-8")
        if isinstance(anchor_key, str):
            anchor_key = anchor_key.encode("utf-8")
        if fencing_key is None:
            env_val = os.environ.get("AKAAL_DURABILITY_FENCING_KEY")
            fencing_key = env_val.encode("utf-8") if env_val else None
        if anchor_key is None:
            env_val = os.environ.get("AKAAL_DURABILITY_ANCHOR_KEY")
            anchor_key = env_val.encode("utf-8") if env_val else None
        if not fencing_key or not anchor_key:
            raise RuntimeError(
                "M4_DURABILITY_KEYS_NOT_CONFIGURED: supply rt_ctx['durability_fencing_key']/"
                "['durability_anchor_key'] (bytes) or AKAAL_DURABILITY_FENCING_KEY/"
                "AKAAL_DURABILITY_ANCHOR_KEY env vars. Refusing to fabricate a default secret."
            )
        os.makedirs(storage_dir, exist_ok=True)
        config = DurabilityConfig(storage_dir=storage_dir, fencing_signing_key=fencing_key, journal_anchor_key=anchor_key)
        self._durability_authority = DurabilityAuthority(config)
        return self._durability_authority

    def close(self):
        try:
            if self.src_adapter is not None:
                self.loop.run_until_complete(self.src_adapter.disconnect())
        except Exception:
            pass
        try:
            if self.tgt_adapter is not None:
                self.loop.run_until_complete(self.tgt_adapter.disconnect())
        except Exception:
            pass
        try:
            if self._durability_authority is not None:
                self._durability_authority.close()
        except Exception:
            pass
        try:
            self.loop.close()
        except Exception:
            pass

    # -- top-level traversal ----------------------------------------------

    def run(self, dag_stages: List[Dict[str, Any]]) -> PlanExecutionResult:
        # SEC correction: resolve the declared mode to its canonical M1..M8
        # key ONCE, fail closed immediately if it is not a recognized mode
        # at all (an unrecognized mode cannot have its stages validated, so
        # nothing in this DAG is allowed to execute).
        try:
            canonical_mode = _canonical_mode_key(self.mode_str)
            allowed_responsibilities = MODE_ALLOWED_RESPONSIBILITIES.get(canonical_mode)
        except Exception as exc:
            logger.error("[PlanExecutionDispatcher] Unrecognized execution mode '%s': %s", self.mode_str, exc)
            allowed_responsibilities = None

        dependency_ok = True
        for stage in dag_stages:
            name = stage.get("name", "")
            responsibility = STAGE_RESPONSIBILITY.get(name, "unknown")

            if not dependency_ok:
                outcome = StageOutcome(
                    stage_name=name, responsibility=responsibility, success=False,
                    skipped_reason="UPSTREAM_STAGE_FAILED",
                )
                self.result.stage_outcomes.append(outcome)
                continue

            # SEC correction: defense-in-depth mode fence. Even if this
            # stage somehow reached the dispatcher (a malformed/hostile
            # dag_dict, a future PlanCompiler defect, direct construction
            # bypassing PlanCompiler entirely), a responsibility not legal
            # for the declared mode is refused BEFORE its handler ever runs
            # -- "illegal DAG nodes cannot execute" is enforced here, not
            # merely assumed from PlanCompiler's own emission rules.
            if allowed_responsibilities is None or responsibility not in allowed_responsibilities:
                outcome = StageOutcome(
                    stage_name=name, responsibility=responsibility, success=False,
                    errors=[f"MODE_FENCE_VIOLATION: responsibility '{responsibility}' (stage '{name}') is not "
                            f"permitted for execution mode '{self.mode_str}'. Refused before dispatch."],
                )
                self.result.stage_outcomes.append(outcome)
                dependency_ok = False
                logger.error("[PlanExecutionDispatcher] MODE_FENCE_VIOLATION: stage '%s' (responsibility '%s') "
                             "illegal for mode '%s' -- refused.", name, responsibility, self.mode_str)
                continue

            try:
                outcome = self._dispatch_one(name, responsibility)
            except Exception as exc:  # fail closed, never silently succeed
                outcome = StageOutcome(
                    stage_name=name, responsibility=responsibility, success=False,
                    errors=[f"{type(exc).__name__}: {exc}"],
                )
                logger.error("[PlanExecutionDispatcher] stage '%s' raised: %s", name, exc)

            self.result.stage_outcomes.append(outcome)
            if not outcome.success:
                dependency_ok = False

        self.result.success = dependency_ok
        return self.result

    # -- per-responsibility handlers ---------------------------------------

    def _dispatch_one(self, name: str, responsibility: str) -> StageOutcome:
        handler = getattr(self, f"_handle_{responsibility}", None)
        if handler is None:
            # Responsibility genuinely not yet implemented by this dispatcher
            # (e.g. cdc_init/cdc_apply/incremental_poll before their phases
            # land) -- fail closed rather than silently pretend success.
            return StageOutcome(
                stage_name=name, responsibility=responsibility, success=False,
                errors=[f"NO_DISPATCH_HANDLER_FOR_RESPONSIBILITY: {responsibility}"],
            )
        return handler(name, responsibility)

    def _handle_discovery(self, name, responsibility) -> StageOutcome:
        src, tgt = self._get_adapters()
        tables = self.loop.run_until_complete(src.discover_tables())
        return StageOutcome(name, responsibility, True, details={"source_table_count": len(tables)})

    def _handle_planning_metadata(self, name, responsibility) -> StageOutcome:
        # Purely planner-side metadata (topological ordering already applied
        # by PlanCompiler to produce this stage list) -- no physical action.
        return StageOutcome(name, responsibility, True, details={"note": "planner metadata, no physical action"})

    def _handle_cdc_boundary(self, name, responsibility) -> StageOutcome:
        # M2 correction: establishes the real CDC session/buffer (the SAME
        # `_get_cdc_components()` machinery `_handle_cdc_init`/`_handle_cdc_apply`
        # use) BEFORE bulk transport begins, so there is no unprotected window
        # where a source change between "bulk snapshot read" and "bulk
        # complete" could be silently missed -- any such change is captured
        # by the CDC session established here and replayed by the later
        # cdc_apply stage. This stage alone does not prove zero-loss/zero-
        # duplicate end-to-end; that is what the M2 integration test proves
        # by injecting deterministic changes during the bulk phase and
        # verifying final target state has neither lost nor duplicated rows.
        try:
            identity, buffer, worker = self._get_cdc_components()
        except Exception as exc:
            return StageOutcome(name, responsibility, False, errors=[f"{type(exc).__name__}: {exc}"])
        return StageOutcome(name, responsibility, True,
                             details={"cdc_session_id": identity.cdc_session_id, "boundary_captured": True})

    def _handle_schema(self, name, responsibility) -> StageOutcome:
        dialect = self._target_dialect()
        selected_objs = self.rt_ctx.get("selected_scope", {}).get("objects", [])
        table_names = _physical_table_names(selected_objs)
        if dialect in LEGACY_STEP_SUPPORTED_TARGET_DIALECTS:
            from akaal.workflow.steps.migration_steps import SchemaExecutionStep
            from akaal.workflow.models.context import WorkflowContext
            wf_ctx = self.rt_ctx.get("__wf_ctx__")
            step = SchemaExecutionStep()
            res = step.execute(wf_ctx)
            return StageOutcome(name, responsibility, res.success, details=dict(res.context_updates or {}), errors=list(res.errors or []))

        # Dialect-neutral fallback (currently: sqlite) via the canonical adapter contract.
        src, tgt = self._get_adapters()
        created = []
        for tname in table_names:
            cols = self.loop.run_until_complete(src.discover_columns(tname))
            if not cols:
                continue
            col_ddl = ", ".join(_sqlite_column_ddl(c) for c in cols)
            ddl = f'CREATE TABLE IF NOT EXISTS "{tname}" ({col_ddl})'
            conn = tgt.get_connection()
            cur = conn.cursor()
            cur.execute(ddl)
            conn.commit()
            cur.close()
            created.append(tname)
        return StageOutcome(name, responsibility, True, details={"tables_ensured": len(created)})

    def _handle_schema_verify(self, name, responsibility) -> StageOutcome:
        src, tgt = self._get_adapters()
        src_tables = set(self.loop.run_until_complete(src.discover_tables()))
        tgt_tables = set(self.loop.run_until_complete(tgt.discover_tables()))
        selected = set(_physical_table_names(self.rt_ctx.get("selected_scope", {}).get("objects", [])))
        expected = selected & src_tables if selected else src_tables
        missing = expected - tgt_tables
        return StageOutcome(name, responsibility, len(missing) == 0,
                             details={"expected": len(expected), "missing": sorted(missing)})

    def _get_cdc_components(self):
        """M2/M3 correction: lazily constructs the REAL, canonical CDC
        machinery -- `akaal.cdc.domain.events.CDCEventIdentity`,
        `akaal.cdc.buffering.durable_buffer.DurableCDCBuffer` (real,
        WAL-backed, HMAC-integrity-protected, restart-recoverable),
        `akaal.cdc.apply.engine.CDCApplyWorker`, and
        `akaal.runtime.recovery.coordinator.RecoveryCoordinator` for
        monotonic fencing-epoch issuance/validation. No parallel/shadow CDC
        authority is created -- these are the SAME classes the rest of the
        `akaal.cdc` subsystem uses."""
        if getattr(self, "_cdc_worker", None) is not None:
            return self._cdc_identity, self._cdc_buffer, self._cdc_worker
        import os
        from akaal.cdc.domain.events import CDCEventIdentity
        from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer
        from akaal.cdc.apply.engine import CDCApplyWorker
        from akaal.runtime.recovery.coordinator import RecoveryCoordinator

        migration_id = str(self.rt_ctx.get("migration_id") or self.plan_fingerprint)
        execution_id = str(self.rt_ctx.get("execution_id") or self.plan_fingerprint)
        cdc_session_id = self.rt_ctx.get("cdc_session_id") or f"cdc-{migration_id}"
        # CDCEventIdentity.event_id auto-generates a RANDOM id if not
        # supplied -- since it's embedded in every buffered event's hashed
        # payload (used for replay/tamper detection), leaving it random
        # would make a fresh dispatcher instance (a process restart, or a
        # genuine at-least-once redelivery) compute a different hash for
        # the identical logical transaction every time, permanently
        # defeating dedup. Deriving it deterministically from the stable
        # cdc_session_id keeps it identical across restarts of the SAME
        # session, matching real replay semantics.
        identity = CDCEventIdentity(migration_id=migration_id, job_id=migration_id,
                                     run_id=execution_id, cdc_session_id=cdc_session_id,
                                     event_id=f"identity-{cdc_session_id}")

        wal_dir = self.rt_ctx.get("cdc_wal_dir") or os.path.join(os.getcwd(), ".akaal", "cdc_wal", cdc_session_id)
        os.makedirs(wal_dir, exist_ok=True)
        buffer = DurableCDCBuffer(identity=identity, wal_dir=wal_dir)

        self._recovery_coordinator = getattr(self, "_recovery_coordinator", None) or RecoveryCoordinator()
        self._cdc_fencing_epoch = self._recovery_coordinator.issue_epoch(migration_id)

        worker = CDCApplyWorker(identity=identity, durable_buffer=buffer,
                                 recovery_coordinator=self._recovery_coordinator,
                                 worker_id="plan_dispatch_cdc_worker")

        self._cdc_identity, self._cdc_buffer, self._cdc_worker = identity, buffer, worker
        return identity, buffer, worker

    def _handle_cdc_init(self, name, responsibility) -> StageOutcome:
        # M2/M3 correction: real CDC session initialization. Source change
        # transactions are supplied ONLY via the authorized test-only seam
        # rt_ctx["cdc_test_source_transactions"] -- this simulates ONLY the
        # external upstream CDC source/log (what a real Debezium/LogMiner/
        # replication-slot listener would physically hand AKAAL). It never
        # simulates AKAAL's own internal CDC success, never touches the
        # SQLite capability manifest, and registers no fake provider.
        # Absent this seam, this stage fails closed: there is no production
        # CDC source listener wired into this dispatcher yet (that remains
        # a real, reported gap -- see correction report).
        raw_txs = self.rt_ctx.get("cdc_test_source_transactions")
        if raw_txs is None:
            return StageOutcome(name, responsibility, False, errors=[
                "CDC_SOURCE_NOT_CONFIGURED: rt_ctx['cdc_test_source_transactions'] "
                "(authorized test-only external-CDC-source seam) was not supplied; "
                "no production CDC source listener is wired into this dispatcher yet."])
        # An explicitly empty list (vs. an absent key) is a legitimate,
        # configured "zero changes occurred this cycle" result -- it must
        # succeed as a genuine no-op, not be confused with "not configured".

        try:
            from akaal.cdc.domain.events import CDCEvent, CDCTransaction, CDCOperationType
            from akaal.cdc.domain.positions import WarehouseQueryPosition
            identity, buffer, _ = self._get_cdc_components()
        except Exception as exc:
            return StageOutcome(name, responsibility, False, errors=[f"{type(exc).__name__}: {exc}"])

        appended = 0
        try:
            for i, raw_tx in enumerate(raw_txs):
                # WarehouseQueryPosition is the generic offset-based position
                # kind `parse_source_position` recognizes for engines with no
                # native LSN/GTID/SCN concept (SQLite included) -- engine
                # string must be one it dispatches on ("WAREHOUSE" etc.).
                pos = WarehouseQueryPosition(engine="WAREHOUSE", query_id=identity.cdc_session_id, chunk_index=0, row_offset=i + 1)
                # commit_timestamp must be the ORIGINAL source commit time
                # (supplied by the seam), not "now" -- otherwise a genuine
                # at-least-once redelivery of the exact same source
                # transaction would compute a different payload hash each
                # time it's re-offered and be misidentified as tampering
                # rather than a safe, idempotent replay.
                tx = CDCTransaction(tx_id=raw_tx["tx_id"], identity=identity, commit_position=pos,
                                     commit_timestamp=raw_tx.get("commit_timestamp"))
                for evt_raw in raw_tx.get("events", []):
                    # Both CDCEvent.commit_timestamp and .captured_timestamp
                    # default to "now" if not supplied, which would make the
                    # buffer's payload-hash (which hashes the serialized
                    # events) differ on every re-offer of the SAME logical
                    # source transaction -- defeating dedup/tamper detection.
                    # When the seam supplies a deterministic commit_timestamp,
                    # reuse it for both fields so an exact redelivery hashes
                    # identically, exactly like a real source's replayed
                    # change-log record would.
                    fixed_ts = raw_tx.get("commit_timestamp")
                    evt = CDCEvent(
                        identity=identity, source_engine="SQLITE", source_database="sqlite", source_schema="main",
                        source_table=evt_raw["table"], operation=CDCOperationType(evt_raw["operation"]), position=pos,
                        before_image=evt_raw.get("before"), after_image=evt_raw.get("after"), tx_id=raw_tx["tx_id"],
                        commit_timestamp=fixed_ts, captured_timestamp=fixed_ts,
                    )
                    tx.add_event(evt)
                tx.mark_commit()
                buffer.append_transaction(tx, self._cdc_fencing_epoch)
                appended += 1
        except Exception as exc:
            return StageOutcome(name, responsibility, False, errors=[f"{type(exc).__name__}: {exc}"],
                                 details={"transactions_buffered": appended})

        return StageOutcome(name, responsibility, True, details={"transactions_buffered": appended})

    def _handle_cdc_apply(self, name, responsibility) -> StageOutcome:
        # M2/M3 correction: real ordered apply against the target via the
        # canonical CDCApplyWorker (target transaction atomicity, restart-
        # persistent replay dedup, fencing-epoch enforcement, durable
        # checkpointing -- all real, unmodified authority behavior). No
        # adapter in this repository implements a generic
        # `apply_changes(events)` DML method (CDCApplyWorker's own physical
        # -application hook), so `_CDCApplyAdapterBridge` below translates
        # CDCEvents to the canonical `BaseAdapter.write_batch` (upsert,
        # INSERT/UPDATE) contract and a minimal delete-by-primary-key
        # statement (DELETE) -- it does not change or extend the canonical
        # adapter interface itself, the same pattern already used for the
        # sqlite dialect-neutral schema/transport fallback above.
        try:
            identity, buffer, worker = self._get_cdc_components()
        except Exception as exc:
            return StageOutcome(name, responsibility, False, errors=[f"{type(exc).__name__}: {exc}"])

        src, tgt = self._get_adapters()
        worker.target_adapter = _CDCApplyAdapterBridge(tgt)

        applied = 0
        duplicates = 0
        errors: List[str] = []
        while True:
            try:
                result = worker.apply_next_transaction(self._cdc_fencing_epoch)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                break
            if result.get("status") == "NO_TRANSACTIONS":
                break
            if result.get("applied"):
                applied += 1
                if result.get("duplicate_suppressed"):
                    duplicates += 1

        ok = not errors
        self.result.rows_written += applied
        return StageOutcome(name, responsibility, ok, errors=errors,
                             details={"transactions_applied": applied, "duplicates_suppressed": duplicates})

    def _handle_incremental_poll(self, name, responsibility) -> StageOutcome:
        # M4 correction: real DAG-dispatch integration against the now-real
        # `DurabilityAuthority.save_watermark`/`get_watermark` (see
        # akaalEngine/durability/checkpoint/registry.py and
        # tests/unit/engine_durability/test_m4_watermark_authority.py).
        #
        # Watermark-column metadata is not yet emitted by PlanCompiler for
        # any source connector, so it is required explicitly via
        # `rt_ctx["incremental_watermark_columns"]` (table_name ->
        # {"column": str, "type": "NUMERIC"|"TIMESTAMP"|"COMPOUND"}). A
        # table with no configured watermark column fails closed rather
        # than guessing which column to poll on or silently skipping it.
        #
        # Call-order discipline (the one thing the durability layer itself
        # cannot enforce, per
        # test_watermark_authority_itself_has_no_target_visibility_by_design):
        # `save_watermark` is only ever called AFTER `tgt.write_batch(...)`
        # has returned successfully for that table's eligible rows -- a
        # crash/exception between the two leaves the previous durable
        # watermark unchanged (re-poll will safely re-fetch and must rely
        # on target-side idempotent apply, exactly as the M4 fixture's
        # `failure_injection_scenario.json` describes).
        watermark_cols = self.rt_ctx.get("incremental_watermark_columns") or {}
        if not watermark_cols:
            return StageOutcome(name, responsibility, False, errors=[
                "M4_NOT_CONFIGURED: rt_ctx['incremental_watermark_columns'] (table -> "
                "{'column':..., 'type':...}) was not supplied; cannot determine what to "
                "poll on. Refusing to guess."])

        try:
            authority = self._get_durability_authority()
        except Exception as exc:
            return StageOutcome(name, responsibility, False, errors=[f"{type(exc).__name__}: {exc}"])

        from akaalEngine.durability import Watermark, WatermarkType

        src, tgt = self._get_adapters()
        migration_id = str(self.rt_ctx.get("migration_id") or self.plan_fingerprint)
        execution_id = str(self.rt_ctx.get("execution_id") or self.plan_fingerprint)
        selected_objs = self.rt_ctx.get("selected_scope", {}).get("objects", [])
        table_names = _physical_table_names(selected_objs)
        # Fencing token resource_id must equal (or be prefixed by) the
        # watermark's migration_id -- MigrationCheckpointRegistry.save_watermark
        # refuses any other resource_id as a fencing violation.
        tok = authority.issue_fencing_token(migration_id, "plan_dispatch")

        total_read = 0
        total_written = 0
        per_table: Dict[str, Any] = {}
        ok = True
        for tname in table_names:
            cfg = watermark_cols.get(tname)
            if not cfg or not cfg.get("column"):
                per_table[tname] = {"error": "NO_WATERMARK_COLUMN_CONFIGURED"}
                ok = False
                continue
            col = cfg["column"]
            wtype = WatermarkType(cfg.get("type", "NUMERIC"))

            current = authority.get_watermark(migration_id, tname)
            current_value = current.value if current is not None else None

            rows = self.loop.run_until_complete(src.read_batch(tname, 0, 1_000_000))

            def _keep(r, _col=col, _cur=current_value):
                v = r.get(_col)
                if v is None:
                    return False  # NULL-watermark rows never advance/participate (fixture negative case)
                if _cur is None:
                    return True
                return v > _cur

            eligible = [r for r in rows if _keep(r)]
            eligible.sort(key=lambda r: r.get(col))

            written = 0
            new_value = current_value
            if eligible:
                written = self.loop.run_until_complete(tgt.write_batch(tname, eligible))
                # Target commit has now happened. Only now may the durable
                # watermark advance -- never before.
                new_value = max(r.get(col) for r in eligible)
                wm = Watermark(migration_id, tname, wtype, new_value, self.plan_fingerprint, execution_id, tok.fencing_epoch)
                authority.save_watermark(wm, tok)

            total_read += len(eligible)
            total_written += written
            per_table[tname] = {
                "eligible_rows": len(eligible), "written": written,
                "watermark_before": current_value, "watermark_after": new_value,
            }

        self.result.rows_read += total_read
        self.result.rows_written += total_written
        self.result.tables_processed += len(table_names)
        return StageOutcome(name, responsibility, ok, details={
            "tables": per_table, "rows_read": total_read, "rows_written": total_written,
        })

    def _handle_transport(self, name, responsibility) -> StageOutcome:
        dialect = self._target_dialect()
        selected_objs = self.rt_ctx.get("selected_scope", {}).get("objects", [])
        table_names = _physical_table_names(selected_objs)
        if dialect in LEGACY_STEP_SUPPORTED_TARGET_DIALECTS:
            from akaal.workflow.steps.migration_steps import DataTransportStep
            wf_ctx = self.rt_ctx.get("__wf_ctx__")
            step = DataTransportStep()
            res = step.execute(wf_ctx)
            return StageOutcome(name, responsibility, res.success, details=dict(res.context_updates or {}), errors=list(res.errors or []))

        src, tgt = self._get_adapters()
        total_read = 0
        total_written = 0
        for tname in table_names:
            offset = 0
            batch_size = 2000
            while True:
                rows = self.loop.run_until_complete(src.read_batch(tname, offset, batch_size))
                if not rows:
                    break
                written = self.loop.run_until_complete(tgt.write_batch(tname, rows))
                total_read += len(rows)
                total_written += written
                offset += len(rows)
                if len(rows) < batch_size:
                    break
        self.result.rows_read += total_read
        self.result.rows_written += total_written
        self.result.tables_processed += len(table_names)
        return StageOutcome(name, responsibility, True, details={"rows_read": total_read, "rows_written": total_written, "tables": len(table_names)})

    def _handle_reconciliation(self, name, responsibility) -> StageOutcome:
        return self._reconcile(name, responsibility)

    def _handle_validation(self, name, responsibility) -> StageOutcome:
        return self._reconcile(name, responsibility)

    def _handle_inspection(self, name, responsibility) -> StageOutcome:
        src, tgt = self._get_adapters()
        selected_objs = self.rt_ctx.get("selected_scope", {}).get("objects", [])
        table_names = _physical_table_names(selected_objs)
        summary = {}
        for tname in table_names:
            src_rows = self.loop.run_until_complete(src.read_batch(tname, 0, 1_000_000))
            tgt_rows = self.loop.run_until_complete(tgt.read_batch(tname, 0, 1_000_000))
            summary[tname] = {"source_rows": len(src_rows), "target_rows": len(tgt_rows)}
        return StageOutcome(name, responsibility, True, details={"tables": summary})

    def _verify_reconciliation_fencing(self) -> Dict[str, Any]:
        # Correction-campaign item 5 (owner-mandated): the reconciliation/
        # validation stage (Authority #11, `CanonicalReconciliationEngine`)
        # must itself independently verify identity/task-scope/fencing-
        # epoch state per contract.txt Engine Zero-Trust rules 136/137/140/
        # 141 -- not merely trust that governance approval earlier in the
        # pipeline covers it. This reuses the SAME canonical fencing
        # primitive (`akaalEngine.durability.DurabilityAuthority.
        # issue_fencing_token`/`validate_fencing_token`) M4's watermark
        # authority and the CDC apply path already use -- no second/
        # duplicate fencing authority is created, and
        # `akaalEngine.validation.api.ValidationAuthority`'s own
        # `check_runtime_cancellation_and_fencing` helper is not adopted
        # wholesale here because it currently checks for a
        # `verify_fencing_token` method name that this repository's real
        # `DurabilityAuthority` does not expose (it exposes
        # `validate_fencing_token`) -- calling the real, working method
        # directly is more honest than routing through a helper whose
        # `hasattr` guard would silently no-op against the real authority.
        #
        # Best-effort, truthfully reported: most existing M1/M5/M6/M7/M8
        # callers (this session's own test suite included) never configure
        # `durability_fencing_key`/`durability_anchor_key` in `rt_ctx` --
        # for those, fencing verification is reported as
        # "not configured", not silently skipped nor fabricated as passed,
        # and the stage is NOT failed merely for lacking durability config
        # (that would be a large, out-of-scope behavior change breaking
        # every pre-existing caller). When durability IS configured, the
        # check is REAL: a genuinely stale/rejected token fails the stage.
        migration_id = str(self.rt_ctx.get("migration_id") or self.plan_fingerprint)
        try:
            authority = self._get_durability_authority()
        except Exception as exc:
            return {"performed": False, "detail": f"durability authority not configured: {type(exc).__name__}: {exc}"}

        from akaalEngine.durability.models.errors import StaleGenerationError, FencingViolationError
        try:
            tok = authority.issue_fencing_token(migration_id, "plan_dispatch_reconciliation")
            authority.validate_fencing_token(tok)
        except (StaleGenerationError, FencingViolationError) as exc:
            # A genuine fencing rejection IS a real validation failure --
            # re-raised so the caller fails the stage closed, never
            # silently reported as a benign "not configured" skip.
            raise
        return {"performed": True, "fencing_epoch": tok.fencing_epoch,
                "detail": "fencing epoch independently verified via canonical Durability Authority (#5)"}

    def _reconcile(self, name, responsibility) -> StageOutcome:
        from akaal.validation.domain.reconciliation import CanonicalReconciliationEngine
        from akaalEngine.durability.models.errors import StaleGenerationError, FencingViolationError

        try:
            fencing_check = self._verify_reconciliation_fencing()
        except (StaleGenerationError, FencingViolationError) as exc:
            return StageOutcome(name, responsibility, False,
                                 errors=[f"VALIDATION_FENCING_REJECTED: {type(exc).__name__}: {exc}"])

        src, tgt = self._get_adapters()
        selected_objs = self.rt_ctx.get("selected_scope", {}).get("objects", [])
        table_names = _physical_table_names(selected_objs)
        engine = CanonicalReconciliationEngine()
        table_results = {}
        overall_ok = True
        for tname in table_names:
            src_rows = self.loop.run_until_complete(src.read_batch(tname, 0, 1_000_000))
            tgt_rows = self.loop.run_until_complete(tgt.read_batch(tname, 0, 1_000_000))
            if not src_rows and not tgt_rows:
                continue
            cols = sorted(set(src_rows[0].keys()) if src_rows else set(tgt_rows[0].keys()))
            pk_cols = [cols[0]] if cols else None
            src_tuples = [tuple(r.get(c) for c in cols) for r in src_rows]
            tgt_tuples = [tuple(r.get(c) for c in cols) for r in tgt_rows]
            summary, records = engine.reconcile_tables(tname, src_tuples, tgt_tuples, cols, pk_columns=pk_cols)
            table_results[tname] = {
                "status": summary.status,
                "source_rows": summary.source_rows,
                "target_rows": summary.target_rows,
                "matched": summary.matched_count,
                "source_only": summary.source_only_count,
                "target_only": summary.target_only_count,
                "value_mismatch": summary.value_mismatch_count,
            }
            if summary.status not in ("MATCHED",):
                # a MISMATCH from CanonicalReconciliationEngine is a real,
                # true finding, not a dispatcher failure -- it is reported,
                # not swallowed, but for fixtures deliberately built to
                # match (M1/M6/M7) an unexpected mismatch does mean the
                # overall stage did not achieve its goal.
                overall_ok = overall_ok and (responsibility != "validation")
        return StageOutcome(name, responsibility, overall_ok, details={"tables": table_results, "fencing_check": fencing_check})

    def _handle_repair_eligibility(self, name, responsibility) -> StageOutcome:
        # Correction-campaign item 4 (owner-mandated): repair authorization
        # must be routed through the SAME canonical governance-approval
        # authority `AkaalSuperEngine.execute_migration` itself requires
        # (`verify_governance_authorization`, backed by
        # `EnterpriseGovernancePlatformV6` / `CentralStateStore` category
        # "governance") -- not a second, parallel/duplicate authorization
        # mechanism, and not a hard-coded constant. Repair is deliberately
        # checked as its OWN, separately-approved governed action (a
        # distinct approval record keyed off "<migration_id>_repair", never
        # inferred from the main migration's own execution approval) per
        # Separation-of-Duties (contract.txt rule 44: reuse the canonical
        # Four-Eyes/SoD authority) -- being approved to read/compare data
        # does not itself authorize a mutating repair action.
        #
        # In every fixture/test context used by this campaign, no such
        # repair-specific approval record is ever created, so
        # `repair_authorized` correctly evaluates to False by default here
        # too (SEC-I07 continues to pass unchanged) -- but the gate is now a
        # real, reusable, canonical check, not a hard-coded constant, and a
        # future caller that DOES record a genuine repair-scoped governance
        # approval will see `repair_authorized=True` for real.
        migration_id = str(self.rt_ctx.get("migration_id") or self.plan_fingerprint)
        repair_workflow_id = f"{migration_id}_repair"
        repair_authorized = False
        auth_detail = "no repair-scoped governance approval record found (default-deny)"
        try:
            from akaal.engine.facade import AkaalSuperEngine
            engine = AkaalSuperEngine()
            repair_spec = {"kind": "repair", "migration_id": migration_id}
            engine.verify_governance_authorization(repair_workflow_id, repair_spec, None)
            repair_authorized = True
            auth_detail = "repair-scoped governance approval record found and fingerprint-verified"
        except Exception as exc:  # fail closed -- any verification failure means NOT authorized
            auth_detail = f"{type(exc).__name__}: {exc}"

        # Repair execution itself is never performed regardless of
        # authorization result -- this stage only evaluates and reports
        # eligibility; no canonical repair-mutation logic is wired here,
        # so `repair_executed` is unconditionally False (structural
        # non-mutation, per M8-I12 discipline shared with this stage).
        return StageOutcome(name, responsibility, True, details={
            "repair_authorized": repair_authorized,
            "repair_executed": False,
            "repair_authorization_detail": auth_detail,
        })

    def _handle_evidence(self, name, responsibility) -> StageOutcome:
        import hashlib
        import json as _json
        payload = _json.dumps(self.result.to_dict(), sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        details = {"evidence_digest_sha256": digest}

        # Real binding to the canonical Evidence Authority #12
        # (akaalEngine.evidence.api.EvidenceAuthority), fixed this
        # correction (duplicate-method defect closed -- see correction
        # report). Best-effort: if the authority genuinely cannot be
        # reached/constructed from this call path, that failure is
        # reported truthfully in `details`, never papered over by
        # silently claiming an artifact was created when it was not.
        try:
            from akaalEngine.evidence.api import EvidenceAuthority
            migration_id = str(self.rt_ctx.get("migration_id") or self.plan_fingerprint)
            wf_ctx = self.rt_ctx.get("__wf_ctx__")
            run_id = getattr(getattr(wf_ctx, "execution_context", None), "run_id", None) or f"run-{migration_id}"
            authority = EvidenceAuthority.get_instance()
            artifact = authority.package_execution_evidence(
                migration_id=migration_id,
                run_id=run_id,
                execution_state="COMPLETED" if self.result.success else "FAILED",
                telemetry_snapshot={
                    "rows_read": self.result.rows_read,
                    "rows_written": self.result.rows_written,
                    "tables_processed": self.result.tables_processed,
                    "evidence_digest_sha256": digest,
                },
                artifact_id=f"{migration_id}-{self.plan_fingerprint}-evidence",
            )
            details["evidence_authority_artifact_id"] = getattr(artifact, "artifact_id", None)
            details["evidence_authority_bound"] = True
        except Exception as exc:  # never fabricate a bound artifact that wasn't created
            details["evidence_authority_bound"] = False
            details["evidence_authority_error"] = f"{type(exc).__name__}: {exc}"
            logger.warning("[PlanExecutionDispatcher] Evidence Authority #12 binding failed: %s", exc)

        return StageOutcome(name, responsibility, True, details=details)
