"""
Akaal — Advisor Governance
==========================
Governance hooks for versioning, audit logging, evidence tracking, decision lineage, and determinism verification.
"""

from typing import Any, Dict

from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel


class AdvisorGovernanceError(Exception):
    """Exception raised for governance violations in Advisor Platform."""
    pass


class AdvisorGovernance:
    """Enterprise Governance Framework for Advisor Platform."""

    SUPPORTED_SCHEMA_VERSIONS = ("1.0.0", "1.0.1", "1.0")

    @classmethod
    def check_version_compatibility(cls, version: str) -> bool:
        """Check if plan or advisory schema version is supported."""
        return version in cls.SUPPORTED_SCHEMA_VERSIONS

    @classmethod
    def audit_model(cls, model: MigrationAdvisoryModel) -> Dict[str, Any]:
        """Perform comprehensive governance audit on a MigrationAdvisoryModel."""
        if not isinstance(model, MigrationAdvisoryModel):
            raise AdvisorGovernanceError(f"Invalid model object: {type(model)}")

        is_valid_checksum = model.verify_checksum()
        recommendations_with_evidence = sum(1 for r in model.recommendations if len(r.evidence) > 0)
        recommendations_with_decisions = sum(1 for r in model.recommendations if r.decision is not None)

        return {
            "advisory_id": model.manifest.advisory_id,
            "checksum_valid": is_valid_checksum,
            "version_compatible": cls.check_version_compatibility(model.schema_version),
            "total_recommendations": len(model.recommendations),
            "evidence_coverage": round(recommendations_with_evidence / max(1, len(model.recommendations)), 2),
            "decision_lineage_coverage": round(recommendations_with_decisions / max(1, len(model.recommendations)), 2),
            "audit_passed": is_valid_checksum and (len(model.recommendations) == 0 or recommendations_with_evidence > 0),
        }

    @classmethod
    def assert_deterministic_equivalence(
        cls, model_a: MigrationAdvisoryModel, model_b: MigrationAdvisoryModel
    ) -> bool:
        """Verify deterministic payload equivalence between two models via SHA-256 checksum and recommendation matching."""
        if model_a.sha256_checksum != model_b.sha256_checksum:
            return False
        if len(model_a.recommendations) != len(model_b.recommendations):
            return False
        for r_a, r_b in zip(model_a.recommendations, model_b.recommendations):
            if r_a.fingerprint != r_b.fingerprint or r_a.recommendation_id != r_b.recommendation_id:
                return False
        return True
