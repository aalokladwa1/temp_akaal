import os
import tempfile
import sys
import hashlib
from types import ModuleType

if "typer" not in sys.modules:
    dummy_typer = ModuleType("typer")
    dummy_typer.Typer = lambda **kwargs: dummy_typer
    dummy_typer.command = lambda *args, **kwargs: (lambda f: f)
    dummy_typer.callback = lambda *args, **kwargs: (lambda f: f)
    dummy_typer.Option = lambda default=None, *a, **kw: default
    dummy_typer.Argument = lambda default=None, *a, **kw: default
    sys.modules["typer"] = dummy_typer
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


def _seed_reports_test_data(db_path: str):
    from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
    uow = SQLiteUnitOfWork(db_path=db_path)
    with uow:
        uow.initialize_schema()
        uow.connection.execute(
            """
            INSERT OR REPLACE INTO migrations (
                migration_id, revision, name, mode, state, tenant_id, workspace_id, project_id,
                configuration, lineage, created_at, updated_at
            ) VALUES ('2026-0101', 1, 'Production Oracle to Postgres', 'M1', 'COMPLETED', 'org-acme', 'ws-main', 'proj-db', '{}', '{}', '2026-09-30T00:00:00Z', '2026-09-30T00:00:00Z')
            """
        )
        uow.connection.execute(
            """
            INSERT OR REPLACE INTO immutable_artifacts (
                artifact_id, tenant_id, artifact_type, fingerprint, content, created_at
            ) VALUES ('CERT-MIG-2026-001', 'org-acme', 'CERTIFICATION', 'fp-cert-01', '{"title": "Prod Cert", "decision": "CERTIFIED"}', '2026-09-30T00:00:00Z')
            """
        )
        ev_content = '{"status": "VERIFIED"}'
        ev_fp = hashlib.sha256(ev_content.encode("utf-8")).hexdigest()
        uow.connection.execute(
            """
            INSERT OR REPLACE INTO immutable_artifacts (
                artifact_id, tenant_id, artifact_type, fingerprint, content, created_at
            ) VALUES ('EV-2026-VAL-01', 'org-acme', 'EVIDENCE_DOSSIER', ?, ?, '2026-09-30T00:00:00Z')
            """,
            (ev_fp, ev_content),
        )


def test_reports_summary_query(temp_db_path, ipc_actor):
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # 1. Unseeded truthful empty check
        q = make_query("report.summary", {}, ipc_actor, CorrelationContext.new())
        res = caller.handle_query(q)
        assert res.status == CallerResultStatus.OK
        assert res.result["total_reports_count"] == 0
        assert res.result["certification_attention_count"] == 0
        assert res.result["evidence_manifests_count"] == 0

        # 2. Seeded dynamic calculation
        _seed_reports_test_data(temp_db_path)
        res_seeded = caller.handle_query(q)
        assert res_seeded.status == CallerResultStatus.OK
        assert res_seeded.result["total_reports_count"] >= 1
        assert res_seeded.result["evidence_manifests_count"] >= 2
    finally:
        caller.close()


def test_reports_list_and_get_query(temp_db_path, ipc_actor):
    _seed_reports_test_data(temp_db_path)
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # List all
        q = make_query("report.list", {}, ipc_actor, CorrelationContext.new())
        res = caller.handle_query(q)
        assert res.status == CallerResultStatus.OK
        reports = res.result.get("reports", [])
        assert len(reports) >= 1
        rep_id = reports[0]["id"]

        # Filter by category
        q_filtered = make_query("report.list", {"category": "MIGRATION"}, ipc_actor, CorrelationContext.new())
        res_filtered = caller.handle_query(q_filtered)
        assert res_filtered.status == CallerResultStatus.OK
        mig_reports = res_filtered.result.get("reports", [])
        assert all(r["category"] == "MIGRATION" for r in mig_reports)

        # Get specific report
        q_get = make_query("report.get", {"report_id": rep_id}, ipc_actor, CorrelationContext.new())
        res_get = caller.handle_query(q_get)
        assert res_get.status == CallerResultStatus.OK
        assert res_get.result["id"] == rep_id
        assert "payload" in res_get.result
        assert "integrity" in res_get.result
    finally:
        caller.close()


def test_report_export_query(temp_db_path, ipc_actor):
    _seed_reports_test_data(temp_db_path)
    caller = authorized_caller(db_path=temp_db_path)
    try:
        q_list = make_query("report.list", {}, ipc_actor, CorrelationContext.new())
        reports = caller.handle_query(q_list).result.get("reports", [])
        rep_id = reports[0]["id"]

        q = make_query("report.export", {"report_id": rep_id, "format": "JSON"}, ipc_actor, CorrelationContext.new())
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
        # Unseeded: returns 0 certifications truthfully
        q_list = make_query("certification.list", {}, ipc_actor, CorrelationContext.new())
        res_empty = caller.handle_query(q_list)
        assert res_empty.status == CallerResultStatus.OK
        assert len(res_empty.result.get("certifications", [])) == 0

        # Seeded: returns real certification
        _seed_reports_test_data(temp_db_path)
        res_seeded = caller.handle_query(q_list)
        assert res_seeded.status == CallerResultStatus.OK
        certs = res_seeded.result.get("certifications", [])
        assert len(certs) >= 1

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
        # Unseeded: empty evidence
        q_list = make_query("evidence.list", {}, ipc_actor, CorrelationContext.new())
        res_empty = caller.handle_query(q_list)
        assert res_empty.status == CallerResultStatus.OK
        assert len(res_empty.result.get("evidence", [])) == 0

        # Seeded: returns real evidence
        _seed_reports_test_data(temp_db_path)
        res_seeded = caller.handle_query(q_list)
        assert res_seeded.status == CallerResultStatus.OK
        items = res_seeded.result.get("evidence", [])
        assert len(items) >= 2

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
        assert len(res_dos.result.get("dossiers", [])) >= 1

        # List packages (truthfully empty when unconfigured)
        q_pkg = make_query("evidence.packages.list", {}, ipc_actor, CorrelationContext.new())
        res_pkg = caller.handle_query(q_pkg)
        assert res_pkg.status == CallerResultStatus.OK
        assert res_pkg.result.get("packages") == []

        # List certificates
        q_cert = make_query("evidence.certificates.list", {}, ipc_actor, CorrelationContext.new())
        res_cert = caller.handle_query(q_cert)
        assert res_cert.status == CallerResultStatus.OK
        assert len(res_cert.result.get("certificates", [])) >= 1
    finally:
        caller.close()

