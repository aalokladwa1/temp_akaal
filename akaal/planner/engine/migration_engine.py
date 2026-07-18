"""
Akaal — Migration Engine
=========================
Generates the master set of ExecutionTasks from RiskAssessmentModel.
Covers schema, data, validation, checkpoint, rollback, and cutover operations.
Zero SQL generation. Zero migration execution.
"""

from typing import List
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_task import ExecutionTask
from akaal.planner.models.execution_state import ExecutionState


class MigrationEngine:
    """Generates master list of ExecutionTask nodes from risk model."""

    def generate_tasks(self, ctx: PlanningContext) -> List[ExecutionTask]:
        tasks: List[ExecutionTask] = []
        risk_items = ctx.risk_model.risk_items
        stats = ctx.risk_model.statistics

        # Stage 1 — Schema DDL tasks (one per risk item domain)
        tasks.append(ExecutionTask(
            task_id="TASK-SCHEMA-INIT",
            task_name="Initialize Schema Operations",
            task_type="SCHEMA_DDL",
            target_object_id="schema_root",
            state=ExecutionState.PLANNED,
            stage_id="stage_1_schema",
            estimated_duration_seconds=30.0,
        ))

        # Per-risk-item tasks
        for i, item in enumerate(risk_items):
            task_id = f"TASK-DATA-{i+1}"
            tasks.append(ExecutionTask(
                task_id=task_id,
                task_name=f"Migrate {item.get('risk_type', 'UNKNOWN')} ({i+1})",
                task_type="DATA_BULK",
                target_object_id=item.get("risk_id", f"obj_{i}"),
                state=ExecutionState.PLANNED,
                stage_id="stage_2_data",
                dependencies=["TASK-SCHEMA-INIT"],
                estimated_duration_seconds=60.0,
            ))

        # Validation task
        tasks.append(ExecutionTask(
            task_id="TASK-VALIDATE-FINAL",
            task_name="Final Validation Gate",
            task_type="VALIDATION_CHECK",
            target_object_id="validation_gate",
            state=ExecutionState.PLANNED,
            stage_id="stage_3_validation",
            dependencies=[f"TASK-DATA-{i+1}" for i in range(len(risk_items))] or ["TASK-SCHEMA-INIT"],
            estimated_duration_seconds=20.0,
        ))

        return tasks
