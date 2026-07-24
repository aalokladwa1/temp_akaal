"""Interfaces for the AKAAL Enterprise Self-Healing Platform."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from akaal.healing.core.models import HealingResult, HealingPlan


class IHealer(ABC):
    """Base interface for all repair action healers."""

    @property
    @abstractmethod
    def healer_name(self) -> str:
        """Unique healer identifier."""
        pass

    @property
    @abstractmethod
    def capability_id(self) -> str:
        """Capability ID."""
        pass

    @abstractmethod
    async def heal(self, context: Any) -> HealingResult:
        """Execute repair logic using HealingContext."""
        pass


class IDomainHealer(ABC):
    """Interface for domain-driven composite healers."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Name of the healing domain."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of capabilities managed by this domain healer."""
        pass

    @abstractmethod
    async def heal_domain(self, context: Any) -> HealingResult:
        """Execute domain-wide repair logic using HealingContext."""
        pass


class IHealingService(ABC):
    """Marker interface for healing infrastructure services."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the infrastructure service."""
        pass


class IHealingPlugin(ABC):
    """Interface for dynamically loaded enterprise repair plugins."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version string."""
        pass

    @abstractmethod
    def initialize(self, context: Any) -> None:
        """Initialize plugin using HealingContext."""
        pass

    @abstractmethod
    def get_healers(self) -> List[IHealer]:
        """Provide custom healers."""
        pass


class IHealingPolicy(ABC):
    """Interface for enterprise compliance repair policy."""

    @property
    @abstractmethod
    def policy_name(self) -> str:
        """Policy name."""
        pass

    @abstractmethod
    def evaluate_repair(self, plan: HealingPlan) -> Dict[str, Any]:
        """Evaluate policy compliance for repair plan."""
        pass
