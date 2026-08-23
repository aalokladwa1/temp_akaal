"""
akaalEngine.extensions.dependencies.python
==========================================
Lazy inspection of Python package dependencies without eager importing.
Uses importlib.util.find_spec and importlib.metadata.version.
"""

from __future__ import annotations

import importlib.util
import importlib.metadata
from typing import Optional, Tuple

from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator
from akaalEngine.extensions.models.dependency import (
    DependencyDiagnostic,
    DependencyStatus,
    DependencyType,
    PythonDependency,
)


class PythonDependencyInspector:
    """
    Inspects Python dependencies lazily and safely without importing the target module.
    """

    @classmethod
    def inspect(cls, dep: PythonDependency) -> DependencyDiagnostic:
        module_name = dep.get_effective_module()
        package_name = dep.name

        # 1. Check module presence using find_spec
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return DependencyDiagnostic(
                    dependency_name=dep.name,
                    dep_type=DependencyType.PYTHON_PACKAGE,
                    status=DependencyStatus.MISSING,
                    is_optional=dep.is_optional,
                    error_message=f"Python module '{module_name}' is not installed.",
                    remediation_hint=dep.remediation_hint or f"Run 'pip install {package_name}'",
                )
        except Exception as exc:
            return DependencyDiagnostic(
                dependency_name=dep.name,
                dep_type=DependencyType.PYTHON_PACKAGE,
                status=DependencyStatus.EVALUATION_ERROR,
                is_optional=dep.is_optional,
                error_message=f"Error inspecting Python module '{module_name}': {exc}",
                remediation_hint=dep.remediation_hint,
            )

        # 2. Check package version if range requirement is specified
        installed_version = None
        try:
            installed_version = importlib.metadata.version(package_name)
        except Exception:
            # Fallback to module name if different from distribution package name
            try:
                if module_name != package_name:
                    installed_version = importlib.metadata.version(module_name)
            except Exception:
                installed_version = None

        if dep.version_range and installed_version:
            comp_res = CompatibilityEvaluator.evaluate(
                target_name=package_name,
                version_str=installed_version,
                required_range=dep.version_range,
            )
            if not comp_res.is_compatible:
                return DependencyDiagnostic(
                    dependency_name=dep.name,
                    dep_type=DependencyType.PYTHON_PACKAGE,
                    status=DependencyStatus.VERSION_MISMATCH,
                    installed_version=installed_version,
                    required_range=dep.version_range,
                    is_optional=dep.is_optional,
                    error_message=comp_res.diagnostic,
                    remediation_hint=dep.remediation_hint or f"Upgrade/downgrade '{package_name}' to match {dep.version_range}",
                )

        return DependencyDiagnostic(
            dependency_name=dep.name,
            dep_type=DependencyType.PYTHON_PACKAGE,
            status=DependencyStatus.SATISFIED,
            installed_version=installed_version,
            required_range=dep.version_range,
            is_optional=dep.is_optional,
        )
