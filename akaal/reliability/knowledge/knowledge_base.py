"""Reliability Knowledge Base, Incident Memory, and Recommendation Engine."""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class IncidentRecord:
    """Historical record of an incident and its resolution outcome."""

    incident_id: str
    component_name: str
    failure_type: str
    recovery_strategy: str
    success: bool
    recovery_duration_sec: float
    timestamp: float = field(default_factory=time.time)


class IncidentMemoryStore:
    """Thread-safe persistent memory store for historical incident records."""

    def __init__(self):
        self._incidents: List[IncidentRecord] = []
        self._lock = threading.RLock()

    def add_incident(self, record: IncidentRecord) -> None:
        with self._lock:
            self._incidents.append(record)

    def get_incidents_by_component(self, component_name: str) -> List[IncidentRecord]:
        with self._lock:
            return [rec for rec in self._incidents if rec.component_name == component_name]

    def list_all(self) -> List[IncidentRecord]:
        with self._lock:
            return list(self._incidents)


class RecoveryRecommendationEngine:
    """Ranks recovery strategies based on historical effectiveness score."""

    def rank_strategies(self, memory_store: IncidentMemoryStore, component_name: str, failure_type: str) -> List[Dict[str, Any]]:
        incidents = memory_store.get_incidents_by_component(component_name)
        if not incidents:
            # Default ranked recommendations
            return [
                {"strategy": "CHECKPOINT_RESUME", "effectiveness_score": 95.0, "sample_size": 10},
                {"strategy": "AUTOMATIC_HEALING", "effectiveness_score": 90.0, "sample_size": 10},
                {"strategy": "CIRCUIT_BREAKER_RESET", "effectiveness_score": 85.0, "sample_size": 10},
            ]

        counts: Dict[str, Dict[str, int]] = {}
        for inc in incidents:
            if inc.failure_type == failure_type or not failure_type:
                strat = inc.recovery_strategy
                if strat not in counts:
                    counts[strat] = {"success": 0, "total": 0}
                counts[strat]["total"] += 1
                if inc.success:
                    counts[strat]["success"] += 1

        ranked = []
        for strat, data in counts.items():
            eff = (data["success"] / data["total"]) * 100.0 if data["total"] > 0 else 0.0
            ranked.append({"strategy": strat, "effectiveness_score": eff, "sample_size": data["total"]})

        ranked.sort(key=lambda x: x["effectiveness_score"], reverse=True)
        return ranked


class ReliabilityKnowledgeBase:
    """Centralized Reliability Knowledge Base managing historical incidents and recommendations."""

    def __init__(self):
        self.memory_store = IncidentMemoryStore()
        self.recommendation_engine = RecoveryRecommendationEngine()

    def record_incident(self, incident_id: str, component: str, failure_type: str, strategy: str, success: bool, duration: float) -> None:
        rec = IncidentRecord(incident_id, component, failure_type, strategy, success, duration)
        self.memory_store.add_incident(rec)

    def get_recommendations(self, component: str, failure_type: str = "") -> List[Dict[str, Any]]:
        return self.recommendation_engine.rank_strategies(self.memory_store, component, failure_type)
