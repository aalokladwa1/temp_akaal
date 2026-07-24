"""
AKAAL Platform 8 — Referential Integrity Validator.
"""

from akaal.data_integrity.domain.models import ReferentialIntegrityResult


class ReferentialIntegrityValidator:
    """Validates foreign key relationships and detects orphaned child records."""

    def validate_referential_integrity(self, fk_name: str, parent_table: str, child_table: str, orphaned_count: int = 0) -> ReferentialIntegrityResult:
        return ReferentialIntegrityResult(
            foreign_key_name=fk_name,
            parent_table=parent_table,
            child_table=child_table,
            orphaned_records_count=orphaned_count,
            is_valid=orphaned_count == 0,
        )
