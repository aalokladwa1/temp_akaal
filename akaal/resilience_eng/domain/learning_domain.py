"""LearningDomain Module implementing Capabilities 17-20 (Replay, Maturity, Provenance, Versioning)."""

import time
from typing import List, Dict, Any
from akaal.resilience_eng.core.interfaces import IDomainResilienceModule
from akaal.resilience_eng.core.models import ResilienceExperimentResult, ResilienceEngStatus, ResilienceEngOutcome
from akaal.resilience_eng.replay.replay_engine import ExperimentReplayEngine
from akaal.resilience_eng.maturity.assessment import ResilienceMaturityEngine
from akaal.resilience_eng.provenance.provenance_manager import ExperimentProvenanceManager
from akaal.resilience_eng.versioning.version_manager import ExperimentVersionManager


class LearningDomain(IDomainResilienceModule):
    """Domain module for Capabilities 17-20: Replay, Maturity, Provenance, Versioning."""

    def __init__(self):
        self.replay_engine = ExperimentReplayEngine()
        self.maturity_engine = ResilienceMaturityEngine()
        self.provenance_mgr = ExperimentProvenanceManager()
        self.version_mgr = ExperimentVersionManager()

    @property
    def domain_name(self) -> str:
        return "LearningDomain"

    @property
    def capabilities(self) -> List[str]:
        return [
            "Cap 17: Experiment Replay Engine",
            "Cap 18: Resilience Maturity Engine",
            "Cap 19: Experiment Provenance System",
            "Cap 20: Experiment Version Control",
        ]

    async def execute_domain(self, context: Any) -> ResilienceExperimentResult:
        start = time.time()
        details = []
        exp_id = "exp_learning_01"

        # Replay Engine
        replay_res = self.replay_engine.replay_experiment(exp_id, [{"event": "fault_inject"}, {"event": "recovery"}])
        details.append({"cap": "Cap 17", "is_reproducible": replay_res["is_reproducible"], "replayed_events": replay_res["original_vs_replay"]["replayed_events_count"], "status": "REPLAYED"})

        # Maturity Engine
        maturity = self.maturity_engine.evaluate_maturity()
        details.append({"cap": "Cap 18", "maturity_level": maturity.overall_maturity_level, "reliability_score": maturity.reliability_score, "status": "ASSESSED"})

        # Provenance
        record = self.provenance_mgr.record_provenance(exp_id, "Chaos_Test_Regional_Outage", "1.0.0")
        details.append({"cap": "Cap 19", "record_id": record.record_id, "experiment_id": record.experiment_id, "status": "RECORDED"})

        # Versioning
        ver = self.version_mgr.create_version(exp_id, "1.0.0", "Initial release", {"scenario": "Regional_Outage"})
        details.append({"cap": "Cap 20", "version": ver.version, "experiment_id": ver.experiment_id, "status": "VERSIONED"})

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
