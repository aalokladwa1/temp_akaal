"""
AKAAL Platform 10 — Recovery Intelligence Domain Models.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from akaal.recovery_intelligence.domain.enums import RecoveryStrategyType, RecoveryReadinessState


@dataclass(frozen=True)
class RecoveryPointRecommendation:
    recommendation_id: str
    target_migration_id: str
    recommended_checkpoint_id: str
    rpo_lag_seconds: float
    data_loss_risk_score: float
    generated_at: str


@dataclass(frozen=True)
class RecoveryTimeEstimate:
    estimate_id: str
    target_migration_id: str
    estimated_rto_minutes: float
    confidence_score: float
    calculated_at: str


@dataclass(frozen=True)
class RecoveryStrategy:
    strategy_id: str
    target_migration_id: str
    strategy_type: RecoveryStrategyType
    steps: List[str]
    estimated_cost_units: float


@dataclass(frozen=True)
class RecoveryReadinessReport:
    report_id: str
    target_migration_id: str
    state: RecoveryReadinessState
    readiness_score: float
    blockers: List[str]
    assessed_at: str


@dataclass(frozen=True)
class RecoverySimulationResult:
    simulation_id: str
    target_migration_id: str
    simulated_rto_minutes: float
    simulated_data_loss_rows: int
    success: bool
    executed_at: str
