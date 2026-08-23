"""
akaalEngine.schema.mapping.serializer
=====================================
Deterministic JSON serialization and deserialization for schema, table, and column mappings.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from akaalEngine.schema.models.mapping import (
    ColumnMapping,
    CompiledSchemaMapping,
    DataTypeOverride,
    SchemaMappingRule,
    TableMapping,
)


class MappingSerializer:
    """Serializes and deserializes CompiledSchemaMapping with deterministic key ordering."""

    @classmethod
    def to_json(cls, mapping: CompiledSchemaMapping, indent: int = 2) -> str:
        """Deterministic JSON export."""
        return json.dumps(mapping.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> CompiledSchemaMapping:
        """Parses JSON string into CompiledSchemaMapping."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CompiledSchemaMapping:
        """Constructs CompiledSchemaMapping from dictionary."""
        schema_routes = []
        for r in data.get("schema_routes", []):
            schema_routes.append(
                SchemaMappingRule(
                    source_schema=r["source_schema"],
                    target_schema=r["target_schema"],
                    prefix=r.get("prefix"),
                    suffix=r.get("suffix"),
                    regex_pattern=r.get("regex_pattern"),
                    regex_replacement=r.get("regex_replacement"),
                    extra=r.get("extra", {}),
                )
            )

        table_mappings = []
        for tm in data.get("table_mappings", []):
            col_maps = []
            for cm in tm.get("column_mappings", []):
                dto = None
                if cm.get("datatype_override"):
                    do_data = cm["datatype_override"]
                    dto = DataTypeOverride(
                        target_data_type=do_data["target_data_type"],
                        target_precision=do_data.get("target_precision"),
                        target_scale=do_data.get("target_scale"),
                        target_length=do_data.get("target_length"),
                        reason=do_data.get("reason"),
                        extra=do_data.get("extra", {}),
                    )
                col_maps.append(
                    ColumnMapping(
                        source_column=cm["source_column"],
                        target_column=cm["target_column"],
                        is_included=cm.get("is_included", True),
                        ordinal_position=cm.get("ordinal_position"),
                        default_expression=cm.get("default_expression"),
                        datatype_override=dto,
                        is_generated=cm.get("is_generated", False),
                        extra=cm.get("extra", {}),
                    )
                )

            table_mappings.append(
                TableMapping(
                    source_schema=tm["source_schema"],
                    source_table=tm["source_table"],
                    target_schema=tm["target_schema"],
                    target_table=tm["target_table"],
                    is_included=tm.get("is_included", True),
                    column_mappings=tuple(col_maps),
                    custom_filter_predicate=tm.get("custom_filter_predicate"),
                    extra=tm.get("extra", {}),
                )
            )

        return CompiledSchemaMapping(
            schema_routes=tuple(schema_routes),
            table_mappings=tuple(table_mappings),
            global_table_prefix=data.get("global_table_prefix"),
            global_table_suffix=data.get("global_table_suffix"),
            extra=data.get("extra", {}),
        )
