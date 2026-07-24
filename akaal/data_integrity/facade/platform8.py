"""
AKAAL Platform 8 — Enterprise Data Integrity Main Engine (EnterpriseDataIntegrityPlatformV8).
"""

from typing import Dict, Any, List
from akaal.data_integrity.verification.verifier import E2EConsistencyVerifier
from akaal.data_integrity.transactions.validator import TransactionBoundaryValidator
from akaal.data_integrity.snapshots.validator import SnapshotConsistencyValidator
from akaal.data_integrity.cross_table.validator import CrossTableConsistencyValidator
from akaal.data_integrity.referential.validator import ReferentialIntegrityValidator
from akaal.data_integrity.incremental.verifier import IncrementalConsistencyVerifier
from akaal.data_integrity.domain.models import ConsistencyReport, TransactionBoundaryResult, ReferentialIntegrityResult


class EnterpriseDataIntegrityPlatformV8:
    """
    Centralized Enterprise Data Integrity Platform (AKAAL Phase 13 Platform 8).
    Provides mathematical confidence that migrated data is fully consistent (Billion-row ready).
    """

    def __init__(self) -> None:
        self.platform_name = "Phase 13 Platform 8 — Enterprise Data Integrity Platform"
        self.version = "8.0.0"
        self.profile = "ENTERPRISE"

        self.e2e_verifier = E2EConsistencyVerifier()
        self.transaction_validator = TransactionBoundaryValidator()
        self.snapshot_validator = SnapshotConsistencyValidator()
        self.cross_table_validator = CrossTableConsistencyValidator()
        self.referential_validator = ReferentialIntegrityValidator()
        self.incremental_verifier = IncrementalConsistencyVerifier()

    def verify_e2e_consistency(self, source_table: str, target_table: str, row_count: int = 1000000) -> ConsistencyReport:
        return self.e2e_verifier.verify_consistency(source_table, target_table, row_count)

    def validate_transaction_boundary(self, transaction_id: str) -> TransactionBoundaryResult:
        return self.transaction_validator.validate_transaction_boundary(transaction_id)

    def validate_snapshot(self, snapshot_id: str, table_name: str) -> ConsistencyReport:
        return self.snapshot_validator.validate_snapshot(snapshot_id, table_name)

    def validate_cross_table(self, tables: List[str]) -> ConsistencyReport:
        return self.cross_table_validator.validate_cross_table_invariants(tables)

    def validate_referential_integrity(self, fk_name: str, parent: str, child: str) -> ReferentialIntegrityResult:
        return self.referential_validator.validate_referential_integrity(fk_name, parent, child)

    def verify_incremental(self, batch_id: str, rows: int) -> ConsistencyReport:
        return self.incremental_verifier.verify_incremental_batch(batch_id, rows)
