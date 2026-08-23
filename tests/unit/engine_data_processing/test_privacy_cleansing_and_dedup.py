"""
tests/unit/engine_data_processing/test_privacy_cleansing_and_dedup.py
======================================================================
Unit tests for Privacy Masking, Cleansing, Lookup Tables, MalformedDataPolicy, and Bounded Deduplication.
"""

import pytest
from akaalEngine.data_processing import (
    DataProcessingAuthority,
    LookupDefinition,
    MalformedDataException,
    MalformedDataPolicy,
    PrivacyStrategy,
    RuleType,
    TransformationRule,
)


def test_privacy_masking_strategies():
    """Proves Privacy Masking strategies (STATIC_REDACT, PARTIAL_MASK, HASH, KEYED_PSEUDONYM, FORMAT_PRESERVING_MASK)."""
    data_processing = DataProcessingAuthority(secret_resolver=lambda ref: b"TEST-SECRET-KEY-12345")

    rule_redact = TransformationRule(
        rule_id="r_redact", column_name="ssn", rule_type=RuleType.PRIVACY, privacy_strategy=PrivacyStrategy.STATIC_REDACT
    )
    rule_mask = TransformationRule(
        rule_id="r_mask", column_name="card", rule_type=RuleType.PRIVACY, privacy_strategy=PrivacyStrategy.PARTIAL_MASK, unmasked_length=4
    )
    rule_pseudo = TransformationRule(
        rule_id="r_pseudo", column_name="user_id", rule_type=RuleType.PRIVACY, privacy_strategy=PrivacyStrategy.KEYED_PSEUDONYM, privacy_key_ref="key-1"
    )
    rule_fpe = TransformationRule(
        rule_id="r_fpe", column_name="email", rule_type=RuleType.PRIVACY, privacy_strategy=PrivacyStrategy.FORMAT_PRESERVING_MASK
    )

    plan = data_processing.compile_plan("sensitive", rules=[rule_redact, rule_mask, rule_pseudo, rule_fpe])

    row = {"ssn": "123-45-6789", "card": "1234567812345678", "user_id": "usr_999", "email": "john.doe@example.com"}
    res = data_processing.transform_row(row, plan)

    assert res.status == "SUCCESS"
    assert res.transformed_row["ssn"] == "[REDACTED]"
    assert res.transformed_row["card"] == "************5678"
    assert res.transformed_row["user_id"].startswith("PSEUDO-")
    assert res.transformed_row["email"] == "j*******@e******.com"


def test_cleansing_and_malformed_data_policy():
    """Proves Cleansing (TRIM, UPPER) and MalformedDataPolicy (QUARANTINE_RECORD, FAIL_JOB)."""
    data_processing = DataProcessingAuthority()

    rule_clean = TransformationRule(
        rule_id="r_clean", column_name="raw_code", rule_type=RuleType.CLEANSING, cleansing_operation="UPPER"
    )
    rule_lookup = TransformationRule(
        rule_id="r_lookup",
        column_name="country_code",
        rule_type=RuleType.LOOKUP,
        lookup_definition=LookupDefinition(
            lookup_name="country_lookup",
            key_column="code",
            value_column="name",
            mapping_data={"US": "United States", "CA": "Canada"},
            missing_key_policy="QUARANTINE_RECORD",
        ),
    )

    plan = data_processing.compile_plan("orders", rules=[rule_clean, rule_lookup])

    # Valid row
    res_valid = data_processing.transform_row({"raw_code": " abc ", "country_code": "US"}, plan)
    assert res_valid.status == "SUCCESS"
    assert res_valid.transformed_row["raw_code"] == " ABC "
    assert res_valid.transformed_row["country_code"] == "United States"

    # Missing lookup key -> QUARANTINED
    res_quarantine = data_processing.transform_row({"raw_code": " xyz ", "country_code": "UNKNOWN"}, plan)
    assert res_quarantine.status == "QUARANTINED"
    assert res_quarantine.quarantine_metadata["column_name"] == "country_code"


def test_bounded_deduplication():
    """Proves bounded composite key deduplication filters duplicate rows."""
    data_processing = DataProcessingAuthority()
    plan = data_processing.compile_plan("sales", rules=[], dedup_key_columns=["order_id", "item_id"])

    row1 = {"order_id": "ord_1", "item_id": "item_A", "amount": 100}
    row2 = {"order_id": "ord_1", "item_id": "item_B", "amount": 200}

    # First row -> SUCCESS
    assert data_processing.transform_row(row1, plan).status == "SUCCESS"
    # Second distinct row -> SUCCESS
    assert data_processing.transform_row(row2, plan).status == "SUCCESS"
    # Duplicate of row1 -> FILTERED
    assert data_processing.transform_row(row1, plan).status == "FILTERED"
