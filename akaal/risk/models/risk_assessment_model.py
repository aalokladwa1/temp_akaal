"""
Akaal — Risk Assessment Model
==============================
The single canonical, immutable, versioned, checksum-protected output artifact produced by Risk Platform.
Consumed by downstream modules (Planner, Advisor, Enterprise Intelligence, Mission Control, Dashboards).
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RiskAssessmentModel:
    """
    Immutable, versioned RiskAssessmentModel artifact.
    Single public output produced by Risk Platform.
    """
    schema_version: str = "1.0.0"
    model_version: str = "1.0.0"
    generator_version: str = "risk-1.0.0"
    model_signature: str = "AKAAL-RISK-SIG-V1"
    sha256_checksum: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)
    overall_risk_score: Dict[str, Any] = field(default_factory=dict)
    readiness: Dict[str, Any] = field(default_factory=dict)
    complexity: Dict[str, Any] = field(default_factory=dict)
    downtime_estimate: Dict[str, Any] = field(default_factory=dict)
    resource_estimate: Dict[str, Any] = field(default_factory=dict)
    performance_prediction: Dict[str, Any] = field(default_factory=dict)
    evidence_graph: Dict[str, Any] = field(default_factory=dict)
    risk_dependency_graph: Dict[str, Any] = field(default_factory=dict)
    risk_items: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    execution_trace: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "generator_version": self.generator_version,
            "model_signature": self.model_signature,
            "sha256_checksum": self.sha256_checksum,
            "metadata": self.metadata,
            "manifest": self.manifest,
            "overall_risk_score": self.overall_risk_score,
            "readiness": self.readiness,
            "complexity": self.complexity,
            "downtime_estimate": self.downtime_estimate,
            "resource_estimate": self.resource_estimate,
            "performance_prediction": self.performance_prediction,
            "evidence_graph": self.evidence_graph,
            "risk_dependency_graph": self.risk_dependency_graph,
            "risk_items": self.risk_items,
            "statistics": self.statistics,
            "execution_trace": self.execution_trace,
            "diagnostics": self.diagnostics,
        }
        if not res["sha256_checksum"]:
            temp_dict = {
                "metadata": {k: v for k, v in self.metadata.items() if k not in ("generated_at", "timestamp")},
                "overall_risk_score": self.overall_risk_score,
                "readiness": self.readiness,
                "complexity": self.complexity,
                "downtime_estimate": self.downtime_estimate,
                "resource_estimate": self.resource_estimate,
                "performance_prediction": self.performance_prediction,
                "risk_items": self.risk_items,
            }
            res["sha256_checksum"] = hashlib.sha256(json.dumps(temp_dict, default=str, sort_keys=True).encode("utf-8")).hexdigest()
        return res

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
