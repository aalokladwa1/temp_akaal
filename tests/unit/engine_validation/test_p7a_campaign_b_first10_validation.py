"""
tests.unit.engine_validation.test_p7a_campaign_b_first10_validation
======================================================================
P7A Campaign B — First-10-Provider validation acceptance closure.

Authority #11 (ValidationAuthority.execute_validation()) operates entirely on
already-materialized row data (List[Dict[str, Any]]) and pk_columns -- it is
genuinely provider-agnostic BY DESIGN, downstream of Transport's real physical
extraction (already proven per-provider in
tests/unit/engine_transport/test_p7a_campaign_b_first10_transport_dataplane.py).
This means Validation's acceptance classification for all 10 first-Campaign-B
providers is honestly PROVEN, not NOT_APPLICABLE or EXTERNAL_DEFERRED: there is no
provider-specific validation code path to be missing, and this suite proves the real,
unmodified ValidationAuthority genuinely reconciles and genuinely detects mismatches
for row shapes matching each provider's real extracted-row structure (DynamoDB's
deserialized scalar values, ClickHouse/SQL-wire tuple-derived dicts, Couchbase's
document-shaped rows with a synthetic key column, InfluxDB's tag/field-flattened rows).
"""

from __future__ import annotations

import pytest

from akaalEngine.validation import (
    ProofScope,
    ValidationAuthority,
    ValidationGateStatus,
    ValidationMode,
    ValidationPlan,
)

# One representative real-shaped row pair (matching each provider's actual
# TransportBatch.rows structure as produced by its driver) per provider.
PROVIDER_ROW_SHAPES = {
    "cockroachdb": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
    "yugabytedb": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
    "tidb": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
    "singlestore": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
    "clickhouse": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
    "dynamodb": [{"id": "1", "name": "alice", "score": 3.5}, {"id": "2", "name": "bob", "score": 1}],
    "couchbase": [{"__doc_id": "d1", "id": 1, "name": "alice"}, {"__doc_id": "d2", "id": 2, "name": "bob"}],
    "influxdb": [{"host": "srv1", "_time": "2024-01-01T00:00:00Z", "temp": 21.5}, {"host": "srv2", "_time": "2024-01-01T00:00:00Z", "temp": 22.0}],
    "rabbitmq": [{"data": b"m1", "properties": {}, "partition_key": None}, {"data": b"m2", "properties": {}, "partition_key": None}],
    "pulsar": [{"data": b"m1", "properties": {}, "partition_key": None}, {"data": b"m2", "properties": {}, "partition_key": None}],
}

PK_COLUMNS = {
    "cockroachdb": ["id"], "yugabytedb": ["id"], "tidb": ["id"], "singlestore": ["id"], "clickhouse": ["id"],
    "dynamodb": ["id"], "couchbase": ["__doc_id"], "influxdb": ["host"],
    "rabbitmq": ["data"], "pulsar": ["data"],
}

NEW_PROVIDERS = list(PROVIDER_ROW_SHAPES.keys())


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_identical_source_target_rows_pass_exact_full_validation(provider_id):
    """For real row shapes matching each provider's own extracted-row structure,
    identical source/target rows must pass EXACT_FULL reconciliation with zero
    mismatches, for all 10 providers."""
    val = ValidationAuthority()
    rows = PROVIDER_ROW_SHAPES[provider_id]
    plan = ValidationPlan(
        "p1", f"mig-val-{provider_id}", f"{provider_id}://src", f"{provider_id}://tgt",
        "t1", mode=ValidationMode.EXACT_FULL, partition_count=1,
    )
    result = val.execute_validation(plan, rows, list(rows), PK_COLUMNS[provider_id])

    assert result.status == "SUCCESS"
    assert result.rows_mismatched == 0
    assert result.rows_matched == len(rows)
    assert result.validation_gate == ValidationGateStatus.PASSED


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_genuine_row_value_mismatch_is_detected_not_silently_passed(provider_id):
    """A genuine value divergence between source and target for one row must be
    detected as a real mismatch (not silently passed), for all 10 providers -- proving
    validation actually compares row CONTENT, not merely row COUNT."""
    val = ValidationAuthority()
    source_rows = PROVIDER_ROW_SHAPES[provider_id]
    target_rows = [dict(r) for r in source_rows]
    # Corrupt one non-key field in the target's first row.
    mutable_keys = [k for k in target_rows[0].keys() if k not in PK_COLUMNS[provider_id]]
    corrupt_key = mutable_keys[0]
    target_rows[0][corrupt_key] = "CORRUPTED-VALUE-FOR-HOSTILE-TEST" if not isinstance(target_rows[0][corrupt_key], bytes) else b"CORRUPTED"

    plan = ValidationPlan(
        "p1", f"mig-val-mismatch-{provider_id}", f"{provider_id}://src", f"{provider_id}://tgt",
        "t1", mode=ValidationMode.EXACT_FULL, partition_count=1,
    )
    result = val.execute_validation(plan, source_rows, target_rows, PK_COLUMNS[provider_id])

    assert result.rows_mismatched >= 1, f"'{provider_id}' failed to detect a genuine row-value mismatch"
    assert result.validation_gate != ValidationGateStatus.PASSED


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_genuine_missing_row_is_detected_as_cardinality_mismatch(provider_id):
    """A row present in source but entirely absent from target must be detected as a
    genuine cardinality/missing-row mismatch, for all 10 providers."""
    val = ValidationAuthority()
    source_rows = PROVIDER_ROW_SHAPES[provider_id]
    target_rows = source_rows[:1]  # target is missing the second row entirely

    plan = ValidationPlan(
        "p1", f"mig-val-missing-{provider_id}", f"{provider_id}://src", f"{provider_id}://tgt",
        "t1", mode=ValidationMode.EXACT_FULL, partition_count=1,
    )
    result = val.execute_validation(plan, source_rows, target_rows, PK_COLUMNS[provider_id])

    assert result.rows_expected == len(source_rows)
    assert result.rows_validated == len(target_rows)
    assert (result.rows_missing >= 1 or result.rows_mismatched >= 1 or result.rows_matched < len(source_rows)), (
        f"'{provider_id}' failed to detect a genuinely missing target row"
    )
    assert result.validation_gate != ValidationGateStatus.PASSED
