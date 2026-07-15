"""
Akaal — Recommendation Engine Subsystem
"""

import abc
from akaal.core.comparison.models import Schema
from akaal.core.intelligence.common.models import RecommendationReport

class IRecommendationAdvisor(abc.ABC):
    """Abstract interface defining the advisory suggestion and ranking engine."""
    @abc.abstractmethod
    def generate_recommendations(self, schema: Schema) -> RecommendationReport:
        pass
