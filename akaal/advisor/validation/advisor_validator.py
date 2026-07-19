"""
Akaal — Advisor Validator
=========================
Validates input execution plans, recommendation models, enum consistency, and SHA-256 checksums.
"""

from typing import Any, List, Optional, Tuple

from akaal.advisor.models.advisory_enums import (
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisorySeverity,
)
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel


class AdvisorValidationError(Exception):
    """Exception raised for validation errors in Advisor Platform."""
    pass


class AdvisorValidator:
    """Enterprise Validator for Advisor Platform Inputs, Recommendations, and Advisory Models."""

    @classmethod
    def validate_input_plan(cls, plan: Any) -> List[str]:
        """Validate input MigrationExecutionPlan integrity and required fields."""
        issues: List[str] = []
        if plan is None:
            raise AdvisorValidationError("Input MigrationExecutionPlan cannot be None.")

        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        
        schema_version = plan_dict.get("schema_version", "")
        if not schema_version:
            issues.append("Input execution plan missing 'schema_version'.")

        checksum = plan_dict.get("sha256_checksum", "")
        if hasattr(plan, "to_dict") and not checksum:
            issues.append("Input execution plan missing SHA-256 checksum.")

        return issues

    @classmethod
    def validate_recommendation(cls, rec: AdvisoryRecommendation) -> List[str]:
        """Validate an individual AdvisoryRecommendation instance."""
        issues: List[str] = []
        if not rec.recommendation_id:
            issues.append("Recommendation missing 'recommendation_id'.")
        if not rec.title:
            issues.append(f"Recommendation {rec.recommendation_id} missing 'title'.")
        if not isinstance(rec.category, AdvisoryCategory):
            issues.append(f"Recommendation {rec.recommendation_id} has invalid category: {rec.category}.")
        if not isinstance(rec.severity, AdvisorySeverity):
            issues.append(f"Recommendation {rec.recommendation_id} has invalid severity: {rec.severity}.")
        if not isinstance(rec.priority, AdvisoryPriority):
            issues.append(f"Recommendation {rec.recommendation_id} has invalid priority: {rec.priority}.")
        if not rec.fingerprint:
            issues.append(f"Recommendation {rec.recommendation_id} missing fingerprint.")

        return issues

    @classmethod
    def validate_advisory_model(cls, model: MigrationAdvisoryModel) -> List[str]:
        """Validate complete MigrationAdvisoryModel output artifact."""
        issues: List[str] = []
        if model is None:
            raise AdvisorValidationError("MigrationAdvisoryModel cannot be None.")

        # 1. Verify checksum integrity
        if not model.verify_checksum():
            issues.append(f"Model checksum verification failed. Recorded={model.sha256_checksum}, Computed={model.compute_checksum()}")

        # 2. Check recommendation ID uniqueness
        seen_ids = set()
        for rec in model.recommendations:
            rec_issues = cls.validate_recommendation(rec)
            issues.extend(rec_issues)

            if rec.recommendation_id in seen_ids:
                issues.append(f"Duplicate recommendation ID detected: '{rec.recommendation_id}'")
            seen_ids.add(rec.recommendation_id)

        # 3. Check manifest total count matching actual recommendations
        if model.manifest.total_recommendations != len(model.recommendations):
            issues.append(
                f"Manifest total recommendations ({model.manifest.total_recommendations}) does not match recommendation list size ({len(model.recommendations)})."
            )

        return issues
