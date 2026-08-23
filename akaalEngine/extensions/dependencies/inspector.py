"""
akaalEngine.extensions.dependencies.inspector
=============================================
Unified dependency inspector coordinating Python, native, and executable checks lazily.
Ensures failure in one provider dependency does NOT disrupt unrelated providers.
"""

from __future__ import annotations

from typing import Sequence

from akaalEngine.extensions.dependencies.diagnostics import DependencyDiagnosticReport
from akaalEngine.extensions.dependencies.native import NativeDependencyInspector
from akaalEngine.extensions.dependencies.python import PythonDependencyInspector
from akaalEngine.extensions.models.dependency import (
    DependencyDiagnostic,
    DependencyGroup,
    DependencyRequirement,
    DependencyStatus,
    DependencyType,
    ExecutableDependency,
    NativeDependency,
    PythonDependency,
)
from akaalEngine.extensions.models.enums import DependencyMatchMode


class DependencyInspector:
    """
    Evaluates a collection of dependency requirements returning structured diagnostics.
    Supports individual Python/Native/Executable requirements and composite ANY_OF/ALL_OF DependencyGroups.
    """

    @classmethod
    def inspect_requirement(cls, req: DependencyRequirement) -> DependencyDiagnostic:
        """Inspects a single dependency requirement or composite dependency group."""
        if isinstance(req, DependencyGroup) or req.dep_type == DependencyType.DEPENDENCY_GROUP:
            group: DependencyGroup = req  # type: ignore
            sub_diagnostics = [cls.inspect_requirement(sub) for sub in group.dependencies]
            if group.match_mode == DependencyMatchMode.ANY_OF:
                # If at least one sub-requirement is satisfied, group is satisfied!
                satisfied_sub = next((d for d in sub_diagnostics if d.is_satisfied), None)
                if satisfied_sub is not None:
                    return DependencyDiagnostic(
                        dependency_name=group.name,
                        dep_type=DependencyType.DEPENDENCY_GROUP,
                        status=DependencyStatus.SATISFIED,
                        installed_version=satisfied_sub.installed_version,
                        is_optional=group.is_optional,
                        remediation_hint=group.remediation_hint or satisfied_sub.remediation_hint,
                    )
                else:
                    remediation = group.remediation_hint or " | ".join(
                        d.remediation_hint for d in sub_diagnostics if d.remediation_hint
                    )
                    return DependencyDiagnostic(
                        dependency_name=group.name,
                        dep_type=DependencyType.DEPENDENCY_GROUP,
                        status=DependencyStatus.MISSING,
                        is_optional=group.is_optional,
                        error_message=f"None of the alternative dependencies for '{group.name}' are satisfied.",
                        remediation_hint=remediation,
                    )
            else:
                # ALL_OF
                unsatisfied = [d for d in sub_diagnostics if not d.is_satisfied]
                if not unsatisfied:
                    return DependencyDiagnostic(
                        dependency_name=group.name,
                        dep_type=DependencyType.DEPENDENCY_GROUP,
                        status=DependencyStatus.SATISFIED,
                        is_optional=group.is_optional,
                    )
                else:
                    remediation = group.remediation_hint or " | ".join(
                        d.remediation_hint for d in unsatisfied if d.remediation_hint
                    )
                    return DependencyDiagnostic(
                        dependency_name=group.name,
                        dep_type=DependencyType.DEPENDENCY_GROUP,
                        status=DependencyStatus.MISSING,
                        is_optional=group.is_optional,
                        error_message=f"Mandatory dependencies missing for group '{group.name}'.",
                        remediation_hint=remediation,
                    )

        elif isinstance(req, PythonDependency) or req.dep_type == DependencyType.PYTHON_PACKAGE:
            python_dep = req if isinstance(req, PythonDependency) else PythonDependency(
                name=req.name,
                version_range=req.version_range,
                is_optional=req.is_optional,
                feature_gate=req.feature_gate,
                remediation_hint=req.remediation_hint,
            )
            return PythonDependencyInspector.inspect(python_dep)

        elif isinstance(req, NativeDependency) or req.dep_type == DependencyType.NATIVE_LIBRARY:
            native_dep = req if isinstance(req, NativeDependency) else NativeDependency(
                name=req.name,
                version_range=req.version_range,
                is_optional=req.is_optional,
                feature_gate=req.feature_gate,
                remediation_hint=req.remediation_hint,
                library_names=(req.name,),
            )
            return NativeDependencyInspector.inspect_native_library(native_dep)

        elif isinstance(req, ExecutableDependency) or req.dep_type == DependencyType.EXECUTABLE:
            exe_dep = req if isinstance(req, ExecutableDependency) else ExecutableDependency(
                name=req.name,
                version_range=req.version_range,
                is_optional=req.is_optional,
                feature_gate=req.feature_gate,
                remediation_hint=req.remediation_hint,
                executable_name=req.name,
            )
            return NativeDependencyInspector.inspect_executable(exe_dep)

        # Fallback for generic/service endpoint
        return DependencyDiagnostic(
            dependency_name=req.name,
            dep_type=req.dep_type,
            status=DependencyStatus.SATISFIED,
            is_optional=req.is_optional,
        )

    @classmethod
    def inspect_all(cls, target_id: str, requirements: Sequence[DependencyRequirement]) -> DependencyDiagnosticReport:
        """Inspects all requirements and returns a consolidated report."""
        diagnostics = [cls.inspect_requirement(req) for req in requirements]
        return DependencyDiagnosticReport(target_id=target_id, diagnostics=tuple(diagnostics))


default_dependency_inspector = DependencyInspector()
