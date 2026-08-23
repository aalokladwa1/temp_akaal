"""
akaalEngine.extensions.dependencies.native
==========================================
Inspection of native OS libraries and CLI executables.
"""

from __future__ import annotations

import ctypes.util
import os
import shutil
from typing import Optional

from akaalEngine.extensions.models.dependency import (
    DependencyDiagnostic,
    DependencyStatus,
    DependencyType,
    ExecutableDependency,
    NativeDependency,
)


class NativeDependencyInspector:
    """
    Inspects native OS libraries and executable presence safely.
    """

    @classmethod
    def inspect_native_library(cls, dep: NativeDependency) -> DependencyDiagnostic:
        found_lib = None
        for candidate in dep.library_names:
            try:
                res = ctypes.util.find_library(candidate)
                if res is not None:
                    found_lib = res
                    break
            except Exception:
                pass

        if found_lib is None:
            return DependencyDiagnostic(
                dependency_name=dep.name,
                dep_type=DependencyType.NATIVE_LIBRARY,
                status=DependencyStatus.MISSING,
                is_optional=dep.is_optional,
                error_message=f"Native OS library '{dep.name}' (tried {dep.library_names}) was not found in system library path.",
                remediation_hint=dep.remediation_hint or "Install native OS database client libraries (e.g. libpq, Oracle Instant Client).",
            )

        return DependencyDiagnostic(
            dependency_name=dep.name,
            dep_type=DependencyType.NATIVE_LIBRARY,
            status=DependencyStatus.SATISFIED,
            installed_version=found_lib,
            is_optional=dep.is_optional,
        )

    @classmethod
    def inspect_executable(cls, dep: ExecutableDependency) -> DependencyDiagnostic:
        exe_name = dep.get_effective_executable()
        exe_path = shutil.which(exe_name)

        if exe_path is None:
            return DependencyDiagnostic(
                dependency_name=dep.name,
                dep_type=DependencyType.EXECUTABLE,
                status=DependencyStatus.MISSING,
                is_optional=dep.is_optional,
                error_message=f"CLI executable '{exe_name}' was not found in system PATH.",
                remediation_hint=dep.remediation_hint or f"Ensure '{exe_name}' is installed and present in system PATH.",
            )

        return DependencyDiagnostic(
            dependency_name=dep.name,
            dep_type=DependencyType.EXECUTABLE,
            status=DependencyStatus.SATISFIED,
            installed_version=exe_path,
            is_optional=dep.is_optional,
        )
