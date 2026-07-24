"""
Platform 10 Public Façade — Recovery Intelligence Integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.recovery_intelligence.facade.platform10 import RecoveryIntelligencePlatformV10


class IPlatform10Facade(IFacade, ABC):
    """Abstract Interface for Platform 10 Recovery Intelligence Façade."""

    @abstractmethod
    async def recommend_recovery_point(self, migration_id: str, checkpoint_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def estimate_recovery_time(self, migration_id: str, uncommitted_batches: int = 1) -> Dict[str, Any]:
        pass


class Platform10Facade(IPlatform10Facade):
    """Production Platform 10 Façade Implementation routing to RecoveryIntelligencePlatformV10."""

    def __init__(self, platform_engine: Optional[RecoveryIntelligencePlatformV10] = None) -> None:
        self._engine = platform_engine or RecoveryIntelligencePlatformV10()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 10 (Recovery Intelligence Platform)",
            version="10.0.0",
            supported_features=[
                "recovery_point_recommendation",
                "recovery_time_estimation",
                "recovery_strategy_recommendation",
                "recovery_readiness_assessment",
                "recovery_scenario_simulation",
            ],
            active_protocols=["REST", "gRPC"],
        )

    async def recommend_recovery_point(self, migration_id: str, checkpoint_id: str) -> Dict[str, Any]:
        try:
            rec = self._engine.recommend_recovery_point(migration_id, checkpoint_id)
            return {
                "recommendation_id": rec.recommendation_id,
                "target_migration_id": rec.target_migration_id,
                "recommended_checkpoint_id": rec.recommended_checkpoint_id,
                "rpo_lag_seconds": rec.rpo_lag_seconds,
                "data_loss_risk_score": rec.data_loss_risk_score,
                "generated_at": rec.generated_at,
            }
        except Exception as e:
            raise FacadeError(f"Platform 10 RPO Recommendation failed: {str(e)}")

    async def estimate_recovery_time(self, migration_id: str, uncommitted_batches: int = 1) -> Dict[str, Any]:
        try:
            est = self._engine.estimate_recovery_time(migration_id, uncommitted_batches)
            return {
                "estimate_id": est.estimate_id,
                "target_migration_id": est.target_migration_id,
                "estimated_rto_minutes": est.estimated_rto_minutes,
                "confidence_score": est.confidence_score,
                "calculated_at": est.calculated_at,
            }
        except Exception as e:
            raise FacadeError(f"Platform 10 RTO Estimation failed: {str(e)}")
