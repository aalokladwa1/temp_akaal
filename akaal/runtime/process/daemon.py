"""
AKAAL Runtime V3 — Migration Runtime Daemon
===========================================
Dedicated OS process runner owning the isolated migration execution lifecycle
for one migration_id.

CORRECTION (M1-M8 bypass closure, this session): this daemon previously built
its OWN fixed `WorkflowEngine` step sequence
(pre_start -> schema_exec -> data_transport -> validation, unconditionally)
independent of `akaal.engine.facade.AkaalSuperEngine` and the compiled,
mode-differentiated DAG (`PlanCompiler`/`dag_dict.dag_stages`). That made this
daemon a confirmed, real, mode-blind bypass of the canonical DAG-driven
physical execution authority: any migration launched through this daemon
(directly, or via `akaal.runtime.supervisor.tree.RuntimeSupervisorTree`)
always executed the same 4 steps no matter what `ExecutionMode` (M1-M8) had
actually been compiled and governance-approved for it.

This daemon is NOT a second execution engine and does not become one here:
it now delegates 100% of physical execution to the single canonical
authority, `AkaalSuperEngine.execute_migration`, using the exact same
compiled-plan lookup `akaal.gateway.engine_gateway.EngineGateway.start_transport`
uses (`CentralStateStore.get_state(migration_id, category="execution_plan")`)
plus the same governance-approval gate (`verify_governance_authorization`,
enforced inside `execute_migration` itself). If no compiled, governance-
approved `dag_dict` exists for this migration_id, this daemon FAILS CLOSED
rather than falling back to any fixed/legacy step sequence.
"""

import os
import sys
import time
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("akaal.runtime.daemon")


