"""
Akaal — Unified Migration Pipeline
====================================
The single entrypoint that runs the full end-to-end migration:

  Stage 1 — Pre-Migration Analysis (Advisory Layer)
    └── Schema Scout parses source DDL
    └── Rulebook maps types deterministically
    └── Risk Scorer scores each field/table
    └── Planner decides migration strategy
    └── Advisor generates the migration advisory report

  Stage 2 — Agent Fleet Execution
    └── Manager orchestrates 16-agent active-standby fleet
    └── Scout Agent discovers live schema
    └── GB Agent loads Greenbox staging environment
    └── Validator Agent verifies data integrity
    └── CDC Agent synchronizes deltas post-migration
    └── Checkpoint Agent persists state for recovery
    └── Human Approval Gate before production cutover

Usage:
    from akaal.pipeline import AkaalPipeline

    pipeline = AkaalPipeline()
    result = await pipeline.run(config)
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional
from unittest.mock import patch

from akaal.adapters.adapter_registry import create_adapter
from akaal.core.models.enums import (
    ApprovalDecision,
    MigrationStrategy,
    SystemType,
    WorkflowState,
)
from akaal.core.models.project import ConnectionConfig
from akaal.core.state.global_state import GlobalState, reset_global_state
from akaal.core.message_bus.bus import MessageBus, reset_message_bus
from akaal.audit.audit_logger import AuditLogger, reset_audit_logger
from akaal.agents.manager.manager_agent import ManagerAgent
from akaal.agents.manager.approval_controller import ApprovalController
from akaal.agents.scout.scout_agent import ScoutAgent
from akaal.agents.validator.validator_agent import ValidatorAgent
from akaal.agents.gb.gb_agent import GBAgent
from akaal.agents.noticer.noticer_agent import NoticerAgent
from akaal.agents.checkpoint.checkpoint_agent import CheckpointAgent
from akaal.agents.cdc.cdc_agent import CDCAgent
from akaal.agents.live_intel.live_intel_agent import LiveIntelAgent
from akaal.core.checkpoint.storage.factory import CheckpointStorageFactory
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager

logger = logging.getLogger("akaal.pipeline")


class MigrationConfig:
    """
    Top-level configuration for a migration run.

    Args:
        source_config:    ConnectionConfig for the source database.
        target_config:    ConnectionConfig for the target database.
        strategy:         MigrationStrategy to use.
        workspace_dir:    Local path for staging files, checkpoints, audit logs.
        project_name:     Human-readable name for the migration project.
        auto_approve:     If True, bypasses human approval gate (for automation/testing).
        ddl_schema_path:  Optional path to DDL file for pre-migration analysis.
    """

    def __init__(
        self,
        source_config: ConnectionConfig,
        target_config: ConnectionConfig,
        strategy: MigrationStrategy = MigrationStrategy.BIG_BANG,
        workspace_dir: str = "./akaal_workspace",
        project_name: str = "Akaal Migration",
        auto_approve: bool = False,
        ddl_schema_path: Optional[str] = None,
        # Phase 7F Adaptive Batch Sizing
        use_adaptive_batch: bool = False,
        minimum_batch_size: int = 10,
        initial_batch_size: int = 500,
        maximum_batch_size: int = 5000,
        growth_factor: float = 1.5,
        shrink_factor: float = 0.5,
        target_batch_duration_ms: float = 1000.0,
        adjustment_window: int = 3,
        # Phase 7G Parallel Migration
        enable_parallel_migration: bool = False,
        max_parallel_workers: int = 4,
        worker_queue_size: int = 100,
        scheduler_policy: str = "fifo",
        worker_idle_timeout: float = 60.0,
        worker_shutdown_timeout: float = 10.0,
        # Phase 7H Connection Pooling
        enable_connection_pooling: bool = False,
        minimum_pool_size: int = 1,
        pool_size: int = 4,
        maximum_pool_size: int = 10,
        connection_idle_timeout: float = 60.0,
        acquisition_timeout: float = 5.0,
        validation_interval: float = 30.0,
        connection_validation_on_checkout: bool = True,
        # Phase 7I Memory Optimization
        enable_memory_optimization: bool = True,
        memory_cleanup_interval: int = 5,
        memory_warning_threshold_mb: float = 512.0,
        # Phase 7J Structured Logging
        log_format: str = "text",
        log_level: str = "INFO",
        log_to_console: bool = True,
        log_to_file: bool = True,
        log_directory: str = "logs",
        log_file_name: str = "akaal.log",
        log_rotation_size_mb: int = 10,
        log_backup_count: int = 5,
    ):
        self.source_config = source_config
        self.target_config = target_config
        self.strategy = strategy
        self.workspace_dir = workspace_dir
        self.project_name = project_name
        self.auto_approve = auto_approve
        self.ddl_schema_path = ddl_schema_path
        
        # Adaptive batch settings
        self.use_adaptive_batch = use_adaptive_batch
        self.minimum_batch_size = minimum_batch_size
        self.initial_batch_size = initial_batch_size
        self.maximum_batch_size = maximum_batch_size
        self.growth_factor = growth_factor
        self.shrink_factor = shrink_factor
        self.target_batch_duration_ms = target_batch_duration_ms
        self.adjustment_window = adjustment_window

        # Parallel migration settings
        self.enable_parallel_migration = enable_parallel_migration
        self.max_parallel_workers = max_parallel_workers
        self.worker_queue_size = worker_queue_size
        self.scheduler_policy = scheduler_policy
        self.worker_idle_timeout = worker_idle_timeout
        self.worker_shutdown_timeout = worker_shutdown_timeout

        # Connection pooling settings
        self.enable_connection_pooling = enable_connection_pooling
        self.minimum_pool_size = minimum_pool_size
        self.pool_size = pool_size
        self.maximum_pool_size = maximum_pool_size
        self.connection_idle_timeout = connection_idle_timeout
        self.acquisition_timeout = acquisition_timeout
        self.validation_interval = validation_interval
        self.connection_validation_on_checkout = connection_validation_on_checkout

        # Memory optimization settings
        self.enable_memory_optimization = enable_memory_optimization
        self.memory_cleanup_interval = memory_cleanup_interval
        self.memory_warning_threshold_mb = memory_warning_threshold_mb

        # Structured logging settings
        self.log_format = log_format
        self.log_level = log_level
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_directory = log_directory
        self.log_file_name = log_file_name
        self.log_rotation_size_mb = log_rotation_size_mb
        self.log_backup_count = log_backup_count


class AkaalPipeline:
    """
    Unified end-to-end migration pipeline.

    Combines:
    - Advisory layer (schema analysis, risk scoring, planning)
    - 16-agent active-standby execution fleet
    - CDC synchronization
    - Checkpointing and recovery
    - Human approval gate
    """

    def __init__(self):
        self._agents = []

    async def run(self, config: MigrationConfig) -> Dict[str, Any]:
        """
        Execute the full migration pipeline.

        Returns a result dict with:
          - status: "completed" | "failed"
          - advisory: pre-migration analysis report (if DDL provided)
          - migration: agent fleet execution result
          - duration_seconds: total wall clock time
        """
        start = time.perf_counter()
        result: Dict[str, Any] = {
            "status": "failed",
            "advisory": None,
            "migration": None,
            "duration_seconds": 0.0,
        }

        os.makedirs(config.workspace_dir, exist_ok=True)

        # ── Stage 1: Pre-Migration Analysis ───────────────────────────
        if config.ddl_schema_path:
            logger.info("[Pipeline] Stage 1: Running pre-migration analysis...")
            try:
                advisory_result = self._run_advisory(config)
                result["advisory"] = advisory_result
                logger.info(
                    "[Pipeline] Advisory complete. Risk level: %s",
                    advisory_result.get("risk_summary", {}).get("overall_level", "UNKNOWN")
                )
            except Exception as e:
                logger.warning("[Pipeline] Advisory stage failed (non-blocking): %s", e)
                result["advisory"] = {"error": str(e)}
        else:
            logger.info("[Pipeline] No DDL schema path provided — skipping advisory stage.")

        # ── Stage 2: Agent Fleet Execution ────────────────────────────
        logger.info("[Pipeline] Stage 2: Launching agent fleet...")
        try:
            migration_result = await self._run_agent_fleet(config)
            result["migration"] = migration_result
            result["status"] = migration_result.get("status", "failed")
        except Exception as e:
            logger.error("[Pipeline] Agent fleet execution failed: %s", e)
            result["migration"] = {"error": str(e)}

        result["duration_seconds"] = round(time.perf_counter() - start, 2)
        logger.info(
            "[Pipeline] Done. Status=%s Duration=%.2fs",
            result["status"], result["duration_seconds"]
        )
        return result

    # ──────────────────────────────────────────────────────────────────
    # Stage 1: Advisory
    # ──────────────────────────────────────────────────────────────────

    def _run_advisory(self, config: MigrationConfig) -> Dict[str, Any]:
        """
        Run the pre-migration advisory pipeline on a DDL file.
        Uses: Schema Scout → Rulebook → Risk Scorer → Planner → Advisor
        """
        from akaal.advisory.schema_scout import Scout
        from akaal.advisory.rulebook.resolver import SemanticResolver
        from akaal.advisory.risk_scorer.risk_scorer import RiskScorerV1
        from akaal.advisory.planner.planner import plan_migration
        from akaal.advisory.orchestrator import OrchestratorV1

        engine = config.source_config.system_type.value.lower()

        # Map Akaal SystemType → advisory engine name
        engine_map = {
            "oracle": "oracle",
            "mysql": "mysql",
            "mariadb": "mysql",
            "postgresql": "postgres",
        }
        advisory_engine = engine_map.get(engine, "mysql")

        scout = Scout(engine=advisory_engine)
        schema_text = scout.load_schema(config.ddl_schema_path)
        blueprint = scout.generate_blueprint(schema_text)

        # Score risk for each column across all tables
        resolver = SemanticResolver()
        scorer = RiskScorerV1()
        orchestrator = OrchestratorV1()

        table_reports = []
        overall_scores = []

        for table in blueprint.get("objects", []):
            col_reports = []
            for col in table.get("attributes", []):
                try:
                    raw_input = {
                        "source_type": advisory_engine,
                        "raw_type": col.get("source_type", "VARCHAR"),
                    }
                    col_result = orchestrator.run(raw_input)
                    col_risk = col_result.get("risk", {})
                    if "risk" in col_risk and isinstance(col_risk["risk"], dict):
                        col_risk = col_risk["risk"]
                    col_reports.append({
                        "column": col["name"],
                        "source_type": col.get("source_type"),
                        "risk_level": col_risk.get("level", "UNKNOWN"),
                        "risk_score": col_risk.get("score", 0),
                        "flags": col_risk.get("flags", []),
                        "plan": col_result.get("plan", {}),
                    })
                    score = col_risk.get("score", 0)
                    if isinstance(score, (int, float)):
                        overall_scores.append(score)
                except Exception:
                    col_reports.append({"column": col["name"], "error": "analysis failed"})

            table_reports.append({
                "table": table["name"],
                "columns": col_reports,
            })

        avg_score = round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0
        overall_level = "LOW" if avg_score <= 2 else "MEDIUM" if avg_score <= 4 else "HIGH" if avg_score <= 6 else "CRITICAL"

        return {
            "source_engine": advisory_engine,
            "tables_analyzed": len(blueprint.get("objects", [])),
            "relationships": len(blueprint.get("relationships", [])),
            "risk_summary": {
                "average_score": avg_score,
                "overall_level": overall_level,
                "total_columns_scored": len(overall_scores),
            },
            "table_reports": table_reports,
        }

    # ──────────────────────────────────────────────────────────────────
    # Stage 2: Agent Fleet
    # ──────────────────────────────────────────────────────────────────

    async def _run_agent_fleet(self, config: MigrationConfig) -> Dict[str, Any]:
        """Spin up the 16-agent fleet and run the migration workflow."""
        import uuid
        from akaal.logging_manager import configure_logging, migration_context
        from akaal.core.observability import ObservabilityContext
        from akaal.metrics.summary import SummaryGenerator

        correlation_id = str(uuid.uuid4())

        # Configure logging dynamically
        log_dir = os.path.join(config.workspace_dir, getattr(config, "log_directory", "logs"))
        configure_logging(
            log_format=getattr(config, "log_format", "text"),
            log_level=getattr(config, "log_level", "INFO"),
            log_to_console=getattr(config, "log_to_console", True),
            log_to_file=getattr(config, "log_to_file", True),
            log_directory=log_dir,
            log_file_name=getattr(config, "log_file_name", "akaal.log"),
            log_rotation_size_mb=getattr(config, "log_rotation_size_mb", 10),
            log_backup_count=getattr(config, "log_backup_count", 5),
            project_name=config.project_name
        )

        with migration_context(
            correlation_id=correlation_id,
            project_name=config.project_name
        ):
            reset_global_state()
            reset_message_bus()
            reset_audit_logger()

            global_state = GlobalState()
            message_bus = MessageBus()
            audit_logger = AuditLogger(
                log_dir=os.path.join(config.workspace_dir, "audit")
            )

            # Approval controller
            approval_ctrl = ApprovalController(cli_mode=False)
            if config.auto_approve:
                async def _auto_approve(packet):
                    return ApprovalDecision.APPROVE
                approval_ctrl.set_decision_callback(_auto_approve)

            # Phase 7K: Create the observability context for this migration run.
            # Lifetime: created here, lives until _run_agent_fleet returns.
            # Ownership: Pipeline → ObservabilityContext → MetricsRegistry.
            # It is not a singleton; a fresh instance is created per run.
            observability = ObservabilityContext()
            registry = observability.registry

            workspace = config.workspace_dir

            # Initialize the checkpoint storage database and create a shared manager instance
            db_path = os.path.join(workspace, "checkpoints.db")
            storage_adapter = CheckpointStorageFactory.create(storage_type="sqlite", db_path=db_path)
            # Note: run initialize asynchronously in the loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                await storage_adapter.initialize()
            else:
                loop.run_until_complete(storage_adapter.initialize())
            checkpoint_manager = CheckpointManager(storage_adapter, metrics_registry=registry)

            # Instantiate 16-agent active-standby fleet
            agents = [
                ManagerAgent(global_state, message_bus, audit_logger, checkpoint_manager, approval_ctrl, agent_id="MANAGER-PRIMARY",    is_backup=False, metrics_registry=registry),
                ManagerAgent(global_state, message_bus, audit_logger, checkpoint_manager, approval_ctrl, agent_id="MANAGER-BACKUP",     is_backup=True,  metrics_registry=registry),
                ScoutAgent(global_state, message_bus, workspace_dir=workspace, agent_id="SCOUT-PRIMARY",            is_backup=False),
                ScoutAgent(global_state, message_bus, workspace_dir=workspace, agent_id="SCOUT-BACKUP",             is_backup=True),
                ValidatorAgent(global_state, message_bus, workspace_dir=workspace, agent_id="VALIDATOR-PRIMARY",    is_backup=False),
                ValidatorAgent(global_state, message_bus, workspace_dir=workspace, agent_id="VALIDATOR-BACKUP",     is_backup=True),
                GBAgent(global_state, message_bus, checkpoint_manager, workspace_dir=workspace, agent_id="GB-PRIMARY",                  is_backup=False, metrics_registry=registry),
                GBAgent(global_state, message_bus, checkpoint_manager, workspace_dir=workspace, agent_id="GB-BACKUP",                   is_backup=True,  metrics_registry=registry),
                NoticerAgent(global_state, message_bus, agent_id="NOTICER-PRIMARY",                                 is_backup=False),
                NoticerAgent(global_state, message_bus, agent_id="NOTICER-BACKUP",                                  is_backup=True),
                CheckpointAgent(global_state, message_bus, checkpoint_manager, agent_id="CHECKPOINT-PRIMARY",  is_backup=False),
                CheckpointAgent(global_state, message_bus, checkpoint_manager, agent_id="CHECKPOINT-BACKUP",   is_backup=True),
                CDCAgent(global_state, message_bus, workspace_dir=workspace, agent_id="CDC-PRIMARY",                is_backup=False),
                CDCAgent(global_state, message_bus, workspace_dir=workspace, agent_id="CDC-BACKUP",                 is_backup=True),
                LiveIntelAgent(global_state, message_bus, agent_id="LIVE-INTEL-PRIMARY",                            is_backup=False),
                LiveIntelAgent(global_state, message_bus, agent_id="LIVE-INTEL-BACKUP",                             is_backup=True),
            ]
            self._agents = agents

            for agent in agents:
                await agent.start()
            await message_bus.start()
            logger.info("[Pipeline] 16-agent fleet started.")

            # Resolve adapter for source DB to enable trigger discovery mock
            from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter

            manager_primary = agents[0]

            project = await manager_primary.create_project(
                name=config.project_name,
                source_config=config.source_config,
                target_config=config.target_config,
                strategy=config.strategy,
                # Phase 7F Adaptive Batch Sizing
                use_adaptive_batch=getattr(config, "use_adaptive_batch", False),
                minimum_batch_size=getattr(config, "minimum_batch_size", 10),
                initial_batch_size=getattr(config, "initial_batch_size", 500),
                maximum_batch_size=getattr(config, "maximum_batch_size", 5000),
                growth_factor=getattr(config, "growth_factor", 1.5),
                shrink_factor=getattr(config, "shrink_factor", 0.5),
                target_batch_duration_ms=getattr(config, "target_batch_duration_ms", 1000.0),
                adjustment_window=getattr(config, "adjustment_window", 3),
                # Phase 7G Parallel Migration
                enable_parallel_migration=getattr(config, "enable_parallel_migration", False),
                max_parallel_workers=getattr(config, "max_parallel_workers", 4),
                worker_queue_size=getattr(config, "worker_queue_size", 100),
                scheduler_policy=getattr(config, "scheduler_policy", "fifo"),
                worker_idle_timeout=getattr(config, "worker_idle_timeout", 60.0),
                worker_shutdown_timeout=getattr(config, "worker_shutdown_timeout", 10.0),
                # Phase 7H Connection Pooling
                enable_connection_pooling=getattr(config, "enable_connection_pooling", False),
                minimum_pool_size=getattr(config, "minimum_pool_size", 1),
                pool_size=getattr(config, "pool_size", 4),
                maximum_pool_size=getattr(config, "maximum_pool_size", 10),
                connection_idle_timeout=getattr(config, "connection_idle_timeout", 60.0),
                acquisition_timeout=getattr(config, "acquisition_timeout", 5.0),
                validation_interval=getattr(config, "validation_interval", 30.0),
                connection_validation_on_checkout=getattr(config, "connection_validation_on_checkout", True),
                # Phase 7I Memory Optimization
                enable_memory_optimization=getattr(config, "enable_memory_optimization", True),
                memory_cleanup_interval=getattr(config, "memory_cleanup_interval", 5),
                memory_warning_threshold_mb=getattr(config, "memory_warning_threshold_mb", 512.0),
                # Phase 7J Structured Logging
                log_format=getattr(config, "log_format", "text"),
                log_level=getattr(config, "log_level", "INFO"),
                log_to_console=getattr(config, "log_to_console", True),
                log_to_file=getattr(config, "log_to_file", True),
                log_directory=getattr(config, "log_directory", "logs"),
                log_file_name=getattr(config, "log_file_name", "akaal.log"),
                log_rotation_size_mb=getattr(config, "log_rotation_size_mb", 10),
                log_backup_count=getattr(config, "log_backup_count", 5),
            )

            # Attach observability context to the session so other components
            # can record metrics without coupling to the pipeline.
            # ``manager_primary`` owns the session; we reach in after run_migration
            # because the session is constructed inside run_migration.
            # We retrieve it from global_state to avoid coupling further.
            try:
                session = await global_state.get_session_for_project(
                    project.project_id
                ) if hasattr(global_state, "get_session_for_project") else None
            except Exception:
                session = None

            if session is not None:
                session.observability = observability

            async def _mock_discover_triggers(self, table_name):
                return []

            with patch.object(PostgreSQLAdapter, "discover_triggers", _mock_discover_triggers):
                migration_task = asyncio.create_task(
                    manager_primary.run_migration(project.project_id)
                )
                while not migration_task.done():
                    await asyncio.sleep(5)
                migration_result = await migration_task

            # Phase 7K: After migration completes, generate and store the summary.
            # SummaryGenerator is called exactly once, here, after the migration.
            # The summary is stored on the session; it is NOT printed or exported here.
            try:
                snapshot = registry.snapshot()
                summary = SummaryGenerator().generate(snapshot)
                # Re-fetch session in case it was updated during migration.
                try:
                    latest_session = await global_state.get_session_for_project(
                        project.project_id
                    ) if hasattr(global_state, "get_session_for_project") else None
                except Exception:
                    latest_session = None
                if latest_session is not None:
                    latest_session.metrics_summary = summary
                elif session is not None:
                    session.metrics_summary = summary
                # Also attach to migration_result for downstream convenience.
                migration_result["metrics_summary"] = {
                    "duration_seconds": summary.duration_seconds,
                    "rows_migrated": summary.rows_migrated,
                    "bytes_migrated": summary.bytes_migrated,
                    "tables_migrated": summary.tables_migrated,
                    "rows_per_sec": summary.rows_per_sec,
                    "mb_per_sec": summary.mb_per_sec,
                }
                logger.info(
                    "[Pipeline] Metrics summary generated: rows=%d tables=%d duration=%.2fs",
                    summary.rows_migrated,
                    summary.tables_migrated,
                    summary.duration_seconds,
                )
            except Exception as exc:
                # Metric failures must NEVER abort migration.
                logger.warning("[Pipeline] Metrics summary generation failed (non-critical): %s", exc)

            # Shutdown
            await message_bus.stop()
            for agent in agents:
                await agent.stop()

            logger.info("[Pipeline] Fleet shut down cleanly.")
            return migration_result
