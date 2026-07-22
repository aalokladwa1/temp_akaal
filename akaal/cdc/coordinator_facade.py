"""
CoordinatorFacade Public Facade for Platform 4 Enterprise CDC.
"""

from akaal.cdc.api.client import CDCClient
from akaal.cdc.coordinator.coordinator import CDCCoordinator

CoordinatorFacade = CDCClient

__all__ = ["CoordinatorFacade", "CDCClient", "CDCCoordinator"]
