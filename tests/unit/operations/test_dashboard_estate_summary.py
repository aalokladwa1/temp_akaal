"""
akaalPipeline.tests.unit.operations.test_dashboard_estate_summary
================================================================
Comprehensive verification of get_estate_summary against real SQLiteUnitOfWork tables
and live host probes with zero synthetic mocks.
"""

import datetime
import sqlite3
import pytest
from akaalPipeline.application.query_service import PipelineQueryService
from akaalPipeline.contracts.enums import AlertLifecycleState, AuditDecision, IncidentStatus
from akaalPipeline.events.audit import SecurityAuditService
from akaalPipeline.operations.service import OperationService
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.repositories import SQLiteSecurityAuditRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def uow():
    uow_inst = SQLiteUnitOfWork(db_path=":memory:")
    uow_inst.initialize_schema()
    return uow_inst


@pytest.fixture
def query_service(uow):
    op_service = OperationService()
    return PipelineQueryService(repository=uow.repository, operation_service=op_service)


@pytest.fixture
def actor():
    return PipelineActorContext(
        actor_id="test-operator",
        actor_type="HUMAN",
        organization_id="tenant-alpha",
        workspace_id="workspace-alpha",
        roles=["OPERATOR", "ADMIN"],
    )


def test_estate_summary_empty_state(query_service, actor, uow):
    summary = query_service.get_estate_summary(actor=actor, conn=uow.connection)

    # 1. Zero counts for clean empty tenant state
    assert summary["runningCount"] == 0
    assert summary["scheduledCount"] == 0
    assert summary["attentionCount"] == 0
    assert summary["completedTodayCount"] == 0
    assert summary["activeMigrations"] == []
    assert summary["attentionItems"] == []
    assert summary["pendingApprovals"] == []
    assert summary["incidents"] == []
    assert summary["recentEvents"] == []

    # 2. Subsystems probe (authoritative statuses)
    assert len(summary["subsystems"]) == 4
    subsystem_names = [s["name"] for s in summary["subsystems"]]
    assert "Core Pipeline Engine" in subsystem_names
    assert "Named Pipe IPC" in subsystem_names
    assert "Database Authority" in subsystem_names
    assert "Validation Authority" in subsystem_names
    for sub in summary["subsystems"]:
        assert sub["status"] in ("healthy", "degraded", "unavailable")

    # 3. Real host capacity metrics (Host Memory, CPU, Host Storage)
    assert len(summary["capacityMetrics"]) == 3
    cap_resources = [c["resource"] for c in summary["capacityMetrics"]]
    assert "Host Memory" in cap_resources
    assert "CPU Utilization" in cap_resources
    assert "Host Storage" in cap_resources

    # 4. Fleet and Security (truthful unconfigured/not-evaluated states for empty database)
    assert summary["fleet"]["clusterState"] == "unconfigured"
    assert summary["fleet"]["nodeCount"] is None
    assert summary["fleet"]["totalCapacityCores"] is None
    assert summary["security"]["auditLedgerActive"] is None
    assert summary["security"]["posture"] == "unconfigured"
    assert summary["security"]["detail"] == "Security Posture Not Evaluated"


