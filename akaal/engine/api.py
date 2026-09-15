"""
AKAAL Native Engine API Entrypoint
==================================
Canonical programmatic interface for discovery, planning, partitioning,
governance, multithreaded transport, checkpointing, and validation.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional

from akaal.engine.spec import (
    MigrationSpecification,
    ExecutionPlan,
    TransportPartition,
    PartitionStrategy,
    MigrationState,
    TuningPolicy,
    ValidationPolicy,
    RecoveryPolicy,
    ConnectionAuthorityDTO,
    ValidationLevel,
)
from akaal.engine.state import EngineStateRepository
from akaal.engine.checkpoint import CheckpointStore
from akaal.engine.partitioner import TransportPartitioner
from akaal.engine.scheduler import MigrationScheduler
from akaal.engine.validator import EngineValidator
from akaal.engine.telemetry import TelemetryEmitter
from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
from akaal.engine.writer import PostgreSQLTargetWriter

logger = logging.getLogger("akaal.engine.api")


class LegacyEngineBypassClosedError(RuntimeError):
    """
    Raised by `AkaalMigrationEngine.start_migration` (see class docstring below)
    when asked to perform physical migration execution. This class is a
    confirmed, real, mode-blind bypass of the canonical execution authority
    and its physical-execution path is closed; it fails closed instead of
    silently running its own independent transport engine.
    """


class AkaalMigrationEngine:
    """
    Legacy Native Python Execution Core for AKAAL Migrations.

    CORRECTION (bypass-closure campaign, this session): despite the historical
    "Canonical Native Python Execution Core" docstring above, this class is
    NOT the canonical execution authority. `start_migration` previously ran
    its own entirely independent Oracle->Postgres multiprocess transport
    engine (TransportPartitioner + MigrationScheduler + PostgreSQLTargetWriter
    + EngineValidator, with its own EngineStateRepository/CheckpointStore) with
    zero awareness of `akaal.engine.facade.AkaalSuperEngine`,
    `akaal.planner.engine.plan_compiler.PlanCompiler`, `ExecutionMode` (M1-M8),
    or governance/plan-fingerprint approval — a confirmed, real, mode-blind
    bypass of the canonical DAG-driven physical execution authority.

    Existing test coverage already treats this class as legacy/dead code that
    must NEVER be reachable from the canonical production transport path (see
    tests/unit/replication/test_step_5_2_canonical_transport.py,
    tests/unit/runtime/test_step_5_4_failure_recovery.py::test_08_legacy_transport_isolation,
    and tests/unit/workflow/test_step_5_5_workflow_gating_telemetry.py), and no
    production code path in this repository calls `start_migration`. Genuinely
    rewiring this class's independent multiprocess transport engine to
    delegate into `AkaalSuperEngine.execute_migration` would mean rebuilding it
    on entirely different primitives (compiled DAG, CentralStateStore,
    governance-approval records) it was never designed around — an
    out-of-scope rearchitecture of code that is supposed to be unreachable
    anyway. So `start_migration` now FAILS CLOSED unconditionally: it refuses
    to perform any physical execution and raises `LegacyEngineBypassClosedError`
    naming the canonical replacement, rather than silently running its own
    alternate physical execution.
    """

    def __init__(self, db_path_state: Optional[str] = None, db_path_checkpoint: Optional[str] = None):
        self.state_repo = EngineStateRepository(db_path=db_path_state)
        self.checkpoint_store = CheckpointStore(db_path=db_path_checkpoint)

    def verify_connection(self, authority: ConnectionAuthorityDTO, password: str) -> Dict[str, Any]:
        """Verify DB connection reachability without side effects."""
        params = {
            "username": authority.username,
            "password": password,
            "host": authority.host,
            "port": authority.port,
            "database": authority.database,
            "database_name": authority.database,
        }

        t_start = time.time()
        if authority.engine == "ORACLE":
            adapter = OracleAdapter(type("Config", (), params)())
            res = adapter.test_connection()
        else:
            adapter = PostgreSQLAdapter(type("Config", (), params)())
            res = adapter.test_connection()

        latency_ms = round((time.time() - t_start) * 1000, 2)
        return {
            "connected": bool(res),
            "fingerprint": authority.authority_fingerprint,
            "latency_ms": latency_ms,
        }

    def register_specification(
        self,
        migration_id: str,
        migration_name: str,
        project_name: str,
        source_auth: ConnectionAuthorityDTO,
        target_auth: ConnectionAuthorityDTO,
        selected_scope: Dict[str, Any],
        tuning_policy: Optional[TuningPolicy] = None,
        validation_policy: Optional[ValidationPolicy] = None,
        recovery_policy: Optional[RecoveryPolicy] = None,
    ) -> MigrationSpecification:
        """Register canonical immutable MigrationSpecification."""
        tuning = tuning_policy or TuningPolicy()
        validation = validation_policy or ValidationPolicy()
        recovery = recovery_policy or RecoveryPolicy()

        plan = ExecutionPlan(
            plan_id=f"plan-{migration_id}",
            migration_id=migration_id,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        spec = MigrationSpecification(
            migration_id=migration_id,
            specification_version="3.0.0",
            migration_name=migration_name,
            project_name=project_name,
            source_authority=source_auth,
            target_authority=target_auth,
            selected_scope=selected_scope,
            schema_plan={},
            execution_plan=plan,
            tuning_policy=tuning,
            validation_policy=validation,
            recovery_policy=recovery,
        )

        spec_dict = {
            "migration_id": migration_id,
            "source_fp": source_auth.authority_fingerprint,
            "target_fp": target_auth.authority_fingerprint,
            "scope": selected_scope,
        }

        self.state_repo.set_migration_state(migration_id, MigrationState.CREATED, spec_json=json.dumps(spec_dict))
        logger.info(f"[ENGINE API] MigrationSpecification registered: {migration_id}")
        return spec

    def start_migration(
        self,
        spec: MigrationSpecification,
        source_pass: str,
        target_pass: str,
    ) -> Dict[str, Any]:
        """
        FAILS CLOSED (bypass-closure campaign, this session): this method used
        to execute end-to-end physical migration using its own independent
        parallel multiprocess transport engine (TransportPartitioner +
        MigrationScheduler + PostgreSQLTargetWriter + EngineValidator),
        entirely bypassing `akaal.engine.facade.AkaalSuperEngine.execute_migration`
        / `PlanExecutionDispatcher` and therefore the compiled-DAG mode fence
        (M1-M8) and governance plan-fingerprint approval those enforce.

        This class is legacy/dead code: no production code path in this
        repository calls `start_migration`, and existing tests
        (tests/unit/replication/test_step_5_2_canonical_transport.py,
        tests/unit/runtime/test_step_5_4_failure_recovery.py,
        tests/unit/workflow/test_step_5_5_workflow_gating_telemetry.py) already
        assert this class must be absent from the canonical production
        transport path. Rebuilding its independent multiprocess engine to
        genuinely delegate into `AkaalSuperEngine.execute_migration` would mean
        re-architecting it onto entirely different primitives (compiled DAG,
        CentralStateStore, governance-approval records) it was never designed
        around, for a class that is supposed to be unreachable in production
        anyway — out of scope for this correction. Rather than leave the
        independent transport engine reachable as a silent, mode-blind
        alternate physical-execution path, `start_migration` now refuses to
        run it at all.
        """
        self.state_repo.set_migration_state(spec.migration_id, MigrationState.FAILED)
        msg = (
            f"LEGACY_ENGINE_BYPASS_CLOSED: AkaalMigrationEngine.start_migration refuses to execute "
            f"physical migration work for '{spec.migration_id}'. This class's independent multiprocess "
            f"transport engine is NOT the canonical execution authority and is not wired to it. Use "
            f"akaal.engine.facade.AkaalSuperEngine.execute_migration (with a plan compiled via "
            f"akaal.planner.engine.plan_compiler.PlanCompiler and governance approval recorded) instead."
        )
        logger.error(f"[ENGINE API] {msg}")
        raise LegacyEngineBypassClosedError(msg)

    def get_status(self, migration_id: str) -> Dict[str, Any]:
        state_dict = self.state_repo.get_migration_state(migration_id)
        if not state_dict:
            return {"migration_id": migration_id, "status": "UNKNOWN"}
        return state_dict
