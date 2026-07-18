"""
Akaal — Cutover Engine
========================
Generates deterministic CutoverPlan with immutable phases.
Planner plans cutover but never executes it.
"""

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.cutover_plan import CutoverPlan, CutoverPhase, CutoverPhaseType
from akaal.planner.analyzers.cutover_analyzer import CutoverAnalyzer


class CutoverEngine:
    """Generates CutoverPlan with phased strategy from readiness model."""

    def build_cutover_plan(self, ctx: PlanningContext) -> CutoverPlan:
        analyzer = CutoverAnalyzer()
        analysis = analyzer.analyze(ctx)

        rollback_window = analysis.get("rollback_window_minutes", 30.0)

        phase_defs = [
            (CutoverPhaseType.PREPARATION, 10.0, ["SCHEMA_VALIDATED"], ["SCHEMA_FROZEN"]),
            (CutoverPhaseType.FREEZE, 5.0, ["SCHEMA_FROZEN"], ["WRITES_PAUSED"]),
            (CutoverPhaseType.SYNCHRONIZATION, 15.0, ["WRITES_PAUSED"], ["DATA_SYNC_COMPLETE"]),
            (CutoverPhaseType.VALIDATION, 10.0, ["DATA_SYNC_COMPLETE"], ["DATA_VALIDATED"]),
            (CutoverPhaseType.SWITCH, 2.0, ["DATA_VALIDATED"], ["DNS_SWITCHED"]),
            (CutoverPhaseType.MONITORING, 20.0, ["DNS_SWITCHED"], ["STABLE_PERIOD_ELAPSED"]),
            (CutoverPhaseType.ROLLBACK_WINDOW, rollback_window, ["MONITORING_STARTED"], ["ROLLBACK_WINDOW_CLOSED"]),
            (CutoverPhaseType.COMPLETION, 2.0, ["ROLLBACK_WINDOW_CLOSED"], ["MIGRATION_COMPLETE"]),
        ]

        phases = [
            CutoverPhase(
                phase_id=f"PHASE-{pt.value}",
                phase_type=pt,
                estimated_duration_minutes=dur,
                entry_criteria=entry,
                exit_criteria=exit_c,
            )
            for pt, dur, entry, exit_c in phase_defs
        ]

        total_dur = sum(p.estimated_duration_minutes for p in phases)

        return CutoverPlan(
            strategy=analysis.get("recommended_strategy", "BULK_CUTOVER"),
            phases=phases,
            rollback_window_minutes=rollback_window,
            total_estimated_duration_minutes=total_dur,
        )
