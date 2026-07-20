"""Enterprise Report Models and Formatters for JSON & Markdown."""

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Mapping
from akaal.workflow.utils.serialization import compute_sha256, canonical_json


class WorkflowReportType(str, Enum):
    """Report type enumeration."""
    PRE_MIGRATION = "PRE_MIGRATION"
    MIGRATION = "MIGRATION"
    VALIDATION = "VALIDATION"
    CUTOVER = "CUTOVER"
    POST_MIGRATION = "POST_MIGRATION"


class ReportFormat(str, Enum):
    """Supported report output formats."""
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"


@dataclass(frozen=True, slots=True)
class EnterpriseReport:
    """Immutable enterprise report model."""

    report_id: str
    report_type: WorkflowReportType
    workflow_id: str
    run_id: str
    status: str
    summary: str
    details: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = "2026-01-01T00:00:00+00:00"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "status": self.status,
            "summary": self.summary,
            "details": dict(self.details),
            "generated_at": self.generated_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "status": self.status,
            "summary": self.summary,
            "details": dict(self.details),
            "generated_at": self.generated_at,
            "checksum": self.checksum,
        }

    def render_json(self) -> str:
        """Render report as canonical JSON string."""
        return canonical_json(self.to_dict())

    def render_markdown(self) -> str:
        """Render report as human-readable markdown."""
        md = [
            f"# {self.report_type.value.replace('_', ' ').title()} Report",
            f"**Report ID:** {self.report_id}  ",
            f"**Workflow ID:** {self.workflow_id}  ",
            f"**Run ID:** {self.run_id}  ",
            f"**Status:** {self.status}  ",
            f"**Generated At:** {self.generated_at}  ",
            f"**Checksum:** `{self.checksum}`  ",
            "",
            "## Executive Summary",
            self.summary,
            "",
            "## Report Details",
            "```json",
            json.dumps(dict(self.details), indent=2),
            "```",
        ]
        return "\n".join(md)
