"""
akaalEngine.validation.gate.evaluator
=====================================
ValidationGateEvaluator for Authority #11 (VAL-040).
Fact-based, fail-closed evaluation of VALIDATION_GATE independent of TECHNICAL_CUTOVER_READY.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.validation.models.result import ValidationGateStatus, ValidationResult

logger = logging.getLogger("akaalEngine.validation.gate.evaluator")


class ValidationGateEvaluator:
    """
    Evaluates VALIDATION_GATE based strictly on mechanical quantitative facts.
    Returns VALIDATION_GATE == PASSED ONLY when all required correctness criteria are satisfied.
    """

    @staticmethod
    def evaluate_gate(
        result: ValidationResult,
        required_cdc_boundary_position: Optional[str] = None,
    ) -> ValidationGateStatus:
        """
        Evaluates ValidationResult facts and returns ValidationGateStatus (PASSED, FAILED, WITHHELD).
        Fail closed on any missing rows, extra rows, value mismatches, duplicate violations,
        schema mismatches, unresolved CDC transactions, or stale CDC boundary proof artifacts.
        """
        reasons: List[str] = []

        if result.status != "SUCCESS":
            reasons.append(f"Validation status is '{result.status}' (not SUCCESS)")

        if result.proof_scope == "UNPROVEN":
            reasons.append("Proof scope is UNPROVEN")

        if result.schema_mismatches > 0:
            reasons.append(f"Schema structural mismatches detected: {result.schema_mismatches}")

        if result.rows_mismatched > 0:
            reasons.append(f"Value mismatched rows detected: {result.rows_mismatched}")

        if result.rows_missing > 0:
            reasons.append(f"Missing rows detected: {result.rows_missing}")

        if result.rows_extra > 0:
            reasons.append(f"Extra rows detected: {result.rows_extra}")

        if result.duplicates > 0:
            reasons.append(f"Duplicate primary key violations detected: {result.duplicates}")

        if result.partitions_total > 0 and result.partitions_matched < result.partitions_total:
            reasons.append(f"Partition mismatches: {result.partitions_total - result.partitions_matched} partitions failed fingerprint validation")

        if result.errors:
            reasons.append(f"Validation errors reported: {len(result.errors)}")

        # Evaluate CDC boundary staleness against immutable result proof artifact
        if required_cdc_boundary_position:
            if not result.cdc_boundary_position:
                reasons.append(f"Validation proof artifact lacks CDC boundary position; cannot satisfy required boundary '{required_cdc_boundary_position}'!")
            elif result.cdc_boundary_position < required_cdc_boundary_position:
                reasons.append(f"Stale CDC validation proof: proof boundary position '{result.cdc_boundary_position}' is behind required CDC boundary position '{required_cdc_boundary_position}'!")

        if len(reasons) > 0:
            logger.warning(f"VALIDATION_GATE FAILED: {reasons}")
            return ValidationGateStatus.FAILED

        logger.info("VALIDATION_GATE PASSED: All quantitative correctness criteria satisfied cleanly.")
        return ValidationGateStatus.PASSED
