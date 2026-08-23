"""
akaalEngine.discovery.errors.exceptions
=======================================
Typed exception taxonomy for Authority #3 Discovery.
All exceptions are sanitized, secret-safe, and carry typed diagnostic metadata.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class DiscoveryEngineException(Exception):
    """Base exception for all Authority #3 Discovery errors."""

    def __init__(
        self,
        message: str,
        provider_id: Optional[str] = None,
        schema_name: Optional[str] = None,
        object_name: Optional[str] = None,
        diagnostics: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider_id = provider_id
        self.schema_name = schema_name
        self.object_name = object_name
        self.diagnostics = dict(diagnostics or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "provider_id": self.provider_id,
            "schema_name": self.schema_name,
            "object_name": self.object_name,
            "diagnostics": self.diagnostics,
        }


class PermissionDeniedDiscoveryError(DiscoveryEngineException):
    """Raised when the connected user lacks SELECT or catalog inspection privileges."""
    pass


class EndpointUnreachableDiscoveryError(DiscoveryEngineException):
    """Raised when the physical endpoint or connection session fails during discovery."""
    pass


class ObjectDisappearedDiscoveryError(DiscoveryEngineException):
    """Raised when a table, view, or schema is dropped concurrently during metadata crawl."""
    pass


class DiscoveryTimeoutError(DiscoveryEngineException):
    """Raised when a metadata catalog or sampling query exceeds its allocated timeout budget."""
    pass


class CorruptedCatalogDiscoveryError(DiscoveryEngineException):
    """Raised when the database system catalog returns malformed or inconsistent metadata."""
    pass


class UnsupportedDiscoveryFeatureError(DiscoveryEngineException):
    """Raised when a discovery capability is requested that the provider cannot physically support."""
    pass


class SchemaMutationDuringScanError(DiscoveryEngineException):
    """Raised when material DDL drift is detected during an active discovery execution."""
    pass
