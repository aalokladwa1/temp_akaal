"""Synchronous AKAAL Python SDK Client Library."""

from typing import Any, Dict
from akaal.workflow.api.server import ApiGatewayServer


class AkaalClient:
    """Synchronous Client SDK for application integration."""

    def __init__(self, gateway_server: ApiGatewayServer | None = None) -> None:
        self.gateway = gateway_server or ApiGatewayServer()

    def submit_workflow(self, workflow_id: str) -> Dict[str, Any]:
        return self.gateway.handle_submit_workflow({"workflow_id": workflow_id})

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        return self.gateway.handle_get_status(workflow_id)
