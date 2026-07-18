"""
Akaal — Simulation Engine
=========================
Single-responsibility engine producing read-only SimulationReport dry-run summaries.
"""

import time
from typing import List, Tuple
from akaal.rulebook.models.rule import Rule
from akaal.rulebook.models.rule_evaluation_context import RuleEvaluationContext
from akaal.rulebook.models.rule_execution_trace import RuleExecutionTrace, TraceStep
from akaal.rulebook.models.simulation_report import SimulationReport
from akaal.rulebook.models.rule_result import RuleEvaluationResult
from akaal.rulebook.models.rule_diagnostic import RuleDiagnostic


class SimulationEngine:
    """Executes dry-run rule evaluation simulation."""

    def simulate(
        self,
        ctx: RuleEvaluationContext,
        results: List[RuleEvaluationResult],
        diagnostics: List[RuleDiagnostic],
        trace: RuleExecutionTrace,
    ) -> SimulationReport:
        t0 = time.time()
        applied_count = sum(1 for r in results if r.status == "APPLIED")
        skipped_count = sum(1 for r in results if r.status == "SKIPPED")
        overridden_count = sum(1 for r in results if r.status == "OVERRIDDEN")

        order = [r.rule_id for r in results if r.status == "APPLIED"]
        t1 = time.time()
        trace.total_trace_duration_ms = (t1 - t0) * 1000.0

        return SimulationReport(
            rules_loaded=len(results),
            rules_applied=applied_count,
            rules_skipped=skipped_count,
            rules_overridden=overridden_count,
            conflicts=[d.to_dict() for d in diagnostics],
            warnings=[d.root_cause for d in diagnostics if d.severity == "WARNING"],
            evaluation_order=order,
            estimated_complexity="LOW" if len(results) < 20 else ("MEDIUM" if len(results) < 100 else "HIGH"),
            execution_trace=trace,
        )
