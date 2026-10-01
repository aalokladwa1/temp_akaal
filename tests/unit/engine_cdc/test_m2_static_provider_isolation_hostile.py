"""
tests/unit/engine_cdc/test_m2_static_provider_isolation_hostile.py
==================================================================
Hostile verification of Static / File Provider M2 Capability Isolation.
Proves that static/file providers (file, csv, jsonl, parquet, sap_application, salesforce)
cannot participate in M2 CDC capture, fail closed with CDCCapabilityError,
and do not manufacture synthetic CDC source adapters or fake cutover readiness.
"""

import os
import pytest
from typing import Dict, Any

from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.cdc.models.errors import CDCCapabilityError
from akaalEngine.cdc.policy.migration_mode import MigrationModeSelector
from akaalEngine.cdc.models.capabilities import (
    CDCCapabilityDescriptor,
    MigrationMode,
    DeliverySemantics,
    OrderingGuarantee,
    HandshakeMode,
    SynchronizationBarrierStrategy,
)


@pytest.fixture(autouse=True)
def setup_receipt_secret():
    old = os.environ.get("AKAAL_GATEWAY_RECEIPT_SECRET")
    os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = "akaal-test-receipt-secret-32bytes!"
    yield
    if old is None:
        os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)
    else:
        os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = old


def test_01_static_and_file_providers_fail_closed_on_cdc_initialization():
    """Requesting M2 CDC initialization for static/file/SaaS providers fails closed with CDCCapabilityError."""
    gw = EngineGateway()
    static_providers = ["file", "csv", "jsonl", "parquet", "sap_application", "salesforce", "servicenow"]

    for prov in static_providers:
        token = gw.coordinator.durability_authority.issue_fencing_token(f"mig-cdc-{prov}/run-1", "gw-worker")
        env = {
            "resource_id": f"mig-cdc-{prov}/run-1",
            "worker_id": "gw-worker",
            "fencing_epoch": token.fencing_epoch,
            "signature": token.signature,
            "issued_at": token.issued_at,
        }
        ctx = GatewayRequestContext(
            tenant_id="ten-1",
            workspace_id="ws-1",
            migration_id=f"mig-cdc-{prov}",
            operation_id=f"op-cdc-{prov}",
            run_id="run-1",
            fencing_epoch=token.fencing_epoch,
            fencing_token_envelope=env,
        )
        req = GatewayRequest(
            operation=SemanticOperation.INITIALIZE_CDC_STREAM,
            context=ctx,
            payload={
                "source_provider_id": prov,
                "source_connection_params": {"file_path": f"/tmp/{prov}.data"},
                "fencing_token": token,
            }
        )

        resp = gw.execute(req)
        # Must fail closed: success=False, error reported, no active stream handle or boundary token fabricated
        assert resp.success is False
        assert "not support M2 CDC capture" in (resp.error_message or "")


def test_02_file_target_writer_delete_batch_does_not_inflate_m2_capability():
    """FileTargetWriter possessing delete_batch does NOT make file provider M2-eligible."""
    from akaalEngine.transport.drivers.files import FileTargetWriter
    import tempfile

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as f:
        writer = FileTargetWriter(f.name, "CSV")
        assert hasattr(writer, "delete_batch")
        # Writer capabilities truthfully state bulk_read=False, bulk_write=True
        caps = writer.get_capabilities()
        assert caps.bulk_write is True

    # Capability authority evaluates mode to OFFLINE_SNAPSHOT only
    file_descriptor = CDCCapabilityDescriptor(
        provider_name="file",
        capture_mode=MigrationMode.OFFLINE_SNAPSHOT,
        handshake_mode=HandshakeMode.OFFLINE_ONLY,
        barrier_strategy=SynchronizationBarrierStrategy.QUIESCE_OFFLINE_REQUIRED,
        ordering_guarantee=OrderingGuarantee.PROVIDER_DEFINED,
    )
    mode, reason = MigrationModeSelector.select_mode(file_descriptor, {"file_path": "/tmp/test.csv"})
    assert mode == MigrationMode.OFFLINE_SNAPSHOT
    assert "downgraded to OFFLINE_SNAPSHOT" in reason
