"""
Akaal — Schema Difference Serializer
====================================
Handles polymorphic JSON serialization and deserialization of DifferenceReports.
Ensures backward compatibility mapping layers and handles nested models.
"""

import datetime
import json
from enum import Enum
from typing import Any, Dict, List, Optional
from akaal.core.models.enums import SystemType
from akaal.core.comparison.models import (
    ComparisonContext,
    DifferenceReport,
    ComparisonSummary,
    SchemaComparisonStatus,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    TableDifference,
    ColumnDifference,
    PrimaryKeyDifference,
    ForeignKeyDifference,
    IndexDifference,
    ConstraintDifference,
    ColumnSchema,
    TableSchema,
    PrimaryKeySchema,
    ForeignKeySchema,
    IndexSchema,
    ConstraintSchema,
    SerializationError,
    IdentityMode,
    IdentityDefinition,
)


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively serializes dataclasses, tuples, enums, and datetimes to dictionaries."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (tuple, list)):
        return [_dataclass_to_dict(x) for x in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def _deserialize_identity(data: Optional[Dict[str, Any]]) -> Optional[IdentityDefinition]:
    if not data:
        return None
    return IdentityDefinition(
        mode=IdentityMode(data["mode"]),
        start=data.get("start", 1),
        increment=data.get("increment", 1),
        min_value=data.get("min_value"),
        max_value=data.get("max_value"),
        cycle=data.get("cycle", False),
        cache=data.get("cache"),
        order=data.get("order", False),
        explicit_insert_policy=data.get("explicit_insert_policy", "BLOCKED"),
        source_engine=data.get("source_engine"),
        source_version=data.get("source_version"),
    )


def _deserialize_column(data: Optional[Dict[str, Any]]) -> Optional[ColumnSchema]:
    if not data:
        return None
    return ColumnSchema(
        name=data["name"],
        data_type=data["data_type"],
        raw_type=data["raw_type"],
        nullable=data["nullable"],
        default_value=data.get("default_value"),
        raw_default=data.get("raw_default"),
        identity=_deserialize_identity(data.get("identity")),
    )


def _deserialize_pk(data: Optional[Dict[str, Any]]) -> Optional[PrimaryKeySchema]:
    if not data:
        return None
    return PrimaryKeySchema(
        name=data.get("name"),
        columns=tuple(data["columns"]),
    )


def _deserialize_fk(data: Optional[Dict[str, Any]]) -> Optional[ForeignKeySchema]:
    if not data:
        return None
    return ForeignKeySchema(
        name=data["name"],
        from_columns=tuple(data["from_columns"]),
        to_table=data["to_table"],
        to_columns=tuple(data["to_columns"]),
        on_delete=data.get("on_delete"),
        on_update=data.get("on_update"),
    )


def _deserialize_index(data: Optional[Dict[str, Any]]) -> Optional[IndexSchema]:
    if not data:
        return None
    return IndexSchema(
        name=data["name"],
        columns=tuple(data["columns"]),
        unique=data["unique"],
    )


def _deserialize_constraint(data: Optional[Dict[str, Any]]) -> Optional[ConstraintSchema]:
    if not data:
        return None
    return ConstraintSchema(
        name=data["name"],
        type=data["type"],
        columns=tuple(data.get("columns", ())),
        definition=data.get("definition"),
    )


def _deserialize_table(data: Optional[Dict[str, Any]]) -> Optional[TableSchema]:
    if not data:
        return None
    return TableSchema(
        name=data["name"],
        columns=tuple(_deserialize_column(c) for c in data.get("columns", ())),
        primary_key=_deserialize_pk(data.get("primary_key")),
        foreign_keys=tuple(_deserialize_fk(f) for f in data.get("foreign_keys", ())),
        indexes=tuple(_deserialize_index(i) for i in data.get("indexes", ())),
        constraints=tuple(_deserialize_constraint(c) for c in data.get("constraints", ())),
    )


class SchemaDifferenceSerializer:
    """
    Serializes and deserializes DifferenceReports and polymorphic differences.
    Maintains backward compatibility across versions.
    """

    @staticmethod
    def serialize_report(report: DifferenceReport) -> str:
        """Converts a DifferenceReport object to a JSON string."""
        try:
            dict_data = _dataclass_to_dict(report)
            return json.dumps(dict_data, indent=2)
        except Exception as exc:
            raise SerializationError(f"Failed to serialize DifferenceReport: {exc}") from exc

    @staticmethod
    def deserialize_report(report_json: str) -> DifferenceReport:
        """Restores a DifferenceReport instance from a JSON string."""
        try:
            data = json.loads(report_json)
        except Exception as exc:
            raise SerializationError(f"Failed to parse JSON string: {exc}") from exc

        # 1. Version Compatibility Check
        version = data.get("report_version", "1.0.0")
        major_ver = int(version.split(".")[0])
        if major_ver > 1:
            raise SerializationError(f"Unsupported report major version: '{version}' (expected '1.x.y')")

        try:
            # 2. Reconstruct context (safely fallback for missing fields in forward compatibility)
            ctx_data = data.get("comparison_options", {})
            context = ComparisonContext(
                strict_type_checking=ctx_data.get("strict_type_checking", True),
                strict_length_precision=ctx_data.get("strict_length_precision", True),
                ignore_index_names=ctx_data.get("ignore_index_names", True),
                ignore_constraint_names=ctx_data.get("ignore_constraint_names", True),
                normalize_identifiers=ctx_data.get("normalize_identifiers", True),
                ignore_views=ctx_data.get("ignore_views", False),
                ignore_triggers=ctx_data.get("ignore_triggers", False),
                custom_type_equivalences=ctx_data.get("custom_type_equivalences", {}),
            )

            # 3. Reconstruct summary statistics
            sum_data = data.get("summary_statistics", {})
            summary = ComparisonSummary(
                total_objects=sum_data.get("total_objects", 0),
                total_differences=sum_data.get("total_differences", 0),
                added=sum_data.get("added", 0),
                removed=sum_data.get("removed", 0),
                modified=sum_data.get("modified", 0),
                info=sum_data.get("info", 0),
                warning=sum_data.get("warning", 0),
                critical=sum_data.get("critical", 0),
            )

            # 4. Reconstruct polymorphic differences
            differences: List[SchemaDifference] = []
            for diff in data.get("differences", []):
                try:
                    category = DifferenceCategory(diff["category"])
                except ValueError as exc:
                    raise SerializationError(f"Unknown difference category: '{diff.get('category')}'") from exc

                try:
                    action = DifferenceAction(diff["action"])
                except ValueError as exc:
                    raise SerializationError(f"Unknown difference action: '{diff.get('action')}'") from exc

                try:
                    severity = DifferenceSeverity(diff.get("severity", "WARNING"))
                except ValueError as exc:
                    raise SerializationError(f"Unknown difference severity: '{diff.get('severity')}'") from exc

                try:
                    impact = MigrationImpact(diff.get("impact", "ONLINE_DDL"))
                except ValueError as exc:
                    raise SerializationError(f"Unknown migration impact: '{diff.get('impact')}'") from exc

                # Fallback fields for AI readiness
                ai_metadata = diff.get("ai_metadata", {})
                
                common_kwargs = {
                    "difference_id": diff["difference_id"],
                    "category": category,
                    "action": action,
                    "path": diff["path"],
                    "severity": severity,
                    "impact": impact,
                    "description": diff["description"],
                    "ai_metadata": ai_metadata,
                }

                if category == DifferenceCategory.TABLE:
                    differences.append(
                        TableDifference(
                            table_name=diff["table_name"],
                            expected=_deserialize_table(diff.get("expected")),
                            actual=_deserialize_table(diff.get("actual")),
                            **common_kwargs
                        )
                    )
                elif category == DifferenceCategory.COLUMN:
                    differences.append(
                        ColumnDifference(
                            table_name=diff["table_name"],
                            column_name=diff["column_name"],
                            expected=_deserialize_column(diff.get("expected")),
                            actual=_deserialize_column(diff.get("actual")),
                            type_mismatch=diff.get("type_mismatch", False),
                            nullability_mismatch=diff.get("nullability_mismatch", False),
                            default_mismatch=diff.get("default_mismatch", False),
                            **common_kwargs
                        )
                    )
                elif category == DifferenceCategory.PRIMARY_KEY:
                    differences.append(
                        PrimaryKeyDifference(
                            table_name=diff["table_name"],
                            expected=_deserialize_pk(diff.get("expected")),
                            actual=_deserialize_pk(diff.get("actual")),
                            **common_kwargs
                        )
                    )
                elif category == DifferenceCategory.FOREIGN_KEY:
                    differences.append(
                        ForeignKeyDifference(
                            table_name=diff["table_name"],
                            fk_name=diff["fk_name"],
                            expected=_deserialize_fk(diff.get("expected")),
                            actual=_deserialize_fk(diff.get("actual")),
                            **common_kwargs
                        )
                    )
                elif category == DifferenceCategory.INDEX:
                    differences.append(
                        IndexDifference(
                            table_name=diff["table_name"],
                            index_name=diff["index_name"],
                            expected=_deserialize_index(diff.get("expected")),
                            actual=_deserialize_index(diff.get("actual")),
                            uniqueness_mismatch=diff.get("uniqueness_mismatch", False),
                            **common_kwargs
                        )
                    )
                elif category == DifferenceCategory.CONSTRAINT:
                    differences.append(
                        ConstraintDifference(
                            table_name=diff["table_name"],
                            constraint_name=diff["constraint_name"],
                            expected=_deserialize_constraint(diff.get("expected")),
                            actual=_deserialize_constraint(diff.get("actual")),
                            **common_kwargs
                        )
                    )

            # 5. Build DifferenceReport container
            timestamp = datetime.datetime.fromisoformat(data["comparison_timestamp"])

            return DifferenceReport(
                report_id=data["report_id"],
                report_version=data["report_version"],
                comparison_timestamp=timestamp,
                source_vendor=SystemType(data["source_vendor"]),
                target_vendor=SystemType(data["target_vendor"]),
                engine_version=data["engine_version"],
                comparison_options=context,
                source_checksum=data["source_checksum"],
                target_checksum=data["target_checksum"],
                status=SchemaComparisonStatus(data["status"]),
                differences=tuple(differences),
                summary_statistics=summary,
            )

        except Exception as exc:
            raise SerializationError(f"Failed to deserialize report structure: {exc}") from exc
