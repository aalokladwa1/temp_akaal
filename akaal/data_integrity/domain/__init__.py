"""
AKAAL Platform 8 — Domain Package Initialization.
"""

from akaal.data_integrity.domain.enums import IntegrityStatus, ConsistencyMode
from akaal.data_integrity.domain.models import ConsistencyReport, TransactionBoundaryResult, ReferentialIntegrityResult

__all__ = [
    "IntegrityStatus",
    "ConsistencyMode",
    "ConsistencyReport",
    "TransactionBoundaryResult",
    "ReferentialIntegrityResult",
]
