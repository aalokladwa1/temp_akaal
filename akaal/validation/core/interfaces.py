"""Interfaces and contracts for the AKAAL Enterprise Validation Platform."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from akaal.validation.core.models import ValidationResult, ValidationIssue


class IValidator(ABC):
    """Base interface for all validators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for the validator."""
        pass

    @property
    @abstractmethod
    def capability_id(self) -> str:
        """Capability ID (e.g., Cap 1, Cap 2)."""
        pass

    @abstractmethod
    async def validate(self, context: Any) -> ValidationResult:
        """Execute validation logic using the shared ValidationContext."""
        pass


class IDomainValidator(ABC):
    """Interface for domain-driven composite validators managing capability subsets."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Name of the validation domain."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of capabilities managed by this domain validator."""
        pass

    @abstractmethod
    async def validate_domain(self, context: Any) -> ValidationResult:
        """Execute domain-wide validation logic using the shared ValidationContext."""
        pass


class IService(ABC):
    """Marker interface for infrastructure services."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the infrastructure service."""
        pass


class IPlugin(ABC):
    """Interface for dynamically loaded enterprise validation plugins."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Unique plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the plugin."""
        pass

    @abstractmethod
    def initialize(self, context: Any) -> None:
        """Initialize plugin resources using ValidationContext."""
        pass

    @abstractmethod
    def get_validators(self) -> List[IValidator]:
        """Provide custom validators exposed by this plugin."""
        pass


class IPolicy(ABC):
    """Interface for enterprise compliance and rule policies."""

    @property
    @abstractmethod
    def policy_name(self) -> str:
        """Name of the validation policy."""
        pass

    @abstractmethod
    def evaluate(self, result: ValidationResult) -> Dict[str, Any]:
        """Evaluate policy compliance against validation results."""
        pass


class ICache(ABC):
    """Interface for Enterprise Validation Cache."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached validation artifact by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store validation artifact in cache."""
        pass

    @abstractmethod
    def invalidate(self, key_pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        pass


class IEventPublisher(ABC):
    """Interface for publishing events to the internal EventBus."""

    @abstractmethod
    async def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Publish an event to subscribers."""
        pass
