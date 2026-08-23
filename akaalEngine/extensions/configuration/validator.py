"""
akaalEngine.extensions.configuration.validator
=============================================
Validates configuration options against declarative ConfigurationSchema definitions.
Ensures typed validation, constraint enforcement, and strict secret-reference policy.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.errors.taxonomy import ConfigurationValidationError
from akaalEngine.extensions.models.configuration import (
    ConfigurationField,
    ConfigurationFieldType,
    ConfigurationSchema,
)


class ConfigurationValidator:
    """
    Validates user or pipeline configuration dictionaries against a target ConfigurationSchema.
    """

    @classmethod
    def validate_type(cls, value: Any, field_def: ConfigurationField) -> None:
        """Validates that value conforms to the field's declared data type."""
        if value is None:
            return

        ftype = field_def.field_type
        fname = field_def.name

        if ftype == ConfigurationFieldType.STRING:
            if not isinstance(value, str):
                raise ConfigurationValidationError(
                    f"Field '{fname}' must be a string, got {type(value).__name__}."
                )

        elif ftype == ConfigurationFieldType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ConfigurationValidationError(
                    f"Field '{fname}' must be an integer, got {type(value).__name__}."
                )

        elif ftype == ConfigurationFieldType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ConfigurationValidationError(
                    f"Field '{fname}' must be a numeric float, got {type(value).__name__}."
                )

        elif ftype == ConfigurationFieldType.BOOLEAN:
            if not isinstance(value, bool):
                raise ConfigurationValidationError(
                    f"Field '{fname}' must be a boolean, got {type(value).__name__}."
                )

        elif ftype == ConfigurationFieldType.LIST:
            if not isinstance(value, (list, tuple)):
                raise ConfigurationValidationError(
                    f"Field '{fname}' must be a list/tuple, got {type(value).__name__}."
                )

        elif ftype == ConfigurationFieldType.OBJECT:
            if not isinstance(value, (dict, Mapping)):
                raise ConfigurationValidationError(
                    f"Field '{fname}' must be a dictionary/object, got {type(value).__name__}."
                )

        elif ftype == ConfigurationFieldType.SECRET_REF:
            # Secret references must be string pointers (e.g. 'vault://path', 'env:VAR', 'ref:secret_1', 'secret://key')
            if not isinstance(value, str):
                raise ConfigurationValidationError(
                    f"Secret reference field '{fname}' must be a string identifier/reference pointer URI, got {type(value).__name__}."
                )
            # Fails closed if caller appears to pass raw multiline key or explicit secret dump
            if "\n" in value or len(value) > 1024:
                raise ConfigurationValidationError(
                    f"Field '{fname}' is configured as a SECRET_REF but appears to contain raw multiline secret material."
                )
            # Must match a recognized pointer URI format (scheme://... or scheme:...)
            # Reject bare arbitrary plaintext strings without pointer scheme
            is_valid_pointer = bool(
                re.match(r"^[a-zA-Z0-9_\-]+://.+$", value)
                or re.match(r"^(env|ref|secret|vault|k8s|aws-sm|azure-kv|gcp-sm):[a-zA-Z0-9_\-./]+$", value)
            )
            if not is_valid_pointer:
                raise ConfigurationValidationError(
                    f"Field '{fname}' is configured as a SECRET_REF and requires a valid secret pointer reference URI "
                    f"(e.g. 'vault://path', 'env:VAR_NAME', 'ref:secret_id', 'secret://name')."
                )

    @classmethod
    def validate(
        cls,
        schema: ConfigurationSchema,
        config_values: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
        strict_unknown: bool = False,
    ) -> None:
        """
        Validates all configuration options against the schema and active conditions.
        Raises ConfigurationValidationError on any violation.
        """
        if not isinstance(config_values, (dict, Mapping)):
            raise ConfigurationValidationError(f"Configuration values must be a dictionary, got {type(config_values).__name__}.")

        schema_fields = {f.name: f for f in schema.fields}

        # Check for unknown fields if strict mode enabled
        if strict_unknown:
            for k in config_values.keys():
                if k not in schema_fields:
                    raise ConfigurationValidationError(
                        f"Unknown configuration property '{k}' for schema '{schema.schema_id}'."
                    )

        from akaalEngine.extensions.configuration.conditions import ConditionEvaluator

        # Validate each schema field
        for field_def in schema.fields:
            # Evaluate conditional applicability
            is_applicable = ConditionEvaluator.evaluate_field_applicability(
                field=field_def,
                config_values=config_values,
                context=context,
            )

            val = config_values.get(field_def.name)

            # If field is inapplicable, do not enforce required
            if not is_applicable:
                if strict_unknown and val is not None:
                    raise ConfigurationValidationError(
                        f"Field '{field_def.name}' is inactive/inapplicable under current configuration conditions for schema '{schema.schema_id}'."
                    )
                continue

            # Check required when applicable
            if field_def.is_required and (val is None or (isinstance(val, str) and not val.strip())):
                if field_def.default_value is None:
                    raise ConfigurationValidationError(
                        f"Required configuration field '{field_def.name}' is missing for schema '{schema.schema_id}'."
                    )

            if val is not None:
                # Validate type
                cls.validate_type(val, field_def)

                # Validate constraints
                if field_def.constraint:
                    try:
                        field_def.constraint.validate_value(val, field_def.name)
                    except ValueError as exc:
                        raise ConfigurationValidationError(str(exc))


default_configuration_validator = ConfigurationValidator()
