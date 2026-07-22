"""
Report Version Manager supporting Semantic Versioning and History.
"""

from typing import Dict, List, Optional
from akaal.reporting.models.report import ReportArtifact, ReportVersion


class ReportVersionManager:
    """Version Manager tracking report iterations and semantic compatibility."""

    def __init__(self) -> None:
        self._history: Dict[str, List[ReportArtifact]] = {}

    def register_version(self, artifact: ReportArtifact) -> ReportVersion:
        report_id = artifact.metadata.report_id
        if report_id not in self._history:
            self._history[report_id] = []

        history = self._history[report_id]
        if not history:
            v = ReportVersion(major=1, minor=0, patch=0, version_string="1.0.0")
        else:
            prev_v = history[-1].metadata.version
            v = ReportVersion(major=prev_v.major, minor=prev_v.minor + 1, patch=0, version_string=f"{prev_v.major}.{prev_v.minor + 1}.0")

        artifact.metadata.version = v
        history.append(artifact)
        return v

    def get_version_history(self, report_id: str) -> List[ReportArtifact]:
        return self._history.get(report_id, [])
