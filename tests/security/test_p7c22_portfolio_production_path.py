"""tests/security/test_p7c22_portfolio_production_path.py
===============================================================
P7C.22 production-path proof: real PipelineUnifiedCaller -> intelligence.
submit (task=QUERY, capability=portfolio_intelligence). Proves a tenant only
ever sees its OWN migrations aggregated -- never another tenant's, even when
both exist in the same database -- because the canonical listing is
tenant-scoped at the SQL level before any per-migration read runs.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _actor(org_id: str) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _seed_migration(caller, migration_id, tenant_id):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id, revision=1, name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK, state=MigrationLifecycleState.DRAFT,
        tenant_id=tenant_id, workspace_id="ws-main", project_id="proj-1",
    )
    caller.repository.save(agg)


def _submit_portfolio(caller, actor, limit=None, cursor=None):
    params = {}
    if limit is not None:
        params["limit"] = limit
    if cursor is not None:
        params["cursor"] = cursor
    payload = {
        "task": "QUERY", "subject_type": "tenant", "subject_id": actor.organization_id,
        "subject_version": "v1", "capability": "portfolio_intelligence", "parameters": params,
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestTenantScopedPortfolio:
    def test_only_own_tenants_migrations_appear(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-a1", "tenant-alpha")
            _seed_migration(caller, "mig-a2", "tenant-alpha")
            _seed_migration(caller, "mig-b1", "tenant-beta")

            actor_a = _actor("tenant-alpha")
            result = _submit_portfolio(caller, actor_a)
            assert result.status == CallerResultStatus.OK
            migration_ids = {m["migration_id"] for m in result.result["result"]["data"]["migrations"]}
            assert migration_ids == {"mig-a1", "mig-a2"}
            assert "mig-b1" not in migration_ids
        finally:
            caller.close()

    def test_empty_portfolio_is_not_an_error(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-empty")
            result = _submit_portfolio(caller, actor)
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["migrations"] == []
        finally:
            caller.close()


class TestGenuinePaginationContinuation:
    """Owner-review Blocker 13 closure: a portfolio larger than one page is
    traversable via real cursor continuation through the production seam --
    never silently capped at page one."""

    def test_traverse_full_portfolio_across_multiple_pages_no_loss_no_duplication(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            expected_ids = set()
            for i in range(23):
                migration_id = f"mig-{i:03d}"
                _seed_migration(caller, migration_id, "tenant-alpha")
                expected_ids.add(migration_id)

            seen_ids = set()
            cursor = None
            page_count = 0
            while True:
                result = _submit_portfolio(caller, actor, limit=10, cursor=cursor)
                assert result.status == CallerResultStatus.OK
                page_count += 1
                page_ids = [m["migration_id"] for m in result.result["result"]["data"]["migrations"]]
                assert not (seen_ids & set(page_ids)), "pagination duplicated a migration across pages"
                seen_ids.update(page_ids)
                cursor = result.result["result"]["data"]["next_cursor"]
                if cursor is None:
                    break
                assert page_count < 10, "pagination did not terminate"

            assert seen_ids == expected_ids
            assert page_count == 3  # 23 migrations at 10/page -> 3 pages

        finally:
            caller.close()

    def test_cursor_cannot_cross_tenant_boundary(self, temp_db_path):
        """A cursor computed for tenant-alpha's listing, replayed by
        tenant-beta, still only ever returns tenant-beta's own rows -- the
        WHERE tenant_id=... clause applies to every page regardless of the
        offset encoded in the cursor."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            for i in range(5):
                _seed_migration(caller, f"mig-a-{i}", "tenant-alpha")
            _seed_migration(caller, "mig-b-0", "tenant-beta")

            actor_a = _actor("tenant-alpha")
            page1 = _submit_portfolio(caller, actor_a, limit=2)
            cursor = page1.result["result"]["data"]["next_cursor"]
            assert cursor is not None

            actor_b = _actor("tenant-beta")
            replayed = _submit_portfolio(caller, actor_b, limit=2, cursor=cursor)
            assert replayed.status == CallerResultStatus.OK
            migration_ids = {m["migration_id"] for m in replayed.result["result"]["data"]["migrations"]}
            assert migration_ids <= {"mig-b-0"}
        finally:
            caller.close()
