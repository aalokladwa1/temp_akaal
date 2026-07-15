from abc import ABC, abstractmethod
from typing import List
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

class BaseHealthPlugin(ABC):
    """Abstract base class for custom pre-migration health precheck rules."""
    @abstractmethod
    def check_health(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        pass
