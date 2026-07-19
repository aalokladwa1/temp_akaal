"""
AKAAL Enterprise Intelligence Platform — Validation Subsystem
==============================================================
Validates input MigrationAdvisoryModel objects and canonical EnterpriseIntelligenceModel
artifacts for schema completeness, checksum integrity, and decision uniqueness.
"""

from typing import Any, Set
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel


class EnterpriseIntelligenceValidationError(Exception):
    """Exception raised when model validation fails."""
    pass


class EnterpriseIntelligenceValidator:
    """
    Production-grade validator for Platform 2 input and output models.
    """

    @staticmethod
    def validate_advisory_model(advisory_model: Any) -> bool:
        """
        Validates input MigrationAdvisoryModel integrity.

        Raises:
            EnterpriseIntelligenceValidationError: If model is null or structurally invalid.
        """
        if advisory_model is None:
            raise EnterpriseIntelligenceValidationError("Input MigrationAdvisoryModel cannot be None.")

        if not isinstance(advisory_model, MigrationAdvisoryModel):
            raise EnterpriseIntelligenceValidationError(
                f"Expected MigrationAdvisoryModel instance, got {type(advisory_model).__name__}."
            )

        model_id = getattr(advisory_model, "model_id", None) or (
            getattr(advisory_model.manifest, "advisory_id", None) if getattr(advisory_model, "manifest", None) else None
        )
        if not model_id:
            raise EnterpriseIntelligenceValidationError("MigrationAdvisoryModel missing required ID.")

        checksum = getattr(advisory_model, "sha256_checksum", None) or getattr(advisory_model, "checksum", None)
        if not checksum:
            raise EnterpriseIntelligenceValidationError("MigrationAdvisoryModel missing required checksum.")

        return True


    @staticmethod
    def validate_intelligence_model(model: Any) -> bool:
        """
        Validates output EnterpriseIntelligenceModel integrity, decision uniqueness,
        and manifest consistency.

        Raises:
            EnterpriseIntelligenceValidationError: If model contains structural errors.
        """
        if model is None:
            raise EnterpriseIntelligenceValidationError("EnterpriseIntelligenceModel cannot be None.")

        if not isinstance(model, EnterpriseIntelligenceModel):
            raise EnterpriseIntelligenceValidationError(
                f"Expected EnterpriseIntelligenceModel instance, got {type(model).__name__}."
            )

        if not model.model_id:
            raise EnterpriseIntelligenceValidationError("EnterpriseIntelligenceModel missing 'model_id'.")

        if not model.advisory_model_id:
            raise EnterpriseIntelligenceValidationError("EnterpriseIntelligenceModel missing 'advisory_model_id'.")

        if not model.checksum:
            raise EnterpriseIntelligenceValidationError("EnterpriseIntelligenceModel missing 'checksum'.")

        # Verify decision ID uniqueness
        seen_ids: Set[str] = set()
        for d in model.decisions:
            if not d.decision_id:
                raise EnterpriseIntelligenceValidationError("EnterpriseDecision missing required 'decision_id'.")
            if d.decision_id in seen_ids:
                raise EnterpriseIntelligenceValidationError(
                    f"Duplicate decision_id '{d.decision_id}' detected in EnterpriseIntelligenceModel."
                )
            seen_ids.add(d.decision_id)

        # Verify manifest consistency
        if model.manifest and model.manifest.total_decisions != len(model.decisions):
            raise EnterpriseIntelligenceValidationError(
                f"Manifest decision count ({model.manifest.total_decisions}) mismatch with actual "
                f"decisions count ({len(model.decisions)})."
            )

        return True
