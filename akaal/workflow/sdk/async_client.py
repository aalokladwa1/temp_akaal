"""Asynchronous AKAAL Python SDK Client Library."""

from typing import Any, Dict
from akaal.workflow.api.server import ApiGatewayServer


class AsyncAkaalClient:
    """Non-blocking asyncio Client SDK for high-performance applications."""

    def __init__(self, gateway_server: ApiGatewayServer | None = None) -> None:
        self.gateway = gateway_server or ApiGatewayServer()

    async def submit_workflow(self, workflow_id: str) -> Dict[str, Any]:
        return self.gateway.handle_submit_workflow({"workflow_id": workflow_id})

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        return self.gateway.handle_get_status(workflow_id)
