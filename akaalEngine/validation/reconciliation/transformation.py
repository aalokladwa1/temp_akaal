"""
akaalEngine.validation.reconciliation.transformation
=====================================================
TransformationAwareReconciler for Authority #11 (VAL-020).
Computes expected target row representations from raw source rows by applying Authority #8 Data Processing transformation, masking, and cleansing rules.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("akaalEngine.validation.reconciliation.transformation")


class TransformationAwareReconciler:
    """
    Applies Authority #8 Data Processing transformation pipeline to source rows to compute expected target values.
    Validates masked target data against expected masked values rather than raw source data.
    """

    def __init__(self, data_processing_authority: Optional[Any] = None) -> None:
        self.data_processing_authority = data_processing_authority

    def compute_expected_row(
        self,
        raw_source_row: Dict[str, Any],
        column_mapping: Dict[str, str],
        table_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Computes expected target row payload from raw source row.
        Executes column renaming and delegates masking/cleansing to Authority #8 if available.
        Fail closed if Authority #8 transformation fails or cannot be deterministically reconstructed.
        """
        # Step 1: Apply Column Renaming Mapping (src_col -> tgt_col)
        mapped_row: Dict[str, Any] = {}
        for src_col, val in raw_source_row.items():
            tgt_col = column_mapping.get(src_col, src_col)
            mapped_row[tgt_col] = val

        # Step 2: Delegate to Authority #8 Data Processing for masking/cleansing if configured
        if self.data_processing_authority and hasattr(self.data_processing_authority, "transform_batch"):
            try:
                # Wrap single row into batch for Authority #8 processing
                transformed_batch = self.data_processing_authority.transform_batch(table_name, [mapped_row])
                if transformed_batch and len(transformed_batch) > 0:
                    return transformed_batch[0]
            except Exception as ex:
                logger.warning(f"Authority #8 transformation evaluation failed on row: {ex}")
                # Fail closed: Do NOT accept raw source as expected target value!
                unprovable_row = dict(mapped_row)
                unprovable_row["__UNPROVABLE_TRANSFORMATION__"] = f"UNRECONSTRUCTABLE_AUTHORITY_8: {ex}"
                return unprovable_row

        return mapped_row
