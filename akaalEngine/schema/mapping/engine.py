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
from akaalEngine.schema.models.partitioning import CanonicalPartitioning
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


from akaalEngine.schema.procedural.lexer import ProceduralLexer, TokenType


class MappingEngine:
    """Applies CompiledSchemaMapping rules to CanonicalSchemaModel."""

    @classmethod
    def _rewrite_sql_identifiers(cls, sql: Optional[str], rename_dict: Dict[str, str]) -> Optional[str]:
        """Token-aware identifier rewriter for check clauses, predicates, and view SQL."""
        if not sql or not rename_dict:
            return sql

        tokens = ProceduralLexer.tokenize(sql)
        out_parts: List[str] = []
        for tok in tokens:
            if tok.token_type == TokenType.IDENTIFIER:
                clean_name = tok.value.strip('"`[]')
                if clean_name.lower() in rename_dict:
                    new_name = rename_dict[clean_name.lower()]
                    # Preserve quoting style if present
                    if tok.value.startswith('"') and tok.value.endswith('"'):
                        out_parts.append(f'"{new_name}"')
                    elif tok.value.startswith('`') and tok.value.endswith('`'):
                        out_parts.append(f'`{new_name}`')
                    elif tok.value.startswith('[') and tok.value.endswith(']'):
                        out_parts.append(f'[{new_name}]')
                    else:
                        out_parts.append(new_name)
                else:
                    out_parts.append(tok.value)
            else:
                out_parts.append(tok.value)

        return " ".join(out_parts)

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
        dropped_fks: List[CanonicalForeignKey] = []

        # Populate excluded tables from both mapping and model
        for tm in mapping.table_mappings:
            if not tm.is_included:
                excluded_tables.add((tm.source_schema.lower(), tm.source_table.lower()))

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
            table_col_rename_dict: Dict[str, str] = {}

            for col in sorted(tbl.columns, key=lambda x: x.ordinal_position):
                cm = tm.get_column_mapping(col.name) if tm else None
                if cm and not cm.is_included:
                    continue

                tgt_c = cm.target_column if cm else col.name
                column_rename_map[(src_s_lower, src_t_lower, col.name.lower())] = tgt_c
                table_col_rename_dict[col.name.lower()] = tgt_c
                included_col_names.add(tgt_c.lower())

                # Apply datatype override if present
                ctype = col.canonical_type
                src_native = col.source_native_type
                col_len = col.length
                col_prec = col.precision
                col_scale = col.scale

                if cm and cm.datatype_override:
                    ovr = cm.datatype_override
                    src_native = ovr.target_data_type
                    if ovr.target_length is not None:
                        col_len = ovr.target_length
                    if ovr.target_precision is not None:
                        col_prec = ovr.target_precision
                    if ovr.target_scale is not None:
                        col_scale = ovr.target_scale

                    from akaalEngine.schema.types.registry import CanonicalTypeRegistry
                    ctype = CanonicalTypeRegistry.normalize_source_type(
                        provider=target_vendor or source_model.source_vendor or "GENERIC",
                        raw_type=ovr.target_data_type,
                        precision=col_prec,
                        scale=col_scale,
                        length=col_len,
                    )

                mapped_cols.append(
                    CanonicalColumn(
                        name=tgt_c,
                        ordinal_position=cm.ordinal_position if (cm and cm.ordinal_position) else col.ordinal_position,
                        source_native_type=src_native,
                        canonical_type=ctype,
                        length=col_len,
                        precision=col_prec,
                        scale=col_scale,
                        byte_semantics=col.byte_semantics,
                        nullable=col.nullable,
                        default_expression=cm.default_expression if (cm and cm.default_expression) else col.default_expression,
                        is_identity=col.is_identity,
                        identity_generation=col.identity_generation,
                        is_computed=col.is_computed,
                        computed_expression=cls._rewrite_sql_identifiers(col.computed_expression, table_col_rename_dict) if col.computed_expression else None,
                        is_lob=col.is_lob,
                        is_array=col.is_array,
                        array_element_type=col.array_element_type,
                        comment=col.comment,
                        raw_metadata=col.raw_metadata,
                        extra=col.extra,
                    )
                )

            # Transform Primary Key
            mapped_pk = None
            if tbl.primary_key:
                new_pk_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in tbl.primary_key.columns]
                if all(c.lower() in included_col_names for c in new_pk_cols):
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

                # If referenced table was explicitly excluded, track dropped FK
                if (ref_s_lower, ref_t_lower) in excluded_tables:
                    dropped_fks.append(fk)
                    continue

                if (ref_s_lower, ref_t_lower) in table_rename_map:
                    tgt_ref_s, tgt_ref_t = table_rename_map[(ref_s_lower, ref_t_lower)]
                else:
                    # In streaming / chunked mode, referenced table may reside in another chunk
                    ref_tm = mapping.get_table_mapping(fk.referenced_schema, fk.referenced_table)
                    if ref_tm and not ref_tm.is_included:
                        dropped_fks.append(fk)
                        continue
                    tgt_ref_s = ref_tm.target_schema if ref_tm else mapping.resolve_target_schema(fk.referenced_schema)
                    tgt_ref_t = ref_tm.target_table if ref_tm else fk.referenced_table
                    if mapping.global_table_prefix and not (ref_tm and ref_tm.target_table != fk.referenced_table):
                        tgt_ref_t = f"{mapping.global_table_prefix}{tgt_ref_t}"
                    if mapping.global_table_suffix and not (ref_tm and ref_tm.target_table != fk.referenced_table):
                        tgt_ref_t = f"{tgt_ref_t}{mapping.global_table_suffix}"

                new_fk_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in fk.columns]
                new_ref_cols = []
                for c in fk.referenced_columns:
                    col_k = (ref_s_lower, ref_t_lower, c.lower())
                    if col_k in column_rename_map:
                        new_ref_cols.append(column_rename_map[col_k])
                    else:
                        ref_tm = mapping.get_table_mapping(fk.referenced_schema, fk.referenced_table)
                        cm = ref_tm.get_column_mapping(c) if ref_tm else None
                        new_ref_cols.append(cm.target_column if cm else c)

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
                else:
                    dropped_fks.append(fk)

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

            # Transform Check Constraints with rewritten column identifiers
            mapped_cks: List[CanonicalCheckConstraint] = []
            for ck in tbl.check_constraints:
                mapped_nn = column_rename_map.get((src_s_lower, src_t_lower, ck.not_null_column.lower()), ck.not_null_column) if ck.not_null_column else None
                rewritten_clause = cls._rewrite_sql_identifiers(ck.check_clause, table_col_rename_dict) if ck.check_clause else ""
                mapped_cks.append(
                    CanonicalCheckConstraint(
                        name=ck.name,
                        table_name=tgt_t,
                        schema_name=tgt_s,
                        check_clause=rewritten_clause,
                        is_enforced=ck.is_enforced,
                        is_not_null=ck.is_not_null,
                        not_null_column=mapped_nn,
                        extra=ck.extra,
                    )
                )

            # Transform Indexes with rewritten predicate/expression column identifiers
            mapped_indexes: List[CanonicalIndex] = []
            for idx in tbl.indexes:
                new_idx_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in idx.columns]
                if all(c.lower() in included_col_names for c in new_idx_cols):
                    mapped_pred = cls._rewrite_sql_identifiers(idx.predicate_expression, table_col_rename_dict) if idx.predicate_expression else None
                    mapped_expr = cls._rewrite_sql_identifiers(idx.expression, table_col_rename_dict) if idx.expression else None
                    mapped_indexes.append(
                        CanonicalIndex(
                            name=idx.name,
                            table_name=tgt_t,
                            schema_name=tgt_s,
                            columns=tuple(new_idx_cols),
                            is_unique=idx.is_unique,
                            is_primary=idx.is_primary,
                            access_method=idx.access_method,
                            predicate_expression=mapped_pred,
                            included_columns=tuple([column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in idx.included_columns]),
                            expression=mapped_expr,
                            is_clustered=idx.is_clustered,
                            vector_dimensions=idx.vector_dimensions,
                            distance_metric=idx.distance_metric,
                        )
                    )

            # Transform Partitioning with rewritten column identifiers and boundary expressions
            mapped_part_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in tbl.partitioning.partition_columns]
            mapped_subpart_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in tbl.partitioning.subpartition_columns]
            mapped_shard_cols = [column_rename_map.get((src_s_lower, src_t_lower, c.lower()), c) for c in tbl.partitioning.shard_key_columns]

            from akaalEngine.schema.models.partitioning import CanonicalPartitionBound, CanonicalSubpartition
            mapped_partitions = []
            for pb in tbl.partitioning.partitions:
                mapped_partitions.append(
                    CanonicalPartitionBound(
                        partition_name=pb.partition_name,
                        strategy=pb.strategy,
                        lower_bound=cls._rewrite_sql_identifiers(pb.lower_bound, table_col_rename_dict) if pb.lower_bound else None,
                        upper_bound=cls._rewrite_sql_identifiers(pb.upper_bound, table_col_rename_dict) if pb.upper_bound else None,
                        partition_ordinal=pb.partition_ordinal,
                        estimated_rows=pb.estimated_rows,
                        estimated_bytes=pb.estimated_bytes,
                        properties=pb.properties,
                    )
                )

            mapped_subpartitions = []
            for sp in tbl.partitioning.subpartitions:
                mapped_subpartitions.append(
                    CanonicalSubpartition(
                        subpartition_name=sp.subpartition_name,
                        parent_partition_name=sp.parent_partition_name,
                        strategy=sp.strategy,
                        bound_value=cls._rewrite_sql_identifiers(sp.bound_value, table_col_rename_dict) if sp.bound_value else None,
                        estimated_rows=sp.estimated_rows,
                        estimated_bytes=sp.estimated_bytes,
                    )
                )

            mapped_part = CanonicalPartitioning(
                strategy=tbl.partitioning.strategy,
                partition_columns=tuple(mapped_part_cols),
                subpartition_strategy=tbl.partitioning.subpartition_strategy,
                subpartition_columns=tuple(mapped_subpart_cols),
                partitions=tuple(mapped_partitions),
                subpartitions=tuple(mapped_subpartitions),
                token_ranges=tbl.partitioning.token_ranges,
                shard_key_columns=tuple(mapped_shard_cols),
                distribution_style=tbl.partitioning.distribution_style,
                extra=tbl.partitioning.extra,
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
                    check_constraints=tuple(mapped_cks),
                    exclusion_constraints=tbl.exclusion_constraints,
                    indexes=tuple(mapped_indexes),
                    partitioning=mapped_part,
                    row_format=tbl.row_format,
                    compression=tbl.compression,
                    tablespace=tbl.tablespace,
                    comment=tbl.comment,
                    raw_source_properties=tbl.raw_source_properties,
                )
            )

        # 3. Transform Views with rewritten schema and table references
        mapped_views: List[CanonicalView] = []
        global_table_token_map = {t_old: t_new for (_, t_old), (_, t_new) in table_rename_map.items()}
        for v in source_model.views:
            tgt_v_schema = mapping.resolve_target_schema(v.schema_name)
            tgt_v_sql = cls._rewrite_sql_identifiers(v.view_definition, global_table_token_map) if v.view_definition else None
            mapped_views.append(
                CanonicalView(
                    view_name=v.view_name,
                    schema_name=tgt_v_schema,
                    catalog_name=v.catalog_name,
                    view_definition=tgt_v_sql,
                    definition_sql=tgt_v_sql,
                    is_materialized=v.is_materialized,
                    materialized_refresh_mode=v.materialized_refresh_mode,
                    check_option=v.check_option,
                    is_read_only=v.is_read_only,
                    columns=v.columns,
                    dependencies=v.dependencies,
                    comment=v.comment,
                    extra=v.extra,
                )
            )

        # 4. Transform Programmables (Routines, Packages, Triggers, Sequences, UDTs, Synonyms)
        mapped_routines = [
            CanonicalRoutine(
                name=r.name,
                schema_name=mapping.resolve_target_schema(r.schema_name),
                routine_type=r.routine_type,
                language=r.language,
                definition_sql=r.definition_sql,
                parameters=r.parameters,
                return_type=r.return_type,
                is_deterministic=r.is_deterministic,
                data_access=r.data_access,
                security_type=r.security_type,
                is_autonomous=r.is_autonomous,
                dependencies=r.dependencies,
                comment=r.comment,
                extra=r.extra,
            )
            for r in source_model.routines
        ]

        mapped_packages = [
            CanonicalPackage(
                name=p.name,
                schema_name=mapping.resolve_target_schema(p.schema_name),
                spec_sql=p.spec_sql,
                body_sql=p.body_sql,
                routines=p.routines,
                comment=p.comment,
                extra=p.extra,
            )
            for p in source_model.packages
        ]

        mapped_triggers = []
        for tr in source_model.triggers:
            tgt_tr_s, tgt_tr_t = table_rename_map.get((tr.schema_name.lower(), tr.table_name.lower()), (mapping.resolve_target_schema(tr.schema_name), tr.table_name))
            mapped_triggers.append(
                CanonicalTrigger(
                    name=tr.name,
                    table_name=tgt_tr_t,
                    schema_name=tgt_tr_s,
                    trigger_event=tr.trigger_event,
                    trigger_timing=tr.trigger_timing,
                    is_row_level=tr.is_row_level,
                    definition_sql=tr.definition_sql,
                    when_clause=tr.when_clause,
                    is_disabled=tr.is_disabled,
                    comment=tr.comment,
                    extra=tr.extra,
                )
            )

        mapped_sequences = [
            CanonicalSequence(
                name=seq.name,
                schema_name=mapping.resolve_target_schema(seq.schema_name),
                start_value=seq.start_value,
                increment_by=seq.increment_by,
                min_value=seq.min_value,
                max_value=seq.max_value,
                is_cycling=seq.is_cycling,
                current_value=seq.current_value,
                cache_size=seq.cache_size,
                comment=seq.comment,
                extra=seq.extra,
            )
            for seq in source_model.sequences
        ]

        mapped_udts = [
            CanonicalUDT(
                name=u.name,
                schema_name=mapping.resolve_target_schema(u.schema_name),
                udt_type=u.udt_type,
                underlying_type=u.underlying_type,
                enum_values=u.enum_values,
                attributes=u.attributes,
                comment=u.comment,
                extra=u.extra,
            )
            for u in source_model.udts
        ]

        mapped_synonyms = []
        for syn in source_model.synonyms:
            tgt_syn_s = mapping.resolve_target_schema(syn.schema_name)
            tgt_syn_target_s, tgt_syn_target_o = table_rename_map.get(
                (syn.target_schema_name.lower(), syn.target_object_name.lower()),
                (mapping.resolve_target_schema(syn.target_schema_name), syn.target_object_name)
            )
            mapped_synonyms.append(
                CanonicalSynonym(
                    synonym_name=syn.synonym_name,
                    schema_name=tgt_syn_s,
                    target_object_name=tgt_syn_target_o,
                    target_schema_name=tgt_syn_target_s,
                    target_catalog_name=syn.target_catalog_name,
                    comment=syn.comment,
                    extra=syn.extra,
                )
            )

        # Assemble Mapped Schemas deterministically
        unique_schemas = {t.schema_name for t in mapped_tables} | {v.schema_name for v in mapped_views} | {r.schema_name for r in mapped_routines} | {p.schema_name for p in mapped_packages} | {seq.schema_name for seq in mapped_sequences} | {u.schema_name for u in mapped_udts} | {syn.schema_name for syn in mapped_synonyms}
        mapped_schema_containers = [CanonicalSchema(schema_name=s) for s in sorted(unique_schemas) if s]

        extra_meta = dict(source_model.extra)
        if dropped_fks:
            extra_meta["dropped_foreign_keys"] = tuple(dropped_fks)

        return CanonicalSchemaModel(
            model_id=f"{source_model.model_id}_mapped",
            source_vendor=target_vendor or source_model.source_vendor,
            source_version=source_model.source_version,
            catalogs=source_model.catalogs,
            schemas=tuple(mapped_schema_containers),
            tables=tuple(mapped_tables),
            views=tuple(mapped_views),
            routines=tuple(mapped_routines),
            packages=tuple(mapped_packages),
            triggers=tuple(mapped_triggers),
            sequences=tuple(mapped_sequences),
            udts=tuple(mapped_udts),
            synonyms=tuple(mapped_synonyms),
            raw_discovery_facts=source_model.raw_discovery_facts,
            extra=extra_meta,
        )