class MigrationRuntimeDaemon:
    """Isolated OS runtime daemon executing a single migration workflow by
    delegating exclusively into the canonical `AkaalSuperEngine` DAG-driven
    execution authority. Holds no independent execution logic of its own."""

    def __init__(self, migration_id: str, epoch: int = 1, config: Optional[Dict[str, Any]] = None, super_engine: Optional[Any] = None) -> None:
        self.migration_id = migration_id
        self.epoch = epoch
        self.config = config or {}
        self.pid = os.getpid()
        # Lazily constructed / test-injectable reference to the ONE canonical
        # physical execution authority. Never a second engine.
        self._super_engine = super_engine
        self.is_alive = True
        self.last_heartbeat = time.time()
        self.status = "INITIALIZED"

    @property
    def super_engine(self):
        if self._super_engine is None:
            from akaal.engine.facade import AkaalSuperEngine
            self._super_engine = AkaalSuperEngine()
        return self._super_engine

    def send_heartbeat(self) -> float:
        self.last_heartbeat = time.time()
        return self.last_heartbeat

    def execute_migration(self) -> Dict[str, Any]:
        self.status = "RUNNING"
        self.send_heartbeat()
        logger.info(f"[RuntimeDaemon-PID:{self.pid}] Executing migration '{self.migration_id}' (Epoch: {self.epoch})...")

        from akaal.core.state.state_store import CentralStateStore
        from akaal.engine.facade import (
            ApprovalRequiredError,
            PlanFingerprintMissingError,
            PlanFingerprintMismatchError,
            PhysicalExecutionContractError,
            PhysicalValidationContractError,
        )

        state_store = CentralStateStore()

        # Same compiled-plan lookup EngineGateway.start_transport uses: an
        # explicit dag_dict in config wins (e.g. injected by a supervisor that
        # already holds it), otherwise fall back to the durable, governance-
        # bound compiled plan keyed by migration_id.
        dag_dict = self.config.get("dag_dict") or state_store.get_state(self.migration_id, category="execution_plan")
        spec_dict = self.config.get("spec_dict") or self.config

        if not dag_dict or not isinstance(dag_dict, dict) or not dag_dict.get("dag_stages"):
            self.status = "FAILED"
            msg = (
                f"RUNTIME_DAEMON_BYPASS_CLOSED: no compiled dag_dict (with dag_stages) is available for "
                f"migration '{self.migration_id}' -- neither in config['dag_dict'] nor in "
                f"CentralStateStore under category='execution_plan'. This daemon refuses to fall back to "
                f"a fixed, mode-blind step sequence; canonical DAG-driven execution requires a compiled, "
                f"governance-approved plan (see akaal.planner.engine.plan_compiler.PlanCompiler)."
            )
            logger.error(f"[RuntimeDaemon-PID:{self.pid}] {msg}")
            return {
                "status": "failed",
                "migration_id": self.migration_id,
                "error": msg,
                "error_code": "PLAN_NOT_LOAD_BEARING",
                "error_category": "GOVERNANCE",
                "failed_stage": "pre_start_validation",
                "failed_object": "compiled_plan",
                "safe_message": msg,
                "remediation": "Compile a plan via PlanCompiler and obtain governance approval before starting this daemon.",
                "retryable": False,
            }

        source_params = self.config.get("source_params")
        target_params = self.config.get("target_params")
        is_physical = self.config.get("is_physical", True)
        is_synthetic_test = self.config.get("is_synthetic_test", False)

        try:
            result = self.super_engine.execute_migration(
                workflow_id=self.migration_id,
                spec_dict=spec_dict,
                dag_dict=dag_dict,
                source_params=source_params,
                target_params=target_params,
                is_physical=is_physical,
                is_synthetic_test=is_synthetic_test,
            )

            exec_record = state_store.get_state(f"{self.migration_id}_plan_execution", category="runtime") or {}
            is_ok = bool(exec_record.get("success", True))
            self.status = "COMPLETED" if is_ok else "FAILED"
            self.send_heartbeat()

            return {
                "status": "transport_running" if is_ok else "failed",
                "migration_id": self.migration_id,
                "plan_fingerprint": result.get("plan_fingerprint") if isinstance(result, dict) else None,
                "rows_migrated": exec_record.get("rows_written", 0),
                "rows_validated": exec_record.get("rows_read", 0),
                "tables_migrated": exec_record.get("tables_processed", 0),
                "throughput_mbps": None,
                "rows_per_sec": None,
                "logs": [],
                "trace": result,
                "plan_execution": exec_record,
            }
        except (ApprovalRequiredError, PlanFingerprintMissingError, PlanFingerprintMismatchError,
                PhysicalExecutionContractError, PhysicalValidationContractError) as exc:
            self.status = "FAILED"
            logger.error(f"[RuntimeDaemon-PID:{self.pid}] Governance/contract gate rejected execution: {exc}")
            return {
                "status": "failed",
                "migration_id": self.migration_id,
                "error": str(exc),
                "error_code": type(exc).__name__.upper(),
                "error_category": "GOVERNANCE",
                "failed_stage": "governance_authorization",
                "safe_message": f"Migration rejected by governance/execution-contract gate: {exc}",
                "remediation": "Verify plan compilation, approval, and physical/validation contract dictionaries.",
                "retryable": False,
            }
        except Exception as exc:
            self.status = "FAILED"
            logger.error(f"[RuntimeDaemon-PID:{self.pid}] Migration execution error: {exc}", exc_info=True)
            err_str = str(exc)
            err_code = "STEP_EXECUTION_FAILED"
            remediation = "Verify database connectivity, user credentials, schema permissions, and network routes."
            category = "DATABASE"
            
            if "CREDENTIAL_RESOLUTION_FAILED" in err_str:
                err_code = "CREDENTIAL_RESOLUTION_FAILED"
                remediation = "Re-enter user passwords in wizard connection configuration."
                category = "CREDENTIAL"
            elif "AUTHORITY_MISMATCH" in err_str:
                err_code = "AUTHORITY_MISMATCH"
                remediation = "Verify target database port, host, and database name settings."
                category = "AUTHORITY"
            elif "StepStatus" in err_str:
                err_code = "PROGRAMMING_ERROR"
                remediation = "Update WorkflowEngine step status enum contract."
                category = "PROGRAMMING"

            return {
                "status": "failed",
                "migration_id": self.migration_id,
                "error": err_str,
                "error_code": err_code,
                "error_category": category,
                "failed_stage": "pre_start_validation",
                "failed_object": "connection_ping",
                "failed_schema": "target_schema",
                "safe_message": f"Migration failed during execution: {err_str}",
                "remediation": remediation,
                "retryable": False
            }

    def shutdown(self) -> None:
        self.is_alive = False
        self.status = "STOPPED"
        logger.info(f"[RuntimeDaemon-PID:{self.pid}] Shutdown cleanly.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mig_id = sys.argv[1]
        daemon = MigrationRuntimeDaemon(migration_id=mig_id)
        res = daemon.execute_migration()
        print(f"Daemon Result: {res}")
