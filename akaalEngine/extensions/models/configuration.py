"""
akaalEngine.extensions.models.configuration
===========================================
Models for declarative configuration schemas, typed fields, constraints, and conditions.
Extensions DESCRIBES configuration structure without persisting secrets or credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.enums import ConfigurationFieldType


@dataclass(frozen=True)
class ConfigurationConstraint:
    """Validation constraint on a configuration field."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex_pattern: Optional[str] = None
    allowed_values: Optional[Sequence[Any]] = None

    def __post_init__(self) -> None:
        if self.allowed_values is not None:
            object.__setattr__(self, "allowed_values", tuple(self.allowed_values))

    def validate_value(self, value: Any, field_name: str) -> None:
        """Validates a value against configured constraints, raising ValueError on failure."""
        if value is None:
            return
        if self.min_value is not None and (isinstance(value, (int, float)) and value < self.min_value):
            raise ValueError(f"Field '{field_name}' value {value} is less than minimum {self.min_value}.")
        if self.max_value is not None and (isinstance(value, (int, float)) and value > self.max_value):
            raise ValueError(f"Field '{field_name}' value {value} is greater than maximum {self.max_value}.")
        if self.min_length is not None and len(str(value)) < self.min_length:
            raise ValueError(f"Field '{field_name}' length {len(str(value))} is less than minimum {self.min_length}.")
        if self.max_length is not None and len(str(value)) > self.max_length:
            raise ValueError(f"Field '{field_name}' length {len(str(value))} exceeds maximum {self.max_length}.")
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ValueError(f"Field '{field_name}' value '{value}' is not in allowed choices {self.allowed_values}.")
        if self.regex_pattern is not None:
            import re
            if not re.match(self.regex_pattern, str(value)):
                raise ValueError(f"Field '{field_name}' value does not match required pattern.")


@dataclass(frozen=True)
class ConfigurationCondition:
    """Condition determining when a field is applicable based on role or required capability."""
    requires_capability: Optional[str] = None
    requires_role: Optional[str] = None
    depends_on_field: Optional[str] = None
    depends_on_value: Optional[Any] = None

    @classmethod
    def when_field_equals(cls, field_name: str, value: Any) -> ConfigurationCondition:
        """Helper to create condition based on field value match."""
        return cls(depends_on_field=field_name, depends_on_value=value)


@dataclass(frozen=True)
class ConfigurationField:
    """Declarative specification of a single provider or strategy configuration parameter."""
    name: str
    field_type: ConfigurationFieldType
    description: str
    is_required: bool = False
    default_value: Optional[Any] = None
    is_sensitive: bool = False
    constraint: Optional[ConfigurationConstraint] = None
    condition: Optional[ConfigurationCondition] = None
    ui_group: Optional[str] = None
    display_name: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("ConfigurationField name must be a non-empty string.")
        # If field type is SECRET_REF, ensure it is marked sensitive
        if self.field_type == ConfigurationFieldType.SECRET_REF:
            object.__setattr__(self, "is_sensitive", True)


@dataclass(frozen=True)
class ConfigurationSchema:
    """Schema descriptor containing all configuration fields for a provider or strategy."""
    schema_id: str
    schema_version: str = "1.0.0"
    fields: Sequence[ConfigurationField] = field(default_factory=tuple)
    description: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", tuple(self.fields) if self.fields else ())

    def get_field(self, name: str) -> Optional[ConfigurationField]:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def get_required_fields(self) -> Sequence[ConfigurationField]:
        return tuple(f for f in self.fields if f.is_required)
