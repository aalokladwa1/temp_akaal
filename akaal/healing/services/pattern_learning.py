"""PatternLearningService: Learns successful repair patterns & knowledge base (Caps 24, 25)."""

from typing import Dict, Any, List, Optional
from akaal.healing.core.interfaces import IHealingService


class PatternLearningService(IHealingService):
    """Infrastructure service learning from successful repairs and persisting repair history."""

    @property
    def service_name(self) -> str:
        return "PatternLearningService"

    def __init__(self):
        self._knowledge_base: Dict[str, Dict[str, Any]] = {}

    def record_pattern(self, issue_type: str, successful_action: str, duration_ms: float) -> None:
        """Record successful repair pattern."""
        if issue_type not in self._knowledge_base:
            self._knowledge_base[issue_type] = {
                "success_count": 0,
                "failure_count": 0,
                "best_action": successful_action,
                "total_duration_ms": 0.0,
            }
        kb = self._knowledge_base[issue_type]
        kb["success_count"] += 1
        kb["total_duration_ms"] += duration_ms

    def get_pattern(self, issue_type: str) -> Optional[Dict[str, Any]]:
        """Query knowledge base for historical pattern."""
        return self._knowledge_base.get(issue_type)
