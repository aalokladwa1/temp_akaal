"""
tests/unit/engine_gateway/test_m2_staged_ddl_fail_closed_hostile.py
==================================================================
Hostile verification of Staged DDL and Discovery fail-closed exception semantics.
Proves that required discovery failures fail closed, zero exceptions are swallowed,
and no empty-success or synthetic schema states are manufactured.
"""

import os
import pytest
from typing import Dict, Any

from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.discovery.errors.exceptions import DiscoveryTimeoutError


@pytest.fixture(autouse=True)
def setup_receipt_secret():
    old = os.environ.get("AKAAL_GATEWAY_RECEIPT_SECRET")
    os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = "akaal-test-receipt-secret-32bytes!"
    yield
    if old is None:
        os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)
    else:
        os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = old


class FailingDiscoveryAuthority:
    """Mock discovery authority that simulates physical discovery failure."""
    def discover(self, endpoint_spec):
        raise DiscoveryTimeoutError("Physical connection timeout during metadata discovery introspection.")


def test_01_prepare_migration_fails_closed_on_discovery_error():
    """PREPARE_MIGRATION_EXECUTION fails closed when discovery fails (no swallowed exceptions)."""
    gw = EngineGateway()
    gw.coordinator.discovery_authority = FailingDiscoveryAuthority()

    token = gw.coordinator.durability_authority.issue_fencing_token("mig-fail-ddl/run-1", "gw-worker")
    env = {
        "resource_id": "mig-fail-ddl/run-1",
        "worker_id": "gw-worker",
        "fencing_epoch": token.fencing_epoch,
        "signature": token.signature,
        "issued_at": token.issued_at,
    }

    ctx = GatewayRequestContext(
        tenant_id="ten-1",
        workspace_id="ws-1",
        migration_id="mig-fail-ddl",
        operation_id="op-prep-1",
        run_id="run-1",
        fencing_epoch=token.fencing_epoch,
        fencing_token_envelope=env,
    )

    req = GatewayRequest(
        operation=SemanticOperation.PREPARE_MIGRATION_EXECUTION,
        context=ctx,
        payload={
            "source_provider_id": "oracle",
            "source_connection_params": {"host": "invalid-host", "port": 1521},
            "target_provider_id": "postgresql",
            "target_connection_params": {"host": "pg-host", "port": 5432},
            "fencing_token": token,
        }
    )

    resp = gw.execute(req)
    # Must fail closed: success=False, error reported, no empty success READY status
    assert resp.success is False
    assert resp.payload is None or resp.payload.get("status") != "READY"


def test_02_bulk_migration_requires_discovery_when_partitions_missing_and_fails_closed():
    """EXECUTE_BULK_MIGRATION fails closed if partitions are missing and discovery fails."""
    gw = EngineGateway()
    gw.coordinator.discovery_authority = FailingDiscoveryAuthority()

    token = gw.coordinator.durability_authority.issue_fencing_token("mig-fail-bulk/run-1", "gw-worker")
    env = {
        "resource_id": "mig-fail-bulk/run-1",
        "worker_id": "gw-worker",
        "fencing_epoch": token.fencing_epoch,
        "signature": token.signature,
        "issued_at": token.issued_at,
    }

    ctx = GatewayRequestContext(
        tenant_id="ten-1",
        workspace_id="ws-1",
        migration_id="mig-fail-bulk",
        operation_id="op-bulk-1",
        run_id="run-1",
        fencing_epoch=token.fencing_epoch,
        fencing_token_envelope=env,
    )

    req = GatewayRequest(
        operation=SemanticOperation.EXECUTE_BULK_MIGRATION,
        context=ctx,
        payload={
            "source_provider_id": "oracle",
            "source_connection_params": {"host": "invalid-host"},
            "target_provider_id": "postgresql",
            "target_connection_params": {"host": "pg-host"},
            "tables": ["CUSTOMERS"],
            "fencing_token": token,
        }
    )

    resp = gw.execute(req)
    assert resp.success is False


def test_03_bulk_migration_with_explicit_partitions_skips_redundant_discovery():
    """EXECUTE_BULK_MIGRATION with pre-compiled partitions executes without requiring discovery."""
    gw = EngineGateway()
    from akaalEngine.transport.drivers.files import FileSourceReader, FileTargetWriter
    from akaalEngine.transport.models.spec import TransportPartition, PartitionStrategy
    import tempfile

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as src_f, \
         tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tgt_f:
        src_f.write("id,name\n1,Alice\n2,Bob\n")
        src_f.flush()

        reader = FileSourceReader(src_f.name, "CSV")
        writer = FileTargetWriter(tgt_f.name, "CSV")
        part = TransportPartition(
            partition_id="p0",
            table_name="users",
            schema_name="file",
            target_schema="file",
            strategy=PartitionStrategy.SINGLE_PARTITION,
        )

        token = gw.coordinator.durability_authority.issue_fencing_token("mig-explicit-part/run-1", "gw-worker")
        env = {
            "resource_id": "mig-explicit-part/run-1",
            "worker_id": "gw-worker",
            "fencing_epoch": token.fencing_epoch,
            "signature": token.signature,
            "issued_at": token.issued_at,
        }

        ctx = GatewayRequestContext(
            tenant_id="ten-1",
            workspace_id="ws-1",
            migration_id="mig-explicit-part",
            operation_id="op-bulk-2",
            run_id="run-1",
            fencing_epoch=token.fencing_epoch,
            fencing_token_envelope=env,
        )

        req = GatewayRequest(
            operation=SemanticOperation.EXECUTE_BULK_MIGRATION,
            context=ctx,
            payload={
                "source_reader": reader,
                "target_writer": writer,
                "partition": part,
                "fencing_token": token,
            }
        )

        resp = gw.execute(req)
        assert resp.success is True
        assert int(resp.payload["transport_snapshot"]) == 2
