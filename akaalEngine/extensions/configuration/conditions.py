"""
akaalEngine.extensions.configuration.conditions
===============================================
Evaluates conditional visibility and applicability of configuration fields based on roles, capabilities, and dependencies.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.configuration import ConfigurationCondition, ConfigurationField


class ConditionEvaluator:
    """
    Evaluates whether a ConfigurationField's condition is met given the current evaluation context.
    """

    @classmethod
    def is_field_applicable(
        cls,
        field: ConfigurationField,
        active_role: Optional[str] = None,
        active_capabilities: Optional[Sequence[str]] = None,
        current_values: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        if field.condition is None:
            return True

        cond = field.condition

        # Check role requirement (fail-closed if context missing or mismatch)
        if cond.requires_role:
            if not active_role or not isinstance(active_role, str):
                return False
            if cond.requires_role.strip().upper() != active_role.strip().upper():
                return False

        # Check capability requirement (fail-closed if context missing or mismatch)
        if cond.requires_capability:
            if not active_capabilities:
                return False
            caps_norm = {c.strip().upper() for c in active_capabilities if isinstance(c, str)}
            if cond.requires_capability.strip().upper() not in caps_norm:
                return False

        # Check field dependency value (fail-closed if field missing or mismatch)
        if cond.depends_on_field:
            if not current_values or cond.depends_on_field not in current_values:
                return False
            val = current_values.get(cond.depends_on_field)
            if cond.depends_on_value is not None:
                if val != cond.depends_on_value:
                    return False
            elif not val:
                return False

        return True

    @classmethod
    def evaluate_field_applicability(
        cls,
        field: ConfigurationField,
        config_values: Optional[Mapping[str, Any]] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        """Helper to evaluate condition against current configuration values and evaluation context."""
        if field.condition is None:
            return True
        ctx = context or {}
        role = ctx.get("role") or ctx.get("active_role")
        caps = ctx.get("capabilities") or ctx.get("active_capabilities")
        return cls.is_field_applicable(
            field=field,
            active_role=role,
            active_capabilities=caps,
            current_values=config_values,
        )
