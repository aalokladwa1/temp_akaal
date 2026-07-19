"""
AKAAL Enterprise Intelligence Platform — Base Intelligence Analyzer Interface
=============================================================================
Abstract base class for all Platform 2 strategic intelligence analyzers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel


class BaseIntelligenceAnalyzer(ABC):
    """
    Abstract base class establishing the contract for Platform 2 strategic analyzers.
    Every analyzer must be independent, pure, deterministic, and side-effect free.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the unique name identifier of the analyzer."""
        pass

    @property
    def version(self) -> str:
        """Returns the semantic version of the analyzer."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Returns a brief summary description of the analyzer's responsibility."""
        return "Base strategic intelligence analyzer."

    @property
    def metadata(self) -> Dict[str, Any]:
        """Returns metadata associated with the analyzer."""
        return {"name": self.name, "version": self.version}

    @abstractmethod
    def analyze(
        self,
        advisory_model: MigrationAdvisoryModel,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Executes strategic analysis on an immutable MigrationAdvisoryModel.

        Args:
            advisory_model: Input canonical MigrationAdvisoryModel.
            context: Optional execution parameters.

        Returns:
            An immutable analysis payload (dataclass or dict).
        """
        pass
