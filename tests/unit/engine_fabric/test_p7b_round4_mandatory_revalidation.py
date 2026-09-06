"""
tests.unit.engine_fabric.test_p7b_round4_mandatory_revalidation
====================================================================
P7B Group-1 Hostile Review Round 4 -- §2/§3: security revalidation must be structurally
mandatory for fabric-bound execution, and revocation must be LIVE, not merely
signature-valid.

Proves:
  * execute_assignment_via_transport exposes NO way to omit revalidation (no
    security_revalidator parameter exists on its signature at all -- structurally
    impossible to pass None and skip it, unlike calling TransportAuthority directly).
  * A site revoked AFTER assignment issuance is caught via live_trust_check, even
    though verify_assignment's own stateless signature check alone would have passed.
  * Tenant rebinding after issuance is likewise caught.
  * Zero external-boundary (file) writes occur once revocation/rebinding is detected.
"""

from __future__ import annotations

import csv
import inspect

import pytest

from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.remote_execution import (
    RemoteExecutionControlPlane,
    RemoteExecutionError,
    execute_assignment_via_transport,
)
from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition
from akaalEngine.transport.models.errors import TransportFencingError

SIGNING_KEY = b"round4-mandatory-revalidation-key"


def _ready_registry(site_id="site-1", tenant_id="tenant-a") -> SiteRegistry:
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity(site_id, verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry


def test_execute_assignment_via_transport_has_no_security_revalidator_parameter_at_all():
    """Structural proof: it is IMPOSSIBLE to call this function while omitting or
    overriding the revalidation gate -- the parameter doesn't exist on its signature,
    unlike the underlying TransportAuthority.execute_partition_transport (which
    correctly still allows None for non-fabric callers)."""
    sig = inspect.signature(execute_assignment_via_transport)
    assert "security_revalidator" not in sig.parameters


def _setup(tmp_path, tenant_id="tenant-a"):
    registry = _ready_registry(tenant_id=tenant_id)
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id=tenant_id, workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )

    source_csv = tmp_path / "source.csv"
    target_csv = tmp_path / "target.csv"
    with open(source_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id"])
        w.writeheader()
        w.writerow({"id": "1"})

    transport_authority = TransportAuthority()
    reader = transport_authority.resolve_source_reader_for_provider("file", file_path=str(source_csv), format_type="CSV")
    writer = transport_authority.resolve_target_writer_for_provider("file", file_path=str(target_csv), format_type="CSV")
    partition = TransportPartition(partition_id="p0", table_name="source.csv", schema_name="file", target_schema="file", strategy=list(PartitionStrategy)[0])

    return registry, assignment, transport_authority, reader, writer, partition, target_csv


def test_happy_path_with_live_trust_check_succeeds_and_writes_rows(tmp_path):
    registry, assignment, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)

    def live_trust_check(a):
        site = registry.get(a.site_id)
        return site.trust_state.value == "TRUSTED" and site.tenant_binding == a.tenant_id

    rows_written = execute_assignment_via_transport(
        transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
        expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
        expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
        live_trust_check=live_trust_check,
    )
    writer.close()
    assert rows_written == 1
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [{"id": "1"}]


def test_site_revoked_after_issuance_is_caught_by_live_trust_check_zero_rows_written(tmp_path):
    """THE critical Round-3-disclosed gap, now closed: verify_assignment's stateless
    signature check alone would still pass after revocation -- live_trust_check is what
    actually catches it, and this function makes supplying one the natural path."""
    registry, assignment, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)

    registry.revoke("site-1", reason="compromised after issuance")

    def live_trust_check(a):
        site = registry.get(a.site_id)
        return site.trust_state.value == "TRUSTED"

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            live_trust_check=live_trust_check,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0
    with open(target_csv, encoding="utf-8") as fh:
        assert fh.read() == ""


def test_tenant_rebound_after_issuance_is_caught_by_live_trust_check(tmp_path):
    registry, assignment, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path, tenant_id="tenant-old")

    registry.bind_tenant("site-1", "tenant-new", authorization_callback=lambda s, a, c: True)

    def live_trust_check(a):
        site = registry.get(a.site_id)
        return site.tenant_binding == a.tenant_id  # a.tenant_id is still "tenant-old"

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-old", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            live_trust_check=live_trust_check,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_live_trust_check_raising_is_not_swallowed(tmp_path):
    """A live_trust_check that raises (rather than returning False) must propagate as a
    failure, never be interpreted as success."""
    registry, assignment, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)

    def broken_live_trust_check(a):
        raise RuntimeError("simulated SiteRegistry lookup outage")

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            live_trust_check=broken_live_trust_check,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_live_trust_check_non_true_return_fails_closed(tmp_path):
    registry, assignment, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)

    def sloppy_live_trust_check(a):
        return 1  # truthy but not True

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            live_trust_check=sloppy_live_trust_check,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_missing_signing_material_rejected():
    with pytest.raises(RemoteExecutionError):
        execute_assignment_via_transport(
            transport_authority=object(), assignment=object(),
            expected_tenant_id="t", expected_plan_id="p", expected_site_id="s",
            expected_seal_fingerprint="f", reader=object(), writer=object(), partition=object(),
        )
