"""Abstract Interfaces for Platform 3 Domain Replicators, Services, and Policies."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from akaal.replication.core.models import ReplicationResult, ReplicationPlan


class IDomainReplicator(ABC):
    """Interface implemented by all 6 Domain Replicators."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Name of the replication domain module."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of 25 capability IDs managed by this domain."""
        pass

    @abstractmethod
    async def replicate_domain(self, context: Any) -> ReplicationResult:
        """Execute replication logic for this domain."""
        pass


class IReplicationService(ABC):
    """Interface implemented by infrastructure services."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        pass


class IReplicationPolicy(ABC):
    """Interface implemented by replication policy engine."""

    @property
    @abstractmethod
    def policy_name(self) -> str:
        pass

    @abstractmethod
    def evaluate_replication(self, plan: ReplicationPlan) -> Dict[str, Any]:
        pass
