"""
AKAAL Enterprise Intelligence Platform — Enterprise Report Builder
===================================================================
Pure presentation layer transforming immutable EnterpriseIntelligenceModel artifacts into
deterministic reports (Full, Executive, Technical, Governance, Summary) in multiple formats (Dict, JSON, Markdown, Text).
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional
from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel
from akaal.intelligence.validation.enterprise_intelligence_validator import EnterpriseIntelligenceValidator


class ReportType(str, Enum):
    """Supported report view types."""
    FULL = "FULL"
    EXECUTIVE = "EXECUTIVE"
    TECHNICAL = "TECHNICAL"
    GOVERNANCE = "GOVERNANCE"
    SUMMARY = "SUMMARY"


class ReportFormat(str, Enum):
    """Supported report output formats."""
    DICT = "DICT"
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    TEXT = "TEXT"


class EnterpriseReportBuilderError(Exception):
    """Exception raised for errors in EnterpriseReportBuilder."""
    pass


class EnterpriseReportBuilder:
    """
    Pure, side-effect-free, deterministic report builder for EnterpriseIntelligenceModel artifacts.
    """

    @classmethod
    def build(
        cls,
        model: EnterpriseIntelligenceModel,
        report_type: ReportType = ReportType.FULL,
        output_format: ReportFormat = ReportFormat.MARKDOWN,
    ) -> Any:
        """
        Builds a report from an EnterpriseIntelligenceModel.

        Args:
            model: Input canonical EnterpriseIntelligenceModel.
            report_type: Report depth level (FULL, EXECUTIVE, TECHNICAL, GOVERNANCE, SUMMARY).
            output_format: Output format (DICT, JSON, MARKDOWN, TEXT).

        Returns:
            Dict, formatted JSON string, Markdown string, or Plain Text string.
        """
        if not model or not isinstance(model, EnterpriseIntelligenceModel):
            raise EnterpriseReportBuilderError("Invalid model: input must be a valid EnterpriseIntelligenceModel instance.")

        EnterpriseIntelligenceValidator.validate_intelligence_model(model)

        raw_data = cls._generate_report_data(model, report_type)

        if output_format == ReportFormat.DICT:
            return raw_data
        elif output_format == ReportFormat.JSON:
            return json.dumps(raw_data, indent=2, sort_keys=True)
        elif output_format == ReportFormat.MARKDOWN:
            return cls._render_markdown(raw_data, report_type)
        elif output_format == ReportFormat.TEXT:
            return cls._render_text(raw_data, report_type)
        else:
            raise EnterpriseReportBuilderError(f"Unsupported output format: {output_format}")

    @classmethod
    def _generate_report_data(cls, model: EnterpriseIntelligenceModel, report_type: ReportType) -> Dict[str, Any]:
        """Generates structured report data dictionary deterministically."""
        base_summary = {
            "model_id": model.model_id,
            "advisory_model_id": model.advisory_model_id,
            "checksum": model.checksum,
            "schema_version": model.version_info.schema_version,
            "readiness_score": model.readiness.overall_readiness_score,
            "readiness_tier": model.readiness.tier.value if hasattr(model.readiness.tier, "value") else str(model.readiness.tier),
            "strategy_type": model.strategy.strategy_type.value if hasattr(model.strategy.strategy_type, "value") else str(model.strategy.strategy_type),
            "total_decisions": len(model.decisions),
        }

        if report_type == ReportType.SUMMARY:
            return {"report_type": "SUMMARY", "summary": base_summary}

        if report_type == ReportType.EXECUTIVE:
            return {
                "report_type": "EXECUTIVE",
                "summary": base_summary,
                "manifest": {
                    "critical_decisions_count": model.manifest.critical_decisions_count,
                    "high_priority_decisions_count": model.manifest.high_priority_decisions_count,
                    "simulated_downtime_p95_seconds": model.manifest.simulated_downtime_p95_seconds,
                },
                "strategy": {
                    "primary_objective": model.strategy.primary_objective,
                    "execution_mode": model.strategy.recommended_execution_mode,
                    "key_advantages": list(model.strategy.strategic_advantages),
                },
                "critical_decisions": [
                    {
                        "id": d.decision_id,
                        "title": d.title,
                        "priority": d.priority.value if hasattr(d.priority, "value") else str(d.priority),
                        "impact": d.strategic_impact,
                    }
                    for d in model.decisions
                    if (d.priority.value if hasattr(d.priority, "value") else str(d.priority)) in ("CRITICAL", "HIGH")
                ],
            }

        if report_type == ReportType.TECHNICAL:
            return {
                "report_type": "TECHNICAL",
                "summary": base_summary,
                "simulation": {
                    "min_downtime_sec": model.simulation.projected_downtime_seconds_min,
                    "max_downtime_sec": model.simulation.projected_downtime_seconds_max,
                    "p95_downtime_sec": model.simulation.projected_downtime_seconds_p95,
                    "estimated_throughput_rps": model.simulation.estimated_throughput_records_per_sec,
                    "bottlenecks": list(model.simulation.bottleneck_stages),
                },
                "agent_coordination": {
                    "total_recommended_agents": model.agent_coordination.total_recommended_agents,
                    "primary_region": model.agent_coordination.primary_region,
                    "worker_distribution": dict(model.agent_coordination.worker_distribution),
                },
                "all_decisions": [
                    {
                        "id": d.decision_id,
                        "title": d.title,
                        "category": d.category,
                        "confidence": d.confidence_score,
                    }
                    for d in model.decisions
                ],
                "trace": {
                    "total_duration_ms": model.trace.total_execution_duration_ms,
                    "analyzer_durations_ms": dict(model.trace.analyzer_durations_ms),
                },
            }

        if report_type == ReportType.GOVERNANCE:
            return {
                "report_type": "GOVERNANCE",
                "summary": base_summary,
                "governance": {
                    "checksum": model.checksum,
                    "generated_at": model.manifest.generated_at_timestamp,
                    "schema_version": model.version_info.schema_version,
                    "platform_version": model.version_info.platform_version,
                },
            }

        # Full Report
        return {
            "report_type": "FULL",
            "summary": base_summary,
            "manifest": {
                "critical_decisions_count": model.manifest.critical_decisions_count,
                "high_priority_decisions_count": model.manifest.high_priority_decisions_count,
                "simulated_downtime_p95_seconds": model.manifest.simulated_downtime_p95_seconds,
            },
            "strategy": {
                "primary_objective": model.strategy.primary_objective,
                "execution_mode": model.strategy.recommended_execution_mode,
                "duration_seconds": model.strategy.estimated_total_duration_seconds,
            },
            "readiness": {
                "overall_score": model.readiness.overall_readiness_score,
                "schema_score": model.readiness.schema_readiness_score,
                "data_score": model.readiness.data_readiness_score,
                "hardware_score": model.readiness.hardware_readiness_score,
            },
            "simulation": {
                "p95_downtime_sec": model.simulation.projected_downtime_seconds_p95,
                "estimated_throughput_rps": model.simulation.estimated_throughput_records_per_sec,
            },
            "decisions": [
                {
                    "id": d.decision_id,
                    "title": d.title,
                    "priority": d.priority.value if hasattr(d.priority, "value") else str(d.priority),
                    "confidence": d.confidence_score,
                }
                for d in model.decisions
            ],
            "trace": {
                "total_duration_ms": model.trace.total_execution_duration_ms,
            },
        }

    @classmethod
    def _render_markdown(cls, data: Dict[str, Any], report_type: ReportType) -> str:
        """Renders Markdown report deterministically."""
        s = data["summary"]
        lines = [
            f"# AKAAL Enterprise Strategic Intelligence Report ({report_type.value})",
            "",
            "## Executive Overview",
            f"- **Model ID**: `{s['model_id']}`",
            f"- **Advisory ID**: `{s['advisory_model_id']}`",
            f"- **Readiness Score**: **{s['readiness_score']} / 100.0** ({s['readiness_tier']})",
            f"- **Strategy Archetype**: `{s['strategy_type']}`",
            f"- **Total Resolved Decisions**: `{s['total_decisions']}`",
            f"- **SHA-256 Checksum**: `{s['checksum']}`",
            "",
        ]

        if "strategy" in data:
            strat = data["strategy"]
            lines.extend([
                "## Strategic Direction",
                f"- **Primary Objective**: {strat.get('primary_objective', 'N/A')}",
                f"- **Execution Mode**: `{strat.get('execution_mode', 'N/A')}`",
                "",
            ])

        if "decisions" in data or "critical_decisions" in data:
            decs = data.get("decisions") or data.get("critical_decisions", [])
            lines.append("## Strategic Decisions")
            lines.append("| Decision ID | Title | Priority |")
            lines.append("|---|---|---|")
            for d in decs:
                lines.append(f"| `{d['id']}` | {d['title']} | `{d.get('priority', 'N/A')}` |")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _render_text(cls, data: Dict[str, Any], report_type: ReportType) -> str:
        """Renders Plain Text report deterministically."""
        s = data["summary"]
        lines = [
            f"=== AKAAL ENTERPRISE REPORT [{report_type.value}] ===",
            f"Model ID:        {s['model_id']}",
            f"Advisory ID:     {s['advisory_model_id']}",
            f"Readiness Score: {s['readiness_score']} ({s['readiness_tier']})",
            f"Strategy Type:   {s['strategy_type']}",
            f"Total Decisions: {s['total_decisions']}",
            f"Checksum:        {s['checksum']}",
            "===================================================",
        ]
        return "\n".join(lines)
