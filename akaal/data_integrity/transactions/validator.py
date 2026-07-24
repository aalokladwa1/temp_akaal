"""
AKAAL Platform 8 — Transaction Boundary Validator.
"""

from akaal.data_integrity.domain.models import TransactionBoundaryResult
from akaal.data_integrity.domain.enums import IntegrityStatus


class TransactionBoundaryValidator:
    """Validates transactional consistency boundaries across migration batches."""

    def validate_transaction_boundary(self, transaction_id: str, uncommitted_count: int = 0) -> TransactionBoundaryResult:
        is_valid = uncommitted_count == 0
        return TransactionBoundaryResult(
            transaction_id=transaction_id,
            is_committed_consistently=is_valid,
            uncommitted_row_count=uncommitted_count,
            status=IntegrityStatus.VALIDATED if is_valid else IntegrityStatus.INCONSISTENT,
        )
