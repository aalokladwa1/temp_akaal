from abc import ABC, abstractmethod
from typing import List
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

class BaseCertificationPlugin(ABC):
    """Abstract base class for custom compliance/certification rules."""
    @abstractmethod
    def certify(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        pass
