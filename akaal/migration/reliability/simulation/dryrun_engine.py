import time
from typing import List
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.simulation_report import SimulationReport
from akaal.migration.reliability.artifacts.simulation_artifact import SimulationArtifact
from akaal.migration.reliability.simulation.estimators import TimeEstimator, StorageEstimator, CostEstimator
from akaal.migration.reliability.plugins.registry import PluginRegistry
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment

class DryRunSimulationEngine(BaseReliabilityEngine):
    """
    DryRunSimulationEngine simulates plan execution offline, compiling timing metrics,
    storage expansions, dollar costs, and risk assessments.
    """
    def __init__(self) -> None:
        super().__init__(name="simulation")
        self.time_est = TimeEstimator()
        self.storage_est = StorageEstimator()
        self.cost_est = CostEstimator()

    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> SimulationReport:
        plan = context.migration_plan

        # Estimate parameters
        total_time = self.time_est.estimate_time(plan)
        total_storage = self.storage_est.estimate_storage(plan)
        total_cost = self.cost_est.estimate_cost(plan)

        # Plugins adjustments
        for plugin in PluginRegistry.get_simulations():
            plug_res = plugin.simulate(context)
            total_time += plug_res.get("time_ms", 0.0)
            total_storage += plug_res.get("storage_bytes", 0)
            total_cost += plug_res.get("cost", 0.0)

        # Risk assessment
        risk_assessment = calculate_risk_assessment(diagnostics)

        # Build report audit metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_sim"
        )

        # Artifact construction (machine-consumable)
        artifact = SimulationArtifact(
            execution_id=report_meta.execution_id,
            time_ms=total_time,
            bytes_used=total_storage,
            cost=total_cost
        )

        return SimulationReport(
            metadata=report_meta,
            estimated_time_ms=total_time,
            estimated_storage_bytes=total_storage,
            estimated_cost=total_cost,
            risk=risk_assessment
        )
