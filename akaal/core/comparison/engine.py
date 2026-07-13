"""
Akaal — Schema Comparison Engine
================================
Implements the central SchemaComparisonEngine class which orchestrates
structural schema comparison and compiles the DifferenceReport.
"""

import datetime
import hashlib
import json
import uuid
from typing import Any, Dict, List, Tuple
from akaal.core.models.enums import SystemType
from akaal.core.comparison.models import (
    ComparisonContext,
    Schema,
    DifferenceReport,
    ComparisonSummary,
    SchemaComparisonStatus,
    SchemaDifference,
    DifferenceAction,
    DifferenceCategory,
    DifferenceSeverity,
    MigrationImpact,
)
from akaal.core.comparison.validator import SchemaValidator
from akaal.core.comparison.support.identifier_resolver import resolve_identifier
from akaal.core.comparison.comparers import COMPARER_REGISTRY


def get_checksum_payload(schema: Schema, context: ComparisonContext) -> Dict[str, Any]:
    """
    Constructs a database-dialect-independent payload representation of a schema
    for structural checksum calculation.
    """
    payload: Dict[str, Any] = {}
    
    # Sort tables by name to be deterministic
    sorted_tables = sorted(schema.tables, key=lambda t: t.name.lower())
    for table in sorted_tables:
        tbl_name = resolve_identifier(table.name, context)
        
        # Columns normalization
        cols_data = {}
        for col in sorted(table.columns, key=lambda c: c.name.lower()):
            c_name = resolve_identifier(col.name, context)
            
            # Apply auto-pk default normalization
            d_val = col.default_value or "NULL"
            is_pk = table.primary_key is not None and col.name in table.primary_key.columns
            if is_pk and col.data_type == "INTEGER" and d_val in ("NULL", "NEXTVAL"):
                d_val = "AUTO_PK"
                
            cols_data[c_name] = {
                "name": c_name,
                "type": col.data_type,
                "nullable": col.nullable,
                "default": d_val
            }
            
        # PK
        pk_data = None
        if table.primary_key:
            pk_data = tuple(resolve_identifier(c, context) for c in table.primary_key.columns)
            
        # Indexes (ignoring naming differences when configured)
        idxs_data = []
        for idx in sorted(table.indexes, key=lambda i: i.name.lower()):
            if context.ignore_index_names:
                idx_name = "__IDX__" + "__".join(sorted(idx.columns))
            else:
                idx_name = idx.name
            idxs_data.append({
                "name": idx_name.lower(),
                "columns": tuple(resolve_identifier(c, context) for c in idx.columns),
                "unique": idx.unique
            })
        idxs_data.sort(key=lambda x: x["name"])
        
        # Foreign Keys
        fks_data = []
        for fk in sorted(table.foreign_keys, key=lambda f: f.name.lower()):
            if context.ignore_constraint_names:
                fk_name = "__FK__" + "__".join(fk.from_columns)
            else:
                fk_name = fk.name
            fks_data.append({
                "name": fk_name.lower(),
                "from_columns": tuple(resolve_identifier(c, context) for c in fk.from_columns),
                "to_table": resolve_identifier(fk.to_table, context),
                "to_columns": tuple(resolve_identifier(c, context) for c in fk.to_columns),
                "on_delete": fk.on_delete,
                "on_update": fk.on_update
            })
        fks_data.sort(key=lambda x: x["name"])
        
        # Constraints
        consts_data = []
        for c in sorted(table.constraints, key=lambda cn: cn.name.lower()):
            if context.ignore_constraint_names:
                c_name = c.type
            else:
                c_name = c.name
            consts_data.append({
                "name": c_name.lower(),
                "type": c.type,
                "columns": tuple(resolve_identifier(col, context) for col in c.columns),
                "definition": c.definition
            })
        consts_data.sort(key=lambda x: x["name"])
        
        payload[tbl_name] = {
            "name": tbl_name,
            "columns": cols_data,
            "primary_key": pk_data,
            "indexes": idxs_data,
            "foreign_keys": fks_data,
            "constraints": consts_data
        }
        
    return payload


