"""
akaalEngine.schema.mapping.validator
====================================
Validation and conflict detection for schema, table, and column mappings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from akaalEngine.schema.models.mapping import CompiledSchemaMapping, TableMapping
from akaalEngine.schema.models.schema import CanonicalSchemaModel


@dataclass(frozen=True)
class MappingDiagnostic:
    """Diagnostic issue produced during mapping validation."""
    severity: str  # ERROR, WARNING, INFO
    rule: str
    message: str
    source_path: str
    target_path: Optional[str] = None


@dataclass(frozen=True)
class MappingValidationResult:
    """Outcome of structural mapping validation."""
    is_valid: bool
    diagnostics: Tuple[MappingDiagnostic, ...] = field(default_factory=tuple)

    def get_errors(self) -> List[MappingDiagnostic]:
        return [d for d in self.diagnostics if d.severity == "ERROR"]

    def get_warnings(self) -> List[MappingDiagnostic]:
        return [d for d in self.diagnostics if d.severity == "WARNING"]


class MappingValidator:
    """Validates mapping consistency, conflict collisions, and referential integrity."""

    @classmethod
    def validate_estate_mapping(
        cls,
        known_table_names: Set[str],
        mapping: CompiledSchemaMapping,
    ) -> MappingValidationResult:
        """
        Pre-validates whole-estate mapping against known table names from lightweight Pass 1 headers.
        Checks for non-existent source tables and cross-chunk target table collisions.
        """
        diagnostics: List[MappingDiagnostic] = []
        target_tables_seen: Set[str] = set()

        for tm in mapping.table_mappings:
            if not tm.is_included:
                continue

            src_key = tm.source_qualified_name.lower()
            if src_key not in known_table_names:
                diagnostics.append(
                    MappingDiagnostic(
                        severity="ERROR",
                        rule="SOURCE_TABLE_NOT_FOUND",
                        message=f"Table mapping references non-existent source table '{tm.source_qualified_name}'",
                        source_path=tm.source_qualified_name,
                        target_path=tm.target_qualified_name,
                    )
                )
                continue

            # Duplicate target table name collision check (cross-chunk)
            tgt_key = f"{tm.target_schema.lower()}.{tm.target_table.lower()}"
            if tgt_key in target_tables_seen:
                diagnostics.append(
                    MappingDiagnostic(
                        severity="ERROR",
                        rule="DUPLICATE_TARGET_TABLE",
                        message=f"Multiple source tables mapped to identical target table '{tm.target_qualified_name}'",
                        source_path=tm.source_qualified_name,
                        target_path=tm.target_qualified_name,
                    )
                )
            target_tables_seen.add(tgt_key)

        has_errors = any(d.severity == "ERROR" for d in diagnostics)
        return MappingValidationResult(
            is_valid=not has_errors,
            diagnostics=tuple(diagnostics),
        )

    @classmethod
    def validate(
        cls,
        source_model: CanonicalSchemaModel,
        mapping: CompiledSchemaMapping,
    ) -> MappingValidationResult:
        diagnostics: List[MappingDiagnostic] = []
        target_tables_seen: Set[str] = set()

        # 1. Check Table Mapping Conflicts and Duplications
        for tm in mapping.table_mappings:
            if not tm.is_included:
                continue

            src_key = f"{tm.source_schema.lower()}.{tm.source_table.lower()}"
            src_tbl = source_model.get_table(tm.source_schema, tm.source_table)
            if not src_tbl:
                diagnostics.append(
                    MappingDiagnostic(
                        severity="ERROR",
                        rule="SOURCE_TABLE_NOT_FOUND",
                        message=f"Table mapping references non-existent source table '{tm.source_qualified_name}'",
                        source_path=tm.source_qualified_name,
                        target_path=tm.target_qualified_name,
                    )
                )
                continue

            # Duplicate target table name collision check
            tgt_key = f"{tm.target_schema.lower()}.{tm.target_table.lower()}"
            if tgt_key in target_tables_seen:
                diagnostics.append(
                    MappingDiagnostic(
                        severity="ERROR",
                        rule="DUPLICATE_TARGET_TABLE",
                        message=f"Multiple source tables mapped to identical target table '{tm.target_qualified_name}'",
                        source_path=tm.source_qualified_name,
                        target_path=tm.target_qualified_name,
                    )
                )
            target_tables_seen.add(tgt_key)

            # Check Column Mappings
            target_cols_seen: Set[str] = set()
            for cm in tm.column_mappings:
                if not cm.is_included:
                    continue

                col_src = src_tbl.get_column(cm.source_column)
                if not col_src and not cm.is_generated:
                    diagnostics.append(
                        MappingDiagnostic(
                            severity="ERROR",
                            rule="SOURCE_COLUMN_NOT_FOUND",
                            message=f"Column mapping references non-existent source column '{cm.source_column}' in '{tm.source_qualified_name}'",
                            source_path=f"{tm.source_qualified_name}.{cm.source_column}",
                            target_path=f"{tm.target_qualified_name}.{cm.target_column}",
                        )
                    )

                # Duplicate target column collision check
                tgt_col_lower = cm.target_column.lower()
                if tgt_col_lower in target_cols_seen:
                    diagnostics.append(
                        MappingDiagnostic(
                            severity="ERROR",
                            rule="DUPLICATE_TARGET_COLUMN",
                            message=f"Multiple columns mapped to identical target column name '{cm.target_column}' in table '{tm.target_qualified_name}'",
                            source_path=f"{tm.source_qualified_name}.{cm.source_column}",
                            target_path=f"{tm.target_qualified_name}.{cm.target_column}",
                        )
                    )
                target_cols_seen.add(tgt_col_lower)

        # 2. Check Referential Integrity (Foreign Keys pointing to excluded tables)
        for tbl in source_model.tables:
            tbl_map = mapping.get_table_mapping(tbl.schema_name, tbl.table_name)
            if tbl_map and not tbl_map.is_included:
                continue

            for fk in tbl.foreign_keys:
                ref_map = mapping.get_table_mapping(fk.referenced_schema, fk.referenced_table)
                if ref_map and not ref_map.is_included:
                    diagnostics.append(
                        MappingDiagnostic(
                            severity="WARNING",
                            rule="FK_TARGET_TABLE_EXCLUDED",
                            message=f"Foreign key '{fk.name}' references excluded target table '{fk.referenced_schema}.{fk.referenced_table}'",
                            source_path=f"{tbl.qualified_name}.{fk.name}",
                        )
                    )

        has_errors = any(d.severity == "ERROR" for d in diagnostics)
        return MappingValidationResult(
            is_valid=not has_errors,
            diagnostics=tuple(diagnostics),
        )
