"""
Platform 6 Public Façade — Enterprise Governance Platform Integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import datetime

from akaal.api.contracts.dto import (
    CapabilityDTO,
    GovernanceApprovalRequestDTO,
    GovernanceDecisionDTO,
)
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.governance.facade.platform6 import EnterpriseGovernancePlatformV6


class IPlatform6Facade(IFacade, ABC):
    """Abstract Public Interface for Platform 6 Governance Façade."""

    @abstractmethod
    async def request_governance_approval(self, request: GovernanceApprovalRequestDTO) -> GovernanceDecisionDTO:
        pass

    @abstractmethod
    async def get_governance_health(self) -> Dict[str, Any]:
        pass


class Platform6Facade(IPlatform6Facade):
    """Production Platform 6 Façade Implementation routing to EnterpriseGovernancePlatformV6."""

    def __init__(self, platform_engine: Optional[EnterpriseGovernancePlatformV6] = None) -> None:
        self._engine = platform_engine or EnterpriseGovernancePlatformV6()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 6 (Enterprise Governance Platform)",
            version="6.0.0",
            supported_features=[
                "request_governance_approval",
                "policy_as_code_evaluator",
                "sod_enforcement",
                "four_eyes_validation",
                "emergency_override_service",
                "governance_impact_analyzer",
                "governance_dependency_graph",
                "governance_lifecycle_engine",
                "immutable_decision_ledger",
            ],
            active_protocols=["REST", "gRPC"],
        )

    async def request_governance_approval(self, request: GovernanceApprovalRequestDTO) -> GovernanceDecisionDTO:
        try:
            decision = self._engine.evaluate_and_govern_operation(
                target_platform=request.target_platform,
                operation_type=request.operation_type,
                requester_id=request.requester_id,
                payload=request.payload,
                requested_approvers=request.requested_approvers,
            )
            return GovernanceDecisionDTO(
                decision_id=decision.decision_id,
                workflow_id=decision.workflow_id,
                status=decision.outcome.value,
                rationale=decision.decision_rationale,
                ledger_block_hash=decision.block_hash,
                evaluated_at=decision.timestamp,
            )
        except Exception as e:
            raise FacadeError(f"Platform 6 Governance Evaluation failed: {str(e)}")

    async def get_governance_health(self) -> Dict[str, Any]:
        try:
            score = self._engine.health_engine.compute_health(0, 100.0, 0)
            return {
                "health_score": score.health_score,
                "posture_status": score.posture_status,
                "calculated_at": score.calculated_at,
            }
        except Exception as e:
            raise FacadeError(f"Failed to fetch Platform 6 health: {str(e)}")
