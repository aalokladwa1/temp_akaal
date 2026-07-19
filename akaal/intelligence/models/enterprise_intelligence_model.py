"""
AKAAL Enterprise Intelligence Platform — Canonical Model
=========================================================
The top-level canonical, immutable, versioned, checksum-protected output artifact
of Platform 2 (Enterprise Intelligence Subsystem).
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple

from akaal.intelligence.models.agent_coordination_plan import AgentCoordinationPlan
from akaal.intelligence.models.enterprise_decision import EnterpriseDecision
from akaal.intelligence.models.enterprise_intelligence_manifest import EnterpriseIntelligenceManifest
from akaal.intelligence.models.enterprise_intelligence_trace import EnterpriseIntelligenceTrace
from akaal.intelligence.models.enterprise_intelligence_version import EnterpriseIntelligenceVersionInfo
from akaal.intelligence.models.migration_simulation_result import MigrationSimulationResult
from akaal.intelligence.models.readiness_assessment import ReadinessAssessment
from akaal.intelligence.models.strategy_synthesis import StrategySynthesis


@dataclass(frozen=True)
class EnterpriseIntelligenceModel:
    """
    Canonical, immutable enterprise intelligence document output by Platform 2.
    """

    model_id: str
    advisory_model_id: str
    version_info: EnterpriseIntelligenceVersionInfo
    manifest: EnterpriseIntelligenceManifest
    decisions: Tuple[EnterpriseDecision, ...]
    strategy: StrategySynthesis
    simulation: MigrationSimulationResult
    readiness: ReadinessAssessment
    agent_coordination: AgentCoordinationPlan
    trace: EnterpriseIntelligenceTrace
    checksum: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.decisions, tuple):
            object.__setattr__(self, "decisions", tuple(self.decisions))

        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "model_id": self.model_id,
            "advisory_model_id": self.advisory_model_id,
            "version_info": self.version_info.to_dict(),
            "manifest": self.manifest.to_dict(),
            "decisions": [d.to_dict() for d in self.decisions],
            "strategy": self.strategy.to_dict(),
            "simulation": self.simulation.to_dict(),
            "readiness": self.readiness.to_dict(),
            "agent_coordination": self.agent_coordination.to_dict(),
            "trace": self.trace.to_dict(),
            "checksum": self.checksum,
            "metadata": dict(self.metadata),
        }
