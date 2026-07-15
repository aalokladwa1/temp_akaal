"""
Akaal — Encryption Recommendation Engine
========================================
Calculates security scores, evaluates operational impact, and ranks security advisors.
"""

from typing import Any, Dict, List

from akaal.core.comparison.models.schema import TableSchema
from akaal.core.comparison.models import Schema
from akaal.core.models.enums import SystemType
from akaal.core.intelligence.encryption_aware.models import (
    EncryptionTranslation,
    EncryptionScore,
    EncryptionRecommendation,
    EncryptionCompatibilityTier,
    EncryptionAlgorithm,
)

class EncryptionScoreCalculator:
    """Computes security improvement, migration complexity, compliance weight, and performance overhead."""

    def calculate_score(
        self,
        table: TableSchema,
        trans: EncryptionTranslation
    ) -> EncryptionScore:
        """Determines prioritized score indices using dialect translation metadata."""
        # Calculate security improvement
        sec_imp = 0.50
        if trans.target_algorithm in (EncryptionAlgorithm.AES256, EncryptionAlgorithm.NATIVE_TDE):
            sec_imp = 0.95
        if trans.source_algorithm == EncryptionAlgorithm.TRIPLE_DES and trans.target_algorithm == EncryptionAlgorithm.AES256:
            sec_imp = 1.00  # significant crypto upgrade

        # Resolve compliance impact
        compliance = 1.00
        if trans.target_algorithm == EncryptionAlgorithm.TRIPLE_DES:
            compliance = 0.40  # deprecated, non-compliant algorithm

        # Priority calculation
        priority = 5
        if sec_imp > 0.50:
            priority += 3

        # Sensitivity name checking
        name_lower = table.name.lower()
        sensitive_keywords = ("user", "member", "payment", "transaction", "credential", "auth", "orders")
        if any(kw in name_lower for kw in sensitive_keywords):
            priority += 2
        priority = min(10, priority)

        # Operational complexity and risk
        complexity = 2
        risk = 1
        effort = 1
        perf_impact = trans.estimated_performance_overhead

        if trans.compatibility_tier == EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION:
            complexity = 4
            risk = 3
            effort = 3
        elif trans.compatibility_tier == EncryptionCompatibilityTier.REQUIRES_KEY_ROTATION:
            complexity = 3
            risk = 2
            effort = 2
        elif trans.compatibility_tier == EncryptionCompatibilityTier.PLUGIN_PROVIDED:
            complexity = 3
            risk = 2
            effort = 2

        evidence = {
            "source_algorithm": trans.source_algorithm.value,
            "target_algorithm": trans.target_algorithm.value,
            "compatibility_tier": trans.compatibility_tier.value,
            "estimated_overhead": trans.estimated_performance_overhead,
        }

        rationale = f"Upgrade encryption layout to target dialect {trans.target_dialect.value} algorithm {trans.target_algorithm.value}."
        if trans.compatibility_tier == EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION:
            rationale += " Requires implementing manual column-level crypto pg_crypto functions."

        return EncryptionScore(
            confidence=trans.translation_confidence,
            priority=priority,
            security_improvement=sec_imp,
            migration_complexity=complexity,
            operational_risk=risk,
            compliance_impact=compliance,
            performance_impact=perf_impact,
            implementation_effort=effort,
            rationale=rationale,
            evidence=evidence
        )

class EncryptionRanker:
    """Stable composite rank sorting engine."""

    @classmethod
    def calculate_composite_rank(cls, score: EncryptionScore) -> float:
        """Applies architectural prioritization formulas to rank options."""
        impact = (score.security_improvement * 8.0) + (score.compliance_impact * 6.0) - (score.performance_impact * 4.0)
        friction = (score.migration_complexity * 0.5) + (score.operational_risk * 0.8)
        friction = max(1.0, friction)
        rank = (impact / friction) * score.confidence
        return round(rank, 2)

    @classmethod
    def rank_recommendations(
        cls,
        recs: List[EncryptionRecommendation]
    ) -> List[EncryptionRecommendation]:
        """Performs a stable sort in descending rank ordering with object paths tie-breaking."""
        def sort_key(r: EncryptionRecommendation) -> Any:
            rank = cls.calculate_composite_rank(r.score)
            return (-rank, r.target_object_path)

        sorted_recs = list(recs)
        sorted_recs.sort(key=sort_key)
        return sorted_recs

class EncryptionRecommendationAdvisor:
    """Generates and prioritizes advisory recommendations list."""

    def __init__(self) -> None:
        self._calculator = EncryptionScoreCalculator()

    def generate_recommendations(
        self,
        schema: Schema,
        translations: Dict[str, EncryptionTranslation]
    ) -> List[EncryptionRecommendation]:
        """Evaluates mapping plans and yields scored recommendation alternatives."""
        recs = []
        for table in schema.tables:
            trans = translations.get(table.name)
            if not trans:
                continue

            score = self._calculator.calculate_score(table, trans)
            rank = EncryptionRanker.calculate_composite_rank(score)

            # Recommendations with composite rank below 0.40 are discarded
            if rank < 0.40:
                continue

            rec_id = f"REC_SEC_{table.name.upper()}"
            title = f"Enable Encryption for Table {table.name}"
            desc = f"Ensure physical storage blocks for {table.name} are secured using {trans.target_algorithm.value} cipher."

            recs.append(EncryptionRecommendation(
                recommendation_id=rec_id,
                title=title,
                description=desc,
                target_object_path=f"tables.{table.name}",
                score=score
            ))

        return EncryptionRanker.rank_recommendations(recs)
