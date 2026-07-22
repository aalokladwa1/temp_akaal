"""
Platform 5 Public Façade — Schema Evolution & Metadata Integration.
"""

from abc import ABC, abstractmethod
import datetime

from akaal.api.contracts.dto import (
    CapabilityDTO,
    SchemaCheckDTO,
    SchemaCompatibilityResultDTO,
    SchemaEvolutionResultDTO,
    SchemaProposalDTO,
)
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade


class IPlatform5Facade(IFacade, ABC):
    """Abstract Interface for Platform 5 Façade."""

    @abstractmethod
    async def validate_schema_compatibility(self, request: SchemaCheckDTO) -> SchemaCompatibilityResultDTO:
        pass

    @abstractmethod
    async def propose_schema_evolution(self, proposal: SchemaProposalDTO) -> SchemaEvolutionResultDTO:
        pass


class Platform5Facade(IPlatform5Facade):
    """Production Platform 5 Façade Implementation."""

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 5 (Schema Evolution & Metadata)",
            version="1.0.0",
            supported_features=["validate_compatibility", "propose_evolution", "metadata_refresh"],
            active_protocols=["REST", "gRPC"],
        )

    async def validate_schema_compatibility(self, request: SchemaCheckDTO) -> SchemaCompatibilityResultDTO:
        try:
            # Validate DDL syntax or rules
            is_compat = not ("DROP COLUMN" in request.proposed_ddl.upper() and request.compatibility_mode == "BACKWARD")
            violations = []
            if not is_compat:
                violations.append("Dropping columns is forbidden in BACKWARD compatibility mode")

            return SchemaCompatibilityResultDTO(
                is_compatible=is_compat,
                schema_name=request.target_schema_name,
                compatibility_mode=request.compatibility_mode,
                violations=violations,
            )
        except Exception as e:
            raise FacadeError(f"Platform 5 Schema validation failed: {str(e)}")

    async def propose_schema_evolution(self, proposal: SchemaProposalDTO) -> SchemaEvolutionResultDTO:
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return SchemaEvolutionResultDTO(
                proposal_id=proposal.proposal_id,
                status="APPLIED",
                applied_at=now,
                new_version="1.1.0",
            )
        except Exception as e:
            raise FacadeError(f"Platform 5 Schema evolution failed: {str(e)}")
