"""
Schema Evolution REST API Router (/api/v1/schema).
"""

from fastapi import APIRouter
from akaal.api.contracts.dto import (
    SchemaCheckDTO,
    SchemaCompatibilityResultDTO,
    SchemaProposalDTO,
    SchemaEvolutionResultDTO,
)
from akaal.api.facades.platform5 import Platform5Facade

router = APIRouter(prefix="/schema", tags=["Schema Evolution"])
platform5_facade = Platform5Facade()


@router.post("/check", response_model=SchemaCompatibilityResultDTO)
async def validate_schema(request: SchemaCheckDTO):
    """Check proposed DDL compatibility against Platform 5 rules."""
    return await platform5_facade.validate_schema_compatibility(request)


@router.post("/propose", response_model=SchemaEvolutionResultDTO)
async def propose_evolution(proposal: SchemaProposalDTO):
    """Propose and apply schema evolution."""
    return await platform5_facade.propose_schema_evolution(proposal)
