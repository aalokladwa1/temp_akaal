"""
akaalEngine.extensions.models.sanitized
=======================================
Gateway-safe, immutable DTOs for public APIs, CLI, and UI presentation.
Strips internal factory instances, secrets, private filepaths, and stack traces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence


@dataclass(frozen=True)
class SanitizedConfigurationField:
    """Gateway-safe representation of a configuration field."""
    name: str
    field_type: str
    description: str
    is_required: bool
    is_sensitive: bool
    is_secret_ref: bool = False
    default_value: Optional[Any] = None
    allowed_choices: Optional[Sequence[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex_pattern: Optional[str] = None
    conditions: Optional[Sequence[dict[str, Any]]] = None
    ui_group: Optional[str] = None
    display_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "field_type": self.field_type,
            "description": self.description,
            "is_required": self.is_required,
            "is_sensitive": self.is_sensitive,
            "is_secret_ref": self.is_secret_ref,
            "default_value": self.default_value,
            "allowed_choices": list(self.allowed_choices) if self.allowed_choices else None,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "regex_pattern": self.regex_pattern,
            "conditions": list(self.conditions) if self.conditions else None,
            "ui_group": self.ui_group,
            "display_name": self.display_name or self.name,
        }


@dataclass(frozen=True)
class SanitizedConfigurationSchema:
    """Gateway-safe representation of a configuration schema."""
    schema_id: str
    schema_version: str
    fields: Sequence[SanitizedConfigurationField] = field(default_factory=tuple)
    description: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass(frozen=True)
class SanitizedStrategyDescriptor:
    """Gateway-safe descriptor of a strategy contribution."""
    strategy_id: str
    authority_id: str
    provider_id: str
    implementation_version: str
    contract_version_range: str
    description: Optional[str] = None
    capabilities: Sequence[str] = field(default_factory=tuple)
    configuration_schema: Optional[SanitizedConfigurationSchema] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "authority_id": self.authority_id,
            "provider_id": self.provider_id,
            "implementation_version": self.implementation_version,
            "contract_version_range": self.contract_version_range,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "configuration_schema": self.configuration_schema.to_dict() if self.configuration_schema else None,
        }


@dataclass(frozen=True)
class SanitizedProviderDescriptor:
    """Gateway-safe descriptor of a provider contribution and its capabilities."""
    provider_id: str
    vendor_name: str
    display_name: str
    family: str
    version: str
    description: Optional[str] = None
    supported_authorities: Sequence[str] = field(default_factory=tuple)
    strategies: Sequence[SanitizedStrategyDescriptor] = field(default_factory=tuple)
    is_available: bool = True
    lifecycle_state: str = "ACTIVE"
    missing_dependencies: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "vendor_name": self.vendor_name,
            "display_name": self.display_name,
            "family": self.family,
            "version": self.version,
            "description": self.description,
            "supported_authorities": list(self.supported_authorities),
            "strategies": [s.to_dict() for s in self.strategies],
            "is_available": self.is_available,
            "lifecycle_state": self.lifecycle_state,
            "missing_dependencies": list(self.missing_dependencies),
        }


@dataclass(frozen=True)
class SanitizedExtensionDescriptor:
    """Gateway-safe descriptor of an installed extension package."""
    extension_id: str
    version: str
    display_name: str
    origin: str
    trust_tier: str
    isolation_mode: str
    lifecycle_state: str
    engine_version_range: str
    description: Optional[str] = None
    authors: Sequence[str] = field(default_factory=tuple)
    license: Optional[str] = None
    website: Optional[str] = None
    providers: Sequence[SanitizedProviderDescriptor] = field(default_factory=tuple)
    active_handle_count: int = 0
    registry_generation: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "extension_id": self.extension_id,
            "version": self.version,
            "display_name": self.display_name,
            "origin": self.origin,
            "trust_tier": self.trust_tier,
            "isolation_mode": self.isolation_mode,
            "lifecycle_state": self.lifecycle_state,
            "engine_version_range": self.engine_version_range,
            "description": self.description,
            "authors": list(self.authors),
            "license": self.license,
            "website": self.website,
            "providers": [p.to_dict() for p in self.providers],
            "active_handle_count": self.active_handle_count,
            "registry_generation": self.registry_generation,
        }
