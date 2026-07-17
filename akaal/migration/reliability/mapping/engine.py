from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple
from akaal.core.models.configuration import MappingConfiguration, TableMapping, ColumnMapping

class MappingValidationReport:
    def __init__(self) -> None:
        self.success = True
        self.errors: List[str] = []
        self.warnings: List[str] = []


class MappingEngine:
    def __init__(self, config: MappingConfiguration) -> None:
        self.config = config

    def validate_mappings(self) -> MappingValidationReport:
        report = MappingValidationReport()
        seen_source_tables: Set[str] = set()
        seen_target_tables: Set[str] = set()

        for t_map in self.config.table_mappings:
            src = t_map.source_table.lower()
            tgt = t_map.target_table.lower()

            # 1. Duplicate mappings check
            if src in seen_source_tables:
                report.success = False
                report.errors.append(f"Duplicate mapping defined for source table '{t_map.source_table}'.")
            seen_source_tables.add(src)

            # 2. Collision mapping check
            if tgt in seen_target_tables:
                report.warnings.append(f"Target collision potential: Multiple source tables map to target table '{t_map.target_table}'.")
            seen_target_tables.add(tgt)

            seen_source_cols: Set[str] = set()
            seen_target_cols: Set[str] = set()
            for col in t_map.column_mappings:
                s_col = col.source_column.lower()
                t_col = col.target_column.lower()

                if s_col in seen_source_cols:
                    report.success = False
                    report.errors.append(f"Duplicate mapping defined for source column '{col.source_column}' in table '{t_map.source_table}'.")
                seen_source_cols.add(s_col)

                if t_col in seen_target_cols:
                    report.success = False
                    report.errors.append(f"Collision: Multiple source columns map to target column '{col.target_column}' in table '{t_map.source_table}'.")
                seen_target_cols.add(t_col)

        return report

    def map_table_name(self, source_table: str) -> str:
        for t_map in self.config.table_mappings:
            if t_map.source_table.lower() == source_table.lower():
                return t_map.target_table
        return source_table

    def map_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """Maps row columns according to configuration rules."""
        t_map = None
        for m in self.config.table_mappings:
            if m.source_table.lower() == table_name.lower():
                t_map = m
                break

        if not t_map:
            return row

        new_row: Dict[str, Any] = {}
        ignored_cols = {col.source_column.lower() for col in t_map.column_mappings if col.is_ignored}

        # First, apply renaming and ignore rules
        for col_name, val in row.items():
            col_lower = col_name.lower()
            if col_lower in ignored_cols:
                continue

            # Check mapping rename
            target_col = col_name
            for c_map in t_map.column_mappings:
                if c_map.source_column.lower() == col_lower:
                    target_col = c_map.target_column
                    break
            new_row[target_col] = val

        # Secondly, inject constants or generated fields
        for c_map in t_map.column_mappings:
            if c_map.is_ignored:
                continue
            if c_map.constant_value is not None:
                new_row[c_map.target_column] = c_map.constant_value
            elif c_map.expression:
                # Basic mock expression evaluator (e.g. constant default value or simple string concatenation)
                if c_map.expression.startswith("concat("):
                    new_row[c_map.target_column] = "computed_concat_value"
                else:
                    new_row[c_map.target_column] = "computed_expression_value"

        return new_row
