import time
from typing import List
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.certification_report import MigrationCertificationReport
from akaal.migration.reliability.artifacts.certification_artifact import CertificationArtifact
from akaal.migration.reliability.certification.certification_registry import CertificationRegistry
from akaal.migration.reliability.certification.certification_rules import NamingStandardCompliance
from akaal.migration.reliability.certification.report_builder import CertificationReportBuilder
from akaal.migration.reliability.plugins.registry import PluginRegistry
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment

class CertificationEngine(BaseReliabilityEngine):
    """
    CertificationEngine runs name matching, type security,
    and registered compliance checks, assigning a letter grade and certification status.
    """
    def __init__(self) -> None:
        super().__init__(name="certification")
        self.naming_check = NamingStandardCompliance()
        self.builder = CertificationReportBuilder()

    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> MigrationCertificationReport:
        rules_checked = 0
        rules_failed = 0

        # 1. Base Naming Standard Compliance
        rules_checked += 1
        naming_diags = self.naming_check.check_compliance(context)
        if naming_diags:
            rules_failed += 1
            diagnostics.extend(naming_diags)

        # 2. Registry checks
        for rule_name, rule_instance in CertificationRegistry.get_rules().items():
            rules_checked += 1
            rule_diags = rule_instance.check_compliance(context)
            if rule_diags:
                rules_failed += 1
                diagnostics.extend(rule_diags)

        # 3. Third-party Certification plugins
        for plugin in PluginRegistry.get_certifiers():
            rules_checked += 1
            plugin_diags = plugin.certify(context)
            if plugin_diags:
                rules_failed += 1
                diagnostics.extend(plugin_diags)

        # Compute final parameters
        grade = self.builder.compute_grade(diagnostics)
        certified = grade in ("A", "B")
        risk_assessment = calculate_risk_assessment(diagnostics)

        # Build report audit metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_cert"
        )

        # Artifact construction (machine-consumable)
        artifact = CertificationArtifact(
            execution_id=report_meta.execution_id,
            compliant=certified,
            rules_checked=rules_checked,
            rules_failed=rules_failed
        )

        return MigrationCertificationReport(
            metadata=report_meta,
            certified=certified,
            compliance_grade=grade,
            risk=risk_assessment
        )
