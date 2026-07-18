"""
Akaal — Checkpoint Analyzer
=============================
Passive analyzer determining checkpoint locations from stage boundaries and risk items.
"""

from typing import List
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.checkpoint_plan import CheckpointLocation


class CheckpointAnalyzer:
    analyzer_id = "checkpoint_analyzer"

    def analyze(self, ctx: PlanningContext) -> List[CheckpointLocation]:
        # Place checkpoints at each stage boundary
        locations = [
            CheckpointLocation(
                checkpoint_id=f"CHKPT-STAGE-{i+1}",
                task_id=f"task_stage_{i+1}_last",
                stage_id=f"stage_{i+1}",
                checkpoint_type="STAGE_BOUNDARY",
            )
            for i in range(3)  # Schema, Data, Validation stages
        ]
        return locations
