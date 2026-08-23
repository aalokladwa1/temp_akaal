"""
akaalEngine.extensions.configuration.sanitizer
=============================================
Transforms internal ConfigurationSchema instances into Gateway-safe sanitized descriptors.
Ensures sensitive defaults and internal objects are never exposed to public APIs or UI.
"""

from __future__ import annotations

from typing import Sequence

from akaalEngine.extensions.models.configuration import (
    ConfigurationField,
    ConfigurationFieldType,
    ConfigurationSchema,
)
from akaalEngine.extensions.models.sanitized import (
    SanitizedConfigurationField,
    SanitizedConfigurationSchema,
)


class ConfigurationSanitizer:
    """
    Sanitizes configuration schemas into Gateway-safe DTOs.
    Guarantees sensitive default values are completely removed/redacted from sanitized DTO objects.
    """

    @classmethod
    def sanitize_field(cls, field_def: ConfigurationField) -> SanitizedConfigurationField:
        is_secret_ref = field_def.field_type == ConfigurationFieldType.SECRET_REF
        is_sensitive = field_def.is_sensitive or is_secret_ref

        # Sensitive defaults must NEVER be stored inside the sanitized DTO instance
        safe_default = None
        if not is_sensitive:
            safe_default = field_def.default_value
        elif field_def.default_value is not None:
            safe_default = "<REDACTED>"

        allowed = None
        min_v = None
        max_v = None
        min_l = None
        max_l = None
        regex_p = None
        if field_def.constraint:
            if field_def.constraint.allowed_values:
                allowed = tuple(field_def.constraint.allowed_values)
            min_v = field_def.constraint.min_value
            max_v = field_def.constraint.max_value
            min_l = field_def.constraint.min_length
            max_l = field_def.constraint.max_length
            regex_p = field_def.constraint.regex_pattern

        cond_list = None
        if field_def.condition:
            role_val = (
                field_def.condition.requires_role.value
                if hasattr(field_def.condition.requires_role, "value")
                else field_def.condition.requires_role
            )
            cond_list = (
                {
                    "requires_capability": field_def.condition.requires_capability,
                    "requires_role": role_val,
                    "depends_on_field": field_def.condition.depends_on_field,
                    "depends_on_value": field_def.condition.depends_on_value,
                },
            )

        return SanitizedConfigurationField(
            name=field_def.name,
            field_type=field_def.field_type.value,
            description=field_def.description,
            is_required=field_def.is_required,
            is_sensitive=is_sensitive,
            is_secret_ref=is_secret_ref,
            default_value=safe_default,
            allowed_choices=allowed,
            min_value=min_v,
            max_value=max_v,
            min_length=min_l,
            max_length=max_l,
            regex_pattern=regex_p,
            conditions=cond_list,
            ui_group=field_def.ui_group,
            display_name=field_def.display_name,
        )

    @classmethod
    def sanitize_schema(cls, schema: ConfigurationSchema) -> SanitizedConfigurationSchema:
        sanitized_fields = tuple(cls.sanitize_field(f) for f in schema.fields)
        return SanitizedConfigurationSchema(
            schema_id=schema.schema_id,
            schema_version=schema.schema_version,
            description=schema.description,
            fields=sanitized_fields,
        )


default_configuration_sanitizer = ConfigurationSanitizer()
