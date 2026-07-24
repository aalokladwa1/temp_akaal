"""Abstract Interfaces for Platform 5 Domain Modules and Services."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from akaal.resilience_eng.core.models import ResilienceExperimentResult, ResilienceExperimentPlan


class IDomainResilienceModule(ABC):
    """Interface implemented by all 6 Domain Resilience Modules."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        pass

    @abstractmethod
    async def execute_domain(self, context: Any) -> ResilienceExperimentResult:
        pass


class IResilienceEngService(ABC):
    @property
    @abstractmethod
    def service_name(self) -> str:
        pass
