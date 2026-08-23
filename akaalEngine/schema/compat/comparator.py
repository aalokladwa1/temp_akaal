"""
akaalEngine.schema.compat.comparator
====================================
Canonical Schema Comparator & Incremental DDL Generation Engine (CONS-001).
Provides database-agnostic schema comparison between two CanonicalSchemaModels,
producing deterministic, machine-readable SchemaDifference objects and
incremental ALTER DDL representations without mutating input models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer
from akaalEngine.schema.models.programmables import CanonicalRoutine
from akaalEngine.schema.models.schema import CanonicalSchemaModel, CanonicalView
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.types.registry import CanonicalTypeRegistry


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


@dataclass(frozen=True)
class SchemaDifference:
    """Strongly-typed, immutable representation of a single schema difference."""
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


@dataclass(frozen=True)
class SchemaDriftReport:
    """Deterministic schema drift evaluation report."""
    source_fingerprint: str
    target_fingerprint: str
    drift_classification: DriftClassification
    differences: Tuple[SchemaDifference, ...]
    is_drift_detected: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_fingerprint": self.source_fingerprint,
            "target_fingerprint": self.target_fingerprint,
            "drift_classification": self.drift_classification.value,
            "differences": [d.to_dict() for d in self.differences],
            "is_drift_detected": self.is_drift_detected,
        }


@dataclass(frozen=True)
class IncrementalDDLAction:
    """Represents a generated incremental ALTER DDL action statement."""
    action_type: str
    object_type: str
    schema_name: str
    object_name: str
    target_dialect: str
    ddl_statement: Optional[str]
    is_safe: bool
    is_destructive: bool
    requires_rebuild: bool
    unsupported_reason: Optional[str] = None


class CanonicalSchemaComparator:
    """
    Universal Canonical Schema Comparison Engine.
    Compares source and target CanonicalSchemaModels and produces deterministic SchemaDifferences.
    Preserves exact physical identifier casing, constraint actions, procedures, and view definitions.
    """

    @classmethod
    def compare_schemas(
        cls,
        source_model: CanonicalSchemaModel,
        target_model: CanonicalSchemaModel,
    ) -> Tuple[SchemaDifference, ...]:
        diffs: List[SchemaDifference] = []

        src_tables_exact = {f"{t.schema_name}.{t.table_name}": t for t in source_model.tables}
        tgt_tables_exact = {f"{t.schema_name}.{t.table_name}": t for t in target_model.tables}

        src_tables_lower = {f"{t.schema_name}.{t.table_name}".lower(): t for t in source_model.tables}
        tgt_tables_lower = {f"{t.schema_name}.{t.table_name}".lower(): t for t in target_model.tables}

        matched_tgt_keys = set()

        # Missing or modified tables in target
        for qname, st in sorted(src_tables_exact.items(), key=lambda x: x[0]):
            lower_qname = qname.lower()
            if qname in tgt_tables_exact:
                tt = tgt_tables_exact[qname]
                matched_tgt_keys.add(qname)
                diffs.extend(cls._compare_table_details(st, tt))
            elif lower_qname in tgt_tables_lower:
                tt = tgt_tables_lower[lower_qname]
                matched_tgt_keys.add(f"{tt.schema_name}.{tt.table_name}")
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-tbl-case-{st.schema_name}.{st.table_name}",
                        object_type="TABLE",
                        schema_name=st.schema_name,
                        object_name=st.table_name,
                        category=DifferenceCategory.IDENTITY_CHANGED,
                        property_name="table_name",
                        source_value=st.table_name,
                        target_value=tt.table_name,
                        severity=RiskSeverity.MEDIUM,
                        compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                        explanation=f"Table '{st.table_name}' case sensitivity mismatch with target '{tt.table_name}'.",
                        recommended_action="RENAME_OR_REVIEW",
                    )
                )
                diffs.extend(cls._compare_table_details(st, tt))
            else:
                diff_id = f"diff-tbl-rem-{st.schema_name}.{st.table_name}"
                diffs.append(
                    SchemaDifference(
                        difference_id=diff_id,
                        object_type="TABLE",
                        schema_name=st.schema_name,
                        object_name=st.table_name,
                        category=DifferenceCategory.REMOVED,
                        source_value=st,
                        severity=RiskSeverity.HIGH,
                        compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                        explanation=f"Table '{st.table_name}' exists in source schema but is missing in target schema.",
                        recommended_action="CREATE_TARGET_OBJECT",
                    )
                )

        # Extra tables in target
        for qname, tt in sorted(tgt_tables_exact.items(), key=lambda x: x[0]):
            if qname not in matched_tgt_keys:
                diff_id = f"diff-tbl-add-{tt.schema_name}.{tt.table_name}"
                diffs.append(
                    SchemaDifference(
                        difference_id=diff_id,
                        object_type="TABLE",
                        schema_name=tt.schema_name,
                        object_name=tt.table_name,
                        category=DifferenceCategory.ADDED,
                        target_value=tt,
                        severity=RiskSeverity.INFO,
                        compatibility=CompatibilityClassification.COMPATIBLE,
                        explanation=f"Extra table '{tt.table_name}' exists in target schema.",
                        recommended_action="NO_ACTION",
                    )
                )

        # Views comparison
        diffs.extend(cls._compare_views(source_model.views, target_model.views))

        # Procedures & Routines comparison
        diffs.extend(cls._compare_procedures(source_model.routines, target_model.routines))

        diffs.sort(key=lambda d: d.difference_id)
        return tuple(diffs)

    @classmethod
    def _compare_table_details(
        cls,
        src_t: CanonicalTable,
        tgt_t: CanonicalTable,
    ) -> List[SchemaDifference]:
        diffs: List[SchemaDifference] = []
        s_name = src_t.schema_name
        t_name = src_t.table_name

        src_cols_exact = {c.name: c for c in src_t.columns}
        tgt_cols_exact = {c.name: c for c in tgt_t.columns}

        src_cols_lower = {c.name.lower(): c for c in src_t.columns}
        tgt_cols_lower = {c.name.lower(): c for c in tgt_t.columns}

        matched_tgt_cols = set()

        # Missing or modified columns in target
        for cname, sc in sorted(src_cols_exact.items(), key=lambda x: x[0]):
            lower_cname = cname.lower()
            if cname in tgt_cols_exact:
                tc = tgt_cols_exact[cname]
                matched_tgt_cols.add(cname)
                diffs.extend(cls._compare_column_attributes(s_name, t_name, sc, tc))
            elif lower_cname in tgt_cols_lower:
                tc = tgt_cols_lower[lower_cname]
                matched_tgt_cols.add(tc.name)
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-case-{s_name}.{t_name}.{sc.name}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.IDENTITY_CHANGED,
                        property_name="column_name",
                        source_value=sc.name,
                        target_value=tc.name,
                        severity=RiskSeverity.MEDIUM,
                        compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                        explanation=f"Column '{sc.name}' case sensitivity mismatch with target column '{tc.name}' in table '{t_name}'.",
                        recommended_action="RENAME_OR_REVIEW",
                    )
                )
                diffs.extend(cls._compare_column_attributes(s_name, t_name, sc, tc))
            else:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-rem-{s_name}.{t_name}.{sc.name}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.REMOVED,
                        property_name=sc.name,
                        source_value=sc,
                        severity=RiskSeverity.HIGH,
                        compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                        explanation=f"Column '{sc.name}' in table '{t_name}' is missing in target.",
                        recommended_action="ALTER_TARGET_OBJECT",
                    )
                )

        # Extra columns in target
        for cname, tc in sorted(tgt_cols_exact.items(), key=lambda x: x[0]):
            if cname not in matched_tgt_cols:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-add-{s_name}.{t_name}.{tc.name}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.ADDED,
                        property_name=tc.name,
                        target_value=tc,
                        severity=RiskSeverity.INFO,
                        compatibility=CompatibilityClassification.COMPATIBLE,
                        explanation=f"Extra column '{tc.name}' exists in target table '{t_name}'.",
                        recommended_action="NO_ACTION",
                    )
                )

        # Primary Key comparison
        src_pk_cols = tuple(c if isinstance(c, str) else getattr(c, "name", str(c)) for c in src_t.primary_key.columns) if src_t.primary_key and hasattr(src_t.primary_key, "columns") else ()
        tgt_pk_cols = tuple(c if isinstance(c, str) else getattr(c, "name", str(c)) for c in tgt_t.primary_key.columns) if tgt_t.primary_key and hasattr(tgt_t.primary_key, "columns") else ()
        if src_pk_cols != tgt_pk_cols:
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-pk-{s_name}.{t_name}",
                    object_type="PRIMARY_KEY",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.CONSTRAINT_CHANGED,
                    property_name="primary_key",
                    source_value=src_pk_cols,
                    target_value=tgt_pk_cols,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                    explanation=f"Primary key mismatch on table '{t_name}' (source: {src_pk_cols}, target: {tgt_pk_cols}).",
                    recommended_action="ALTER_PRIMARY_KEY",
                )
            )

        # Foreign Key comparison (including ON DELETE and ON UPDATE actions)
        src_fks = {fk.name or f"fk_{idx}": fk for idx, fk in enumerate(src_t.foreign_keys)}
        tgt_fks = {fk.name or f"fk_{idx}": fk for idx, fk in enumerate(tgt_t.foreign_keys)}

        for fk_name, sfk in sorted(src_fks.items(), key=lambda x: x[0]):
            if fk_name in tgt_fks:
                tfk = tgt_fks[fk_name]
                if sfk.on_delete != tfk.on_delete:
                    diffs.append(
                        SchemaDifference(
                            difference_id=f"diff-fk-action-del-{s_name}.{t_name}.{fk_name}",
                            object_type="FOREIGN_KEY",
                            schema_name=s_name,
                            object_name=t_name,
                            category=DifferenceCategory.CONSTRAINT_CHANGED,
                            property_name="on_delete",
                            source_value=sfk.on_delete,
                            target_value=tfk.on_delete,
                            severity=RiskSeverity.MEDIUM,
                            compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                            explanation=f"Foreign Key '{fk_name}' ON DELETE mismatch ({sfk.on_delete} vs {tfk.on_delete}).",
                            recommended_action="ALTER_TARGET_OBJECT",
                        )
                    )
                if sfk.on_update != tfk.on_update:
                    diffs.append(
                        SchemaDifference(
                            difference_id=f"diff-fk-action-upd-{s_name}.{t_name}.{fk_name}",
                            object_type="FOREIGN_KEY",
                            schema_name=s_name,
                            object_name=t_name,
                            category=DifferenceCategory.CONSTRAINT_CHANGED,
                            property_name="on_update",
                            source_value=sfk.on_update,
                            target_value=tfk.on_update,
                            severity=RiskSeverity.MEDIUM,
                            compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                            explanation=f"Foreign Key '{fk_name}' ON UPDATE mismatch ({sfk.on_update} vs {tfk.on_update}).",
                            recommended_action="ALTER_TARGET_OBJECT",
                        )
                    )
                if sfk.referenced_table != tfk.referenced_table or tuple(sfk.columns) != tuple(tfk.columns) or tuple(sfk.referenced_columns) != tuple(tfk.referenced_columns):
                    diffs.append(
                        SchemaDifference(
                            difference_id=f"diff-fk-def-{s_name}.{t_name}.{fk_name}",
                            object_type="FOREIGN_KEY",
                            schema_name=s_name,
                            object_name=t_name,
                            category=DifferenceCategory.CONSTRAINT_CHANGED,
                            property_name="definition",
                            source_value=f"{sfk.referenced_table}({','.join(sfk.referenced_columns)})",
                            target_value=f"{tfk.referenced_table}({','.join(tfk.referenced_columns)})",
                            severity=RiskSeverity.HIGH,
                            compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                            explanation=f"Foreign Key '{fk_name}' definition mismatch on table '{t_name}'.",
                            recommended_action="ALTER_TARGET_OBJECT",
                        )
                    )
            else:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-fk-rem-{s_name}.{t_name}.{fk_name}",
                        object_type="FOREIGN_KEY",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.REMOVED,
                        property_name=fk_name,
                        source_value=sfk,
                        severity=RiskSeverity.MEDIUM,
                        compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                        explanation=f"Foreign Key '{fk_name}' missing in target table '{t_name}'.",
                        recommended_action="CREATE_FOREIGN_KEY",
                    )
                )

        for fk_name, tfk in sorted(tgt_fks.items(), key=lambda x: x[0]):
            if fk_name not in src_fks:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-fk-add-{s_name}.{t_name}.{fk_name}",
                        object_type="FOREIGN_KEY",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.ADDED,
                        property_name=fk_name,
                        target_value=tfk,
                        severity=RiskSeverity.INFO,
                        compatibility=CompatibilityClassification.COMPATIBLE,
                        explanation=f"Extra Foreign Key '{fk_name}' exists in target table '{t_name}'.",
                        recommended_action="NO_ACTION",
                    )
                )

        return diffs

    @classmethod
    def _compare_column_attributes(
        cls,
        s_name: str,
        t_name: str,
        sc: CanonicalColumn,
        tc: CanonicalColumn,
    ) -> List[SchemaDifference]:
        diffs: List[SchemaDifference] = []
        sc_cat = sc.canonical_type.category
        tc_cat = tc.canonical_type.category

        # Category comparison
        if sc_cat != tc_cat:
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-type-{s_name}.{t_name}.{sc.name}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.TYPE_CHANGED,
                    property_name=sc.name,
                    source_value=sc,
                    target_value=tc,
                    severity=RiskSeverity.MEDIUM,
                    compatibility=CompatibilityClassification.POTENTIALLY_LOSSY,
                    explanation=f"Column '{sc.name}' type category mismatch ({sc_cat.value} vs {tc_cat.value}).",
                    recommended_action="REVIEW_TYPE_CONVERSION",
                )
            )

        # Length narrowing / widening check
        sc_len = sc.length or sc.canonical_type.length
        tc_len = tc.length or tc.canonical_type.length
        if sc_len and tc_len:
            if sc_len > tc_len:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-len-narrow-{s_name}.{t_name}.{sc.name}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.MODIFIED,
                        property_name="length",
                        source_value=sc_len,
                        target_value=tc_len,
                        severity=RiskSeverity.HIGH,
                        compatibility=CompatibilityClassification.POTENTIALLY_LOSSY,
                        explanation=f"Column '{sc.name}' length narrowing ({sc_len} -> {tc_len}) may truncate data.",
                        recommended_action="REVIEW_TYPE_CONVERSION",
                    )
                )
            elif sc_len < tc_len:
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-col-len-wide-{s_name}.{t_name}.{sc.name}",
                        object_type="COLUMN",
                        schema_name=s_name,
                        object_name=t_name,
                        category=DifferenceCategory.MODIFIED,
                        property_name="length",
                        source_value=sc_len,
                        target_value=tc_len,
                        severity=RiskSeverity.LOW,
                        compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                        explanation=f"Column '{sc.name}' length widening ({sc_len} -> {tc_len}) is safe.",
                        recommended_action="NO_ACTION",
                    )
                )

        # Precision & scale narrowing check
        sc_prec = sc.precision or sc.canonical_type.precision
        tc_prec = tc.precision or tc.canonical_type.precision
        if sc_prec and tc_prec and sc_prec > tc_prec:
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-prec-narrow-{s_name}.{t_name}.{sc.name}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.MODIFIED,
                    property_name="precision",
                    source_value=sc_prec,
                    target_value=tc_prec,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.POTENTIALLY_LOSSY,
                    explanation=f"Column '{sc.name}' precision narrowing ({sc_prec} -> {tc_prec}) may truncate numeric data.",
                    recommended_action="REVIEW_TYPE_CONVERSION",
                )
            )

        sc_scale = sc.scale if sc.scale is not None else sc.canonical_type.scale
        tc_scale = tc.scale if tc.scale is not None else tc.canonical_type.scale
        if sc_scale is not None and tc_scale is not None and sc_scale > tc_scale:
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-scale-narrow-{s_name}.{t_name}.{sc.name}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.MODIFIED,
                    property_name="scale",
                    source_value=sc_scale,
                    target_value=tc_scale,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.POTENTIALLY_LOSSY,
                    explanation=f"Column '{sc.name}' scale narrowing ({sc_scale} -> {tc_scale}) may truncate decimal precision.",
                    recommended_action="REVIEW_TYPE_CONVERSION",
                )
            )

        # Nullability mismatch
        sc_null = getattr(sc, "nullable", getattr(sc, "is_nullable", True))
        tc_null = getattr(tc, "nullable", getattr(tc, "is_nullable", True))
        if sc_null != tc_null:
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-null-{s_name}.{t_name}.{sc.name}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.NULLABILITY_CHANGED,
                    property_name=sc.name,
                    source_value=sc_null,
                    target_value=tc_null,
                    severity=RiskSeverity.MEDIUM if not sc_null else RiskSeverity.LOW,
                    compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                    explanation=f"Column '{sc.name}' nullability mismatch (source: {sc_null}, target: {tc_null}).",
                    recommended_action="ALTER_TARGET_OBJECT",
                )
            )

        # Default expression mismatch
        if sc.default_expression != tc.default_expression:
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-col-default-{s_name}.{t_name}.{sc.name}",
                    object_type="COLUMN",
                    schema_name=s_name,
                    object_name=t_name,
                    category=DifferenceCategory.DEFAULT_CHANGED,
                    property_name="default_expression",
                    source_value=sc.default_expression,
                    target_value=tc.default_expression,
                    severity=RiskSeverity.LOW,
                    compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                    explanation=f"Column '{sc.name}' default expression mismatch (source: {sc.default_expression}, target: {tc.default_expression}).",
                    recommended_action="ALTER_TARGET_OBJECT",
                )
            )

        return diffs

    @classmethod
    def _compare_views(
        cls, src_views: Sequence[CanonicalView], tgt_views: Sequence[CanonicalView]
    ) -> List[SchemaDifference]:
        diffs = []
        src_map = {f"{v.schema_name}.{v.view_name}": v for v in src_views}
        tgt_map = {f"{v.schema_name}.{v.view_name}": v for v in tgt_views}

        # Missing views in target
        for qname in sorted(set(src_map.keys()) - set(tgt_map.keys())):
            sv = src_map[qname]
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-view-rem-{sv.schema_name}.{sv.view_name}",
                    object_type="VIEW",
                    schema_name=sv.schema_name,
                    object_name=sv.view_name,
                    category=DifferenceCategory.REMOVED,
                    source_value=sv,
                    severity=RiskSeverity.MEDIUM,
                    compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                    explanation=f"View '{sv.view_name}' exists in source but is missing in target.",
                    recommended_action="CREATE_TARGET_OBJECT",
                )
            )

        # Extra views in target
        for qname in sorted(set(tgt_map.keys()) - set(src_map.keys())):
            tv = tgt_map[qname]
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-view-add-{tv.schema_name}.{tv.view_name}",
                    object_type="VIEW",
                    schema_name=tv.schema_name,
                    object_name=tv.view_name,
                    category=DifferenceCategory.ADDED,
                    target_value=tv,
                    severity=RiskSeverity.INFO,
                    compatibility=CompatibilityClassification.COMPATIBLE,
                    explanation=f"Extra view '{tv.view_name}' exists in target schema.",
                    recommended_action="NO_ACTION",
                )
            )

        # Modified view definitions
        for qname in sorted(set(src_map.keys()).intersection(set(tgt_map.keys()))):
            sv = src_map[qname]
            tv = tgt_map[qname]
            if sv.view_definition and tv.view_definition and sv.view_definition.strip() != tv.view_definition.strip():
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-view-def-{sv.schema_name}.{sv.view_name}",
                        object_type="VIEW",
                        schema_name=sv.schema_name,
                        object_name=sv.view_name,
                        category=DifferenceCategory.DEFINITION_CHANGED,
                        property_name="view_definition",
                        source_value=sv.view_definition,
                        target_value=tv.view_definition,
                        severity=RiskSeverity.MEDIUM,
                        compatibility=CompatibilityClassification.COMPATIBLE_WITH_CONVERSION,
                        explanation=f"View '{sv.view_name}' definition differs between source and target.",
                        recommended_action="RECREATE_VIEW",
                    )
                )

        return diffs

    @classmethod
    def _compare_procedures(
        cls, src_procs: Sequence[CanonicalRoutine], tgt_procs: Sequence[CanonicalRoutine]
    ) -> List[SchemaDifference]:
        diffs = []
        src_map = {f"{p.schema_name}.{p.name}": p for p in src_procs}
        tgt_map = {f"{p.schema_name}.{p.name}": p for p in tgt_procs}

        # Missing procedures in target
        for qname in sorted(set(src_map.keys()) - set(tgt_map.keys())):
            sp = src_map[qname]
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-proc-rem-{sp.schema_name}.{sp.name}",
                    object_type="PROCEDURE",
                    schema_name=sp.schema_name,
                    object_name=sp.name,
                    category=DifferenceCategory.REMOVED,
                    source_value=sp,
                    severity=RiskSeverity.HIGH,
                    compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                    explanation=f"Procedure '{sp.name}' exists in source but is missing in target; requires manual review.",
                    recommended_action="REVIEW_PROGRAMMABLE_OBJECT",
                )
            )

        # Extra procedures in target
        for qname in sorted(set(tgt_map.keys()) - set(src_map.keys())):
            tp = tgt_map[qname]
            diffs.append(
                SchemaDifference(
                    difference_id=f"diff-proc-add-{tp.schema_name}.{tp.name}",
                    object_type="PROCEDURE",
                    schema_name=tp.schema_name,
                    object_name=tp.name,
                    category=DifferenceCategory.ADDED,
                    target_value=tp,
                    severity=RiskSeverity.INFO,
                    compatibility=CompatibilityClassification.COMPATIBLE,
                    explanation=f"Extra procedure '{tp.name}' exists in target schema.",
                    recommended_action="NO_ACTION",
                )
            )

        # Modified procedure definitions
        for qname in sorted(set(src_map.keys()).intersection(set(tgt_map.keys()))):
            sp = src_map[qname]
            tp = tgt_map[qname]
            if sp.definition_sql and tp.definition_sql and sp.definition_sql.strip() != tp.definition_sql.strip():
                diffs.append(
                    SchemaDifference(
                        difference_id=f"diff-proc-def-{sp.schema_name}.{sp.name}",
                        object_type="PROCEDURE",
                        schema_name=sp.schema_name,
                        object_name=sp.name,
                        category=DifferenceCategory.DEFINITION_CHANGED,
                        property_name="definition_sql",
                        source_value=sp.definition_sql,
                        target_value=tp.definition_sql,
                        severity=RiskSeverity.HIGH,
                        compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                        explanation=f"Procedure '{sp.name}' definition SQL differs between source and target.",
                        recommended_action="REVIEW_PROGRAMMABLE_OBJECT",
                    )
                )

        return diffs


class SchemaDiffEngine:
    """
    Transforms structured SchemaDifferences into incremental ALTER DDL actions for target database dialects.
    Reuses existing akaalEngine.schema.ddl infrastructure without inventing a parallel SQL dialect engine.
    Applies target vendor identifier quoting and canonical datatype resolution.
    """

    @classmethod
    def generate_incremental_ddl(
        cls,
        differences: Sequence[SchemaDifference],
        target_dialect: str = "postgresql",
    ) -> Tuple[IncrementalDDLAction, ...]:
        actions: List[IncrementalDDLAction] = []
        dialect = target_dialect.lower().strip()

        for diff in differences:
            if diff.object_type == "COLUMN":
                q_table = IdentifierSanitizer.format_qualified_name(diff.schema_name, diff.object_name, dialect)
                raw_col_name = diff.property_name or diff.object_name
                q_col = IdentifierSanitizer.quote_identifier(raw_col_name, dialect)

                if diff.category == DifferenceCategory.REMOVED:
                    # Missing column in target -> ADD COLUMN
                    col_obj = diff.source_value if isinstance(diff.source_value, CanonicalColumn) else None
                    if col_obj:
                        emission = CanonicalTypeRegistry.emit_target_type(dialect, col_obj.canonical_type)
                        type_str = emission.target_native_type
                        null_str = " NOT NULL" if not col_obj.nullable else ""
                        default_str = f" DEFAULT {col_obj.default_expression}" if col_obj.default_expression else ""
                        identity_str = " GENERATED ALWAYS AS IDENTITY" if col_obj.is_identity else ""
                        ddl_sql = f"ALTER TABLE {q_table} ADD COLUMN {q_col} {type_str}{null_str}{default_str}{identity_str};"
                        actions.append(
                            IncrementalDDLAction(
                                action_type="ADD_COLUMN",
                                object_type="COLUMN",
                                schema_name=diff.schema_name,
                                object_name=diff.object_name,
                                target_dialect=dialect,
                                ddl_statement=ddl_sql,
                                is_safe=True,
                                is_destructive=False,
                                requires_rebuild=False,
                            )
                        )
                    else:
                        actions.append(
                            IncrementalDDLAction(
                                action_type="ADD_COLUMN",
                                object_type="COLUMN",
                                schema_name=diff.schema_name,
                                object_name=diff.object_name,
                                target_dialect=dialect,
                                ddl_statement="",
                                is_safe=False,
                                is_destructive=False,
                                requires_rebuild=False,
                                unsupported_reason="UNSUPPORTED_INCREMENTAL_DDL: Missing canonical column data-type definition for incremental DDL generation.",
                            )
                        )

                elif diff.category == DifferenceCategory.ADDED:
                    # Extra column in target -> DROP COLUMN
                    ddl_sql = f"ALTER TABLE {q_table} DROP COLUMN {q_col};"
                    actions.append(
                        IncrementalDDLAction(
                            action_type="DROP_COLUMN",
                            object_type="COLUMN",
                            schema_name=diff.schema_name,
                            object_name=diff.object_name,
                            target_dialect=dialect,
                            ddl_statement=ddl_sql,
                            is_safe=False,
                            is_destructive=True,
                            requires_rebuild=False,
                        )
                    )

                elif diff.category == DifferenceCategory.TYPE_CHANGED:
                    # Alter column type
                    if dialect == "sqlite":
                        actions.append(
                            IncrementalDDLAction(
                                action_type="ALTER_TYPE",
                                object_type="COLUMN",
                                schema_name=diff.schema_name,
                                object_name=diff.object_name,
                                target_dialect=dialect,
                                ddl_statement=None,
                                is_safe=False,
                                is_destructive=False,
                                requires_rebuild=True,
                                unsupported_reason="SQLite does not support direct ALTER COLUMN TYPE; table rebuild required.",
                            )
                        )
                    else:
                        col_src = diff.source_value if isinstance(diff.source_value, CanonicalColumn) else None
                        if col_src:
                            emission = CanonicalTypeRegistry.emit_target_type(dialect, col_src.canonical_type)
                            target_type = emission.target_native_type
                            if dialect in ("mysql", "mariadb"):
                                ddl_sql = f"ALTER TABLE {q_table} MODIFY COLUMN {q_col} {target_type};"
                            elif dialect in ("oracle",):
                                ddl_sql = f"ALTER TABLE {q_table} MODIFY ({q_col} {target_type});"
                            else:
                                ddl_sql = f"ALTER TABLE {q_table} ALTER COLUMN {q_col} TYPE {target_type};"

                            actions.append(
                                IncrementalDDLAction(
                                    action_type="ALTER_TYPE",
                                    object_type="COLUMN",
                                    schema_name=diff.schema_name,
                                    object_name=diff.object_name,
                                    target_dialect=dialect,
                                    ddl_statement=ddl_sql,
                                    is_safe=False,
                                    is_destructive=False,
                                    requires_rebuild=False,
                                )
                            )
                        else:
                            actions.append(
                                IncrementalDDLAction(
                                    action_type="ALTER_TYPE",
                                    object_type="COLUMN",
                                    schema_name=diff.schema_name,
                                    object_name=diff.object_name,
                                    target_dialect=dialect,
                                    ddl_statement="",
                                    is_safe=False,
                                    is_destructive=False,
                                    requires_rebuild=False,
                                    unsupported_reason="UNSUPPORTED_INCREMENTAL_DDL: Missing canonical column data-type definition for type alter DDL generation.",
                                )
                            )

            elif diff.object_type == "TABLE" and diff.category == DifferenceCategory.REMOVED:
                tbl_obj = diff.source_value if isinstance(diff.source_value, CanonicalTable) else None
                if tbl_obj:
                    try:
                        emitter = DDLGenerator.get_emitter(dialect)
                        artifacts = emitter.emit_table_artifacts(tbl_obj)
                        ddl_sql = "\n".join(art.sql for art in artifacts if art.sql)
                        actions.append(
                            IncrementalDDLAction(
                                action_type="CREATE_TABLE",
                                object_type="TABLE",
                                schema_name=diff.schema_name,
                                object_name=diff.object_name,
                                target_dialect=dialect,
                                ddl_statement=ddl_sql,
                                is_safe=True,
                                is_destructive=False,
                                requires_rebuild=False,
                            )
                        )
                    except Exception as e:
                        actions.append(
                            IncrementalDDLAction(
                                action_type="CREATE_TABLE",
                                object_type="TABLE",
                                schema_name=diff.schema_name,
                                object_name=diff.object_name,
                                target_dialect=dialect,
                                ddl_statement=None,
                                is_safe=False,
                                is_destructive=False,
                                requires_rebuild=False,
                                unsupported_reason=f"Failed to generate CREATE TABLE DDL: {e}",
                            )
                        )
                else:
                    actions.append(
                        IncrementalDDLAction(
                            action_type="CREATE_TABLE",
                            object_type="TABLE",
                            schema_name=diff.schema_name,
                            object_name=diff.object_name,
                            target_dialect=dialect,
                            ddl_statement=None,
                            is_safe=False,
                            is_destructive=False,
                            requires_rebuild=False,
                            unsupported_reason="Target emitter requires source CanonicalTable object to generate CREATE TABLE DDL.",
                        )
                    )

        return tuple(actions)


class CanonicalDriftAnalyzer:
    """Universal Deterministic Schema Drift Analysis Authority for #4 Schema."""

    @classmethod
    def analyze_drift(
        cls, baseline_model: CanonicalSchemaModel, current_model: CanonicalSchemaModel
    ) -> SchemaDriftReport:
        src_fp = baseline_model.compute_schema_fingerprint()
        tgt_fp = current_model.compute_schema_fingerprint()

        differences = CanonicalSchemaComparator.compare_schemas(baseline_model, current_model)
        is_drift = (src_fp != tgt_fp) or (len(differences) > 0)

        classification = DriftClassification.NO_DRIFT
        if is_drift:
            has_breaking = any(
                d.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL, RiskSeverity.BLOCKING)
                or d.compatibility in (CompatibilityClassification.BLOCKING, CompatibilityClassification.MANUAL_REVIEW_REQUIRED, CompatibilityClassification.UNSUPPORTED)
                for d in differences
            )
            classification = DriftClassification.BREAKING_DRIFT if has_breaking else DriftClassification.NON_BREAKING_DRIFT

        return SchemaDriftReport(
            source_fingerprint=src_fp,
            target_fingerprint=tgt_fp,
            drift_classification=classification,
            differences=tuple(differences),
            is_drift_detected=is_drift,
        )