def compute_schema_checksum(schema: Schema, context: ComparisonContext) -> str:
    """
    Computes a stable, reproducible SHA-256 fingerprint for a schema structure.
    """
    payload = get_checksum_payload(schema, context)
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def diff_sort_key(diff: SchemaDifference) -> Tuple[int, str, str, str]:
    """
    Deterministic sort order for schema differences.
    Sort priority: Category type, dot-path alphabetically, action, deterministic difference ID.
    """
    category_order = {
        DifferenceCategory.TABLE: 0,
        DifferenceCategory.COLUMN: 1,
        DifferenceCategory.PRIMARY_KEY: 2,
        DifferenceCategory.INDEX: 3,
        DifferenceCategory.FOREIGN_KEY: 4,
        DifferenceCategory.CONSTRAINT: 5,
    }
    cat_val = category_order.get(diff.category, 99)
    return (cat_val, diff.path.lower(), diff.action.value, diff.difference_id)


class SchemaComparisonEngine:
    """
    The orchestrator class of the Schema Comparison Engine.
    Executes pre-validation, processes table comparers, and generates DifferenceReports.
    """

    def __init__(self, context: ComparisonContext = ComparisonContext()) -> None:
        self.context = context
        self._validator = SchemaValidator()

    def compare(self, source: Schema, target: Schema) -> DifferenceReport:
        """
        Compares target schema structure against source schema definition.
        Returns a DifferenceReport detailing the additions, deletions, or alterations required.
        """
        # 1. Pre-validation of both schemas
        self._validator.validate(source)
        self._validator.validate(target)

        # 2. Extract and index tables by resolved name mapping
        source_tables = {resolve_identifier(t.name, self.context): t for t in source.tables}
        target_tables = {resolve_identifier(t.name, self.context): t for t in target.tables}

        # 3. Dynamic lookup of the registered TableComparer
        table_comparer = COMPARER_REGISTRY["TABLE"]()
        raw_differences: List[SchemaDifference] = []

        # Find missing tables (ADD Table)
        for tbl_name in sorted(source_tables.keys() - target_tables.keys()):
            raw_differences.extend(
                table_comparer.compare(
                    expected=source_tables[tbl_name],
                    actual=None,
                    context=self.context,
                )
            )

        # Find extra tables (REMOVE Table)
        for tbl_name in sorted(target_tables.keys() - source_tables.keys()):
            raw_differences.extend(
                table_comparer.compare(
                    expected=None,
                    actual=target_tables[tbl_name],
                    context=self.context,
                )
            )

        # Find common tables (MODIFY checks)
        for tbl_name in sorted(source_tables.keys() & target_tables.keys()):
            raw_differences.extend(
                table_comparer.compare(
                    expected=source_tables[tbl_name],
                    actual=target_tables[tbl_name],
                    context=self.context,
                )
            )

        # 4. Deterministic sorting of all raw differences
        sorted_differences = sorted(raw_differences, key=diff_sort_key)

        # 5. Compute metadata structural checksums
        source_checksum = compute_schema_checksum(source, self.context)
        target_checksum = compute_schema_checksum(target, self.context)

        # 6. Aggregate Comparison Summary Metrics
        added_count = 0
        removed_count = 0
        modified_count = 0
        info_count = 0
        warning_count = 0
        critical_count = 0

        for diff in sorted_differences:
            if diff.action == DifferenceAction.ADD:
                added_count += 1
            elif diff.action == DifferenceAction.REMOVE:
                removed_count += 1
            elif diff.action == DifferenceAction.MODIFY:
                modified_count += 1

            if diff.severity == DifferenceSeverity.INFO:
                info_count += 1
            elif diff.severity == DifferenceSeverity.WARNING:
                warning_count += 1
            elif diff.severity == DifferenceSeverity.CRITICAL:
                critical_count += 1

        summary = ComparisonSummary(
            total_objects=len(source_tables.keys() | target_tables.keys()),
            total_differences=len(sorted_differences),
            added=added_count,
            removed=removed_count,
            modified=modified_count,
            info=info_count,
            warning=warning_count,
            critical=critical_count,
        )

        status = SchemaComparisonStatus.IDENTICAL if not sorted_differences else SchemaComparisonStatus.DIFFERENT

        # 7. Construct DifferenceReport container
        report = DifferenceReport(
            report_id=str(uuid.uuid4()),
            report_version="1.0.0",
            comparison_timestamp=datetime.datetime.now(datetime.timezone.utc),
            source_vendor=source.vendor or SystemType.GENERIC,
            target_vendor=target.vendor or SystemType.GENERIC,
            engine_version="1.0.0",
            comparison_options=self.context,
            source_checksum=source_checksum,
            target_checksum=target_checksum,
            status=status,
            differences=tuple(sorted_differences),
            summary_statistics=summary,
        )

        return report
