"""
Platform 8 Public Façade — Enterprise Data Integrity Platform Integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import datetime

from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.data_integrity.facade.platform8 import EnterpriseDataIntegrityPlatformV8


class IPlatform8Facade(IFacade, ABC):
    """Abstract Interface for Platform 8 Data Integrity Façade."""

    @abstractmethod
    async def verify_e2e_consistency(self, source_table: str, target_table: str, row_count: int = 1000000) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def validate_transaction_boundary(self, transaction_id: str) -> Dict[str, Any]:
        pass


class Platform8Facade(IPlatform8Facade):
    """Production Platform 8 Façade Implementation routing to EnterpriseDataIntegrityPlatformV8."""

    def __init__(self, platform_engine: Optional[EnterpriseDataIntegrityPlatformV8] = None) -> None:
        self._engine = platform_engine or EnterpriseDataIntegrityPlatformV8()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 8 (Enterprise Data Integrity Platform)",
            version="8.0.0",
            supported_features=[
                "e2e_consistency_verification",
                "transaction_boundary_validation",
                "snapshot_consistency_validation",
                "cross_table_consistency_validation",
                "referential_integrity_validation",
                "incremental_consistency_verification",
            ],
            active_protocols=["REST", "gRPC"],
        )

    async def verify_e2e_consistency(self, source_table: str, target_table: str, row_count: int = 1000000) -> Dict[str, Any]:
        try:
            report = self._engine.verify_e2e_consistency(source_table, target_table, row_count)
            return {
                "report_id": report.report_id,
                "source_table": report.source_table,
                "target_table": report.target_table,
                "rows_compared": report.rows_compared,
                "mismatches_found": report.mismatches_found,
                "status": report.status.value,
                "mode": report.mode.value,
                "checksum_source": report.checksum_source,
                "checksum_target": report.checksum_target,
                "generated_at": report.generated_at,
            }
        except Exception as e:
            raise FacadeError(f"Platform 8 Data Integrity verification failed: {str(e)}")

    async def validate_transaction_boundary(self, transaction_id: str) -> Dict[str, Any]:
        try:
            res = self._engine.validate_transaction_boundary(transaction_id)
            return {
                "transaction_id": res.transaction_id,
                "is_committed_consistently": res.is_committed_consistently,
                "uncommitted_row_count": res.uncommitted_row_count,
                "status": res.status.value,
            }
        except Exception as e:
            raise FacadeError(f"Platform 8 Transaction boundary validation failed: {str(e)}")