def test_estate_summary_populated_state(query_service, actor, uow):
    conn = uow.connection
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 0. Insert Tenant, Workspace & Principal
    conn.execute(
        """
        INSERT INTO enterprise_tenants (tenant_id, name, status, created_at, updated_at)
        VALUES ('tenant-alpha', 'Tenant Alpha', 'ACTIVE', ?, ?)
        """,
        (now_iso, now_iso),
    )
    conn.execute(
        """
        INSERT INTO enterprise_workspaces (workspace_id, tenant_id, name, status, created_at, updated_at)
        VALUES ('workspace-alpha', 'tenant-alpha', 'Workspace Alpha', 'ACTIVE', ?, ?)
        """,
        (now_iso, now_iso),
    )
    conn.execute(
        """
        INSERT INTO enterprise_principals (principal_id, tenant_id, principal_type, username, created_at, updated_at)
        VALUES ('secops-lead', 'tenant-alpha', 'HUMAN', 'secops-lead', ?, ?),
               ('test-operator', 'tenant-alpha', 'HUMAN', 'test-operator', ?, ?)
        """,
        (now_iso, now_iso, now_iso, now_iso),
    )

    # 1. Insert migrations: 1 running, 1 completed today, 1 failed
    conn.execute(
        """
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, configuration, lineage, created_at, updated_at)
        VALUES 
        ('mig-1', 1, 'Core Finance Bulk', 'M1_BULK', 'RUNNING', 'tenant-alpha', 'workspace-alpha', '{"source_provider": "PostgreSQL", "target_provider": "Snowflake"}', '[]', ?, ?),
        ('mig-2', 1, 'Analytics Warehouse Sync', 'M2_BULK_CDC', 'COMPLETED', 'tenant-alpha', 'workspace-alpha', '{"source_provider": "Oracle", "target_provider": "PostgreSQL"}', '[]', ?, ?),
        ('mig-3', 1, 'Customer Service Stream', 'M3_CDC_CONTINUOUS', 'FAILED', 'tenant-alpha', 'workspace-alpha', '{"source_provider": "MySQL", "target_provider": "Kafka"}', '[]', ?, ?)
        """,
        (now_iso, now_iso, now_iso, now_iso, now_iso, now_iso),
    )

    # 2. Insert pending governance approval (stage 2 -> quorum 0 of 2)
    conn.execute(
        """
        INSERT INTO governance_approvals (approval_id, tenant_id, migration_id, intent_fingerprint, policy_id, stage_number, status, requester_id, issued_at)
        VALUES ('app-1', 'tenant-alpha', 'mig-1', 'fp-intent-1', 'POL_PROD_CUTOVER', 2, 'PENDING', 'secops-lead', ?)
        """,
        (now_iso,),
    )

    # 3. Insert active incident and active alert (using canonical OPEN state)
    conn.execute(
        """
        INSERT INTO incidents (incident_id, tenant_id, title, severity, status, summary, migration_id, created_at, updated_at)
        VALUES ('inc-1', 'tenant-alpha', 'CDC Lag Spike', 'CRITICAL', 'INVESTIGATING', 'Replication lag exceeded 10s', 'mig-3', ?, ?)
        """,
        (now_iso, now_iso),
    )
    conn.execute(
        """
        INSERT INTO alerts (alert_id, tenant_id, signal_name, dedup_fingerprint, severity, lifecycle_state, message, first_observed_at, last_observed_at, created_at, updated_at)
        VALUES ('alt-1', 'tenant-alpha', 'Disk_Usage_High', 'fp-disk-1', 'WARNING', 'OPEN', 'Disk usage > 85%', ?, ?, ?, ?)
        """,
        (now_iso, now_iso, now_iso, now_iso),
    )

    # 4. Insert lifecycle history and security audit entry via SecurityAuditService (cryptographically verified)
    conn.execute(
        """
        INSERT INTO lifecycle_history (history_id, migration_id, tenant_id, from_state, to_state, actor, reason, details, timestamp)
        VALUES 
        ('hist-1', 'mig-1', 'tenant-alpha', 'INITIALIZED', 'RUNNING', 'test-operator', 'Manual start', '{}', ?),
        ('hist-2', 'mig-2', 'tenant-alpha', 'RUNNING', 'COMPLETED', 'test-operator', 'Bulk complete', '{}', ?)
        """,
        (now_iso, now_iso),
    )
    audit_service = SecurityAuditService(SQLiteSecurityAuditRepository(conn))
    audit_service.record_event(
        tenant_id="tenant-alpha",
        actor_id="test-operator",
        actor_type="HUMAN",
        event_type="SECURITY_POLICY",
        resource_type="MIGRATION",
        resource_id="mig-1",
        action="START_MIGRATION",
        decision=AuditDecision.ALLOW,
    )
    conn.commit()

    # Query estate summary
    summary = query_service.get_estate_summary(actor=actor, conn=conn)

    # 1. Verify counts
    assert summary["runningCount"] == 1
    assert summary["completedTodayCount"] == 1
    assert summary["attentionCount"] == len(summary["attentionItems"])
    assert len(summary["activeMigrations"]) == 3

    # 2. Verify attention items (failed migration, pending approval, incident, alert)
    att_categories = [a["category"] for a in summary["attentionItems"]]
    assert "error" in att_categories
    assert "approval" in att_categories
    assert "capacity" in att_categories

    # 3. Verify pending approvals and real quorum calculation
    assert len(summary["pendingApprovals"]) == 1
    assert summary["pendingApprovals"][0]["id"] == "app-1"
    assert summary["pendingApprovals"][0]["migrationName"] == "Core Finance Bulk"
    assert summary["pendingApprovals"][0]["requester"] == "secops-lead"
    assert summary["pendingApprovals"][0]["quorum"] == "0 of 2"

    # 4. Verify incidents
    assert len(summary["incidents"]) == 1
    assert summary["incidents"][0]["id"] == "inc-1"
    assert summary["incidents"][0]["severity"] == "critical"
    assert summary["incidents"][0]["subject"] == "CDC Lag Spike"

    # 5. Verify recent events stream
    assert len(summary["recentEvents"]) == 2
    event_ids = [e["id"] for e in summary["recentEvents"]]
    assert "hist-1" in event_ids
    assert "hist-2" in event_ids

    # 6. Verify security posture (cryptographically verified hash chain -> sealed/active)
    assert summary["security"]["auditLedgerActive"] is True
    assert summary["security"]["posture"] == "partial"
    assert summary["security"]["detail"] == "Audit Ledger Verified"


