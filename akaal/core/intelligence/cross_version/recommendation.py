"""
Akaal — Cross-Version Compatibility Recommendation Engine
==========================================================
Generates scored, ranked advisory recommendations from
compatibility findings. Surfaces actionable migration guidance.
No SQL generation. No DDL output.
"""

from typing import Any, Dict, List, Tuple

from akaal.core.intelligence.cross_version.models import (
    CompatibilityFinding,
    CompatibilityRuleAction,
    CompatibilityTier,
    CompatibilityScore,
)


class CompatibilityRecommendation:
    """
    Lightweight advisory record (not a frozen dataclass deliberately — kept
    mutable for builder-style accumulation, then converted to the shared
    Recommendation model at report-assembly time).
    """
    __slots__ = (
        "recommendation_id", "title", "description",
        "target_object_path", "score", "composite_rank",
    )

    def __init__(
        self,
        recommendation_id: str,
        title: str,
        description: str,
        target_object_path: str,
        score: CompatibilityScore,
        composite_rank: float,
    ) -> None:
        self.recommendation_id = recommendation_id
        self.title = title
        self.description = description
        self.target_object_path = target_object_path
        self.score = score
        self.composite_rank = composite_rank


class CompatibilityScoreCalculator:
    """
    Derives a CompatibilityScore from a CompatibilityFinding.

    Scoring formula (composite_rank):
        rank = (confidence × 10) / max(1, risk × 1.5 + effort + blocking × 3)
    """

    def calculate_score(self, finding: CompatibilityFinding) -> CompatibilityScore:
        """Computes score metrics from a single finding."""
        return finding.score

    def compute_composite_rank(self, score: CompatibilityScore) -> float:
        """
        Produces a deterministic composite rank:
        High confidence, low risk, and no blocking issues yield the highest rank.
        """
        benefit = score.confidence * 10.0
        friction = max(
            1.0,
            (score.risk_level * 1.5)
            + (score.migration_effort * 1.0)
            + (score.blocking_issues * 3.0),
        )
        return round((benefit / friction) * score.confidence, 2)


class CompatibilityRanker:
    """
    Applies stable descending composite rank ordering to a list of
    CompatibilityRecommendations. Tie-breaks by target_object_path.
    """

    @classmethod
    def rank(
        cls,
        recs: List[CompatibilityRecommendation],
    ) -> List[CompatibilityRecommendation]:
        """Returns a new list sorted by descending rank, then path."""
        return sorted(
            recs,
            key=lambda r: (-r.composite_rank, r.target_object_path),
        )


class CompatibilityRecommendationAdvisor:
    """
    Generates migration advisory recommendations from compatibility findings.

    Recommendations are generated for:
    - WARN / REQUIRE_MANUAL actions (opportunity to document workaround)
    - BLOCK actions (critical — must be surfaced)

    ALLOW findings with NATIVE tier are skipped (no action needed).
    Composite rank threshold: 0.05 (very low bar to ensure BLOCK items surface).
    """

    _RANK_THRESHOLD = 0.05

    def __init__(self) -> None:
        self._calculator = CompatibilityScoreCalculator()

    def generate_recommendations(
        self,
        findings: List[CompatibilityFinding],
    ) -> List[CompatibilityRecommendation]:
        """
        Evaluates all findings and returns ranked advisory recommendations.

        Args:
            findings: Output from CompatibilityCapabilityAnalyzer.

        Returns:
            Ranked list of CompatibilityRecommendation instances.
        """
        recs: List[CompatibilityRecommendation] = []

        for finding in findings:
            # Skip fully compatible native features — nothing to recommend
            if (
                finding.action == CompatibilityRuleAction.ALLOW
                and finding.compatibility_tier == CompatibilityTier.NATIVE
            ):
                continue

            score = self._calculator.calculate_score(finding)
            rank = self._calculator.compute_composite_rank(score)

            if rank < self._RANK_THRESHOLD:
                continue

            rec_id = f"REC_COMPAT_{finding.feature_id.upper().replace('.', '_')}"
            title = self._build_title(finding)
            description = self._build_description(finding)

            recs.append(CompatibilityRecommendation(
                recommendation_id=rec_id,
                title=title,
                description=description,
                target_object_path=f"features.{finding.feature_id}",
                score=score,
                composite_rank=rank,
            ))

        return CompatibilityRanker.rank(recs)

    def _build_title(self, finding: CompatibilityFinding) -> str:
        tier_label = {
            CompatibilityTier.EMULATED: "Emulation Required",
            CompatibilityTier.PARTIAL: "Partial Support",
            CompatibilityTier.PLUGIN_PROVIDED: "Plugin Installation Required",
            CompatibilityTier.UNSUPPORTED: "UNSUPPORTED — Migration Blocker",
        }.get(finding.compatibility_tier, "Compatibility Advisory")

        return f"[{tier_label}] {finding.feature_name}"

    def _build_description(self, finding: CompatibilityFinding) -> str:
        action_clause = {
            CompatibilityRuleAction.WARN: "Review and validate the migration plan for this feature.",
            CompatibilityRuleAction.BLOCK: (
                "This feature BLOCKS migration. Redesign or remove before proceeding."
            ),
            CompatibilityRuleAction.REQUIRE_MANUAL: (
                "Manual operator intervention is required to migrate this feature."
            ),
        }.get(finding.action, "Review compatibility documentation.")

        guidance = finding.remediation_guidance or action_clause

        return (
            f"Feature '{finding.feature_name}' ({finding.feature_id}) from "
            f"{finding.source_dialect.value} is categorized as "
            f"'{finding.compatibility_tier.value}' on target "
            f"{finding.target_dialect.value}. {guidance}"
        )
