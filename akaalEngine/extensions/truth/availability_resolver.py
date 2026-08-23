"""
akaalEngine.extensions.truth.availability_resolver
==================================================
Derives consolidated runtime availability status for extensions, providers, and strategies.
"""

from __future__ import annotations

from typing import Sequence

from akaalEngine.extensions.dependencies.diagnostics import DependencyDiagnosticReport
from akaalEngine.extensions.models.availability import ExtensionAvailability
from akaalEngine.extensions.models.enums import ExtensionLifecycleState


class AvailabilityResolver:
    """
    Computes ExtensionAvailability from lifecycle states and dependency diagnostic reports.
    """

    @classmethod
    def resolve_availability(
        cls,
        lifecycle_state: ExtensionLifecycleState,
        dep_report: DependencyDiagnosticReport,
    ) -> ExtensionAvailability:
        is_dep_ok = dep_report.is_all_mandatory_satisfied
        missing_mandatory = tuple(d.dependency_name for d in dep_report.missing_mandatory)
        missing_optional = tuple(d.dependency_name for d in dep_report.missing_optional)

        is_available = (
            lifecycle_state == ExtensionLifecycleState.ACTIVE
            and is_dep_ok
        )

        reason = None
        if lifecycle_state != ExtensionLifecycleState.ACTIVE:
            reason = f"Extension is in lifecycle state '{lifecycle_state.value}'."
        elif not is_dep_ok:
            reason = f"Missing mandatory dependencies: {list(missing_mandatory)}."

        return ExtensionAvailability(
            is_available=is_available,
            lifecycle_state=lifecycle_state,
            dependency_satisfied=is_dep_ok,
            missing_mandatory_dependencies=missing_mandatory,
            missing_optional_dependencies=missing_optional,
            diagnostics=dep_report.diagnostics,
            reason=reason,
        )


default_availability_resolver = AvailabilityResolver()
