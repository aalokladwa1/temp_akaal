from abc import ABC, abstractmethod
from akaal.core.conversion.api.aoir import AOIRNode

class BaseRoutineRenderer(ABC):
    def __init__(self, aoir: AOIRNode) -> None:
        self.aoir = aoir

    @abstractmethod
    def render(self) -> str:
        """Render versioned AOIR node to target SQL dialect."""
        pass
