"""
Akaal — Base Recommendation Analyzer
=====================================
Abstract base class for all independent recommendation analyzers in Advisor Platform.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.advisory_enums import AdvisoryCategory
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation


class RecommendationAnalyzer(ABC):
    """Abstract base analyzer interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique analyzer identifier."""
        pass

    @property
    @abstractmethod
    def category(self) -> AdvisoryCategory:
        """Domain category of recommendations produced by this analyzer."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of analyzer scope."""
        pass

    @abstractmethod
    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        """
        Analyze execution plan and return list of advisory recommendations.
        Must be pure and side-effect free.
        """
        pass
