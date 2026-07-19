"""
AKAAL Enterprise Intelligence Platform — Strategy Analyzer
===========================================================
Evaluates architectural migration trade-offs and synthesizes StrategySynthesis objects.
"""

from typing import Any, Dict, Optional
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.intelligence.analyzers.base_intelligence_analyzer import BaseIntelligenceAnalyzer
from akaal.intelligence.models.enterprise_intelligence_enums import StrategyType
from akaal.intelligence.models.strategy_synthesis import StrategySynthesis


class StrategyAnalyzer(BaseIntelligenceAnalyzer):
    """
    Synthesizes migration execution strategy (Aggressive Parallel vs Stage-by-Stage vs High Availability).
    """

    @property
    def name(self) -> str:
        return "strategy"

    @property
    def description(self) -> str:
        return "Synthesizes migration execution strategy archetypes and trade-off guidelines."

    def analyze(
        self,
        advisory_model: MigrationAdvisoryModel,
        context: Optional[Dict[str, Any]] = None,
    ) -> StrategySynthesis:
        ctx = context or {}
        preferred_strategy = ctx.get("preferred_strategy")

        if preferred_strategy:
            try:
                strategy_type = StrategyType(preferred_strategy)
            except ValueError:
                strategy_type = StrategyType.BALANCED_STAGE_BY_STAGE
        else:
            # Default to Aggressive Parallel for low-risk, high-throughput advisory models
            strategy_type = StrategyType.AGGRESSIVE_PARALLEL

        return StrategySynthesis(
            strategy_id=f"STRAT-{strategy_type.value[:8]}",
            strategy_type=strategy_type,
            primary_objective="Minimize cutover window duration while preserving data integrity.",
            recommended_execution_mode="PARALLEL" if strategy_type == StrategyType.AGGRESSIVE_PARALLEL else "STAGE_BY_STAGE",
            estimated_total_duration_seconds=3600.0,
            max_recommended_parallelism=16 if strategy_type == StrategyType.AGGRESSIVE_PARALLEL else 4,
            key_assumptions=(
                "Target database IOPS >= 10,000.",
                "Source database read replication active.",
            ),
            strategic_advantages=(
                "Reduces downtime window by up to 60%.",
                "Enables automated continuous validation.",
            ),
            identified_constraints=("High network bandwidth required during initial bulk sync.",),
            mitigation_guidelines=("Monitor target DB queue depth during batch extraction.",),
            metadata={"source_analyzer": self.name},
        )
