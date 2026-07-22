"""
Unit tests for ReportingClient, Platform8Facade, and Platform 7 Wrapper.
"""

import pytest
from akaal.api.facades.platform8 import Platform8Facade as Platform7FacadeWrapper
from akaal.reporting.api.client import ReportingClient
from akaal.reporting.api.facade import Platform8Facade
from akaal.reporting.contracts.dto import ReportRequestDTO


@pytest.mark.asyncio
async def test_reporting_facade_and_wrapper_flow():
    p7_wrapper = Platform7FacadeWrapper()
    facade = Platform8Facade()

    # Capabilities check via Platform 7 wrapper
    caps = await p7_wrapper.get_capabilities()
    assert caps.platform_name == "Platform 8 (Reporting Engine)"
    assert "premigration_report" in caps.supported_features

    # Report Generation via Platform 8 Facade
    req = ReportRequestDTO(report_type="PRE_MIGRATION", migration_id="mig-facade-1", export_format="JSON")
    art_dto = await facade.generate_report(req)
    assert art_dto.report_type == "PRE_MIGRATION"
    assert art_dto.format == "JSON"
    assert len(art_dto.checksum_sha256) == 64

    # Audit Package Generation via Facade
    audit_pkg = await facade.generate_audit_package("mig-facade-1", ["PRE_MIGRATION", "EXECUTIVE_SUMMARY"])
    assert audit_pkg.migration_id == "mig-facade-1"
    assert audit_pkg.reports_count == 2
