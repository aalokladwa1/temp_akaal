"""
Reporting REST API Router (/api/v1/reports).
"""

from fastapi import APIRouter
from akaal.api.contracts.dto import ReportDTO
from akaal.api.facades.platform8 import Platform8Facade

router = APIRouter(prefix="/reports", tags=["Reporting"])
platform8_facade = Platform8Facade()


@router.get("/{report_id}", response_model=ReportDTO)
async def get_report(report_id: str):
    """Retrieve an executive or compliance report."""
    return await platform8_facade.get_report(report_id)
