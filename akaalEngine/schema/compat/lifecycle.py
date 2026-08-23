"""
akaalEngine.schema.compat.lifecycle
===================================
Tracks compatibility pack requirements, requesting objects, and installation scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Set, Tuple

from akaalEngine.schema.compat.pack_definitions import (
    CompatibilityFunctionDef,
    CompatibilityPackDefinitions,
)


@dataclass(frozen=True)
class CompatibilityRequirement:
    """A requirement for an emulation function requested by a specific object."""
    helper_name: str
    requesting_object: str
    target_engine: str = "POSTGRESQL"
    risk_level: str = "LOW"
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True)
class CompatibilityPackReport:
    """Summary of all required emulation helpers and their installation script."""
    required_helpers: Tuple[str, ...]
    install_script_sql: str
    requirements: Tuple[CompatibilityRequirement, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.required_helpers, tuple):
            object.__setattr__(self, "required_helpers", tuple(self.required_helpers))
        if not isinstance(self.requirements, tuple):
            object.__setattr__(self, "requirements", tuple(self.requirements))

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_helpers": list(self.required_helpers),
            "install_script_sql": self.install_script_sql,
            "total_helpers": len(self.required_helpers),
        }


class CompatibilityRequirementTracker:
    """Tracks and builds compatibility requirements across a compilation cycle."""

    def __init__(self):
        self._requirements: List[CompatibilityRequirement] = []

    def record_requirement(self, helper_name: str, requesting_object: str, target_engine: str = "POSTGRESQL") -> None:
        self._requirements.append(
            CompatibilityRequirement(
                helper_name=helper_name.lower(),
                requesting_object=requesting_object,
                target_engine=target_engine,
            )
        )

    def build_report(self) -> CompatibilityPackReport:
        unique_helpers: Set[str] = {r.helper_name for r in self._requirements}
        script_parts: List[str] = []

        if unique_helpers:
            script_parts.append("CREATE SCHEMA IF NOT EXISTS akaal_compat;")
            script_parts.append("CREATE SCHEMA IF NOT EXISTS akaal_compat_dbms_output;\n")

            for h in sorted(unique_helpers):
                defn = CompatibilityPackDefinitions.get_function(h)
                if defn:
                    script_parts.append(defn.definition_sql)
                    script_parts.append("")

        return CompatibilityPackReport(
            required_helpers=tuple(sorted(unique_helpers)),
            install_script_sql="\n".join(script_parts),
            requirements=tuple(self._requirements),
        )
