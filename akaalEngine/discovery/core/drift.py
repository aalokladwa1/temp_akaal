"""
akaalEngine.discovery.core.drift
================================
Lightweight metadata drift detector comparing historical discovery snapshots against live probes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.discovery.models.snapshot import DiscoveryFingerprint


class DiscoveryDriftSeverity(str, Enum):
    """Severity classification of detected metadata drift."""
    NONE = "NONE"
    LOW = "LOW"            # Non-structural drift (e.g. statistics / row counts changed)
    HIGH = "HIGH"          # Structural drift (e.g. columns added/modified, indexes altered)
    CRITICAL = "CRITICAL"  # Breaking drift (e.g. tables dropped, primary keys altered)


@dataclass(frozen=True)
class DiscoveryDriftReport:
    """Detailed comparison report between historical baseline and live metadata."""
    is_drifted: bool
    severity: DiscoveryDriftSeverity = DiscoveryDriftSeverity.NONE
    baseline_hash: str = ""
    current_hash: str = ""
    component_diffs: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    change_summary: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.component_diffs, MappingProxyType):
            object.__setattr__(self, "component_diffs", MappingProxyType(dict(self.component_diffs)))
        if not isinstance(self.change_summary, tuple):
            object.__setattr__(self, "change_summary", tuple(self.change_summary))

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_drifted": self.is_drifted,
            "severity": self.severity.value,
            "baseline_hash": self.baseline_hash,
            "current_hash": self.current_hash,
            "component_diffs": dict(self.component_diffs),
            "change_summary": list(self.change_summary),
        }


class MetadataDriftDetector:
    """Evaluates whether metadata has mutated since a baseline snapshot was taken."""

    @classmethod
    def compare_fingerprints(
        cls,
        baseline: DiscoveryFingerprint,
        current: DiscoveryFingerprint,
    ) -> DiscoveryDriftReport:
        if baseline.sha256_hash == current.sha256_hash:
            return DiscoveryDriftReport(
                is_drifted=False,
                severity=DiscoveryDriftSeverity.NONE,
                baseline_hash=baseline.sha256_hash,
                current_hash=current.sha256_hash,
            )

        diffs = {}
        changes = []
        all_keys = set(baseline.component_hashes.keys()) | set(current.component_hashes.keys())
        for k in sorted(all_keys):
            b_val = baseline.component_hashes.get(k, "")
            c_val = current.component_hashes.get(k, "")
            if b_val != c_val:
                diffs[k] = f"Baseline: {b_val[:8]}... -> Current: {c_val[:8]}..."
                changes.append(f"Component '{k}' structural hash changed.")

        severity = DiscoveryDriftSeverity.HIGH
        if "structures" in diffs or "namespaces" in diffs:
            severity = DiscoveryDriftSeverity.CRITICAL

        return DiscoveryDriftReport(
            is_drifted=True,
            severity=severity,
            baseline_hash=baseline.sha256_hash,
            current_hash=current.sha256_hash,
            component_diffs=diffs,
            change_summary=tuple(changes),
        )
