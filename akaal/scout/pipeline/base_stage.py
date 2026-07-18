"""
Akaal — Base Discovery Stage Interface
======================================
Abstract contract for Scout discovery pipeline stages with explicit dependencies.
"""

from abc import ABC, abstractmethod
from typing import List
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import StageDiagnostics


class BaseDiscoveryStage(ABC):
    """
    Abstract discovery stage interface.
    Each stage has explicit declared dependencies to build a DAG execution pipeline.
    """

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of the discovery stage."""

    @property
    def dependencies(self) -> List[str]:
        """List of stage names that must execute before this stage."""
        return []

    @abstractmethod
    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        """Execute discovery logic on DiscoveryContext."""
