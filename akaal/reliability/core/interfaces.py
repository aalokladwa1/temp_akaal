"""Abstract Interfaces for Platform 4 Domain Modules, Services, and Policies."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from akaal.reliability.core.models import ReliabilityResult, ReliabilityPlan


class IDomainReliabilityModule(ABC):
    """Interface implemented by all 6 Domain Reliability Modules."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Name of the reliability domain module."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of capability IDs managed by this domain."""
        pass

    @abstractmethod
    async def execute_domain(self, context: Any) -> ReliabilityResult:
        """Execute domain-driven reliability logic."""
        pass


class IReliabilityService(ABC):
    """Interface implemented by infrastructure services."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        pass


class IReliabilityPolicy(ABC):
    """Interface implemented by reliability policy engine."""

    @property
    @abstractmethod
    def policy_name(self) -> str:
        pass

    @abstractmethod
    def evaluate_reliability(self, plan: Optional[ReliabilityPlan] = None) -> Dict[str, Any]:
        pass
