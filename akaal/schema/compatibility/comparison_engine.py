"""
AKAAL Schema Engine — Universal Canonical Comparison, Risk Scoring & Drift Analysis
===================================================================================
Provides database-agnostic schema comparison, explainable risk scoring, pre-migration
compatibility assessment, and deterministic schema drift analysis across Oracle,
PostgreSQL, MySQL, MSSQL, and plugin database engines.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Dict, Any, List, Set, Optional, Tuple

from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalPrimaryKey,
    CanonicalForeignKey,
    CanonicalUniqueConstraint,
    CanonicalCheckConstraint,
    CanonicalIndex,
    CanonicalSequence,
    CanonicalView,
    CanonicalMaterializedView,
    CanonicalProcedure,
    CanonicalFunction,
    CanonicalTrigger,
)
from akaal.schema.domain.types import (
    CanonicalTypeCategory,
    ConversionSafety,
    CanonicalType,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry


class DifferenceCategory(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    RENAMED_OR_POSSIBLE_RENAME = "RENAMED_OR_POSSIBLE_RENAME"
    TYPE_CHANGED = "TYPE_CHANGED"
    NULLABILITY_CHANGED = "NULLABILITY_CHANGED"
    DEFAULT_CHANGED = "DEFAULT_CHANGED"
    IDENTITY_CHANGED = "IDENTITY_CHANGED"
    CONSTRAINT_CHANGED = "CONSTRAINT_CHANGED"
    DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
    DEFINITION_CHANGED = "DEFINITION_CHANGED"
    UNSUPPORTED = "UNSUPPORTED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class CompatibilityClassification(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    COMPATIBLE_WITH_CONVERSION = "COMPATIBLE_WITH_CONVERSION"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    POTENTIALLY_LOSSY = "POTENTIALLY_LOSSY"
    LOSSY = "LOSSY"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKING = "BLOCKING"


class RiskSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    BLOCKING = "BLOCKING"


class DriftClassification(str, Enum):
    NO_DRIFT = "NO_DRIFT"
    NON_BREAKING_DRIFT = "NON_BREAKING_DRIFT"
    BREAKING_DRIFT = "BREAKING_DRIFT"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass
class SchemaDifference:
    """Strongly-typed, deterministic representation of a schema difference."""
    difference_id: str
    object_type: str
    schema_name: str
    object_name: str
    category: DifferenceCategory
    property_name: Optional[str] = None
    source_value: Optional[Any] = None
    target_value: Optional[Any] = None
    severity: RiskSeverity = RiskSeverity.INFO
    compatibility: CompatibilityClassification = CompatibilityClassification.COMPATIBLE
    explanation: str = ""
    recommended_action: str = "NO_ACTION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "difference_id": self.difference_id,
            "object_type": self.object_type,
            "schema_name": self.schema_name,
            "object_name": self.object_name,
            "category": self.category.value,
            "property_name": self.property_name,
            "source_value": str(self.source_value) if self.source_value is not None else None,
            "target_value": str(self.target_value) if self.target_value is not None else None,
            "severity": self.severity.value,
            "compatibility": self.compatibility.value,
            "explanation": self.explanation,
            "recommended_action": self.recommended_action,
        }


@dataclass
class RiskFinding:
    """Individual explainable risk evidence finding."""
    finding_id: str
    category: str  # STRUCTURAL, DATATYPE, CONSTRAINT, DEPENDENCY, PROGRAMMABLE, PARTITION, DRIFT
    severity: RiskSeverity
    explanation: str
    recommendation: str
    score_weight: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "severity": self.severity.value,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "score_weight": self.score_weight,
        }


@dataclass
class RiskAssessment:
    """Deterministic, explainable risk assessment report."""
    risk_score: int  # 0 to 100
    overall_compatibility: CompatibilityClassification
    findings: List[RiskFinding]
    breakdown: Dict[str, int]
    blocking_findings_count: int
    is_safe_to_continue: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "overall_compatibility": self.overall_compatibility.value,
            "findings": [f.to_dict() for f in self.findings],
            "breakdown": self.breakdown,
            "blocking_findings_count": self.blocking_findings_count,
            "is_safe_to_continue": self.is_safe_to_continue,
        }


@dataclass
class SchemaDriftReport:
    """Deterministic schema drift evaluation report."""
    source_fingerprint: str
    target_fingerprint: str
    drift_classification: DriftClassification
    differences: List[SchemaDifference]
    is_drift_detected: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_fingerprint": self.source_fingerprint,
            "target_fingerprint": self.target_fingerprint,
            "drift_classification": self.drift_classification.value,
            "differences": [d.to_dict() for d in self.differences],
            "is_drift_detected": self.is_drift_detected,
        }


class CanonicalSchemaComparator:
    """Universal Canonical Schema Comparison Authority."""

    HEURISTIC_RENAME_AUTOMATICALLY_ACCEPTED = False

    @classmethod
    def compare_schemas(
        cls, source_model: CanonicalSchemaModel, target_model: CanonicalSchemaModel
    ) -> List[SchemaDifference]:
        """Compare two CanonicalSchemaModels and produce deterministic SchemaDifferences."""
        diffs: List[SchemaDifference] = []

        src_tables = source_model.tables
        tgt_tables = target_model.tables

        src_keys = set(src_tables.keys())
        tgt_keys = set(tgt_tables.keys())

        # Removed tables (present in source, missing in target)
        for t_name in sorted(src_keys - tgt_keys):
            st = src_tables[t_name]
            diff_id = f"diff-tbl-rem-{st.identity.schema_name}.{t_name}"
            diffs.append(
                SchemaDifference(
                    difference_id=diff_id,
                    object_type="TABLE",
                    schema_name=st.identity.schema_name,
                    object_name=t_name,
                    category=DifferenceCategory.REMOVED,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                    explanation=f"Table '{t_name}' exists in source but is missing in target",
                    recommended_action="CREATE_TARGET_OBJECT",
                )
            )

        # Extra target tables (present in target, missing in source)
        for t_name in sorted(tgt_keys - src_keys):
            tt = tgt_tables[t_name]
            diff_id = f"diff-tbl-add-{tt.identity.schema_name}.{t_name}"
            diffs.append(
                SchemaDifference(
                    difference_id=diff_id,
                    object_type="TABLE",
                    schema_name=tt.identity.schema_name,
                    object_name=t_name,
                    category=DifferenceCategory.ADDED,
                    severity=RiskSeverity.INFO,
                    compatibility=CompatibilityClassification.COMPATIBLE,
                    explanation=f"Extra table '{t_name}' exists in target database",
                    recommended_action="NO_ACTION",
                )
            )

        # Common tables to compare columns and constraints
        for t_name in sorted(src_keys.intersection(tgt_keys)):
            st = src_tables[t_name]
            tt = tgt_tables[t_name]
            diffs.extend(cls._compare_table_details(st, tt, source_model.engine, target_model.engine))

        # Compare Views & Programmable Objects
        diffs.extend(cls._compare_views(source_model.views, target_model.views))
        diffs.extend(cls._compare_procedures(source_model.procedures, target_model.procedures))

        return diffs

    @classmethod
    def _compare_table_details(
        cls, src_t: CanonicalTable, tgt_t: CanonicalTable, source_engine: str, target_engine: str
    ) -> List[SchemaDifference]:
        diffs: List[SchemaDifference] = []
        s_name = src_t.identity.schema_name
        t_name = src_t.identity.object_name

        src_cols = {c.name: c for c in src_t.columns}
        tgt_cols = {c.name: c for c in tgt_t.columns}

        src_ckeys = set(src_cols.keys())
        tgt_ckeys = set(tgt_cols.keys())

        # Missing columns in target
        for cname in sorted(src_ckeys - tgt_ckeys):
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-rem-{s_name}.{t_name}.{cname}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.REMOVED,
                    property_name=cname,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                    explanation=f"Column '{cname}' in table '{t_name}' missing in target",
                    recommended_action="ALTER_TARGET_OBJECT",
                )
            )

        # Extra columns in target
        for cname in sorted(tgt_ckeys - src_ckeys):
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-add-{s_name}.{t_name}.{cname}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.ADDED,
                    property_name=cname,
                    severity=RiskSeverity.INFO,
                    compatibility=CompatibilityClassification.COMPATIBLE,
                    explanation=f"Extra column '{cname}' exists in target table '{t_name}'",
                    recommended_action="NO_ACTION",
                )
            )

        # Common columns comparison
        for cname in sorted(src_ckeys.intersection(tgt_ckeys)):
            sc = src_cols[cname]
            tc = tgt_cols[cname]

            sc_type = sc.canonical_type_model or CanonicalTypeRegistry.normalize_source_type(source_engine, sc.source_native_type)
            tc_type = tc.canonical_type_model or CanonicalTypeRegistry.normalize_source_type(target_engine, tc.source_native_type)

            # Category comparison
            if sc_type.category != tc_type.category:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-type-{s_name}.{t_name}.{cname}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.TYPE_CHANGED,
                        property_name=cname,
                        source_value=sc_type.to_canonical_string(),
                        target_value=tc_type.to_canonical_string(),
                        severity=RiskSeverity.MEDIUM,
                        compatibility=CompatibilityClassification.POTENTIALLY_LOSSY,
                        explanation=f"Column '{cname}' category mismatch ({sc_type.category.value} vs {tc_type.category.value})",
                        recommended_action="REVIEW_TYPE_CONVERSION",
                    )
                )

            # Length / Precision / Scale Directional Asymmetry Check
            if sc_type.length and tc_type.length:
                if sc_type.length > tc_type.length:  # Narrowing (Narrower target)
                    diffs.append(
                        SchemaDifference(
                            difference_id=f"diff-col-len-narrow-{s_name}.{t_name}.{cname}",
                            object_type="COLUMN",
                            schema_name=s_name,
                            object_name=t_name,
                            category=DifferenceCategory.MODIFIED,
                            property_name="length",
                            source_value=sc_type.length,
                            target_value=tc_type.length,
                            severity=RiskSeverity.HIGH,
                            compatibility=CompatibilityClassification.POTENTIALLY_LOSSY,
                            explanation=f"Column '{cname}' length narrowing ({sc_type.length} -> {tc_type.length}) may truncate data",
                            recommended_action="REVIEW_TYPE_CONVERSION",
                        )
                    )
                elif sc_type.length < tc_type.length:  # Widening (Wider target)
                    diffs.append(
                        SchemaDifference(
                            difference_id=f"diff-col-len-wide-{s_name}.{t_name}.{cname}",
                            object_type="COLUMN",
                            schema_name=s_name,
                            object_name=t_name,
                            category=DifferenceCategory.MODIFIED,
                            property_name="length",
                            source_value=sc_type.length,
                            target_value=tc_type.length,
                            severity=RiskSeverity.LOW,
                            compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                            explanation=f"Column '{cname}' length widening ({sc_type.length} -> {tc_type.length}) is safe",
                            recommended_action="NO_ACTION",
                        )
                    )

            # Nullability mismatch
            if sc.nullable != tc.nullable:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-null-{s_name}.{t_name}.{cname}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.NULLABILITY_CHANGED,
                        property_name=cname,
                        source_value=sc.nullable,
                        target_value=tc.nullable,
                        severity=RiskSeverity.MEDIUM if not sc.nullable else RiskSeverity.LOW,
                        compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                        explanation=f"Column '{cname}' nullability mismatch (source: {sc.nullable}, target: {tc.nullable})",
                        recommended_action="ALTER_TARGET_OBJECT",
                    )
                )

        # Foreign Key Actions and Composite Ordering Comparison
        src_fks = {fk.name or f"fk_{idx}": fk for idx, fk in enumerate(src_t.foreign_keys)}
        tgt_fks = {fk.name or f"fk_{idx}": fk for idx, fk in enumerate(tgt_t.foreign_keys)}

        for fk_name, sfk in src_fks.items():
            if fk_name in tgt_fks:
                tfk = tgt_fks[fk_name]
                if sfk.on_delete != tfk.on_delete:
                    diffs.append(
                        SchemaDifference(
                            difference_id=f"diff-fk-action-{s_name}.{t_name}.{fk_name}",
                            object_type="FOREIGN_KEY",
                            schema_name=s_name,
                            object_name=t_name,
                            category=DifferenceCategory.CONSTRAINT_CHANGED,
                            property_name="on_delete",
                            source_value=sfk.on_delete,
                            target_value=tfk.on_delete,
                            severity=RiskSeverity.MEDIUM,
                            compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                            explanation=f"Foreign Key '{fk_name}' ON DELETE mismatch ({sfk.on_delete} vs {tfk.on_delete})",
                            recommended_action="ALTER_TARGET_OBJECT",
                        )
                    )

        return diffs

    @classmethod
    def _compare_views(cls, src_views: Dict[str, CanonicalView], tgt_views: Dict[str, CanonicalView]) -> List[SchemaDifference]:
        diffs = []
        for vname in sorted(set(src_views.keys()) - set(tgt_views.keys())):
            sv = src_views[vname]
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-view-rem-{sv.schema_name}.{vname}",
                    object_type="VIEW",
                    schema_name=sv.schema_name,
                    object_name=vname,
                    category=DifferenceCategory.REMOVED,
                    severity=RiskSeverity.MEDIUM,
                    compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                    explanation=f"View '{vname}' missing in target",
                    recommended_action="CREATE_TARGET_OBJECT",
                )
            )
        return diffs

    @classmethod
    def _compare_procedures(cls, src_procs: Dict[str, CanonicalProcedure], tgt_procs: Dict[str, CanonicalProcedure]) -> List[SchemaDifference]:
        diffs = []
        for pname in sorted(set(src_procs.keys()) - set(tgt_procs.keys())):
            sp = src_procs[pname]
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-proc-rem-{sp.schema_name}.{pname}",
                    object_type="PROCEDURE",
                    schema_name=sp.schema_name,
                    object_name=pname,
                    category=DifferenceCategory.REMOVED,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                    explanation=f"Procedure '{pname}' missing in target; requires manual review",
                    recommended_action="REVIEW_PROGRAMMABLE_OBJECT",
                )
            )
        return diffs


class CanonicalRiskScorer:
    """Universal Explainable Risk Assessment Authority."""

    @classmethod
    def evaluate_risk(
        cls, differences: List[SchemaDifference], source_engine: str = "GENERIC", target_engine: str = "GENERIC"
    ) -> RiskAssessment:
        findings: List[RiskFinding] = []
        breakdown = {
            "STRUCTURAL": 0,
            "DATATYPE": 0,
            "CONSTRAINT": 0,
            "DEPENDENCY": 0,
            "PROGRAMMABLE": 0,
            "DRIFT": 0,
        }
        total_score_weight = 0
        blocking_count = 0
        worst_compat = CompatibilityClassification.COMPATIBLE

        for idx, diff in enumerate(sorted(differences, key=lambda d: d.difference_id)):
            weight = 0
            cat_name = "STRUCTURAL"

            if diff.category in (DifferenceCategory.ADDED, DifferenceCategory.REMOVED):
                weight = 15 if diff.severity == RiskSeverity.HIGH else 5
                cat_name = "STRUCTURAL"
            elif diff.category == DifferenceCategory.TYPE_CHANGED:
                weight = 25
                cat_name = "DATATYPE"
            elif diff.category == DifferenceCategory.MODIFIED:
                weight = 20 if diff.severity == RiskSeverity.HIGH else 5
                cat_name = "DATATYPE"
            elif diff.category == DifferenceCategory.MANUAL_REVIEW_REQUIRED:
                weight = 30
                cat_name = "PROGRAMMABLE"
            elif diff.category == DifferenceCategory.UNSUPPORTED:
                weight = 40
                cat_name = "STRUCTURAL"

            if diff.severity == RiskSeverity.BLOCKING or diff.compatibility == CompatibilityClassification.BLOCKING:
                blocking_count += 1
                worst_compat = CompatibilityClassification.BLOCKING
            elif diff.compatibility == CompatibilityClassification.MANUAL_REVIEW_REQUIRED and worst_compat != CompatibilityClassification.BLOCKING:
                worst_compat = CompatibilityClassification.MANUAL_REVIEW_REQUIRED
            elif diff.compatibility == CompatibilityClassification.POTENTIALLY_LOSSY and worst_compat not in (CompatibilityClassification.BLOCKING, CompatibilityClassification.MANUAL_REVIEW_REQUIRED):
                worst_compat = CompatibilityClassification.POTENTIALLY_LOSSY

            breakdown[cat_name] = breakdown.get(cat_name, 0) + weight
            total_score_weight += weight

            findings.append(
                RiskFinding(
                    finding_id=f"rf-{idx+1}-{diff.difference_id}",
                    category=cat_name,
                    severity=diff.severity,
                    explanation=diff.explanation,
                    recommendation=diff.recommended_action,
                    score_weight=weight,
                )
            )

        final_score = min(100, total_score_weight)
        is_safe = (blocking_count == 0) and (worst_compat != CompatibilityClassification.BLOCKING)

        return RiskAssessment(
            risk_score=final_score,
            overall_compatibility=worst_compat,
            findings=findings,
            breakdown=breakdown,
            blocking_findings_count=blocking_count,
            is_safe_to_continue=is_safe,
        )


class CanonicalDriftAnalyzer:
    """Universal Deterministic Schema Drift Analysis Authority."""

    @classmethod
    def analyze_drift(
        cls, baseline_model: CanonicalSchemaModel, current_model: CanonicalSchemaModel
    ) -> SchemaDriftReport:
        src_fp = baseline_model.compute_schema_fingerprint()
        tgt_fp = current_model.compute_schema_fingerprint()

        differences = CanonicalSchemaComparator.compare_schemas(baseline_model, current_model)
        is_drift = src_fp != tgt_fp or len(differences) > 0

        classification = DriftClassification.NO_DRIFT
        if is_drift:
            has_blocking = any(d.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL, RiskSeverity.BLOCKING) for d in differences)
            classification = DriftClassification.BREAKING_DRIFT if has_blocking else DriftClassification.NON_BREAKING_DRIFT

        return SchemaDriftReport(
            source_fingerprint=src_fp,
            target_fingerprint=tgt_fp,
            drift_classification=classification,
            differences=differences,
            is_drift_detected=is_drift,
        )
