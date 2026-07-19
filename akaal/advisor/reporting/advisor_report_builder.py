"""
Akaal — Advisor Report Builder
==============================
Generates technical advisory reports, recommendation breakdowns, statistics, and engineering summaries.
NOTE: Executive summaries are EXPLICITLY OMITTED as they belong exclusively to Enterprise Intelligence Reporting (Phase 14).
"""

from typing import List

from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel


class AdvisorReportBuilder:
    """Enterprise Technical Report Builder for MigrationAdvisoryModel."""

    @classmethod
    def build_technical_report(cls, model: MigrationAdvisoryModel) -> str:
        """Generate a complete markdown technical advisory report."""
        lines: List[str] = [
            "# AKAAL TECHNICAL MIGRATION ADVISORY REPORT",
            "============================================",
            f"Advisory ID: {model.manifest.advisory_id}",
            f"Plan ID: {model.manifest.plan_id}",
            f"Plan Checksum: {model.manifest.plan_checksum}",
            f"Advisory Checksum: {model.sha256_checksum}",
            f"Creation Timestamp: {model.manifest.creation_timestamp}",
            "",
            "## 1. ADVISORY CONTEXT",
            "---------------------",
            f"- Environment: {model.context.environment}",
            f"- Database Type: {model.context.database_type}",
            f"- Migration Type: {model.context.migration_type}",
            f"- Target Tier: {model.context.target_tier}",
            "",
            "## 2. RECOMMENDATION SUMMARY STATISTICS",
            "---------------------------------------",
            f"- Total Recommendations: {model.manifest.total_recommendations}",
            f"- Severity Breakdown: {model.manifest.summary_by_severity}",
            f"- Priority Breakdown: {model.manifest.summary_by_priority}",
            f"- Category Breakdown: {model.manifest.summary_by_category}",
            "",
            "## 3. DETAILED TECHNICAL RECOMMENDATIONS",
            "----------------------------------------",
        ]

        for idx, rec in enumerate(model.recommendations, 1):
            lines.extend([
                f"### [{rec.priority.value} | {rec.severity.value}] Recommendation #{idx}: {rec.title}",
                f"- ID: {rec.recommendation_id}",
                f"- Category: {rec.category.value}",
                f"- Fingerprint: {rec.fingerprint}",
                f"- Description: {rec.description}",
                f"- Rationale: {rec.rationale}",
                f"- Impact: {rec.impact}",
                f"- Affected Nodes: {', '.join(rec.affected_nodes) if rec.affected_nodes else 'None'}",
                "- Action Items:",
            ])
            for item in rec.action_items:
                lines.append(f"  * {item}")

            if rec.decision:
                lines.extend([
                    "- Decision Lineage:",
                    f"  * Decision ID: {rec.decision.decision_id}",
                    f"  * Risk Mitigation: {rec.decision.risk_mitigation}",
                    f"  * Alternatives Considered: {', '.join(rec.decision.alternatives_considered)}",
                ])
            lines.append("")

        lines.extend([
            "## 4. ENGINEERING EXECUTION TRACE",
            "----------------------------------",
            f"- Total Duration: {model.trace.execution_duration_ms:.2f} ms",
            f"- Analyzers Run: {len(model.trace.analyzer_traces)}",
            "",
            "============================================",
            "END OF TECHNICAL ADVISORY REPORT",
        ])

        return "\n".join(lines)

    @classmethod
    def build_recommendation_report(cls, model: MigrationAdvisoryModel) -> str:
        """Generate a concise recommendation-only text report."""
        lines = [
            f"AKAAL ADVISORY RECOMMENDATIONS FOR PLAN [{model.manifest.plan_id}]",
            f"Total Recommendations: {len(model.recommendations)}",
            "-" * 60,
        ]
        for rec in model.recommendations:
            lines.append(
                f"[{rec.priority.value}] [{rec.severity.value}] [{rec.category.value}] {rec.recommendation_id}: {rec.title}"
            )
        return "\n".join(lines)

    @classmethod
    def build_engineering_summary(cls, model: MigrationAdvisoryModel) -> str:
        """Generate engineering summary for platform developers."""
        return (
            f"ENGINEERING SUMMARY: Model {model.manifest.advisory_id} generated for plan {model.manifest.plan_id}. "
            f"Recommendations: {model.manifest.total_recommendations} total "
            f"({model.manifest.summary_by_severity.get('CRITICAL', 0)} Critical, "
            f"{model.manifest.summary_by_severity.get('HIGH', 0)} High). "
            f"Execution Duration: {model.trace.execution_duration_ms:.2f}ms."
        )
