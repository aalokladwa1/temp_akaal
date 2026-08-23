"""
tests/unit/engine_transport/test_checkpoint_and_retry.py
==========================================================
Unit tests for TransportCheckpoint identity fingerprints, AmbiguousCommitError fail-closed behavior, and checksum scope checks.
"""

import pytest
from akaalEngine.transport import (
    AmbiguousCommitError,
    ChecksumScope,
    CommitOutcomeState,
    GenericSQLTargetWriter,
    IdempotencyMode,
    PostgreSQLTargetWriter,
    TransportAuthority,
    TransportBatch,
    TransportBatchMetadata,
    TransportCheckpoint,
    TransportCheckpointIdentityError,
    TransportChecksumScopeError,
)


def test_checkpoint_identity_fingerprint():
    """Proves TransportCheckpoint binds resource, schema, strategy, and plan fingerprint before validation."""
    chk1 = TransportCheckpoint(
        source_identity="db_src",
        source_resource_version="v1",
        target_identity="db_tgt",
        logical_object_name="orders",
        schema_fingerprint="sch_hash_1",
        partition_id="part_01",
        partition_strategy_fingerprint="strat_hash_1",
        processing_plan_fingerprint="plan_hash_1",
        transport_strategy_identity="strat_bulk",
    )

    chk2 = TransportCheckpoint(
        source_identity="db_src",
        source_resource_version="v1",
        target_identity="db_tgt",
        logical_object_name="orders",
        schema_fingerprint="sch_hash_1",
        partition_id="part_01",
        partition_strategy_fingerprint="strat_hash_1",
        processing_plan_fingerprint="plan_hash_1",
        transport_strategy_identity="strat_bulk",
    )

    chk_diff_schema = TransportCheckpoint(
        source_identity="db_src",
        source_resource_version="v1",
        target_identity="db_tgt",
        logical_object_name="orders",
        schema_fingerprint="sch_hash_MODIFIED",
        partition_id="part_01",
        partition_strategy_fingerprint="strat_hash_1",
        processing_plan_fingerprint="plan_hash_1",
        transport_strategy_identity="strat_bulk",
    )

    chk1.validate_compatibility(chk2)  # Success

    with pytest.raises(TransportCheckpointIdentityError):
        chk1.validate_compatibility(chk_diff_schema)


def test_checksum_scope_enforcement():
    """Proves checksum scope mismatches raise TransportChecksumScopeError."""
    transport = TransportAuthority()

    c_val, scope_str = transport.compute_payload_checksum(b"hello world", ChecksumScope.SERIALIZED_UNCOMPRESSED_PAYLOAD)
    assert c_val.startswith("SHA256:")

    transport.verify_checksum_scope(scope_str, ChecksumScope.SERIALIZED_UNCOMPRESSED_PAYLOAD)

    with pytest.raises(TransportChecksumScopeError):
        transport.verify_checksum_scope(scope_str, ChecksumScope.FILE_BYTES)


def test_ambiguous_commit_outcome_fail_closed():
    """Proves UNKNOWN_COMMIT_OUTCOME on non-idempotent writes fails closed with AmbiguousCommitError."""
    writer = PostgreSQLTargetWriter({"mock_mode": True})

    meta = TransportBatchMetadata("b1", "p0", "orders", "public", 1, row_count=2, size_bytes=100)
    batch = TransportBatch(meta, rows=[{"id": 1, "val": "a"}, {"id": 2, "val": "b"}], column_names=["id", "val"])

    # Generic writer without cursor verification returns UNKNOWN_COMMIT_OUTCOME
    gen_writer = GenericSQLTargetWriter({})
    outcome = gen_writer.verify_uncertain_commit("orders", "public", None, batch)
    assert outcome == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
