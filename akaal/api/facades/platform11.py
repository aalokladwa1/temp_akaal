"""
Platform 11 Public Façade — Enterprise Trust & Certification Integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.trust_certification.facade.platform11 import EnterpriseTrustCertificationPlatformV11


class IPlatform11Facade(IFacade, ABC):
    """Abstract Interface for Platform 11 Enterprise Trust & Certification Façade."""

    @abstractmethod
    async def record_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def compute_trust_score(self, migration_id: str, integrity_pct: float = 100.0, reliability_pct: float = 100.0) -> Dict[str, Any]:
        pass


class Platform11Facade(IPlatform11Facade):
    """Production Platform 11 Façade Implementation routing to EnterpriseTrustCertificationPlatformV11."""

    def __init__(self, platform_engine: Optional[EnterpriseTrustCertificationPlatformV11] = None) -> None:
        self._engine = platform_engine or EnterpriseTrustCertificationPlatformV11()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 11 (Enterprise Trust & Certification Platform)",
            version="11.0.0",
            supported_features=[
                "immutable_validation_ledger",
                "migration_trust_score",
                "enterprise_certification_report",
                "compliance_evidence_package",
                "digital_certification_seal",
                "audit_export_package",
            ],
            active_protocols=["REST", "gRPC"],
        )

    async def record_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            entry = self._engine.record_validation(payload)
            return {
                "entry_id": entry.entry_id,
                "index": entry.index,
                "timestamp": entry.timestamp,
                "previous_hash": entry.previous_hash,
                "block_hash": entry.block_hash,
            }
        except Exception as e:
            raise FacadeError(f"Platform 11 Record Validation failed: {str(e)}")

    async def compute_trust_score(self, migration_id: str, integrity_pct: float = 100.0, reliability_pct: float = 100.0) -> Dict[str, Any]:
        try:
            score = self._engine.compute_trust_score(migration_id, integrity_pct, reliability_pct)
            return {
                "target_migration_id": score.target_migration_id,
                "trust_score": score.trust_score,
                "grade": score.grade.value,
                "calculated_at": score.calculated_at,
            }
        except Exception as e:
            raise FacadeError(f"Platform 11 Trust Score calculation failed: {str(e)}")
