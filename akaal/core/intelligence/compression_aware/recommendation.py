"""
Akaal — Compression Recommendation Engine
==========================================
Implements the Score Calculator, the Composite Ranker,
and the Strategy Recommendation Advisor.
"""

from typing import Any, Dict, List, Tuple

from akaal.core.comparison.models import Schema, TableSchema
from akaal.core.intelligence.common.models import (
    Diagnostic,
    Recommendation,
    RecommendationScore,
)
from akaal.core.intelligence.compression_aware.models import (
    CompressionAlgorithm,
    CompressionProfile,
    CompressionScore,
    CompressionRecommendation,
    CompressionTranslation,
)


class CompressionScoreCalculator:
    """Computes raw metrics and priority scores for compression strategies."""

    def calculate_score(
        self,
        table: TableSchema,
        translation: CompressionTranslation,
        projected_size_kb: int,
        uncompressed_size_kb: int
    ) -> CompressionScore:
        """Calculates expected storage, CPU, IO, complexity, and risk parameters."""
        algo = translation.target_algorithm

        # Storage benefit: ratio of space saved
        storage_benefit = 0.0
        if uncompressed_size_kb > 0:
            storage_benefit = (uncompressed_size_kb - projected_size_kb) / uncompressed_size_kb

        # CPU impact based on target algorithm complexity
        if algo in (CompressionAlgorithm.HCC_ARCHIVE_HIGH, CompressionAlgorithm.HCC_QUERY_HIGH, CompressionAlgorithm.COLUMNSTORE):
            cpu_impact = 0.40  # high CPU write compression overhead
            io_benefit = 0.85  # high read IO speedup
            complexity = 4     # columnar structures are more complex
            risk = 3
            maintenance = 3
        elif algo in (CompressionAlgorithm.PAGE, CompressionAlgorithm.ADVANCED_ROW):
            cpu_impact = 0.15
            io_benefit = 0.45
            complexity = 2
            risk = 1
            maintenance = 2
        elif algo == CompressionAlgorithm.TOAST:
            cpu_impact = 0.10
            io_benefit = 0.30
            complexity = 1
            risk = 1
            maintenance = 1
        else:
            cpu_impact = 0.0
            io_benefit = 0.0
            complexity = 1
            risk = 1
            maintenance = 1

        priority = 5
        if storage_benefit > 0.50:
            priority += 3
        if table.name.lower() in ("orders", "transactions", "logs"):
            priority += 2  # target transaction histories
        priority = min(10, priority)

        confidence = translation.translation_confidence

        rationale = (
            f"Table '{table.name}' target compression resolves to '{algo.value}' via "
            f"translation path: {' -> '.join(translation.translation_path)}. "
            f"Estimated space reduction of {int(storage_benefit * 100)}% with a read IO "
            f"speedup factor of {round(1.0 / (1.0 - storage_benefit), 2)}x."
        )

        evidence = {
            "uncompressed_size_kb": uncompressed_size_kb,
            "projected_size_kb": projected_size_kb,
            "ratio_loss": translation.estimated_ratio_loss,
            "compatibility_tier": translation.compatibility_tier.value
        }

        return CompressionScore(
            confidence=confidence,
            priority=priority,
            expected_storage_benefit=round(storage_benefit, 4),
            expected_cpu_impact=cpu_impact,
            expected_io_benefit=io_benefit,
            implementation_complexity=complexity,
            migration_risk=risk,
            maintenance_impact=maintenance,
            rationale=rationale,
            evidence=evidence
        )


class CompressionRanker:
    """Ranks recommendations by composite score, resolving tie-breakers deterministically."""

    @staticmethod
    def calculate_composite_rank(score: CompressionScore) -> float:
        """Calculates rank combining benefit, priority, CPU penalty, and friction."""
        impact = (score.priority * 1.5) + (score.expected_storage_benefit * 8.0) + (score.expected_io_benefit * 6.0)
        friction = (score.implementation_complexity * 0.5) + (score.migration_risk * 0.8) - (score.expected_cpu_impact * 4.0)
        
        # Ensure friction divisor is positive and bounded
        divisor = max(1.0, friction)
        return round((impact / divisor) * score.confidence, 2)

    @classmethod
    def rank_recommendations(
        cls,
        recommendations: List[CompressionRecommendation]
    ) -> List[CompressionRecommendation]:
        """Stable-sorts recommendations descending, resolving ties deterministically."""
        
        def sort_key(rec: CompressionRecommendation) -> Any:
            rank = cls.calculate_composite_rank(rec.score)
            # Tie breakers:
            # 1. Composite Rank (descending)
            # 2. Priority (descending)
            # 3. Object Path (alphabetical ascending)
            return (-rank, -rec.score.priority, rec.target_object_path)

        sorted_recs = list(recommendations)
        sorted_recs.sort(key=sort_key)
        return sorted_recs


class CompressionRecommendationAdvisor:
    """Generates and ranks prioritized suggestions for compression planning."""

    def __init__(self) -> None:
        self.calculator = CompressionScoreCalculator()

    def generate_recommendations(
        self,
        schema: Schema,
        translations: Dict[str, CompressionTranslation],
        allocations: Dict[str, Any]
    ) -> List[CompressionRecommendation]:
        """Scans tables and maps scored recommendations."""
        recs: List[CompressionRecommendation] = []

        for table in schema.tables:
            trans = translations.get(table.name)
            if not trans or trans.target_algorithm == CompressionAlgorithm.NONE:
                continue

            tbl_alloc = allocations.get(table.name, {})
            proj_size = tbl_alloc.get("total_size_kb", 500)
            uncompressed = tbl_alloc.get("data_size_kb", 1000)

            score = self.calculator.calculate_score(table, trans, proj_size, uncompressed)
            
            # Filter low composite rank recommendations
            composite_score = CompressionRanker.calculate_composite_rank(score)
            if composite_score < 0.40:
                continue

            rec = CompressionRecommendation(
                recommendation_id=f"rec:compression:{table.name}",
                title=f"Enable Compression on '{table.name}'",
                description=f"Configure table '{table.name}' to use target algorithm {trans.target_algorithm.value}.",
                target_object_path=f"tables.{table.name}",
                score=score
            )
            recs.append(rec)

        return CompressionRanker.rank_recommendations(recs)
