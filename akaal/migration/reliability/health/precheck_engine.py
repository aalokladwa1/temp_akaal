import time
from typing import List
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.health_report import HealthCheckReport
from akaal.migration.reliability.health.capacity_health import CapacityHealthCheck
from akaal.migration.reliability.health.dependency_health import DependencyHealthCheck
from akaal.migration.reliability.health.compatibility_health import CompatibilityHealthCheck
from akaal.migration.reliability.plugins.registry import PluginRegistry
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment

class HealthPrecheckEngine(BaseReliabilityEngine):
    """
    HealthPrecheckEngine assesses schema resource requirements, dialect feature support,
    and dependency constraints before physical migration deployment.
    """
    def __init__(self) -> None:
        super().__init__(name="health")
        self.capacity_check = CapacityHealthCheck()
        self.dependency_check = DependencyHealthCheck()
        self.compatibility_check = CompatibilityHealthCheck()

    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> HealthCheckReport:
        passed_checks = []
        failed_checks = []

        # 1. Capacity Checks
        capacity_diags = self.capacity_check.check(context)
        if capacity_diags:
            failed_checks.append("CAPACITY_RESOURCE_VERIFICATION")
            diagnostics.extend(capacity_diags)
        else:
            passed_checks.append("CAPACITY_RESOURCE_VERIFICATION")

        # 2. Dependency Loop Checks
        dep_diags = self.dependency_check.check(context)
        if dep_diags:
            failed_checks.append("OBJECT_DEPENDENCY_CYCLE_VERIFICATION")
            diagnostics.extend(dep_diags)
        else:
            passed_checks.append("OBJECT_DEPENDENCY_CYCLE_VERIFICATION")

        # 3. Dialect Compatibility Checks
        comp_diags = self.compatibility_check.check(context)
        if comp_diags:
            failed_checks.append("DATABASE_DIALECT_COMPATIBILITY_VERIFICATION")
            diagnostics.extend(comp_diags)
        else:
            passed_checks.append("DATABASE_DIALECT_COMPATIBILITY_VERIFICATION")

        # 4. Third-party Health plugins
        for idx, plugin in enumerate(PluginRegistry.get_health_checks()):
            plugin_diags = plugin.check_health(context)
            p_name = f"PLUGIN_HEALTH_CHECK_{idx}"
            if plugin_diags:
                failed_checks.append(p_name)
                diagnostics.extend(plugin_diags)
            else:
                passed_checks.append(p_name)

        # Risk assessment
        risk_assessment = calculate_risk_assessment(diagnostics)

        # Build report audit metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_health"
        )

        return HealthCheckReport(
            metadata=report_meta,
            passed_checks=tuple(passed_checks),
            failed_checks=tuple(failed_checks),
            diagnostics=tuple(diagnostics),
            risk=risk_assessment
        )