def test_estate_summary_tenant_and_workspace_isolation(query_service, uow):
    conn = uow.connection
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Insert Tenant A and Tenant B
    conn.execute("INSERT INTO enterprise_tenants (tenant_id, name, status, created_at, updated_at) VALUES ('tenant-A', 'Tenant A', 'ACTIVE', ?, ?)", (now_iso, now_iso))
    conn.execute("INSERT INTO enterprise_tenants (tenant_id, name, status, created_at, updated_at) VALUES ('tenant-B', 'Tenant B', 'ACTIVE', ?, ?)", (now_iso, now_iso))
    conn.execute("INSERT INTO enterprise_principals (principal_id, tenant_id, principal_type, username, created_at, updated_at) VALUES ('user-A', 'tenant-A', 'HUMAN', 'user-A', ?, ?)", (now_iso, now_iso))
    conn.execute("INSERT INTO enterprise_principals (principal_id, tenant_id, principal_type, username, created_at, updated_at) VALUES ('user-B', 'tenant-B', 'HUMAN', 'user-B', ?, ?)", (now_iso, now_iso))

    # Tenant A records
    conn.execute(
        """
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, configuration, lineage, created_at, updated_at)
        VALUES ('mig-A', 1, 'Tenant A Migration', 'M1_BULK', 'RUNNING', 'tenant-A', 'ws-A', '{}', '[]', ?, ?)
        """,
        (now_iso, now_iso),
    )
    conn.execute("INSERT INTO governance_approvals (approval_id, tenant_id, migration_id, intent_fingerprint, policy_id, stage_number, status, requester_id, issued_at) VALUES ('app-A', 'tenant-A', 'mig-A', 'fp-A', 'POL_A', 1, 'PENDING', 'user-A', ?)", (now_iso,))
    conn.execute("INSERT INTO incidents (incident_id, tenant_id, title, severity, status, summary, migration_id, created_at, updated_at) VALUES ('inc-A', 'tenant-A', 'Incident A', 'WARNING', 'OPEN', 'Summary A', 'mig-A', ?, ?)", (now_iso, now_iso))
    conn.execute("INSERT INTO alerts (alert_id, tenant_id, signal_name, dedup_fingerprint, severity, lifecycle_state, message, first_observed_at, last_observed_at, created_at, updated_at) VALUES ('alt-A', 'tenant-A', 'Signal_A', 'fp-alt-A', 'WARNING', 'OPEN', 'Msg A', ?, ?, ?, ?)", (now_iso, now_iso, now_iso, now_iso))

    audit_service = SecurityAuditService(SQLiteSecurityAuditRepository(conn))
    audit_service.record_event(
        tenant_id="tenant-A",
        actor_id="user-A",
        actor_type="HUMAN",
        event_type="SECURITY_POLICY",
        resource_type="MIGRATION",
        resource_id="mig-A",
        action="START_MIGRATION",
        decision=AuditDecision.ALLOW,
    )

    # Tenant B records
    conn.execute(
        """
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, configuration, lineage, created_at, updated_at)
        VALUES ('mig-B', 1, 'Tenant B Migration', 'M1_BULK', 'RUNNING', 'tenant-B', 'ws-B', '{}', '[]', ?, ?)
        """,
        (now_iso, now_iso),
    )
    conn.execute("INSERT INTO governance_approvals (approval_id, tenant_id, migration_id, intent_fingerprint, policy_id, stage_number, status, requester_id, issued_at) VALUES ('app-B', 'tenant-B', 'mig-B', 'fp-B', 'POL_B', 1, 'PENDING', 'user-B', ?)", (now_iso,))
    conn.execute("INSERT INTO incidents (incident_id, tenant_id, title, severity, status, summary, migration_id, created_at, updated_at) VALUES ('inc-B', 'tenant-B', 'Incident B', 'CRITICAL', 'OPEN', 'Summary B', 'mig-B', ?, ?)", (now_iso, now_iso))
    conn.execute("INSERT INTO alerts (alert_id, tenant_id, signal_name, dedup_fingerprint, severity, lifecycle_state, message, first_observed_at, last_observed_at, created_at, updated_at) VALUES ('alt-B', 'tenant-B', 'Signal_B', 'fp-alt-B', 'CRITICAL', 'OPEN', 'Msg B', ?, ?, ?, ?)", (now_iso, now_iso, now_iso, now_iso))
    conn.commit()

    actor_a = PipelineActorContext(actor_id="actor-a", actor_type="HUMAN", organization_id="tenant-A", workspace_id="ws-A")
    actor_b = PipelineActorContext(actor_id="actor-b", actor_type="HUMAN", organization_id="tenant-B", workspace_id="ws-B")

    summary_a = query_service.get_estate_summary(actor=actor_a, conn=conn)
    summary_b = query_service.get_estate_summary(actor=actor_b, conn=conn)

    # Prove Actor A sees ONLY Tenant A data
    assert summary_a["runningCount"] == 1
    assert [m["id"] for m in summary_a["activeMigrations"]] == ["mig-A"]
    assert [app["id"] for app in summary_a["pendingApprovals"]] == ["app-A"]
    assert [inc["id"] for inc in summary_a["incidents"]] == ["inc-A"]
    assert summary_a["security"]["auditLedgerActive"] is True

    # Prove Actor B sees ONLY Tenant B data (and cannot see Tenant A's audit ledger)
    assert summary_b["runningCount"] == 1
    assert [m["id"] for m in summary_b["activeMigrations"]] == ["mig-B"]
    assert [app["id"] for app in summary_b["pendingApprovals"]] == ["app-B"]
    assert [inc["id"] for inc in summary_b["incidents"]] == ["inc-B"]
    assert summary_b["security"]["auditLedgerActive"] is None
    assert summary_b["security"]["posture"] == "unconfigured"


