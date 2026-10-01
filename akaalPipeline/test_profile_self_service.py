"""
test_profile_self_service.py
=============================
Focused backend integration test verifying self-service profile, email, avatar, and password persistence & authorization boundaries.
"""

import os
import tempfile
import sqlite3
from typing import Mapping, Any
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.application.command_handlers import CommandHandlerRegistry
from akaalPipeline.application.query_service import PipelineQueryService
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.execution.controller import PipelineExecutionController
from akaalPipeline.operations.service import OperationService
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.contracts.errors import PipelineError


def setup_test_uow():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    uow = SQLiteUnitOfWork(db_path=db_path)

    # Initialize schema and seed tenant
    with uow:
        uow.connection.execute(
            "INSERT OR IGNORE INTO enterprise_tenants (tenant_id, name, status, created_at, updated_at) VALUES ('tenant-test', 'Test Tenant', 'ACTIVE', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )

    repo = SQLiteMigrationRepository(db_path=db_path)
    op_svc = OperationService()
    idemp_svc = IdempotencyService()
    exec_ctrl = PipelineExecutionController(None, None, None, op_svc)

    cmd_handlers = CommandHandlerRegistry(repo, op_svc, idemp_svc, exec_ctrl)
    query_svc = PipelineQueryService(repo, op_svc)

    return uow, cmd_handlers, query_svc


def test_self_service_profile_update_and_persistence():
    uow, cmd_handlers, query_svc = setup_test_uow()
    actor = PipelineActorContext(actor_id="usr-aalok-01", actor_type="HUMAN", organization_id="tenant-test")

    with uow:
        # Seed test principal
        uow.principals.create("tenant-test", "usr-aalok-01", "HUMAN", "aalok", display_name="Aalok Initial", email="aalok.old@akaal.io")

    # Update display_name & email via self-service handler
    with uow:
        res = cmd_handlers.handle_account_profile_update(
            {"display_name": "Aalok Ladwa Updated", "email": "aalok.new@akaal.io"},
            actor,
            uow,
        )
        assert res["display_name"] == "Aalok Ladwa Updated"
        assert res["email"] == "aalok.new@akaal.io"

    # Query current account from DB
    with uow:
        acc = query_svc.get_current_account(actor=actor, conn=uow.connection)
        assert acc["name"] == "Aalok Ladwa Updated"
        assert acc["email"] == "aalok.new@akaal.io"


def test_self_service_avatar_update_and_removal():
    uow, cmd_handlers, query_svc = setup_test_uow()
    actor = PipelineActorContext(actor_id="usr-aalok-01", actor_type="HUMAN", organization_id="tenant-test")

    with uow:
        uow.principals.create("tenant-test", "usr-aalok-01", "HUMAN", "aalok", display_name="Aalok Avatar Test")

    # Upload avatar Data URL
    fake_avatar = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    with uow:
        res = cmd_handlers.handle_account_avatar_update({"avatar": fake_avatar}, actor, uow)
        assert res["avatar"] == fake_avatar

    # Verify query returns persisted avatar
    with uow:
        acc = query_svc.get_current_account(actor=actor, conn=uow.connection)
        assert acc["avatar"] == fake_avatar

    # Remove avatar
    with uow:
        res = cmd_handlers.handle_account_avatar_remove({}, actor, uow)
        assert res["avatar"] is None

    # Verify query returns null avatar
    with uow:
        acc = query_svc.get_current_account(actor=actor, conn=uow.connection)
        assert acc["avatar"] is None


def test_self_service_password_verification_and_change():
    uow, cmd_handlers, _ = setup_test_uow()
    actor = PipelineActorContext(actor_id="usr-aalok-01", actor_type="HUMAN", organization_id="tenant-test")

    with uow:
        uow.principals.create("tenant-test", "usr-aalok-01", "HUMAN", "aalok", display_name="Aalok Pass Test")
        from akaalPipeline.identity.principals import PrincipalManager
        from akaalPipeline.state.repositories import SQLiteCredentialRepository
        mgr = PrincipalManager(uow.principals, SQLiteCredentialRepository(uow.connection))
        mgr.set_password("tenant-test", "usr-aalok-01", "OldSecretPassword123")

    # Incorrect current password fails closed
    try:
        with uow:
            cmd_handlers.handle_account_password_change(
                {"current_password": "WrongPassword123", "new_password": "NewSecretPassword123"},
                actor,
                uow,
            )
        assert False, "Should have raised PipelineError for incorrect current password"
    except PipelineError as err:
        assert "incorrect" in str(err).lower()

    # Correct current password updates credentials
    with uow:
        res = cmd_handlers.handle_account_password_change(
            {"current_password": "OldSecretPassword123", "new_password": "NewSecretPassword123"},
            actor,
            uow,
        )
        assert res["status"] == "SUCCESS"


if __name__ == "__main__":
    test_self_service_profile_update_and_persistence()
    test_self_service_avatar_update_and_removal()
    test_self_service_password_verification_and_change()
    print("ALL BACKEND SELF-SERVICE TESTS PASSED SUCCESSFULLY!")
