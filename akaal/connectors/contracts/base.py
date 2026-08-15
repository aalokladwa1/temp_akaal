"""
AKAAL Universal Connector Core Contract (P4.1).
================================================
Defines abstract base contract IUniversalConnector that all enterprise connectors must implement.
Provides lifecycle operations, configuration validation, connection testing, health check,
and error classification without duplicating P0-P3 authorities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, TypeVar
import datetime

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    ConnectorErrorCategory,
    ProofLevel,
)
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.connectors.profile import ConnectionProfile

T = TypeVar("T")


class ConnectionTestResult:
    """Standardized connection test result."""

    def __init__(
        self,
        success: bool,
        message: str,
        latency_ms: float = 0.0,
        discovered_version: Optional[str] = None,
        error_category: Optional[ConnectorErrorCategory] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.success = success
        self.message = message
        self.latency_ms = latency_ms
        self.discovered_version = discovered_version
        self.error_category = error_category
        self.details = details or {}
        self.tested_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "discovered_version": self.discovered_version,
            "error_category": self.error_category.value if hasattr(self.error_category, "value") else str(self.error_category),
            "details": self.details,
            "tested_at": self.tested_at,
        }


class HealthStatus:
    """Standardized connector runtime health status."""

    def __init__(
        self,
        is_healthy: bool,
        status_string: str = "HEALTHY",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.is_healthy = is_healthy
        self.status_string = status_string
        self.details = details or {}
        self.checked_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy": self.is_healthy,
            "status": self.status_string,
            "details": self.details,
            "checked_at": self.checked_at,
        }


class IUniversalConnector(ABC):
    """
    Abstract Universal Connector Contract.
    All system connectors implement this interface or plug into it via adapters.
    """

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Unique vendor/system connector identifier (e.g. 'oracle', 'postgresql', 'snowflake')."""
        pass

    @property
    @abstractmethod
    def family(self) -> ConnectorFamily:
        """Technology family classification."""
        pass

    @property
    @abstractmethod
    def manifest(self) -> UniversalCapabilityManifest:
        """Authoritative capability manifest."""
        pass

    @abstractmethod
    def validate_configuration(self, config: ConnectionProfile) -> Dict[str, Any]:
        """Validates connection profile parameters. Returns dict with 'valid': bool and 'errors': list."""
        pass

    @abstractmethod
    async def connect(self, config: ConnectionProfile) -> None:
        """Establishes connection to endpoint."""
        pass

    @abstractmethod
    async def test_connection(self, config: ConnectionProfile) -> ConnectionTestResult:
        """Tests endpoint connectivity and authentication."""
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Evaluates active connection health."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully closes endpoint connection."""
        pass

    @abstractmethod
    async def reconnect(self) -> None:
        """Re-establishes broken connection."""
        pass

    @abstractmethod
    def classify_error(self, exception: Exception) -> ConnectorErrorCategory:
        """Classifies native exception into canonical ConnectorErrorCategory."""
        pass

    def get_capability_extension(self, extension_cls: Type[T]) -> Optional[T]:
        """
        Returns capability extension instance if supported, else None.
        Enables clean progressive capability querying (e.g. IDatabaseCapability, IStreamingCapability).
        """
        if isinstance(self, extension_cls):
            return self
        return None
