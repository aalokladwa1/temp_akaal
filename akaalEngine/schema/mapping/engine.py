"""
akaalEngine.schema.mapping.engine
=================================
Structural mapping application engine: applies schema routes, table renames,
column projections, and data type overrides to produce a mapped CanonicalSchemaModel.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from akaalEngine.schema.mapping.validator import MappingValidator
from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalExclusionConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)
from akaalEngine.schema.models.indexes import CanonicalIndex
from akaalEngine.schema.models.mapping import (
    ColumnMapping,
    CompiledSchemaMapping,
    TableMapping,
)
from akaalEngine.schema.models.schema import (
    CanonicalCatalog,
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalView,
)
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable


class MappingEngine:
    """Applies CompiledSchemaMapping rules to CanonicalSchemaModel."""

    @classmethod
    def apply_mapping(
        cls,
        source_model: CanonicalSchemaModel,
        mapping: CompiledSchemaMapping,
        target_vendor: Optional[str] = None,
    ) -> CanonicalSchemaModel:
        # 1. Validate mapping
        val_result = MappingValidator.validate(source_model, mapping)
        if not val_result.is_valid:
            errors = [d.message for d in val_result.get_errors()]
            raise ValueError(f"Mapping validation failed with errors: {'; '.join(errors)}")

        mapped_tables: List[CanonicalTable] = []
        table_rename_map: Dict[Tuple[str, str], Tuple[str, str]] = {}  # (src_s, src_t) -> (tgt_s, tgt_t)
        column_rename_map: Dict[Tuple[str, str, str], str] = {}         # (src_s, src_t, src_c) -> tgt_c
        excluded_tables: Set[Tuple[str, str]] = set()

        # Build table lookup index
        for tbl in source_model.tables:
            src_s = tbl.schema_name
            src_t = tbl.table_name
            tm = mapping.get_table_mapping(src_s, src_t)

            if tm and not tm.is_included:
                excluded_tables.add((src_s.lower(), src_t.lower()))
                continue

            tgt_s = tm.target_schema if tm else mapping.resolve_target_schema(src_s)
            tgt_t = tm.target_table if tm else src_t

            if mapping.global_table_prefix and not (tm and tm.target_table != src_t):
                tgt_t = f"{mapping.global_table_prefix}{tgt_t}"
            if mapping.global_table_suffix and not (tm and tm.target_table != src_t):
                tgt_t = f"{tgt_t}{mapping.global_table_suffix}"

            table_rename_map[(src_s.lower(), src_t.lower())] = (tgt_s, tgt_t)

        # 2. Transform each included table
        for tbl in source_model.tables:
            src_s_lower = tbl.schema_name.lower()
            src_t_lower = tbl.table_name.lower()

            if (src_s_lower, src_t_lower) in excluded_tables:
                continue

            tgt_s, tgt_t = table_rename_map.get((src_s_lower, src_t_lower), (tbl.schema_name, tbl.table_name))
            tm = mapping.get_table_mapping(tbl.schema_name, tbl.table_name)

            # Transform Columns
            mapped_cols: List[CanonicalColumn] = []
            included_col_names: Set[str] = set()

            for col in sorted(tbl.columns, key=lambda x: x.ordinal_position):
                cm = tm.get_column_mapping(col.name) if tm else None
                if cm and not cm.is_included:
                    continue

                tgt_c = cm.target_column if cm else col.name
                column_rename_map[(src_s_lower, src_t_lower, col.name.lower())] = tgt_c
                included_col_names.add(tgt_c.lower())

                # Apply datatype override if present
                ctype = col.canonical_type
                if cm and cm.datatype_override:
                    # Keep canonical type category but annotate override
                    ctype = ctype  # Override handled during target emission

                mapped_cols.append(
                    CanonicalColumn(
                        name=tgt_c,
                        ordinal_position=cm.ordinal_position if (cm and cm.ordinal_position) else col.ordinal_position,
                        source_native_type=col.source_native_type,
                        canonical_type=ctype,
                        length=cm.datatype_override.target_length if (cm and cm.datatype_override and cm.datatype_override.target_length) else col.length,
                        precision=cm.datatype_override.target_precision if (cm and cm.datatype_override and cm.datatype_override.target_precision) else col.precision,
                        scale=cm.datatype_override.target_scale if (cm and cm.datatype_override and cm.datatype_override.target_scale) else col.scale,
                        byte_semantics=col.byte_semantics,
                        nullable=col.nullable,
                        default_expression=cm.default_expression if (cm and cm.default_expression) else col.default_expression,
                        is_identity=col.is_identity,
                        identity_generation=col.identity_generation,
                        is_computed=col.is_computed,
                        computed_expression=col.computed_expression,
                        is_lob=col.is_lob,
                        is_array=col.is_array,
                        array_element_type=col.array_element_type,
                        comment=col.comment,
                        raw_metadata=col.raw_metadata,
                        extra=col.extra,
                    )
                )

            # Transform Primary Key
            mapped_pk: Optional[CanonicalPrimaryKey] = None
            if tbl.primary_key:
                new_pk_cols = []
                for c in tbl.primary_key.columns:
                    mapped_c = column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c)
                    if mapped_c.lower() in included_col_names:
                        new_pk_cols.append(mapped_c)
                if new_pk_cols:
                    mapped_pk = CanonicalPrimaryKey(
                        name=tbl.primary_key.name,
                        table_name=tgt_t,
                        schema_name=tgt_s,
                        columns=tuple(new_pk_cols),
                        is_enforced=tbl.primary_key.is_enforced,
                    )

            # Transform Foreign Keys
            mapped_fks: List[CanonicalForeignKey] = []
            for fk in tbl.foreign_keys:
                ref_s_lower = fk.referenced_schema.lower()
                ref_t_lower = fk.referenced_table.lower()

                # If referenced table was excluded, skip FK
                if (ref_s_lower, ref_t_lower) in excluded_tables:
                    continue

                tgt_ref_s, tgt_ref_t = table_rename_map.get((ref_s_lower, ref_t_lower), (fk.referenced_schema, fk.referenced_table))
                new_fk_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in fk.columns]
                new_ref_cols = [column_rename_map.get((ref_s_lower, ref_t_lower, c.lower()), c) for c in fk.referenced_columns]

                # Check if all columns are included
                if all(c.lower() in included_col_names for c in new_fk_cols):
                    mapped_fks.append(
                        CanonicalForeignKey(
                            name=fk.name,
                            table_name=tgt_t,
                            schema_name=tgt_s,
                            columns=tuple(new_fk_cols),
                            referenced_schema=tgt_ref_s,
                            referenced_table=tgt_ref_t,
                            referenced_columns=tuple(new_ref_cols),
                            on_update=fk.on_update,
                            on_delete=fk.on_delete,
                            is_deferrable=fk.is_deferrable,
                            is_initially_deferred=fk.is_initially_deferred,
                            is_validated=fk.is_validated,
                            is_enforced=fk.is_enforced,
                        )
                    )

            # Transform Unique Constraints
            mapped_ucs: List[CanonicalUniqueConstraint] = []
            for uc in tbl.unique_constraints:
                new_uc_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in uc.columns]
                if all(c.lower() in included_col_names for c in new_uc_cols):
                    mapped_ucs.append(
                        CanonicalUniqueConstraint(
                            name=uc.name,
                            table_name=tgt_t,
                            schema_name=tgt_s,
                            columns=tuple(new_uc_cols),
                            is_deferrable=uc.is_deferrable,
                            nulls_not_distinct=uc.nulls_not_distinct,
                            is_enforced=uc.is_enforced,
                        )
                    )

            # Transform Indexes
            mapped_indexes: List[CanonicalIndex] = []
            for idx in tbl.indexes:
                new_idx_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in idx.columns]
                if all(c.lower() in included_col_names for c in new_idx_cols):
                    mapped_indexes.append(
                        CanonicalIndex(
                            name=idx.name,
                            table_name=tgt_t,
                            schema_name=tgt_s,
                            columns=tuple(new_idx_cols),
                            is_unique=idx.is_unique,
                            is_primary=idx.is_primary,
                            access_method=idx.access_method,
                            predicate_expression=idx.predicate_expression,
                            included_columns=tuple([column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in idx.included_columns]),
                            expression=idx.expression,
                            is_clustered=idx.is_clustered,
                            vector_dimensions=idx.vector_dimensions,
                            distance_metric=idx.distance_metric,
                        )
                    )

            mapped_tables.append(
                CanonicalTable(
                    table_name=tgt_t,
                    schema_name=tgt_s,
                    catalog_name=tbl.catalog_name,
                    table_type=tbl.table_type,
                    storage_format=tbl.storage_format,
                    columns=tuple(mapped_cols),
                    primary_key=mapped_pk,
                    foreign_keys=tuple(mapped_fks),
                    unique_constraints=tuple(mapped_ucs),
                    check_constraints=tbl.check_constraints,
                    exclusion_constraints=tbl.exclusion_constraints,
                    indexes=tuple(mapped_indexes),
                    partitioning=tbl.partitioning,
                    row_format=tbl.row_format,
                    compression=tbl.compression,
                    tablespace=tbl.tablespace,
                    comment=tbl.comment,
                    raw_source_properties=tbl.raw_source_properties,
                )
            )

        # Assemble Mapped Schemas
        unique_schemas = {t.schema_name for t in mapped_tables}
        mapped_schema_containers = [CanonicalSchema(schema_name=s) for s in unique_schemas]

        return CanonicalSchemaModel(
            model_id=f"{source_model.model_id}_mapped",
            source_vendor=target_vendor or source_model.source_vendor,
            source_version=source_model.source_version,
            catalogs=source_model.catalogs,
            schemas=tuple(mapped_schema_containers),
            tables=tuple(mapped_tables),
            views=source_model.views,
            routines=source_model.routines,
            packages=source_model.packages,
            triggers=source_model.triggers,
            sequences=source_model.sequences,
            udts=source_model.udts,
            synonyms=source_model.synonyms,
            raw_discovery_facts=source_model.raw_discovery_facts,
            extra=source_model.extra,
        )
