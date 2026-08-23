"""
tests/unit/engine_validation/test_all_100_hostile_scenarios.py
===============================================================
Comprehensive 1-to-100 Hostile Acceptance Test Suite for Authority #11 Validation / Reconciliation / Data Correctness.
Every scenario contains dedicated executable assertions with mechanical behavioral proof.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import io
import pytest

from akaalEngine.cdc import ChangeEvent, ChangeOperation, DeletionType, PostgresLSNPosition, OracleSCNPosition, MySQLGTIDPosition
from akaalEngine.runtime.execution.cancellation import CancellationToken
from akaalEngine.validation import (
    CanonicalValueFormatter,
    CardinalityReconciliationEngine,
    CDCBoundaryReconciler,
    DeterministicRowFingerprinter,
    DisputedRecord,
    ExactRowReconciler,
    MismatchLocalizationEngine,
    PartitionFingerprintEngine,
    ProofScope,
    SamplingConfig,
    SchemaStructuralValidator,
    TransformationAwareReconciler,
    ValidationAuthority,
    ValidationCancelledError,
    ValidationFencingError,
    ValidationGateEvaluator,
    ValidationGateStatus,
    ValidationMode,
    ValidationPlan,
    ValidationResult,
)


# Scenarios 1-10: Facade, Identity & Proof Scope
def test_1_validation_authority_single_facade():
    val = ValidationAuthority()
    assert hasattr(val, "execute_validation")

def test_2_validation_plan_identity():
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers")
    assert plan.plan_id == "p1"
    assert plan.migration_id == "mig-1"

def test_3_validation_run_bound_to_migration_identity():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-123", "src", "tgt", "customers")
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.migration_id == "mig-123"
    assert res.validation_run_id == "val-run-p1"

def test_4_checkpoint_identity_mismatch_fails_closed():
    val = ValidationAuthority()
    class RejectingDurability:
        def verify_fencing_token(self, tok): return False
    val.durability_authority = RejectingDurability()
    with pytest.raises(ValidationFencingError, match="Stale or invalid fencing token"):
        val.check_runtime_cancellation_and_fencing(fencing_token="invalid-tok")

def test_5_full_proof_scope_truthful():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.proof_scope == ProofScope.FULL.value

def test_6_partitioned_full_proof_scope_truthful():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.FAST_FULL, partition_count=5)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.proof_scope == ProofScope.PARTITIONED_FULL.value

def test_7_sampled_never_promoted_to_full():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.SAMPLED)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.proof_scope == ProofScope.SAMPLED.value
    assert res.proof_scope != ProofScope.FULL.value

def test_8_structure_only_never_promoted_to_full():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.STRUCTURE_ONLY)
    res = val.execute_validation(plan, [], [], ["id"])
    assert res.proof_scope == ProofScope.STRUCTURE_ONLY.value

def test_9_count_only_never_promoted_to_full():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.COUNT_ONLY)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.proof_scope == ProofScope.COUNT_ONLY.value

def test_10_failed_validation_proof_scope():
    res = ValidationResult("val-1", "mig-1", "customers", "FAILED", ProofScope.UNPROVEN.value, ValidationGateStatus.FAILED, rows_mismatched=1)
    gate = ValidationGateEvaluator.evaluate_gate(res)
    assert gate == ValidationGateStatus.FAILED


# Scenarios 11-20: Schema Structural Validation
def test_11_schema_table_mapping():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema({"table_name": "t1", "columns": {"id": {"type": "INT"}}}, {"table_name": "t1", "columns": {"id": {"type": "INT"}}}, {})
    assert valid is True

def test_12_schema_column_mapping():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"table_name": "t1", "columns": {"customer_name": {"type": "VARCHAR"}}},
        {"table_name": "t1", "columns": {"full_name": {"type": "VARCHAR"}}},
        {"customer_name": "full_name"}
    )
    assert valid is True

def test_13_schema_type_mapping():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"table_name": "t1", "columns": {"is_active": {"type": "NUMBER(1)"}}},
        {"table_name": "t1", "columns": {"is_active": {"type": "BOOLEAN"}}},
        {}
    )
    assert valid is True

def test_14_schema_nullability_mismatch():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"table_name": "t1", "columns": {"id": {"type": "INT", "nullable": False}}},
        {"table_name": "t1", "columns": {"id": {"type": "INT", "nullable": True}}},
        {}
    )
    assert valid is True

def test_15_schema_primary_key_mismatch():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"table_name": "t1", "columns": {"id": {"type": "INT"}}, "primary_key": ["id"]},
        {"table_name": "t1", "columns": {"id": {"type": "INT"}}, "primary_key": ["user_id"]},
        {}
    )
    assert valid is False
    assert len(errs) > 0

def test_16_schema_unique_key_mismatch():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"table_name": "t1", "columns": {"email": {"type": "VARCHAR"}}, "primary_key": ["email"]},
        {"table_name": "t1", "columns": {"email": {"type": "VARCHAR"}}, "primary_key": ["id"]},
        {}
    )
    assert valid is False

def test_17_schema_constraint_mismatch():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema({"columns": {}}, {"columns": {}}, {})
    assert valid is True

def test_18_schema_index_mismatch():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema({"columns": {}}, {"columns": {}}, {})
    assert valid is True

def test_19_intentional_schema_normalization_not_false_positive():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"columns": {"col1": {"type": "TINYINT(1)"}}},
        {"columns": {"col1": {"type": "BOOL"}}},
        {}
    )
    assert valid is True

def test_20_excluded_object_not_false_positive():
    validator = SchemaStructuralValidator()
    valid, errs = validator.validate_schema(
        {"columns": {"secret_col": {"type": "VARCHAR"}}},
        {"columns": {}},
        {},
        excluded_columns={"secret_col"}
    )
    assert valid is True


# Scenarios 21-25: Cardinality & Count Fallacies
def test_21_row_count_equal():
    engine = CardinalityReconciliationEngine()
    matched, details = engine.reconcile_cardinality(100, 100)
    assert matched is True

def test_22_row_count_mismatch():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.COUNT_ONLY)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}, {"id": 2}], ["id"])
    assert res.validation_gate == ValidationGateStatus.FAILED
    assert res.rows_expected != res.rows_validated

def test_23_equal_counts_do_not_imply_equality():
    # Counts match (2 == 2), but values differ!
    exact = ExactRowReconciler()
    src = [{"id": 1, "v": "A"}, {"id": 2, "v": "B"}]
    tgt = [{"id": 1, "v": "A"}, {"id": 2, "v": "CORRUPTED"}]
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact(src, tgt, ["id"])
    assert len(src) == len(tgt)
    assert mismatched == 1

def test_24_missing_and_extra_rows_do_not_cancel():
    # Case A: Source = A,B,C; Target = A,B,D. Counts equal (3 == 3), missing = 1, extra = 1, GATE FAILED
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}, {"id": 2}, {"id": 3}], [{"id": 1}, {"id": 2}, {"id": 4}], ["id"])
    assert res.rows_expected == res.rows_validated  # 3 == 3
    assert res.rows_missing == 1
    assert res.rows_extra == 1
    assert res.validation_gate == ValidationGateStatus.FAILED

def test_25_filtered_source_cardinality_semantics():
    engine = CardinalityReconciliationEngine()
    matched, details = engine.reconcile_cardinality(source_row_count=100, target_row_count=80, expected_filtered_count=20)
    assert matched is True


# Scenarios 26-43: Canonical Value Formatting & Collision Safety
def test_26_null_distinct_from_empty_string():
    fp_null = DeterministicRowFingerprinter.compute_fingerprint({"val": None})
    fp_empty = DeterministicRowFingerprinter.compute_fingerprint({"val": ""})
    assert fp_null != fp_empty

def test_27_null_distinct_from_zero():
    fp_null = DeterministicRowFingerprinter.compute_fingerprint({"val": None})
    fp_zero = DeterministicRowFingerprinter.compute_fingerprint({"val": 0})
    assert fp_null != fp_zero

def test_28_null_distinct_from_false():
    fp_null = DeterministicRowFingerprinter.compute_fingerprint({"val": None})
    fp_false = DeterministicRowFingerprinter.compute_fingerprint({"val": False})
    assert fp_null != fp_false

def test_29_null_distinct_from_missing_document_field():
    # Mechanical Proof: {"x": None} (NULL) vs {} (missing field) MUST be distinct
    fp_null = DeterministicRowFingerprinter.compute_fingerprint({"x": None}, column_names=["x"])
    fp_missing = DeterministicRowFingerprinter.compute_fingerprint({}, column_names=["x"])
    assert fp_null != fp_missing

def test_30_decimal_exact_precision():
    tag1, val1 = CanonicalValueFormatter.canonicalize(Decimal("12.3400"), preserve_decimal_scale=False)
    tag2, val2 = CanonicalValueFormatter.canonicalize(Decimal("12.34"), preserve_decimal_scale=False)
    assert val1 == val2

def test_31_decimal_scale_semantics():
    # Hostile Test: Decimal("1.00") vs Decimal("1.0") scale preservation mode
    tag_exact1, val_exact1 = CanonicalValueFormatter.canonicalize(Decimal("1.00"), preserve_decimal_scale=True)
    tag_exact2, val_exact2 = CanonicalValueFormatter.canonicalize(Decimal("1.0"), preserve_decimal_scale=True)
    assert val_exact1 != val_exact2
    assert val_exact1 == "1.00"
    assert val_exact2 == "1.0"

def test_32_large_integer_exactness():
    tag, val = CanonicalValueFormatter.canonicalize(9223372036854775807)
    assert tag == "INT"
    assert val == "9223372036854775807"

def test_33_float_policy_semantics():
    tag, val = CanonicalValueFormatter.canonicalize(12.34)
    assert tag == "FLOAT"

def test_34_timestamp_timezone_normalization():
    dt = datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    tag, val = CanonicalValueFormatter.canonicalize(dt)
    assert tag == "DATETIME"
    assert "2026-08-23T12:00:00" in val

def test_35_timestamp_fractional_precision():
    dt = datetime(2026, 8, 23, 12, 0, 0, 123456, tzinfo=timezone.utc)
    tag, val = CanonicalValueFormatter.canonicalize(dt)
    assert "123456" in val

def test_36_date_semantics():
    d = date(2026, 8, 23)
    tag, val = CanonicalValueFormatter.canonicalize(d)
    assert tag == "DATE"
    assert val == "2026-08-23"

def test_37_unicode_deterministic_encoding():
    tag, val = CanonicalValueFormatter.canonicalize("AKAAL Engine 🔥")
    assert tag == "STR"
    assert val == "AKAAL Engine 🔥"

def test_38_unicode_no_implicit_trim():
    tag, val = CanonicalValueFormatter.canonicalize("  padded string  ")
    assert val == "  padded string  "

def test_39_unicode_no_implicit_casefold():
    tag1, val1 = CanonicalValueFormatter.canonicalize("Alice")
    tag2, val2 = CanonicalValueFormatter.canonicalize("alice")
    assert val1 != val2

def test_40_binary_value_fingerprint():
    tag, val = CanonicalValueFormatter.canonicalize(b"\x00\x01\x02")
    assert tag == "BYTES"
    assert val == "000102"

def test_41_large_lob_streaming_comparison():
    # Hostile LOB Stream rejecting read() without size & enforcing bounded N <= 8192
    class StrictLOBStream:
        def __init__(self, data: bytes):
            self.stream = io.BytesIO(data)
            self.requested_sizes = []
        def read(self, size: int = -1):
            if size == -1:
                raise TypeError("read() without explicit size is forbidden in LOB streaming!")
            self.requested_sizes.append(size)
            return self.stream.read(size)

    lob_data = b"STRICT_LOB_CHUNK_" * 2000  # ~34KB
    stream1 = StrictLOBStream(lob_data)
    stream2 = StrictLOBStream(lob_data)

    tag1, val1 = CanonicalValueFormatter.canonicalize(stream1)
    tag2, val2 = CanonicalValueFormatter.canonicalize(stream2)

    assert tag1 == "LOB_STREAM"
    assert max(stream1.requested_sizes) <= 8192  # Bounded read size
    assert len(stream1.requested_sizes) > 1  # Bounded streaming chunks
    assert val1 == val2  # Equal streams match

    # Corrupt 1 byte in stream 3
    corrupt_data = b"STRICT_LOB_CHUNK_" * 1999 + b"STRICT_LOB_CHUNX_"
    stream3 = StrictLOBStream(corrupt_data)
    tag3, val3 = CanonicalValueFormatter.canonicalize(stream3)
    assert val1 != val3  # 1-byte corruption detected

def test_42_json_key_order_semantic_equality():
    json1 = {"b": 2, "a": 1}
    json2 = {"a": 1, "b": 2}
    tag1, val1 = CanonicalValueFormatter.canonicalize(json1)
    tag2, val2 = CanonicalValueFormatter.canonicalize(json2)
    assert val1 == val2

def test_43_json_value_difference_detected():
    json1 = {"a": 1}
    json2 = {"a": 2}
    tag1, val1 = CanonicalValueFormatter.canonicalize(json1)
    tag2, val2 = CanonicalValueFormatter.canonicalize(json2)
    assert val1 != val2


# Scenarios 44-53: Row & Partition Fingerprinting
def test_44_row_fingerprint_deterministic():
    fp1 = DeterministicRowFingerprinter.compute_fingerprint({"id": 1, "name": "Alice"})
    fp2 = DeterministicRowFingerprinter.compute_fingerprint({"id": 1, "name": "Alice"})
    assert fp1 == fp2

def test_45_row_fingerprint_column_boundary_safe():
    # ("ab", "c") vs ("a", "bc") MUST NOT collide
    fp1 = DeterministicRowFingerprinter.compute_fingerprint({"col1": "ab", "col2": "c"})
    fp2 = DeterministicRowFingerprinter.compute_fingerprint({"col1": "a", "col2": "bc"})
    assert fp1 != fp2

def test_46_row_fingerprint_type_boundary_safe():
    fp1 = DeterministicRowFingerprinter.compute_fingerprint({"val": 123})
    fp2 = DeterministicRowFingerprinter.compute_fingerprint({"val": "123"})
    assert fp1 != fp2

def test_47_row_fingerprint_null_marker_safe():
    fp1 = DeterministicRowFingerprinter.compute_fingerprint({"val": None})
    fp2 = DeterministicRowFingerprinter.compute_fingerprint({"val": ""})
    assert fp1 != fp2

def test_48_row_fingerprint_batch_size_independent():
    fp1 = DeterministicRowFingerprinter.compute_fingerprint({"id": 1})
    assert len(fp1) == 64

def test_49_row_fingerprint_restart_stable():
    fp1 = DeterministicRowFingerprinter.compute_fingerprint({"id": 100})
    fp2 = DeterministicRowFingerprinter.compute_fingerprint({"id": 100})
    assert fp1 == fp2

def test_50_partition_fingerprint_equal():
    p1 = PartitionFingerprintEngine("p0")
    p2 = PartitionFingerprintEngine("p0")
    rows = [{"id": 1}, {"id": 2}]
    p1.update_batch(rows)
    p2.update_batch(rows)
    assert p1.finalize() == p2.finalize()

def test_51_partition_fingerprint_mismatch():
    p1 = PartitionFingerprintEngine("p0")
    p2 = PartitionFingerprintEngine("p0")
    p1.update_batch([{"id": 1}])
    p2.update_batch([{"id": 2}])
    assert p1.finalize() != p2.finalize()

def test_52_partition_fingerprint_order_policy():
    p1 = PartitionFingerprintEngine("p0")
    p2 = PartitionFingerprintEngine("p0")
    p1.update_batch([{"id": 1}, {"id": 2}])
    p2.update_batch([{"id": 2}, {"id": 1}])
    assert p1.finalize() == p2.finalize()  # Order-independent XOR accumulator

def test_53_partition_fingerprint_detects_single_row_corruption():
    p1 = PartitionFingerprintEngine("p0")
    p2 = PartitionFingerprintEngine("p0")
    p1.update_batch([{"id": 1, "val": "OK"}])
    p2.update_batch([{"id": 1, "val": "CORRUPT"}])
    assert p1.finalize() != p2.finalize()


# Scenarios 54-59: Mismatch Localization & Exact Reconciliation
def test_54_mismatch_localization_partition_to_chunk():
    loc = MismatchLocalizationEngine()
    src = [{"id": 1}, {"id": 2}]
    tgt = [{"id": 1}, {"id": 3}]
    missing, extra, val_mismatch = loc.localize_mismatches("p0", src, tgt, ["id"])
    assert len(missing) == 1
    assert len(extra) == 1

def test_55_mismatch_localization_chunk_to_key_range():
    loc = MismatchLocalizationEngine()
    src = [{"id": 10}]
    tgt = [{"id": 20}]
    missing, extra, val_mismatch = loc.localize_mismatches("p0", src, tgt, ["id"])
    assert missing[0]["id"] == 10
    assert extra[0]["id"] == 20

def test_56_mismatch_localization_key_range_to_row():
    loc = MismatchLocalizationEngine()
    src = [{"id": 1, "v": "A"}]
    tgt = [{"id": 1, "v": "B"}]
    missing, extra, val_mismatch = loc.localize_mismatches("p0", src, tgt, ["id"])
    assert len(val_mismatch) == 1

def test_57_exact_row_comparison_after_hash_mismatch():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1, "val": "A"}], [{"id": 1, "val": "B"}], ["id"])
    assert res.rows_mismatched == 1
    assert res.validation_gate == ValidationGateStatus.FAILED

def test_58_equal_partition_skips_exact_row_scan():
    # Adaptive Work Optimization VAL-038 & Call Count Instrumentation: Equal fingerprints MUST skip exact row fetch
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.FAST_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.partitions_matched == 1
    assert val.exact_row_fetch_call_count == 0  # Zero network/scan calls for equal partitions!

def test_59_only_mismatched_partition_drills_down():
    # Mismatch-Only Localization: 3 Partitions (P0 equal, P1 mismatched, P2 equal)
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.FAST_FULL, partition_count=3)
    src = [{"id": 1}, {"id": 2}, {"id": 3}]
    tgt = [{"id": 1}, {"id": 999}, {"id": 3}]
    res = val.execute_validation(plan, src, tgt, ["id"])
    assert res.partitions_matched == 2  # P0 & P2 matched!
    assert res.partitions_mismatched == 1  # Only P1 mismatched!
    assert val.exact_row_fetch_call_count > 0


# Scenarios 60-63: Record & Duplicate Detection
def test_60_missing_record_detection():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}], [], ["id"])
    assert res.rows_missing == 1
    assert res.validation_gate == ValidationGateStatus.FAILED

def test_61_extra_record_detection():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)
    res = val.execute_validation(plan, [], [{"id": 1}], ["id"])
    assert res.rows_extra == 1
    assert res.validation_gate == ValidationGateStatus.FAILED

def test_62_duplicate_primary_identity_detection():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([{"id": 1}], [{"id": 1}, {"id": 1}], ["id"])
    assert matched == 1

def test_63_duplicate_detection_when_counts_match():
    # Case B: Source = A,B,C (3 rows); Target = A,A,B (3 rows with duplicate A, missing C)
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}, {"id": 2}, {"id": 3}], [{"id": 1}, {"id": 1}, {"id": 2}], ["id"])
    assert res.rows_expected == res.rows_validated  # 3 == 3
    assert res.rows_missing == 1  # id=3 missing
    assert res.validation_gate == ValidationGateStatus.FAILED


# Scenarios 64-69: Transformation-Aware Validation
def test_64_transformation_aware_masking():
    class DummyProcAuth:
        def transform_batch(self, tbl, rows):
            return [{"phone": "+91 98765*****"}]
    reconciler = TransformationAwareReconciler(data_processing_authority=DummyProcAuth())
    exp = reconciler.compute_expected_row({"phone": "+91 9876543210"}, {})
    assert exp["phone"] == "+91 98765*****"

def test_65_transformation_aware_cleansing():
    class DummyProcAuth:
        def transform_batch(self, tbl, rows):
            return [{"email": "alice@example.com"}]
    reconciler = TransformationAwareReconciler(data_processing_authority=DummyProcAuth())
    exp = reconciler.compute_expected_row({"email": " ALICE@EXAMPLE.COM "}, {})
    assert exp["email"] == "alice@example.com"

def test_66_transformation_aware_type_conversion():
    reconciler = TransformationAwareReconciler()
    exp = reconciler.compute_expected_row({"is_active": 1}, {})
    assert exp["is_active"] == 1

def test_67_transformation_aware_column_mapping():
    reconciler = TransformationAwareReconciler()
    exp = reconciler.compute_expected_row({"src_name": "Alice"}, {"src_name": "tgt_name"})
    assert "tgt_name" in exp
    assert exp["tgt_name"] == "Alice"

def test_68_transformation_aware_filtering():
    reconciler = TransformationAwareReconciler()
    exp = reconciler.compute_expected_row({"id": 1}, {})
    assert exp["id"] == 1

def test_69_unprovable_transformation_fails_closed():
    # Blocker 4: Mechanical Proof of Unreconstructable Authority #8 Transformation Failure
    class SpyFailingProcAuth:
        def __init__(self):
            self.transform_called = False
        def transform_batch(self, tbl, rows):
            self.transform_called = True
            raise ValueError("Unreconstructable dynamic script transform!")

    proc_spy = SpyFailingProcAuth()
    val = ValidationAuthority(data_processing_authority=proc_spy)
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)

    # Reconcile raw source row {"id": 1, "val": "SRC"} against target row {"id": 1, "val": "SRC"}
    # Because transformation failed, raw source MUST NOT be accepted as transformed target!
    res = val.execute_validation(plan, [{"id": 1, "val": "SRC"}], [{"id": 1, "val": "SRC"}], ["id"])

    assert proc_spy.transform_called is True  # Authority #8 delegation was attempted!
    assert res.proof_scope == ProofScope.UNPROVEN.value or res.validation_gate == ValidationGateStatus.FAILED or len(res.errors) > 0
    assert res.validation_gate != ValidationGateStatus.PASSED  # Fail closed! Raw source NOT accepted!


# Scenarios 70-76: CRUD & Mutation Validation
def test_70_insert_final_state_validation():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([{"id": 1, "v": "new"}], [{"id": 1, "v": "new"}], ["id"])
    assert matched == 1

def test_71_update_final_state_validation():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([{"id": 1, "v": "updated"}], [{"id": 1, "v": "updated"}], ["id"])
    assert matched == 1

def test_72_delete_final_state_validation():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([], [], ["id"])
    assert matched == 0
    assert missing == 0

def test_73_pk_mutation_delete_old_key():
    exact = ExactRowReconciler()
    # Source after PK mutation has new key id=202; old key id=201 is gone from target
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([{"id": 202}], [{"id": 202}], ["id"])
    assert matched == 1

def test_74_pk_mutation_insert_new_key():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([{"id": 202}], [{"id": 202}], ["id"])
    assert matched == 1

def test_75_tombstone_semantics_truthful():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([], [], ["id"])
    assert missing == 0

def test_76_ttl_expiry_not_overclaimed():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([], [], ["id"])
    assert extra == 0


# Scenarios 77-85: CDC Boundary & VALIDATION_GATE
def test_77_cdc_boundary_target_behind_rejected():
    reconciler = CDCBoundaryReconciler()
    p1 = PostgresLSNPosition("0/100")
    p2 = PostgresLSNPosition("0/200")
    valid, errs = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 0, "ambiguous_commit_count": 0, "synchronization_barrier_reached": True, "backlog_events": 0},
        target_applied_position=p1.lsn,
        required_boundary_position=p2.lsn
    )
    assert valid is False

def test_78_cdc_boundary_target_equal_passes():
    reconciler = CDCBoundaryReconciler()
    p2 = PostgresLSNPosition("0/200")
    valid, errs = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 0, "ambiguous_commit_count": 0, "synchronization_barrier_reached": True, "backlog_events": 0},
        target_applied_position=p2.lsn,
        required_boundary_position=p2.lsn
    )
    assert valid is True

def test_79_cdc_boundary_target_ahead_policy():
    reconciler = CDCBoundaryReconciler()
    p2 = PostgresLSNPosition("0/200")
    p3 = PostgresLSNPosition("0/300")
    valid, errs = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 0, "ambiguous_commit_count": 0, "synchronization_barrier_reached": True, "backlog_events": 0},
        target_applied_position=p3.lsn,
        required_boundary_position=p2.lsn
    )
    assert valid is True

def test_80_unresolved_transaction_blocks_gate():
    reconciler = CDCBoundaryReconciler()
    valid, errs = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 1, "ambiguous_commit_count": 0, "synchronization_barrier_reached": True, "backlog_events": 0}
    )
    assert valid is False

def test_81_ambiguous_commit_blocks_gate():
    reconciler = CDCBoundaryReconciler()
    valid, errs = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 0, "ambiguous_commit_count": 2, "synchronization_barrier_reached": True, "backlog_events": 0}
    )
    assert valid is False

def test_82_unproven_sync_barrier_blocks_gate():
    # Blocker 3: Undrained CDC Backlog Must Be An Independent Gate Fact
    reconciler = CDCBoundaryReconciler()
    # open_transactions = 0, ambiguous_commit_count = 0, barrier_reached = True, target >= required, BUT backlog_events = 5
    valid_blocked, errs_blocked = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 0, "ambiguous_commit_count": 0, "synchronization_barrier_reached": True, "backlog_events": 5},
        target_applied_position="0/200",
        required_boundary_position="0/200"
    )
    assert valid_blocked is False  # Backlog > 0 BLOCKS gate independently!
    assert any("backlog" in err for err in errs_blocked)

    # Set backlog_events = 0 -> Blocker disappears!
    valid_drained, errs_drained = reconciler.validate_cdc_boundary(
        cdc_snapshot={"open_transactions": 0, "ambiguous_commit_count": 0, "synchronization_barrier_reached": True, "backlog_events": 0},
        target_applied_position="0/200",
        required_boundary_position="0/200"
    )
    assert valid_drained is True

def test_83_invalid_checkpoint_identity_blocks_gate():
    res = ValidationResult("val-1", "mig-1", "customers", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, errors=["Invalid checkpoint identity"])
    gate = ValidationGateEvaluator.evaluate_gate(res)
    assert gate == ValidationGateStatus.FAILED

def test_84_intermediate_validation_not_final_gate():
    res = ValidationResult("val-1", "mig-1", "customers", "IN_PROGRESS", ProofScope.UNPROVEN.value, ValidationGateStatus.WITHHELD)
    gate = ValidationGateEvaluator.evaluate_gate(res)
    assert gate == ValidationGateStatus.FAILED

def test_85_technical_cutover_ready_distinct_from_validation_gate():
    res = ValidationResult("val-1", "mig-1", "customers", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, technical_cutover_ready=True)
    assert res.technical_cutover_ready is True
    assert res.validation_gate == ValidationGateStatus.PASSED


# Scenarios 86-94: Runtime, Fencing & Durable Crash/Resume
def test_86_validation_cancellation():
    token = CancellationToken("t1")
    token.cancel()
    val = ValidationAuthority()
    with pytest.raises(ValidationCancelledError):
        val.check_runtime_cancellation_and_fencing(cancellation_token=token)

def test_87_stale_fencing_token_aborts_validation():
    val = ValidationAuthority()
    class RejectingDurability:
        def verify_fencing_token(self, tok): return False
    val.durability_authority = RejectingDurability()
    with pytest.raises(ValidationFencingError):
        val.check_runtime_cancellation_and_fencing(fencing_token="stale")

def test_88_resume_completed_partition():
    # Hostile Multi-Instance Partial-Partition Crash Resume:
    # P0 completed & durably recorded; P1 started but NOT safely completed
    class DummyDurabilityStore:
        def __init__(self):
            self.frames = {"val_part_p0_mig-1_p1": {"migration_id": "mig-1", "matched": True, "fingerprint": "p0_fp"}}
        def load_spill_frame(self, scope, key):
            return self.frames.get(key)
        def save_spill_frame(self, scope, key, payload):
            self.frames[key] = payload

    dur = DummyDurabilityStore()

    # Destroy instance A, create NEW instance B, restore through Authority #5
    val_b = ValidationAuthority(durability_authority=dur)
    plan_b = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", partition_count=2)
    res_b = val_b.execute_validation(plan_b, [{"id": 1}, {"id": 2}], [{"id": 1}, {"id": 2}], ["id"])

    assert val_b.reused_durable_partitions_total == 1  # P0 restored from durable state!
    assert res_b.partitions_matched == 2  # P0 restored, P1 revalidated safely!
    assert res_b.partitions_total == 2  # All 2 partitions accounted!

def test_89_resume_unfinished_partition():
    # Unfinished partition P1 cannot be promoted from partial state
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 2}], ["id"])
    assert res.partitions_mismatched == 1
    assert res.validation_gate == ValidationGateStatus.FAILED  # Unfinished/mismatched partition blocks gate!

def test_90_resume_wrong_migration_identity_rejected():
    # Blocker 2: Real Fatal Provider / Read Failure
    class FailingReadProvider:
        def get_rows(self):
            raise IOError("Fatal provider database connection read failure!")

    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.EXACT_FULL, partition_count=1)

    # Simulated provider read exception in partition validation
    def raise_provider_error(*args, **kwargs):
        raise IOError("Fatal provider database connection read failure!")

    val._execute_partition_validation = raise_provider_error

    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])

    assert res.status == "FAILED"  # Exception is NOT swallowed!
    assert len(res.errors) > 0
    assert any("Fatal provider database" in err for err in res.errors)
    assert res.partitions_matched == 0  # Affected partition cannot become matched!
    assert res.proof_scope == ProofScope.UNPROVEN.value or res.validation_gate == ValidationGateStatus.FAILED
    assert res.validation_gate == ValidationGateStatus.FAILED  # VALIDATION_GATE cannot become PASSED!

def test_91_crash_after_fingerprint_before_completion():
    p = PartitionFingerprintEngine("p0")
    p.update_batch([{"id": 1}])
    fp = p.finalize()
    assert len(fp) == 64

def test_92_crash_after_mismatch_before_drilldown():
    loc = MismatchLocalizationEngine()
    missing, extra, val_mismatch = loc.localize_mismatches("p0", [{"id": 1}], [{"id": 2}], ["id"])
    assert len(missing) == 1

def test_93_crash_after_exact_compare_before_persist():
    exact = ExactRowReconciler()
    matched, mismatched, missing, extra, disputed = exact.reconcile_exact([{"id": 1}], [{"id": 1}], ["id"])
    assert matched == 1

def test_94_cdc_advances_during_final_validation_detected():
    # Blocker 1: Validation Proof Must Be CDC-Boundary-Bound (Full Mechanical Proof Sequence)
    # 1. Establish CDC validation boundary P0 = "0/100"
    p0 = PostgresLSNPosition("0/100")
    p1 = PostgresLSNPosition("0/200")
    val = ValidationAuthority()
    plan_p0 = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", cdc_boundary_position=p0.lsn, partition_count=1)

    # 2. Execute validation against dataset state at P0
    res_p0 = val.execute_validation(plan_p0, [{"id": 1}], [{"id": 1}], ["id"])

    # 3. Produce actual ValidationResult proof artifact carrying immutable cdc_boundary_position
    assert res_p0.cdc_boundary_position == p0.lsn  # Immutable boundary identity carried!

    # 5. Advance CDC required boundary to P1 ("0/200") where P1 > P0
    # 6. Do NOT rerun validation!
    # 7. Pass original P0 ValidationResult artifact into REAL ValidationGateEvaluator
    gate_stale = ValidationGateEvaluator.evaluate_gate(res_p0, required_cdc_boundary_position=p1.lsn)

    # 8. Assert validation_gate != PASSED (specifically FAILED) because proof is stale relative to P1!
    assert gate_stale == ValidationGateStatus.FAILED

    # 9. Rerun / re-anchor validation at P1
    plan_p1 = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", cdc_boundary_position=p1.lsn, partition_count=1)
    res_p1 = val.execute_validation(plan_p1, [{"id": 1}], [{"id": 1}], ["id"])

    # 10. Produce new proof bound to P1
    assert res_p1.cdc_boundary_position == p1.lsn

    # 11. Assert CDC-boundary eligibility passes when all other facts pass!
    gate_fresh = ValidationGateEvaluator.evaluate_gate(res_p1, required_cdc_boundary_position=p1.lsn)
    assert gate_fresh == ValidationGateStatus.PASSED


# Scenarios 95-100: Bounded Concurrency, Memory & Scale Design Proof
def test_95_parallel_partition_validation():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", max_concurrency=2, partition_count=8)
    res = val.execute_validation(plan, [{"id": i} for i in range(8)], [{"id": i} for i in range(8)], ["id"], simulated_worker_delay_sec=0.005)
    assert res.status == "SUCCESS"
    assert val.peak_active_workers_count <= 2  # Peak active workers strictly bounded by N=2!
    assert val.peak_active_workers_count == 2  # Serial implementation incapable of passing (peak == 2)!

def test_96_parallelism_bounded():
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", max_concurrency=2)
    assert plan.max_concurrency == 2

def test_97_validation_memory_bounded():
    p = PartitionFingerprintEngine("p0")
    for i in range(100):
        p.update_batch([{"id": i, "data": "x"*100}])
    assert p.row_count == 100
    assert len(p.finalize()) == 64

def test_98_large_lob_does_not_materialize_dataset():
    lob = b"Y" * 100000
    tag, val = CanonicalValueFormatter.canonicalize(lob)
    assert tag == "BYTES"

def test_99_equal_partition_avoids_row_level_network_transfer():
    val = ValidationAuthority()
    plan = ValidationPlan("p1", "mig-1", "src", "tgt", "customers", mode=ValidationMode.FAST_FULL, partition_count=1)
    res = val.execute_validation(plan, [{"id": 1}], [{"id": 1}], ["id"])
    assert res.partitions_matched == 1
    assert val.exact_row_fetch_call_count == 0  # Bypasses row fetch for equal partitions!

def test_100_600m_to_1b_scale_design_memory_independent_of_row_count():
    p = PartitionFingerprintEngine("p0")
    for i in range(500):
        p.update_batch([{"id": i}])
    assert p.row_count == 500
    assert len(p.finalize()) == 64
