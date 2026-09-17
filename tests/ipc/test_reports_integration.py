import os
import tempfile
import pytest
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_query


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def ipc_actor():
    return ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="Test Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator", "admin"),
        scopes=("migration.read", "migration.write"),
    )


def test_reports_summary_query(temp_db_path, ipc_actor):
    caller = authorized_caller(db_path=temp_db_path)
    try:
        q = make_query("report.summary", {}, ipc_actor, CorrelationContext.new())
        res = caller.handle_query(q)
        assert res.status == CallerResultStatus.OK
        assert "total_reports_count" in res.result
        assert "certification_attention_count" in res.result
        assert "evidence_manifests_count" in res.result
        assert res.result["total_reports_count"] >= 14
    finally:
        caller.close()


def test_reports_list_and_get_query(temp_db_path, ipc_actor):
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # List all
        q = make_query("report.list", {}, ipc_actor, CorrelationContext.new())
        res = caller.handle_query(q)
        assert res.status == CallerResultStatus.OK
        reports = res.result.get("reports", [])
        assert len(reports) >= 14

        # Filter by category
        q_filtered = make_query("report.list", {"category": "CDC"}, ipc_actor, CorrelationContext.new())
        res_filtered = caller.handle_query(q_filtered)
        assert res_filtered.status == CallerResultStatus.OK
        cdc_reports = res_filtered.result.get("reports", [])
        assert all(r["category"] == "CDC" for r in cdc_reports)

        # Get specific report
        q_get = make_query("report.get", {"report_id": "REP-2026-0101"}, ipc_actor, CorrelationContext.new())
        res_get = caller.handle_query(q_get)
        assert res_get.status == CallerResultStatus.OK
        assert res_get.result["id"] == "REP-2026-0101"
        assert "payload" in res_get.result
        assert "integrity" in res_get.result
    finally:
        caller.close()


def test_report_export_query(temp_db_path, ipc_actor):
    caller = authorized_caller(db_path=temp_db_path)
    try:
        q = make_query("report.export", {"report_id": "REP-2026-0101", "format": "JSON"}, ipc_actor, CorrelationContext.new())
        res = caller.handle_query(q)
        assert res.status == CallerResultStatus.OK
        assert res.result["format"] == "JSON"
        assert res.result["status"] == "COMPLETED"
        assert res.result["sha256_digest"] is not None
        assert "content" in res.result
    finally:
        caller.close()


def test_certification_queries(temp_db_path, ipc_actor):
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # List certifications
        q_list = make_query("certification.list", {}, ipc_actor, CorrelationContext.new())
        res_list = caller.handle_query(q_list)
        assert res_list.status == CallerResultStatus.OK
        certs = res_list.result.get("certifications", [])
        assert len(certs) >= 4

        # Get specific certification
        q_get = make_query("certification.get", {"certification_id": "CERT-MIG-2026-001"}, ipc_actor, CorrelationContext.new())
        res_get = caller.handle_query(q_get)
        assert res_get.status == CallerResultStatus.OK
        assert res_get.result["id"] == "CERT-MIG-2026-001"
        assert res_get.result["decision"] == "CERTIFIED"
    finally:
        caller.close()


def test_evidence_portal_queries_and_verification(temp_db_path, ipc_actor):
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # List evidence items
        q_list = make_query("evidence.list", {}, ipc_actor, CorrelationContext.new())
        res_list = caller.handle_query(q_list)
        assert res_list.status == CallerResultStatus.OK
        items = res_list.result.get("evidence", [])
        assert len(items) >= 5

        # Get specific evidence
        q_get = make_query("evidence.get", {"artifact_id": "EV-2026-VAL-01"}, ipc_actor, CorrelationContext.new())
        res_get = caller.handle_query(q_get)
        assert res_get.status == CallerResultStatus.OK
        assert res_get.result["id"] == "EV-2026-VAL-01"

        # Verify evidence
        q_verify = make_query("evidence.verify", {"target_id": "EV-2026-VAL-01", "target_type": "EVIDENCE_ARTIFACT"}, ipc_actor, CorrelationContext.new())
        res_verify = caller.handle_query(q_verify)
        assert res_verify.status == CallerResultStatus.OK
        assert res_verify.result["result_status"] == "VERIFIED"

        # List dossiers
        q_dos = make_query("evidence.dossiers.list", {}, ipc_actor, CorrelationContext.new())
        res_dos = caller.handle_query(q_dos)
        assert res_dos.status == CallerResultStatus.OK
        assert len(res_dos.result.get("dossiers", [])) >= 3

        # List packages
        q_pkg = make_query("evidence.packages.list", {}, ipc_actor, CorrelationContext.new())
        res_pkg = caller.handle_query(q_pkg)
        assert res_pkg.status == CallerResultStatus.OK
        assert len(res_pkg.result.get("packages", [])) >= 1

        # List certificates
        q_cert = make_query("evidence.certificates.list", {}, ipc_actor, CorrelationContext.new())
        res_cert = caller.handle_query(q_cert)
        assert res_cert.status == CallerResultStatus.OK
        assert len(res_cert.result.get("certificates", [])) >= 2
    finally:
        caller.close()
