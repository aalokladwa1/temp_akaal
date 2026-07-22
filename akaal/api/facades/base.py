"""
Abstract Public Façade Interface Base.
"""

from abc import ABC, abstractmethod
from akaal.api.contracts.dto import CapabilityDTO


class IFacade(ABC):
    """Abstract Base Class for all Platform Façades."""

    @abstractmethod
    async def get_capabilities(self) -> CapabilityDTO:
        """Retrieve capability declaration for target platform."""
        pass
