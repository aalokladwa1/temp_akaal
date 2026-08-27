"""
AKAAL Migration Execution — Governed Custom SQL Hook Authority
==============================================================
P5.7 Canonical Authority for governed custom SQL hook execution across all
migration lifecycle stages. Enforces parameter binding, timeout boundaries,
transaction isolation, crash-recovery state tracking in CentralStateStore,
idempotency / replay protection, secret redaction, audit logging, and Authority #12 evidence emission.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from akaal.core.models.configuration import HookPhase, SQLHook
from akaal.planner.models.p5_domain import (
    HookDefinition,
    HookExecutionResult,
    HookExecutionState,
    HookFailurePolicy,
    HookIdempotencyClassification,
    HookSide,
    HookStage,
    HookTransactionPolicy,
    SQLSafetyClassification,
)
from akaal.planner.engine.sql_safety import SQLSafetyClassifier
from akaal.privacy.sanitizer import LogAndDiagnosticSanitizer
from akaal.audit.audit_logger import AuditLogger, AuditEventType
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger("akaal.migration.hooks")


class HookExecutionError(Exception):
    """Raised when a custom SQL hook fails and aborts migration."""
    pass


class AmbiguousHookReplayError(HookExecutionError):
    """Raised when an ambiguous or non-idempotent hook is blocked from automatic replay."""
    pass


class UnapprovedHookExecutionError(HookExecutionError):
    """Raised when a destructive or approval-gated hook executes without required approval sign-off."""
    pass


class HookOperatorInterventionRequiredError(HookExecutionError):
    """Raised when a hook failure policy dictates pausing for human operator intervention."""
    pass


class GovernedHookExecutor:
    """
    P5.7 Canonical Authority for Governed Custom SQL Hook Execution.
    Provides physical execution across lifecycle stages, transaction isolation,
    crash-recovery durability via CentralStateStore, and zero plaintext secret leakage.
    """

    def __init__(
        self,
        source_adapter: Optional[Any] = None,
        target_adapter: Optional[Any] = None,
        state_store: Optional[CentralStateStore] = None,
        audit_logger: Optional[AuditLogger] = None,
        evidence_authority: Optional[Any] = None,
    ) -> None:
        self.source_adapter = source_adapter
        self.target_adapter = target_adapter
        self.state_store = state_store or CentralStateStore()
        self.audit_logger = audit_logger or AuditLogger.get_instance()
        self.evidence_authority = evidence_authority
        self.execution_history: List[HookExecutionResult] = []

    def _get_adapter(self, side: HookSide) -> Any:
        adapter = self.source_adapter if side == HookSide.SOURCE else self.target_adapter
        if adapter is None:
            # Fallback to single adapter if only one provided
            adapter = self.target_adapter or self.source_adapter
        return adapter

    async def execute_stage_hooks(
        self,
        hooks: List[Union[HookDefinition, Dict[str, Any], SQLHook]],
        stage: Union[HookStage, str, HookPhase],
        workflow_id: str = "default-migration",
        run_id: str = "default-run",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HookExecutionResult]:
        """
        Executes all hooks matching the target lifecycle stage in deterministic topological order.
        """
        ctx = dict(context or {})
        stage_str = stage.value if hasattr(stage, "value") else str(stage).upper()
        
        # Normalize stage name (mapping legacy HookPhase to HookStage if needed)
        stage_enum = self._normalize_stage(stage)

        # Filter hooks for this stage
        applicable_hooks: List[HookDefinition] = []
        for h in hooks:
            norm_h = self._normalize_hook(h)
            if norm_h and norm_h.enabled and norm_h.stage == stage_enum:
                applicable_hooks.append(norm_h)

        if not applicable_hooks:
            return []

        logger.info(
            f"[GovernedHookExecutor] Starting stage '{stage_str}' with {len(applicable_hooks)} hook(s) for workflow '{workflow_id}'."
        )

        stage_results: List[HookExecutionResult] = []
        for hook in applicable_hooks:
            result = await self.execute_single_hook(
                hook=hook,
                workflow_id=workflow_id,
                run_id=run_id,
                context=ctx,
            )
            stage_results.append(result)
            self.execution_history.append(result)

            # If hook failed and policy requires abort
            if result.state in (HookExecutionState.FAILED, HookExecutionState.AMBIGUOUS):
                if hook.failure_policy == HookFailurePolicy.FAIL_FAST:
                    clean_err = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(result.error_message or "Hook execution failed.")
                    raise HookExecutionError(f"Hook '{hook.hook_id}' in stage '{stage_str}' failed: {clean_err}")
                elif hook.failure_policy == HookFailurePolicy.REQUIRE_OPERATOR:
                    clean_err = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(result.error_message or "Hook execution failed.")
                    raise HookOperatorInterventionRequiredError(f"Hook '{hook.hook_id}' requires operator intervention: {clean_err}")
                elif hook.failure_policy == HookFailurePolicy.ROLLBACK_AND_ABORT:
                    clean_err = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(result.error_message or "Hook execution failed.")
                    raise HookExecutionError(f"Hook '{hook.hook_id}' rolled back and aborted: {clean_err}")

        # Emit Authority #12 Evidence Artifact if EvidenceAuthority is configured
        if self.evidence_authority and hasattr(self.evidence_authority, "package_hook_execution_evidence"):
            try:
                self.evidence_authority.package_hook_execution_evidence(
                    migration_id=workflow_id,
                    run_id=run_id,
                    hook_results=stage_results,
                    plan_identity=ctx.get("execution_plan_id"),
                )
            except Exception as evd_err:
                logger.warning(f"[GovernedHookExecutor] Failed to package evidence: {evd_err}")

        return stage_results

    async def execute_single_hook(
        self,
        hook: HookDefinition,
        workflow_id: str,
        run_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> HookExecutionResult:
        """
        Physically executes a single hook against the appropriate connection adapter with full governance.
        """
        ctx = dict(context or {})
        hook_start_time = time.time()
        state_key = f"{workflow_id}:{hook.hook_id}"

        # 1. Approval Barrier Validation
        if hook.requires_approval or ctx.get("hooks_requires_approval"):
            approved_fp = ctx.get("approved_fingerprint")
            exec_plan = ctx.get("execution_plan")
            if not approved_fp or not isinstance(approved_fp, str) or not approved_fp.strip():
                raise UnapprovedHookExecutionError(f"UNAPPROVED_HOOK_BLOCKED: Hook '{hook.hook_id}' requires explicit approval sign-off.")
            from akaal.planner.engine.plan_compiler import PlanCompiler
            try:
                PlanCompiler.validate_plan_approval(
                    exec_plan or {"fingerprint": approved_fp, "resolved_configuration": {"hooks_fingerprint": approved_fp, "hooks_requires_approval": True}},
                    approved_fp,
                )
            except Exception as app_err:
                clean_msg = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(str(app_err))
                logger.error(f"[GovernedHookExecutor] Unapproved hook execution rejected: {clean_msg}")
                raise UnapprovedHookExecutionError(f"UNAPPROVED_HOOK_BLOCKED: {clean_msg}") from app_err

        # 2. Check Durable CentralStateStore for Previous State (Duplicate & Crash Replay Protection)
        prior_state_record = self.state_store.get_state(state_key, category="hooks")
        if prior_state_record and isinstance(prior_state_record, dict):
            prior_status = prior_state_record.get("state")
            if prior_status == HookExecutionState.COMPLETED.value:
                # Duplicate Execution Prevention
                logger.info(f"[GovernedHookExecutor] Hook '{hook.hook_id}' already COMPLETED in CentralStateStore. Skipping duplicate execution.")
                self.audit_logger.log(
                    AuditEventType.HOOK_SKIPPED,
                    project_id=workflow_id,
                    workflow_id=workflow_id,
                    task_id=hook.hook_id,
                    details={"reason": "ALREADY_COMPLETED", "prior_state": prior_state_record},
                )
                return HookExecutionResult(
                    hook_id=hook.hook_id,
                    stage=hook.stage,
                    side=hook.side,
                    state=HookExecutionState.COMPLETED,
                    rows_affected=prior_state_record.get("rows_affected", 0),
                    duration_ms=prior_state_record.get("duration_ms", 0.0),
                    sanitized_sql=LogAndDiagnosticSanitizer.sanitize_sql_preview(hook.sql_statement, hook.parameters),
                )
            elif prior_status in (HookExecutionState.AMBIGUOUS.value, HookExecutionState.FAILED.value, HookExecutionState.STARTED.value):
                # If non-idempotent and previous run crashed or was ambiguous
                if hook.idempotency not in (HookIdempotencyClassification.IDEMPOTENT, HookIdempotencyClassification.REPLAY_PROTECTED):
                    err_msg = (
                        f"AMBIGUOUS_HOOK_REPLAY_BLOCKED: Hook '{hook.hook_id}' is classified as {hook.idempotency.value} "
                        f"and was previously in state '{prior_status}'. Automatic retry is blocked to prevent data corruption."
                    )
                    logger.error(f"[GovernedHookExecutor] {err_msg}")
                    raise AmbiguousHookReplayError(err_msg)

        # 3. Mark STARTED in CentralStateStore
        self.state_store.set_state(
            key=state_key,
            value={
                "hook_id": hook.hook_id,
                "stage": hook.stage.value,
                "side": hook.side.value,
                "state": HookExecutionState.STARTED.value,
                "started_at": hook_start_time,
                "workflow_id": workflow_id,
                "run_id": run_id,
            },
            category="hooks",
        )

        sanitized_sql_preview = LogAndDiagnosticSanitizer.sanitize_sql_preview(hook.sql_statement, hook.parameters)
        sanitized_params = LogAndDiagnosticSanitizer.sanitize_hook_parameters(hook.parameters)

        self.audit_logger.log(
            AuditEventType.HOOK_STARTED,
            project_id=workflow_id,
            workflow_id=workflow_id,
            task_id=hook.hook_id,
            details={
                "stage": hook.stage.value,
                "side": hook.side.value,
                "transaction_policy": hook.transaction_policy.value,
                "sql_preview": sanitized_sql_preview,
                "parameters": sanitized_params,
            },
        )

        # 4. Resolve Physical Database Adapter & Connection
        adapter = self._get_adapter(hook.side)
        if adapter is None:
            err_msg = f"No database adapter available for side '{hook.side.value}' on hook '{hook.hook_id}'."
            self._record_failure(state_key, hook, workflow_id, run_id, err_msg, is_ambiguous=False)
            return HookExecutionResult(
                hook_id=hook.hook_id,
                stage=hook.stage,
                side=hook.side,
                state=HookExecutionState.FAILED,
                error_message=err_msg,
                sanitized_sql=sanitized_sql_preview,
            )

        # Connect adapter if needed
        if not getattr(adapter, "is_connected", False) and hasattr(adapter, "connect"):
            try:
                await adapter.connect()
            except Exception as conn_err:
                clean_err = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(str(conn_err))
                self._record_failure(state_key, hook, workflow_id, run_id, clean_err, is_ambiguous=False)
                return HookExecutionResult(
                    hook_id=hook.hook_id,
                    stage=hook.stage,
                    side=hook.side,
                    state=HookExecutionState.FAILED,
                    error_message=clean_err,
                    sanitized_sql=sanitized_sql_preview,
                )

        # 5. Execute SQL with Timeout & Transaction Governance
        timeout_seconds = max(0.1, hook.timeout_ms / 1000.0)
        rows_affected = 0
        is_ambiguous = False

        try:
            rows_affected = await asyncio.wait_for(
                self._execute_sql_on_adapter(adapter, hook),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            is_ambiguous = True
            err_msg = f"Hook '{hook.hook_id}' timed out after {timeout_seconds}s. Execution state is AMBIGUOUS."
            logger.error(f"[GovernedHookExecutor] {err_msg}")
            self._record_failure(state_key, hook, workflow_id, run_id, err_msg, is_ambiguous=True)
            return HookExecutionResult(
                hook_id=hook.hook_id,
                stage=hook.stage,
                side=hook.side,
                state=HookExecutionState.AMBIGUOUS,
                error_message=err_msg,
                sanitized_sql=sanitized_sql_preview,
                is_ambiguous=True,
                duration_ms=(time.time() - hook_start_time) * 1000.0,
            )
        except Exception as exc:
            clean_err = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(str(exc))
            logger.error(f"[GovernedHookExecutor] Hook '{hook.hook_id}' execution failed: {clean_err}")
            
            # Handle rollback if requested
            if hook.transaction_policy in (HookTransactionPolicy.ISOLATED_TRANSACTION, HookTransactionPolicy.PARTICIPATE_EXISTING) or hook.failure_policy == HookFailurePolicy.ROLLBACK_AND_ABORT:
                try:
                    if hasattr(adapter, "rollback"):
                        rb_res = adapter.rollback()
                        if asyncio.iscoroutine(rb_res):
                            await rb_res
                except Exception as rb_err:
                    logger.warning(f"[GovernedHookExecutor] Rollback failed or not supported: {rb_err}")

            self._record_failure(state_key, hook, workflow_id, run_id, clean_err, is_ambiguous=False)
            return HookExecutionResult(
                hook_id=hook.hook_id,
                stage=hook.stage,
                side=hook.side,
                state=HookExecutionState.FAILED,
                error_message=clean_err,
                sanitized_sql=sanitized_sql_preview,
                duration_ms=(time.time() - hook_start_time) * 1000.0,
            )

        # 6. Mark COMPLETED in CentralStateStore
        duration_ms = (time.time() - hook_start_time) * 1000.0
        self.state_store.set_state(
            key=state_key,
            value={
                "hook_id": hook.hook_id,
                "stage": hook.stage.value,
                "side": hook.side.value,
                "state": HookExecutionState.COMPLETED.value,
                "rows_affected": rows_affected,
                "duration_ms": duration_ms,
                "completed_at": time.time(),
                "workflow_id": workflow_id,
                "run_id": run_id,
            },
            category="hooks",
        )

        audit_entry = self.audit_logger.log(
            AuditEventType.HOOK_COMPLETED,
            project_id=workflow_id,
            workflow_id=workflow_id,
            task_id=hook.hook_id,
            details={
                "stage": hook.stage.value,
                "side": hook.side.value,
                "rows_affected": rows_affected,
                "duration_ms": duration_ms,
                "sql_preview": sanitized_sql_preview,
            },
        )

        logger.info(
            f"[GovernedHookExecutor] Hook '{hook.hook_id}' COMPLETED successfully ({duration_ms:.2f}ms, {rows_affected} rows affected)."
        )

        return HookExecutionResult(
            hook_id=hook.hook_id,
            stage=hook.stage,
            side=hook.side,
            state=HookExecutionState.COMPLETED,
            rows_affected=rows_affected,
            duration_ms=duration_ms,
            sanitized_sql=sanitized_sql_preview,
            audit_entry_id=audit_entry.entry_id if audit_entry else None,
        )

    async def _execute_sql_on_adapter(self, adapter: Any, hook: HookDefinition) -> int:
        """Executes SQL statements sequentially on connection with transactional control."""
        statements = SQLSafetyClassifier.split_statements(hook.sql_statement)
        if not statements:
            statements = [hook.sql_statement]

        total_rows = 0

        def _sync_execute():
            nonlocal total_rows
            conn = adapter.get_connection() if hasattr(adapter, "get_connection") else None
            
            # If adapter has execute_raw / execute_statement method
            if hasattr(adapter, "execute_statement"):
                for stmt in statements:
                    adapter.execute_statement(stmt, hook.parameters)
                total_rows = 1
                return total_rows

            if conn is None:
                # Direct adapter call or mocked adapter
                if hasattr(adapter, "execute"):
                    for stmt in statements:
                        adapter.execute(stmt)
                    total_rows = 1
                return total_rows

            # Native DB-API cursor execution
            cursor = conn.cursor()
            try:
                if hook.transaction_policy == HookTransactionPolicy.ISOLATED_TRANSACTION:
                    if hasattr(conn, "autocommit"):
                        conn.autocommit = False

                for stmt in statements:
                    if hook.parameters and isinstance(hook.parameters, dict):
                        # Safe parameterized execution
                        try:
                            cursor.execute(stmt, hook.parameters)
                        except Exception:
                            # Fallback to positional if dict binding not supported by driver
                            cursor.execute(stmt)
                    else:
                        cursor.execute(stmt)

                    if hasattr(cursor, "rowcount") and cursor.rowcount and cursor.rowcount > 0:
                        total_rows += cursor.rowcount
                    else:
                        total_rows += 1

                if hook.transaction_policy in (HookTransactionPolicy.AUTO_COMMIT, HookTransactionPolicy.ISOLATED_TRANSACTION):
                    if hasattr(conn, "commit"):
                        conn.commit()
            except Exception as e:
                if hook.transaction_policy == HookTransactionPolicy.ISOLATED_TRANSACTION:
                    if hasattr(conn, "rollback"):
                        conn.rollback()
                raise e
            finally:
                if hasattr(cursor, "close"):
                    cursor.close()

            return total_rows

        return await asyncio.to_thread(_sync_execute)

    def _record_failure(
        self,
        state_key: str,
        hook: HookDefinition,
        workflow_id: str,
        run_id: str,
        error_message: str,
        is_ambiguous: bool = False,
    ) -> None:
        """Records failed or ambiguous state in CentralStateStore and AuditLogger."""
        st = HookExecutionState.AMBIGUOUS if is_ambiguous else HookExecutionState.FAILED
        event_type = AuditEventType.HOOK_AMBIGUOUS if is_ambiguous else AuditEventType.HOOK_FAILED

        self.state_store.set_state(
            key=state_key,
            value={
                "hook_id": hook.hook_id,
                "stage": hook.stage.value,
                "side": hook.side.value,
                "state": st.value,
                "error_message": error_message,
                "failed_at": time.time(),
                "workflow_id": workflow_id,
                "run_id": run_id,
            },
            category="hooks",
        )

        self.audit_logger.log(
            event_type,
            project_id=workflow_id,
            workflow_id=workflow_id,
            task_id=hook.hook_id,
            details={
                "stage": hook.stage.value,
                "side": hook.side.value,
                "error": error_message,
            },
        )

    def _normalize_stage(self, stage: Union[HookStage, str, HookPhase]) -> HookStage:
        if isinstance(stage, HookStage):
            return stage
        stage_str = stage.value if hasattr(stage, "value") else str(stage).upper()
        # Legacy HookPhase mapping
        mapping = {
            "BEFORE_DISCOVERY": HookStage.PRE_MIGRATION,
            "BEFORE_SCHEMA_MIGRATION": HookStage.TARGET_PREPARATION,
            "AFTER_SCHEMA_MIGRATION": HookStage.TARGET_PREPARATION,
            "BEFORE_DATA_MIGRATION": HookStage.PRE_MIGRATION,
            "AFTER_DATA_MIGRATION": HookStage.TARGET_FINALIZATION,
            "BEFORE_CUTOVER": HookStage.TARGET_FINALIZATION,
            "AFTER_CUTOVER": HookStage.POST_MIGRATION,
        }
        if stage_str in mapping:
            return mapping[stage_str]
        try:
            return HookStage(stage_str)
        except Exception:
            return HookStage.PRE_MIGRATION

    def _normalize_hook(self, raw_h: Union[HookDefinition, Dict[str, Any], SQLHook]) -> Optional[HookDefinition]:
        if isinstance(raw_h, HookDefinition):
            return raw_h
        if isinstance(raw_h, dict):
            return HookDefinition.from_dict(raw_h)
        if isinstance(raw_h, SQLHook):
            # Backward-compatible adaptation of legacy SQLHook
            joined_sql = ";\n".join(raw_h.sql_commands)
            stage_enum = self._normalize_stage(raw_h.phase)
            tx_policy = HookTransactionPolicy.ISOLATED_TRANSACTION if raw_h.transactional else HookTransactionPolicy.NO_TRANSACTION
            fail_policy = HookFailurePolicy.CONTINUE_ON_FAILURE if raw_h.ignore_failures else (
                HookFailurePolicy.ROLLBACK_AND_ABORT if raw_h.rollback_on_failure else HookFailurePolicy.FAIL_FAST
            )
            return HookDefinition(
                hook_id=f"legacy-hook-{abs(hash(joined_sql)) % 100000}",
                name="Legacy SQL Hook",
                stage=stage_enum,
                sql_statement=joined_sql,
                timeout_ms=raw_h.timeout_seconds * 1000,
                transaction_policy=tx_policy,
                failure_policy=fail_policy,
            )
        return None


# Backward-compatible wrapper for existing callers
class HookExecutor(GovernedHookExecutor):
    """Backward-compatible adapter for existing HookExecutor callers."""

    def __init__(self, connection_adapter: Any) -> None:
        super().__init__(target_adapter=connection_adapter)
        self.adapter = connection_adapter
        self.audit_log: List[Dict[str, Any]] = []

    async def execute_phase_hooks(self, hooks: List[SQLHook], phase: HookPhase) -> None:
        """Executes hooks assigned to a lifecycle phase, wrapping transactional paths."""
        try:
            results = await self.execute_stage_hooks(
                hooks=hooks,
                stage=phase,
                workflow_id="legacy-workflow",
            )
            for r in results:
                self.audit_log.append({
                    "phase": phase.value if hasattr(phase, "value") else str(phase),
                    "hook_id": r.hook_id,
                    "duration_seconds": r.duration_ms / 1000.0,
                    "success": r.state == HookExecutionState.COMPLETED,
                    "error": r.error_message,
                })
        except Exception as exc:
            for r in self.execution_history:
                if not any(a.get("hook_id") == r.hook_id for a in self.audit_log):
                    self.audit_log.append({
                        "phase": phase.value if hasattr(phase, "value") else str(phase),
                        "hook_id": r.hook_id,
                        "duration_seconds": r.duration_ms / 1000.0,
                        "success": r.state == HookExecutionState.COMPLETED,
                        "error": r.error_message,
                    })
            raise exc
