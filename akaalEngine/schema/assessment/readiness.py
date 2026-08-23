"""
akaalEngine.schema.assessment.readiness
=======================================
Pre-migration schema readiness gate evaluation.
Emits evidence-backed readiness facts (READY, READY_WITH_WARNINGS, WAIVER_REQUIRED, BLOCKED).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, List, Mapping, Optional, Tuple

from akaalEngine.schema.assessment.compatibility import CompatibilityBreakdown
from akaalEngine.schema.assessment.risk import RiskLevel, StructuralRiskReport
from akaalEngine.schema.models.types import freeze_deep


class ReadinessStatus(str, Enum):
    """Canonical migration readiness gate status."""
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    WAIVER_REQUIRED = "WAIVER_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ReadinessGateReport:
    """Readiness assessment findings and required governance actions."""
    status: ReadinessStatus
    blocking_reasons: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    required_waivers: Tuple[str, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("blocking_reasons", "warnings", "required_waivers"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def is_executable(self) -> bool:
        return self.status != ReadinessStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "required_waivers": list(self.required_waivers),
            "is_executable": self.is_executable,
            "extra": dict(self.extra),
        }


class SchemaReadinessGateProvider:
    """Evaluates readiness gates based on compatibility and risk evidence."""

    @classmethod
    def evaluate_readiness(
        cls,
        compat_breakdown: CompatibilityBreakdown,
        risk_report: StructuralRiskReport,
    ) -> ReadinessGateReport:
        blockers: List[str] = []
        warnings: List[str] = []
        waivers: List[str] = []

        # 1. Check for Unsupported Datatypes (Blocker)
        if compat_breakdown.unsupported_count > 0:
            blockers.append(f"{compat_breakdown.unsupported_count} unsupported column datatypes must be mapped or excluded before migration")

        # 2. Check for User Decisions & Relational Integrity Breaks (Waiver / Blocker)
        dropped_fk_count = compat_breakdown.extra.get("dropped_foreign_keys_count", 0)
        if dropped_fk_count > 0:
            waivers.append(f"Operator waiver required for {dropped_fk_count} dropped foreign key constraints referencing excluded tables")
            warnings.append(f"{dropped_fk_count} foreign key constraints were dropped because referenced target tables were excluded")

        if getattr(compat_breakdown, "decision_required_count", 0) > 0:
            non_fk_decisions = compat_breakdown.decision_required_count - dropped_fk_count
            if non_fk_decisions > 0:
                waivers.append(f"Explicit operator resolution required for {non_fk_decisions} ambiguous column conversions")
                warnings.append(f"{non_fk_decisions} columns require explicit mapping decisions")

        # 3. Check for Lossy Conversions (Waiver Required)
        if compat_breakdown.lossy_count > 0:
            waivers.append(f"Operator waiver required for {compat_breakdown.lossy_count} lossy column conversions")
            warnings.append(f"{compat_breakdown.lossy_count} columns have potential truncation or precision reduction")

        # 4. Check for Compatibility Pack Requirement
        if getattr(compat_breakdown, "compat_layer_count", 0) > 0:
            count = compat_breakdown.compat_layer_count
            warnings.append(f"{count} constructs require akaal_compat support layer deployment")

        # 5. Check Risk Level
        if risk_report.risk_level == RiskLevel.CRITICAL and not blockers:
            waivers.append("Executive risk waiver required for CRITICAL structural complexity score")
        elif risk_report.risk_level == RiskLevel.HIGH:
            warnings.append("High structural complexity score detected across foreign keys, partitions, or LOBs")

        # Determine Final Status
        if blockers:
            status = ReadinessStatus.BLOCKED
        elif waivers:
            status = ReadinessStatus.WAIVER_REQUIRED
        elif warnings:
            status = ReadinessStatus.READY_WITH_WARNINGS
        else:
            status = ReadinessStatus.READY

        return ReadinessGateReport(
            status=status,
            blocking_reasons=tuple(blockers),
            warnings=tuple(warnings),
            required_waivers=tuple(waivers),
        )
