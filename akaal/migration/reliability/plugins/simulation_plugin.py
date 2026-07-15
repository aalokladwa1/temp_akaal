from abc import ABC, abstractmethod
from typing import Dict, Any
from akaal.migration.reliability.context.reliability_context import ReliabilityContext

class BaseSimulationPlugin(ABC):
    """Abstract base class for custom time/cost estimators."""
    @abstractmethod
    def simulate(self, context: ReliabilityContext) -> Dict[str, Any]:
        pass
