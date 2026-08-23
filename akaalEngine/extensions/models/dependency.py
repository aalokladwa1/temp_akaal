"""
akaalEngine.extensions.models.dependency
========================================
Immutable dependency specification models and typed diagnostic records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.enums import (
    DependencyMatchMode,
    DependencyStatus,
    DependencyType,
)


@dataclass(frozen=True)
class DependencyRequirement:
    """Base requirement definition for external packages, libraries, or executables."""
    name: str
    dep_type: DependencyType
    version_range: Optional[str] = None
    is_optional: bool = False
    feature_gate: Optional[str] = None
    remediation_hint: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("DependencyRequirement name must be a non-empty string.")
        object.__setattr__(self, "name", self.name.strip())


@dataclass(frozen=True)
class PythonDependency(DependencyRequirement):
    """Python package requirement (e.g. 'psycopg2', 'pymongo', 'snowflake-connector-python')."""
    import_module: Optional[str] = None
    dep_type: DependencyType = field(default=DependencyType.PYTHON_PACKAGE, init=False)

    def get_effective_module(self) -> str:
        return self.import_module or self.name


@dataclass(frozen=True)
class NativeDependency(DependencyRequirement):
    """Native OS shared library requirement (e.g. 'libpq.so', 'libaio.so.1', 'oci.dll')."""
    library_names: Sequence[str] = field(default_factory=tuple)
    dep_type: DependencyType = field(default=DependencyType.NATIVE_LIBRARY, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "library_names", tuple(self.library_names) if self.library_names else ())


@dataclass(frozen=True)
class ExecutableDependency(DependencyRequirement):
    """External CLI executable requirement (e.g. 'bcp', 'sqlldr', 'mysqldump')."""
    executable_name: Optional[str] = None
    dep_type: DependencyType = field(default=DependencyType.EXECUTABLE, init=False)

    def get_effective_executable(self) -> str:
        return self.executable_name or self.name


@dataclass(frozen=True)
class DependencyGroup(DependencyRequirement):
    """Group of dependencies evaluated with ALL_OF or ANY_OF operator."""
    dependencies: Sequence[DependencyRequirement] = field(default_factory=tuple)
    match_mode: DependencyMatchMode = DependencyMatchMode.ALL_OF
    dep_type: DependencyType = field(default=DependencyType.DEPENDENCY_GROUP, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "dependencies", tuple(self.dependencies) if self.dependencies else ())


@dataclass(frozen=True)
class DependencyDiagnostic:
    """Detailed diagnostic report for a single dependency inspection."""
    dependency_name: str
    dep_type: DependencyType
    status: DependencyStatus
    installed_version: Optional[str] = None
    required_range: Optional[str] = None
    is_optional: bool = False
    error_message: Optional[str] = None
    remediation_hint: Optional[str] = None

    @property
    def is_satisfied(self) -> bool:
        return self.status == DependencyStatus.SATISFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.dependency_name,
            "type": self.dep_type.value,
            "status": self.status.value,
            "installed_version": self.installed_version,
            "required_range": self.required_range,
            "is_optional": self.is_optional,
            "is_satisfied": self.is_satisfied,
            "error_message": self.error_message,
            "remediation_hint": self.remediation_hint,
        }
