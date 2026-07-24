"""ExperimentDomain Module implementing Capabilities 11-13 (Isolation, Approval, Digital Twin)."""

import time
from typing import List, Dict, Any
from akaal.resilience_eng.core.interfaces import IDomainResilienceModule
from akaal.resilience_eng.core.models import ResilienceExperimentResult, ResilienceEngStatus, ResilienceEngOutcome
from akaal.resilience_eng.isolation.experiment_context import ExperimentIsolationContext
from akaal.resilience_eng.approval.workflow import ApprovalWorkflowEngine
from akaal.resilience_eng.digital_twin.fidelity import DigitalTwinEngine


class ExperimentDomain(IDomainResilienceModule):
    """Domain module for Capabilities 11-13: Isolation, Approval Workflow, Digital Twin."""

    def __init__(self):
        self.approval_engine = ApprovalWorkflowEngine()
        self.twin_engine = DigitalTwinEngine()

    @property
    def domain_name(self) -> str:
        return "ExperimentDomain"

    @property
    def capabilities(self) -> List[str]:
        return [
            "Cap 11: Experiment Isolation Layer",
            "Cap 12: Enterprise Approval Workflow",
            "Cap 13: Digital Twin Fidelity Simulation",
        ]

    async def execute_domain(self, context: Any) -> ResilienceExperimentResult:
        start = time.time()
        exp_id = "exp_domain_01"
        details = []

        # Isolation Context
        iso_ctx = ExperimentIsolationContext()
        with iso_ctx:
            details.append({"cap": "Cap 11", "sandbox_id": iso_ctx.sandbox.sandbox_id, "status": "ISOLATED"})

        # Approval Workflow
        appr = self.approval_engine.submit_and_approve(exp_id)
        details.append({"cap": "Cap 12", "approval_id": appr.approval_id, "status": appr.status})

        # Digital Twin Simulation
        twin_result = self.twin_engine.simulate_experiment_preflight(exp_id)
        details.append({"cap": "Cap 13", "simulation_passed": twin_result["simulation_passed"], "fidelity_score": twin_result["fidelity_assessment"]["fidelity_score"]})

        duration = (time.time() - start) * 1000.0
        return ResilienceExperimentResult(
            domain_name=self.domain_name,
            capabilities_executed=self.capabilities,
            status=ResilienceEngStatus.COMPLETED,
            outcome=ResilienceEngOutcome.VALIDATED,
            total_actions=len(details),
            successful_actions=len(details),
            execution_time_ms=duration,
            action_details=details,
        )