def test_estate_summary_missing_provider_configuration_remains_null(query_service, actor, uow):
    conn = uow.connection
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, configuration, lineage, created_at, updated_at)
        VALUES ('mig-unconfigured', 1, 'Unconfigured Migration', 'M1_BULK', 'RUNNING', 'tenant-alpha', 'workspace-alpha', '{}', '[]', ?, ?)
        """,
        (now_iso, now_iso),
    )
    conn.commit()

    summary = query_service.get_estate_summary(actor=actor, conn=conn)
    assert len(summary["activeMigrations"]) == 1
    mig = summary["activeMigrations"][0]
    # Prove zero fake fallback to PostgreSQL / Snowflake
    assert mig["sourceEngine"] is None
    assert mig["targetEngine"] is None
    assert mig["sourceEndpoint"] is None
    assert mig["targetEndpoint"] is None


def test_estate_summary_canonical_lifecycle_and_terminal_states(query_service, actor, uow):
    conn = uow.connection
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Alerts: OPEN (visible), ACKNOWLEDGED (visible), REOPENED (visible), RESOLVED (hidden), SUPPRESSED (hidden)
    conn.execute(
        """
        INSERT INTO alerts (alert_id, tenant_id, signal_name, dedup_fingerprint, severity, lifecycle_state, message, first_observed_at, last_observed_at, created_at, updated_at)
        VALUES 
        ('alt-open', 'tenant-alpha', 'Signal_Open', 'fp-1', 'CRITICAL', 'OPEN', 'Open alert', ?, ?, ?, ?),
        ('alt-ack', 'tenant-alpha', 'Signal_Ack', 'fp-2', 'WARNING', 'ACKNOWLEDGED', 'Acked alert', ?, ?, ?, ?),
        ('alt-res', 'tenant-alpha', 'Signal_Res', 'fp-3', 'INFO', 'RESOLVED', 'Resolved alert', ?, ?, ?, ?),
        ('alt-supp', 'tenant-alpha', 'Signal_Supp', 'fp-4', 'LOW', 'SUPPRESSED', 'Suppressed alert', ?, ?, ?, ?)
        """,
        (now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso),
    )

    # Incidents: INVESTIGATING (active), OPEN (active), RESOLVED (terminal hidden), CLOSED (terminal hidden)
    conn.execute(
        """
        INSERT INTO incidents (incident_id, tenant_id, title, severity, status, summary, migration_id, created_at, updated_at)
        VALUES 
        ('inc-active', 'tenant-alpha', 'Active Incident', 'CRITICAL', 'INVESTIGATING', 'Under investigation', NULL, ?, ?),
        ('inc-resolved', 'tenant-alpha', 'Resolved Incident', 'WARNING', 'RESOLVED', 'Resolved', NULL, ?, ?),
        ('inc-closed', 'tenant-alpha', 'Closed Incident', 'LOW', 'CLOSED', 'Closed', NULL, ?, ?)
        """,
        (now_iso, now_iso, now_iso, now_iso, now_iso, now_iso),
    )
    conn.commit()

    summary = query_service.get_estate_summary(actor=actor, conn=conn)

    # Active incidents list must contain only 'inc-active' (neither RESOLVED nor CLOSED)
    inc_ids = [i["id"] for i in summary["incidents"]]
    assert inc_ids == ["inc-active"]

    # Attention items must contain OPEN and ACKNOWLEDGED alerts, not RESOLVED or SUPPRESSED
    alt_att_ids = [a["id"] for a in summary["attentionItems"] if a["id"].startswith("att-alt-")]
    assert "att-alt-alt-open" in alt_att_ids
    assert "att-alt-alt-ack" in alt_att_ids
    assert "att-alt-alt-res" not in alt_att_ids
    assert "att-alt-alt-supp" not in alt_att_ids


def test_estate_summary_disconnected_failure_semantics(query_service, actor):
    # Proves conn=None returns truthful unavailable state (None counts, not fake 0)
    summary = query_service.get_estate_summary(actor=actor, conn=None)
    assert summary["runningCount"] is None
    assert summary["scheduledCount"] is None
    assert summary["attentionCount"] is None
    assert summary["completedTodayCount"] is None
    assert summary["activeMigrations"] is None
    assert summary["attentionItems"] is None
    assert summary["pendingApprovals"] is None
    assert summary["incidents"] is None
    assert summary["recentEvents"] is None
    assert summary["security"]["auditLedgerActive"] is None
    db_sub = next(s for s in summary["subsystems"] if s["name"] == "Database Authority")
    assert db_sub["status"] == "unavailable"
    assert db_sub["metric"] == "Disconnected"


def test_estate_summary_completed_today_boundary_filter(query_service, actor, uow):
    conn = uow.connection
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today_iso = now_utc.isoformat()
    yesterday_iso = (now_utc - datetime.timedelta(days=1)).isoformat()

    conn.execute(
        """
        INSERT INTO lifecycle_history (history_id, migration_id, tenant_id, from_state, to_state, actor, reason, details, timestamp)
        VALUES 
        ('hist-today', 'mig-today', 'tenant-alpha', 'RUNNING', 'COMPLETED', 'test-operator', 'Today finish', '{}', ?),
        ('hist-yesterday', 'mig-old', 'tenant-alpha', 'RUNNING', 'COMPLETED', 'test-operator', 'Yesterday finish', '{}', ?)
        """,
        (today_iso, yesterday_iso),
    )
    conn.commit()

    summary = query_service.get_estate_summary(actor=actor, conn=conn)
    # Only the migration completed today is counted in completedTodayCount
    assert summary["completedTodayCount"] == 1


def test_estate_summary_partial_query_failure_semantics(query_service, actor, uow):
    # Proves that when one optional table is dropped/corrupted, the dashboard does not crash
    # and returns None for that specific surface while preserving other working surfaces.
    conn = uow.connection
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, configuration, lineage, created_at, updated_at)
        VALUES ('mig-ok', 1, 'Working Migration', 'M1_BULK', 'RUNNING', 'tenant-alpha', 'workspace-alpha', '{}', '[]', ?, ?)
        """,
        (now_iso, now_iso),
    )
    # Drop governance_approvals table to simulate surface query failure
    conn.execute("DROP TABLE governance_approvals")
    conn.commit()

    summary = query_service.get_estate_summary(actor=actor, conn=conn)

    # Working surface still succeeds
    assert summary["runningCount"] == 1
    assert len(summary["activeMigrations"]) == 1

    # Failed surface returns None (truthful unavailable state, NOT silent empty list)
    assert summary["pendingApprovals"] is None


def test_estate_summary_via_unified_caller(uow):
    from akaalIPC.protocol.envelopes import QueryEnvelope
    from akaalIPC.protocol.schemas import RequestKind
    from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
    from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
    from akaalIPC.transport.ports import CallerResultStatus

    caller = PipelineUnifiedCaller(shared_uow=uow, bind_gateway=False)

    actor_ctx = ActorContext(
        actor=ActorReference(actor_id="test-operator", actor_type="HUMAN"),
        organization_id="default-tenant",
        roles=["OPERATOR"],
    )
    corr_ctx = CorrelationContext(request_id="req-1", correlation_id="corr-1")

    envelope = QueryEnvelope(
        request_id="req-1",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="estate.get_summary",
        kind=RequestKind.QUERY,
        actor=actor_ctx,
        correlation=corr_ctx,
        payload={},
    )

    result = caller.handle_query(envelope)
    assert result.status == CallerResultStatus.OK
    assert isinstance(result.result, dict)
    assert "runningCount" in result.result
    assert "activeMigrations" in result.result
    assert "subsystems" in result.result
    assert "capacityMetrics" in result.result
    assert "fleet" in result.result
    assert "security" in result.result

