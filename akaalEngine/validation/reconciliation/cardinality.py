"""
akaalEngine.validation.reconciliation.cardinality
==================================================
CardinalityReconciliationEngine for Authority #11 (VAL-012).
Compares source expected row counts with target row counts, accounting for Authority #8 filtering.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from akaalEngine.validation.models.errors import CardinalityValidationError

logger = logging.getLogger("akaalEngine.validation.reconciliation.cardinality")


class CardinalityReconciliationEngine:
    """
    Reconciles record counts between source and target systems.
    Accounts for intentional filtering executed by Authority #8 Data Processing.
    """

    def reconcile_cardinality(
        self,
        source_row_count: int,
        target_row_count: int,
        expected_filtered_count: int = 0,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Reconciles cardinality.
        Expected target count = source_row_count - expected_filtered_count.
        """
        expected_target_count = source_row_count - expected_filtered_count
        diff = target_row_count - expected_target_count

        matched = (diff == 0)
        details = {
            "source_row_count": source_row_count,
            "expected_filtered_count": expected_filtered_count,
            "expected_target_count": expected_target_count,
            "target_row_count": target_row_count,
            "difference": diff,
            "matched": matched,
        }

        if not matched:
            logger.warning(f"Cardinality mismatch: expected {expected_target_count} target rows, got {target_row_count} (diff: {diff})")

        return matched, details
