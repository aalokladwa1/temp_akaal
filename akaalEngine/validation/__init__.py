"""
akaalEngine.validation
======================
Authority #11 — Validation / Reconciliation / Data Correctness.
Canonical public facade and model exports.
"""

from akaalEngine.validation.api import ValidationAuthority
from akaalEngine.validation.fingerprint import DeterministicRowFingerprinter, PartitionFingerprintEngine
from akaalEngine.validation.gate import ValidationGateEvaluator
from akaalEngine.validation.models import (
    CanonicalValueFormatter,
    CardinalityValidationError,
    DisputedRecord,
    FingerprintError,
    PartitionValidationResult,
    ProofScope,
    ReconciliationMismatchError,
    SamplingConfig,
    SchemaValidationError,
    ValidationCancelledError,
    ValidationError,
    ValidationFencingError,
    ValidationGateError,
    ValidationGateStatus,
    ValidationMode,
    ValidationPlan,
    ValidationPlanError,
    ValidationResult,
    ValidationTimeoutError,
)
from akaalEngine.validation.reconciliation import (
    CardinalityReconciliationEngine,
    CDCBoundaryReconciler,
    ExactRowReconciler,
    MismatchLocalizationEngine,
    SchemaStructuralValidator,
    TransformationAwareReconciler,
)

__all__ = [
    "ValidationAuthority",
    "ValidationError",
    "ValidationPlanError",
    "SchemaValidationError",
    "CardinalityValidationError",
    "FingerprintError",
    "ReconciliationMismatchError",
    "ValidationGateError",
    "ValidationTimeoutError",
    "ValidationFencingError",
    "ValidationCancelledError",
    "ProofScope",
    "ValidationMode",
    "SamplingConfig",
    "ValidationPlan",
    "DisputedRecord",
    "PartitionValidationResult",
    "ValidationResult",
    "ValidationGateStatus",
    "CanonicalValueFormatter",
    "DeterministicRowFingerprinter",
    "PartitionFingerprintEngine",
    "SchemaStructuralValidator",
    "CardinalityReconciliationEngine",
    "TransformationAwareReconciler",
    "MismatchLocalizationEngine",
    "ExactRowReconciler",
    "CDCBoundaryReconciler",
    "ValidationGateEvaluator",
]
