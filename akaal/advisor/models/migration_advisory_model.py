"""
Akaal — Migration Advisory Model
=================================
The single canonical, immutable, versioned, checksum-protected output artifact produced by Advisor Platform.
Consumed downstream by Enterprise Intelligence, Mission Control, and Dashboards.
Enforces deep immutability via MappingProxyType.
"""

import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Tuple

from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.advisory_manifest import AdvisoryManifest
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
from akaal.advisor.models.advisory_trace import AdvisoryTrace


@dataclass(frozen=True)
class MigrationAdvisoryModel:
    """Immutable, versioned MigrationAdvisoryModel output artifact."""
    schema_version: str = "1.0.0"
    model_version: str = "1.0.0"
    generator_version: str = "advisor-1.0.0"
    model_signature: str = "AKAAL-ADVISOR-SIG-V1"
    sha256_checksum: str = ""

    manifest: AdvisoryManifest = field(default_factory=lambda: AdvisoryManifest(
        advisory_id="ADV-DEFAULT", plan_id="", plan_checksum="", total_recommendations=0
    ))
    context: AdvisoryContext = field(default_factory=AdvisoryContext)
    recommendations: Tuple[AdvisoryRecommendation, ...] = field(default_factory=tuple)
    trace: AdvisoryTrace = field(default_factory=lambda: AdvisoryTrace(
        trace_id="TR-DEFAULT", execution_duration_ms=0.0
    ))
    governance: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    statistics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.governance, dict):
            object.__setattr__(self, "governance", MappingProxyType(dict(self.governance)))
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        if isinstance(self.statistics, dict):
            object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))

        if not self.sha256_checksum:
            cksum = self.compute_checksum()
            object.__setattr__(self, "sha256_checksum", cksum)

    def compute_checksum(self) -> str:
        """Compute SHA-256 checksum over deterministic payload (stable manifest, context, recommendations)."""
        stable_manifest = {
            "advisory_id": self.manifest.advisory_id,
            "plan_id": self.manifest.plan_id,
            "plan_checksum": self.manifest.plan_checksum,
            "total_recommendations": self.manifest.total_recommendations,
            "summary_by_category": dict(self.manifest.summary_by_category),
            "summary_by_severity": dict(self.manifest.summary_by_severity),
            "summary_by_priority": dict(self.manifest.summary_by_priority),
        }
        payload = {
            "manifest": stable_manifest,
            "context": self.context.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
        }
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def verify_checksum(self) -> bool:
        """Verify model checksum integrity."""
        return self.sha256_checksum == self.compute_checksum()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "generator_version": self.generator_version,
            "model_signature": self.model_signature,
            "sha256_checksum": self.sha256_checksum,
            "manifest": self.manifest.to_dict(),
            "context": self.context.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "trace": self.trace.to_dict(),
            "governance": dict(self.governance),
            "metadata": dict(self.metadata),
            "statistics": dict(self.statistics),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
