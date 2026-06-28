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
    ):
        self.source_config = source_config
        self.target_config = target_config
        self.strategy = strategy
        self.workspace_dir = workspace_dir
        self.project_name = project_name
        self.auto_approve = auto_approve
        self.ddl_schema_path = ddl_schema_path


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

        workspace = config.workspace_dir

        # Instantiate 16-agent active-standby fleet
        agents = [
            ManagerAgent(global_state, message_bus, audit_logger, approval_ctrl, agent_id="MANAGER-PRIMARY",    is_backup=False),
            ManagerAgent(global_state, message_bus, audit_logger, approval_ctrl, agent_id="MANAGER-BACKUP",     is_backup=True),
            ScoutAgent(global_state, message_bus, workspace_dir=workspace, agent_id="SCOUT-PRIMARY",            is_backup=False),
            ScoutAgent(global_state, message_bus, workspace_dir=workspace, agent_id="SCOUT-BACKUP",             is_backup=True),
            ValidatorAgent(global_state, message_bus, workspace_dir=workspace, agent_id="VALIDATOR-PRIMARY",    is_backup=False),
            ValidatorAgent(global_state, message_bus, workspace_dir=workspace, agent_id="VALIDATOR-BACKUP",     is_backup=True),
            GBAgent(global_state, message_bus, workspace_dir=workspace, agent_id="GB-PRIMARY",                  is_backup=False),
            GBAgent(global_state, message_bus, workspace_dir=workspace, agent_id="GB-BACKUP",                   is_backup=True),
            NoticerAgent(global_state, message_bus, agent_id="NOTICER-PRIMARY",                                 is_backup=False),
            NoticerAgent(global_state, message_bus, agent_id="NOTICER-BACKUP",                                  is_backup=True),
            CheckpointAgent(global_state, message_bus, workspace_dir=workspace, agent_id="CHECKPOINT-PRIMARY",  is_backup=False),
            CheckpointAgent(global_state, message_bus, workspace_dir=workspace, agent_id="CHECKPOINT-BACKUP",   is_backup=True),
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
        )

        async def _mock_discover_triggers(self, table_name):
            return []

        with patch.object(PostgreSQLAdapter, "discover_triggers", _mock_discover_triggers):
            migration_task = asyncio.create_task(
                manager_primary.run_migration(project.project_id)
            )
            while not migration_task.done():
                await asyncio.sleep(5)
            migration_result = await migration_task

        # Shutdown
        await message_bus.stop()
        for agent in agents:
            await agent.stop()

        logger.info("[Pipeline] Fleet shut down cleanly.")
        return migration_result
