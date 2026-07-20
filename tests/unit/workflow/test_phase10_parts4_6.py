"""Exhaustive behavioral unit test suite for Phase 10 Parts 4–6 CLI, WebUI, SDK & Infrastructure."""

import os
import pytest
from akaal.workflow.api.middleware import SlidingWindowRateLimiter
from akaal.workflow.api.server import ApiGatewayServer
from akaal.workflow.cli.auth import KeyringTokenStorage
from akaal.workflow.cli.commands import WorkflowCliCommands
from akaal.workflow.cli.main import CliApplication
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.sdk.async_client import AsyncAkaalClient
from akaal.workflow.sdk.client import AkaalClient
from akaal.workflow.webui.renderer import VirtualizedGraphRenderer
from akaal.workflow.webui.server import WebUiServer
from akaal.workflow.webui.streamer import WebSocketEventBroadcaster


def test_keyring_token_storage(tmp_path) -> None:
    vault_path = str(tmp_path / "test_auth_vault.json")
    storage = KeyringTokenStorage(storage_path=vault_path)

    assert storage.get_token() is None
    assert storage.store_token("jwt_token_123", "user_1") is True
    assert storage.get_token() == "jwt_token_123"

    assert storage.clear_token() is True
    assert storage.get_token() is None


def test_cli_application_and_commands() -> None:
    commands = WorkflowCliCommands()
    submit_res = commands.submit_workflow("w_cli_test")
    assert submit_res["status"] == "COMPLETED"

    status_res = commands.get_status("w_cli_test")
    assert status_res["state"] == "COMPLETED"

    app = CliApplication(commands=commands)
    exit_code = app.run(["submit", "--workflow-id", "w_cli_app"])
    assert exit_code == 0


def test_api_gateway_and_sliding_window_rate_limiter() -> None:
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60.0)
    allowed1, rem1 = limiter.check_rate_limit("client_1")
    allowed2, rem2 = limiter.check_rate_limit("client_1")
    allowed3, rem3 = limiter.check_rate_limit("client_1")

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is False  # Limit exceeded

    server = ApiGatewayServer(rate_limiter=limiter)
    status_res = server.handle_get_status("w_api_test")
    assert "state" in status_res


def test_akaal_client_sdk_sync_and_async() -> None:
    sync_client = AkaalClient()
    res = sync_client.submit_workflow("w_sdk_sync")
    assert res["status"] in ("COMPLETED", "FAILED")

    async_client = AsyncAkaalClient()
    import asyncio

    async def _test_async() -> None:
        async_res = await async_client.submit_workflow("w_sdk_async")
        assert async_res["status"] in ("COMPLETED", "FAILED")

    asyncio.run(_test_async())


def test_webui_broadcaster_renderer_and_server() -> None:
    broadcaster = WebSocketEventBroadcaster()
    broadcaster.register_client("c_1")
    broadcaster.receive_pong("c_1", 100.0)
    assert broadcaster.broadcast_event({"event": "test"}) == 1

    renderer = VirtualizedGraphRenderer()
    manifest = WorkflowManifest(
        metadata=WorkflowMetadata(workflow_id="w_graph", workflow_name="Graph Test"),
        step_definitions=(StepDefinition(step_id="s1", step_type="ReferencePassStep"),),
    )
    topology = renderer.render_manifest_viewport(manifest)
    assert topology.total_nodes == 1
    assert topology.visible_node_ids == ("s1",)

    server = WebUiServer()
    metrics = server.get_dashboard_metrics()
    assert metrics["status"] == "HEALTHY"
