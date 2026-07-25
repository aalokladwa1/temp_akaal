"""
Unit tests for Stage 3: Batch-Level Validation.
"""

import pytest
from akaal.data_integrity.batch_validator import BatchLevelValidator
from akaal.data_integrity.domain.enums import IntegrityStatus


def test_batch_validator_valid_batch():
    validator = BatchLevelValidator()
    records = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]

    result = validator.validate_batch(
        batch_index=1,
        table_name="users",
        records=records,
        transaction_id="tx-001",
        uncommitted_count=0,
    )

    assert result.is_valid is True
    assert result.status == IntegrityStatus.VALIDATED
    assert result.row_count == 2
    assert len(result.batch_checksum) == 64
    assert len(result.validation_issues) == 0


def test_batch_validator_uncommitted_transaction_failure():
    validator = BatchLevelValidator()
    records = [{"id": 10, "val": "x"}]

    result = validator.validate_batch(
        batch_index=2,
        table_name="users",
        records=records,
        transaction_id="tx-002",
        uncommitted_count=3,
    )

    assert result.is_valid is False
    assert result.status == IntegrityStatus.INCONSISTENT
    assert any("uncommitted rows" in issue for issue in result.validation_issues)


def test_batch_validator_checksum_mismatch():
    validator = BatchLevelValidator()
    records = [{"id": 100, "val": "z"}]

    result = validator.validate_batch(
        batch_index=3,
        table_name="orders",
        records=records,
        transaction_id="tx-003",
        expected_checksum="bad_expected_hash",
    )

    assert result.is_valid is False
    assert result.status == IntegrityStatus.INCONSISTENT
    assert any("checksum mismatch" in issue for issue in result.validation_issues)
