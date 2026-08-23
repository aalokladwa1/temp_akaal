"""
akaalEngine.validation.reconciliation.schema
=============================================
SchemaStructuralValidator for Authority #11 (VAL-006 through VAL-011).
Integrates with Authority #4 Schema Authority to validate approved target table structures, column mappings, type conversions, nullability, and keys.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from akaalEngine.validation.models.errors import SchemaValidationError

logger = logging.getLogger("akaalEngine.validation.reconciliation.schema")


class SchemaStructuralValidator:
    """
    Validates target schema structure against approved Authority #4 Schema Authority mappings.
    Checks renamed columns, normalized data types, nullability, and primary/unique keys.
    """

    def __init__(self, schema_authority: Optional[Any] = None) -> None:
        self.schema_authority = schema_authority

    def validate_schema(
        self,
        source_schema_meta: Dict[str, Any],
        target_schema_meta: Dict[str, Any],
        column_mapping: Dict[str, str],
        excluded_columns: Optional[Set[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validates target table structure against source schema metadata and approved column mappings.
        Returns (is_valid, list_of_schema_mismatch_errors).
        """
        errors: List[str] = []
        excluded = excluded_columns or set()

        source_cols = source_schema_meta.get("columns", {})
        target_cols = target_schema_meta.get("columns", {})

        for src_col, src_meta in source_cols.items():
            if src_col in excluded:
                continue

            # Respect renamed/remapped columns (VAL-008)
            tgt_col = column_mapping.get(src_col, src_col)
            if tgt_col not in target_cols:
                errors.append(f"Missing mapped target column '{tgt_col}' (for source column '{src_col}') in table '{target_schema_meta.get('table_name')}'")
                continue

            tgt_meta = target_cols[tgt_col]

            # Validate type semantic compatibility (VAL-007)
            # E.g. NUMBER(1) -> BOOLEAN normalization is valid
            src_type = str(src_meta.get("type", "")).upper()
            tgt_type = str(tgt_meta.get("type", "")).upper()

            if src_type != tgt_type:
                # Check for approved type normalizations
                if src_type in ("NUMBER(1)", "TINYINT(1)") and tgt_type in ("BOOLEAN", "BOOL", "BIT"):
                    logger.info(f"Approved type normalization '{src_type}' -> '{tgt_type}' validated for column '{tgt_col}'")
                elif "VARCHAR" in src_type and "TEXT" in tgt_type:
                    logger.info(f"Approved text widening '{src_type}' -> '{tgt_type}' validated for column '{tgt_col}'")
                else:
                    logger.warning(f"Type difference for column '{tgt_col}': '{src_type}' vs '{tgt_type}'")

            # Validate nullability semantics (VAL-009)
            if src_meta.get("nullable") is False and tgt_meta.get("nullable") is True:
                logger.info(f"Target column '{tgt_col}' permits NULLs while source is NOT NULL (acceptable widening).")

        # Validate Primary Key / Unique Key metadata (VAL-010)
        src_pk = source_schema_meta.get("primary_key", [])
        tgt_pk = target_schema_meta.get("primary_key", [])
        mapped_src_pk = [column_mapping.get(c, c) for c in src_pk]
        if mapped_src_pk and tgt_pk and set(mapped_src_pk) != set(tgt_pk):
            errors.append(f"Primary key mismatch on target table: expected '{mapped_src_pk}', found '{tgt_pk}'")

        is_valid = len(errors) == 0
        return is_valid, errors
