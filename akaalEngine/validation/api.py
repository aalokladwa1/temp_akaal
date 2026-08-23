"""
akaalEngine.validation.api
==========================
Canonical Entrypoint and Public Façade for Authority #11 — Validation / Reconciliation / Data Correctness (`ValidationAuthority`).
Physically integrates with Authorities #1, #4, #5, #6, #7, #8, #9, #10.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from threading import Lock, RLock
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from akaalEngine.validation.fingerprint.partition import PartitionFingerprintEngine
from akaalEngine.validation.fingerprint.row import DeterministicRowFingerprinter
from akaalEngine.validation.gate.evaluator import ValidationGateEvaluator
from akaalEngine.validation.models.canonical import CanonicalValueFormatter
from akaalEngine.validation.models.errors import (
    CardinalityValidationError,
    ReconciliationMismatchError,
    SchemaValidationError,
    ValidationCancelledError,
    ValidationFencingError,
    ValidationGateError,
    ValidationPlanError,
)
from akaalEngine.validation.models.plan import ProofScope, SamplingConfig, ValidationMode, ValidationPlan
from akaalEngine.validation.models.result import DisputedRecord, PartitionValidationResult, ValidationGateStatus, ValidationResult
from akaalEngine.validation.reconciliation.cardinality import CardinalityReconciliationEngine
from akaalEngine.validation.reconciliation.cdc_boundary import CDCBoundaryReconciler
from akaalEngine.validation.reconciliation.exact import ExactRowReconciler
from akaalEngine.validation.reconciliation.localization import MismatchLocalizationEngine
from akaalEngine.validation.reconciliation.schema import SchemaStructuralValidator
from akaalEngine.validation.reconciliation.transformation import TransformationAwareReconciler

logger = logging.getLogger("akaalEngine.validation.api")


class ValidationAuthority:
    """
    Single Canonical Public Façade for Authority #11 — Validation / Reconciliation / Data Correctness.
    Owns structural validation, cardinality reconciliation, deterministic fingerprinting,
    partition reconciliation, mismatch localization, exact row reconciliation,
    CDC-boundary validation, and VALIDATION_GATE evaluation.
    """

    def __init__(
        self,
        connection_authority: Optional[Any] = None,
        schema_authority: Optional[Any] = None,
        durability_authority: Optional[Any] = None,
        runtime_authority: Optional[Any] = None,
        telemetry_authority: Optional[Any] = None,
        data_processing_authority: Optional[Any] = None,
        transport_authority: Optional[Any] = None,
        cdc_authority: Optional[Any] = None,
    ) -> None:
        self.connection_authority = connection_authority
        self.schema_authority = schema_authority
        self.durability_authority = durability_authority
        self.runtime_authority = runtime_authority
        self.telemetry_authority = telemetry_authority
        self.data_processing_authority = data_processing_authority
        self.transport_authority = transport_authority
        self.cdc_authority = cdc_authority

        self._lock = RLock()
        self.schema_validator = SchemaStructuralValidator(schema_authority=self.schema_authority)
        self.cardinality_engine = CardinalityReconciliationEngine()
        self.transformation_reconciler = TransformationAwareReconciler(data_processing_authority=self.data_processing_authority)
        self.localization_engine = MismatchLocalizationEngine()
        self.exact_reconciler = ExactRowReconciler()
        self.cdc_boundary_reconciler = CDCBoundaryReconciler()

        # Telemetry and instrumentation counters
        self.validation_rows_total = 0
        self.validation_rows_matched_total = 0
        self.validation_rows_mismatched_total = 0
        self.validation_rows_missing_total = 0
        self.validation_rows_extra_total = 0
        self.reused_durable_partitions_total = 0
        self.exact_row_fetch_call_count = 0
        self.active_workers_count = 0
        self.peak_active_workers_count = 0
        self._worker_lock = Lock()

    def check_runtime_cancellation_and_fencing(
        self, cancellation_token: Optional[Any] = None, fencing_token: Optional[Any] = None
    ) -> None:
        """Physical integration check for Authority #6 CancellationTokens and Authority #5 Fencing Tokens."""
        if cancellation_token and hasattr(cancellation_token, "is_cancelled"):
            is_cancelled = cancellation_token.is_cancelled() if callable(cancellation_token.is_cancelled) else cancellation_token.is_cancelled
            if is_cancelled:
                raise ValidationCancelledError("Validation operation cancelled by Runtime Authority (#6) CancellationToken")

        if fencing_token and self.durability_authority and hasattr(self.durability_authority, "verify_fencing_token"):
            valid = self.durability_authority.verify_fencing_token(fencing_token)
            if not valid:
                raise ValidationFencingError("Stale or invalid fencing token rejected by Durability Authority (#5)")

    def record_telemetry_metrics(self) -> None:
        """Physical integration with Authority #7 Telemetry metrics registry."""
        if self.telemetry_authority:
            if hasattr(self.telemetry_authority, "record_counter"):
                self.telemetry_authority.record_counter("validation_rows_total", self.validation_rows_total)
                self.telemetry_authority.record_counter("validation_rows_matched_total", self.validation_rows_matched_total)
                self.telemetry_authority.record_counter("validation_rows_mismatched_total", self.validation_rows_mismatched_total)
                self.telemetry_authority.record_counter("validation_rows_missing_total", self.validation_rows_missing_total)
                self.telemetry_authority.record_counter("validation_rows_extra_total", self.validation_rows_extra_total)
                self.telemetry_authority.record_counter("reused_durable_partitions_total", self.reused_durable_partitions_total)

    def _execute_partition_validation(
        self,
        partition_id: str,
        plan: ValidationPlan,
        source_rows: List[Dict[str, Any]],
        target_rows: List[Dict[str, Any]],
        pk_columns: List[str],
        cancellation_token: Optional[Any] = None,
        fencing_token: Optional[Any] = None,
        simulated_delay_sec: float = 0.0,
    ) -> PartitionValidationResult:
        """Validates a single partition concurrently while measuring worker concurrency."""
        with self._worker_lock:
            self.active_workers_count += 1
            if self.active_workers_count > self.peak_active_workers_count:
                self.peak_active_workers_count = self.active_workers_count

        try:
            if simulated_delay_sec > 0.0:
                time.sleep(simulated_delay_sec)

            self.check_runtime_cancellation_and_fencing(cancellation_token, fencing_token)

            # Step 1: Durable partition checkpoint check (VAL-035)
            if self.durability_authority and hasattr(self.durability_authority, "load_spill_frame"):
                checkpoint_key = f"val_part_{partition_id}_{plan.migration_id}_{plan.plan_id}"
                cached_frame = self.durability_authority.load_spill_frame("validation", checkpoint_key)
                if cached_frame:
                    if cached_frame.get("migration_id") != plan.migration_id:
                        raise ValidationFencingError("Durable checkpoint migration identity mismatch on resume!")
                    logger.info(f"Authority #5 Durability SPI: Reused safe completed partition proof for '{checkpoint_key}'")
                    self.reused_durable_partitions_total += 1
                    return PartitionValidationResult(
                        partition_id=partition_id,
                        rows_expected=len(target_rows),
                        rows_validated=len(target_rows),
                        matched=True,
                        source_fingerprint=cached_frame.get("fingerprint", ""),
                        target_fingerprint=cached_frame.get("fingerprint", ""),
                    )

            # Step 2: Transformation-aware source row preparation
            expected_target_rows = [
                self.transformation_reconciler.compute_expected_row(r, plan.column_mapping, plan.table_name)
                for r in source_rows
            ]

            # Step 3: Compute partition fingerprints
            src_part_engine = PartitionFingerprintEngine(partition_id)
            tgt_part_engine = PartitionFingerprintEngine(partition_id)

            src_part_engine.update_batch(expected_target_rows)
            tgt_part_engine.update_batch(target_rows)

            src_fp = src_part_engine.finalize()
            tgt_fp = tgt_part_engine.finalize()

            matched = (src_fp == tgt_fp)

            if matched and self.durability_authority and hasattr(self.durability_authority, "save_spill_frame"):
                checkpoint_key = f"val_part_{partition_id}_{plan.migration_id}_{plan.plan_id}"
                self.durability_authority.save_spill_frame("validation", checkpoint_key, {"migration_id": plan.migration_id, "matched": True, "fingerprint": src_fp})

            return PartitionValidationResult(
                partition_id=partition_id,
                rows_expected=len(expected_target_rows),
                rows_validated=len(target_rows),
                matched=matched,
                source_fingerprint=src_fp,
                target_fingerprint=tgt_fp,
            )
        finally:
            with self._worker_lock:
                self.active_workers_count -= 1

    def execute_validation(
        self,
        plan: ValidationPlan,
        source_rows: List[Dict[str, Any]],
        target_rows: List[Dict[str, Any]],
        pk_columns: List[str],
        source_schema_meta: Optional[Dict[str, Any]] = None,
        target_schema_meta: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[Any] = None,
        fencing_token: Optional[Any] = None,
        simulated_worker_delay_sec: float = 0.0,
    ) -> ValidationResult:
        """
        Executes progressive validation pipeline (Levels 1 to 7):
          Level 1: Schema Structural Validation
          Level 2: Cardinality Reconciliation
          Level 3: Partition Fingerprint Validation & Durable Resume
          Level 4: Mismatch Localization
          Level 5: Exact Row Reconciliation
          Level 6: CDC Boundary Validation
          Level 7: VALIDATION_GATE Evaluation
        """
        start_time = time.time()
        self.check_runtime_cancellation_and_fencing(cancellation_token=cancellation_token, fencing_token=fencing_token)

        result = ValidationResult(
            validation_run_id=f"val-run-{plan.plan_id}",
            migration_id=plan.migration_id,
            table_name=plan.table_name,
            status="SUCCESS",
            proof_scope=ProofScope.UNPROVEN.value,
            validation_gate=ValidationGateStatus.WITHHELD,
            started_at=start_time,
        )

        # Step 1: Schema Structural Validation (Level 1)
        if plan.mode in (ValidationMode.FAST_FULL, ValidationMode.EXACT_FULL, ValidationMode.STRUCTURE_ONLY, ValidationMode.SAMPLED):
            if source_schema_meta and target_schema_meta:
                schema_valid, schema_errs = self.schema_validator.validate_schema(
                    source_schema_meta=source_schema_meta,
                    target_schema_meta=target_schema_meta,
                    column_mapping=plan.column_mapping,
                )
                if not schema_valid:
                    result.schema_mismatches = len(schema_errs)
                    result.errors.extend(schema_errs)
                    logger.warning(f"Schema validation failed: {schema_errs}")

        if plan.mode == ValidationMode.STRUCTURE_ONLY:
            result.proof_scope = ProofScope.STRUCTURE_ONLY.value
            result.completed_at = time.time()
            result.duration_sec = result.completed_at - start_time
            result.validation_gate = ValidationGateEvaluator.evaluate_gate(result, required_cdc_boundary_position=plan.cdc_boundary_position)
            return result

        # Step 2: Cardinality Reconciliation (Level 2)
        if plan.mode != ValidationMode.STRUCTURE_ONLY:
            card_matched, card_details = self.cardinality_engine.reconcile_cardinality(
                source_row_count=len(source_rows),
                target_row_count=len(target_rows),
            )
            result.rows_expected = card_details["expected_target_count"]
            result.rows_validated = len(target_rows)
            if not card_matched:
                result.errors.append(f"Cardinality mismatch: expected {card_details['expected_target_count']}, got {len(target_rows)}")

        if plan.mode == ValidationMode.COUNT_ONLY:
            result.proof_scope = ProofScope.COUNT_ONLY.value
            result.completed_at = time.time()
            result.duration_sec = result.completed_at - start_time
            result.validation_gate = ValidationGateEvaluator.evaluate_gate(result, required_cdc_boundary_position=plan.cdc_boundary_position)
            return result

        # Step 3: Multi-Partition Validation with Bounded Parallelism (VAL-037)
        num_partitions = max(1, plan.partition_count)
        result.partitions_total = num_partitions

        # Partition data streams
        chunk_src_size = max(1, len(source_rows) // num_partitions) if source_rows else 1
        chunk_tgt_size = max(1, len(target_rows) // num_partitions) if target_rows else 1

        partition_results: List[PartitionValidationResult] = []

        with ThreadPoolExecutor(max_workers=max(1, plan.max_concurrency)) as executor:
            futures = []
            for i in range(num_partitions):
                part_id = f"p{i}"
                src_part = source_rows[i * chunk_src_size : (i + 1) * chunk_src_size] if i < num_partitions - 1 else source_rows[i * chunk_src_size :]
                tgt_part = target_rows[i * chunk_tgt_size : (i + 1) * chunk_tgt_size] if i < num_partitions - 1 else target_rows[i * chunk_tgt_size :]

                futures.append(
                    executor.submit(
                        self._execute_partition_validation,
                        part_id,
                        plan,
                        src_part,
                        tgt_part,
                        pk_columns,
                        cancellation_token,
                        fencing_token,
                        simulated_worker_delay_sec,
                    )
                )

            for f in as_completed(futures):
                try:
                    res_p = f.result()
                    partition_results.append(res_p)
                except (ValidationFencingError, ValidationCancelledError):
                    raise
                except Exception as ex:
                    result.errors.append(str(ex))
                    result.status = "FAILED"

        # Evaluate partition results
        all_partitions_equal = True
        for p_res in partition_results:
            if p_res.matched:
                result.partitions_matched += 1
            else:
                result.partitions_mismatched += 1
                all_partitions_equal = False

        expected_target_rows = [
            self.transformation_reconciler.compute_expected_row(r, plan.column_mapping, plan.table_name)
            for r in source_rows
        ]

        if all_partitions_equal and not result.errors:
            result.rows_matched = len(target_rows)
            logger.info("All partition fingerprints equal: Skipping exact row fetch (Network Minimization VAL-038).")
        else:
            # Step 4: Network Minimization & Mismatch Drilldown (VAL-038)
            self.exact_row_fetch_call_count += 1
            logger.info("Partition fingerprint mismatch detected: Invoking exact row fetch and drilldown.")
            matched, mismatched, missing, extra, disputed = self.exact_reconciler.reconcile_exact(
                source_rows=expected_target_rows,
                target_rows=target_rows,
                pk_columns=pk_columns,
                column_mapping=plan.column_mapping,
            )
            result.rows_matched = matched
            result.rows_mismatched = mismatched
            result.rows_missing = missing
            result.rows_extra = extra
            result.disputed_records = disputed

        # Step 5: Update Telemetry
        self.validation_rows_total += result.rows_validated
        self.validation_rows_matched_total += result.rows_matched
        self.validation_rows_mismatched_total += result.rows_mismatched
        self.validation_rows_missing_total += result.rows_missing
        self.validation_rows_extra_total += result.rows_extra
        self.record_telemetry_metrics()

        # Step 6: CDC Boundary Validation (Level 6)
        if self.cdc_authority and hasattr(self.cdc_authority, "get_snapshot"):
            cdc_snap = self.cdc_authority.get_snapshot().to_dict()
            boundary_valid, boundary_errs = self.cdc_boundary_reconciler.validate_cdc_boundary(
                cdc_snapshot=cdc_snap,
                target_applied_position=cdc_snap.get("target_applied_position"),
                required_boundary_position=plan.cdc_boundary_position,
            )
            if not boundary_valid:
                result.errors.extend(boundary_errs)
                logger.warning(f"CDC boundary validation failed: {boundary_errs}")

        # Step 7: Proof Scope Classification & Gate Evaluation (Level 7)
        if plan.mode == ValidationMode.SAMPLED:
            result.proof_scope = ProofScope.SAMPLED.value
        elif plan.mode in (ValidationMode.FAST_FULL, ValidationMode.EXACT_FULL):
            result.proof_scope = ProofScope.PARTITIONED_FULL.value if plan.partition_count > 1 else ProofScope.FULL.value

        result.cdc_boundary_position = plan.cdc_boundary_position
        result.completed_at = time.time()
        result.duration_sec = result.completed_at - start_time
        result.validation_gate = ValidationGateEvaluator.evaluate_gate(result, required_cdc_boundary_position=plan.cdc_boundary_position)
        return result
