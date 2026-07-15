from abc import ABC, abstractmethod
from typing import List
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

class BaseValidatorPlugin(ABC):
    """Abstract base class for custom validator extensions."""
    @abstractmethod
    def validate(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        pass
