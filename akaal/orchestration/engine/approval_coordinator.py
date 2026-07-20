"""
ApprovalCoordinator module.
Manages workflow approval requests, pending pauses, and approval resolution.
"""

from typing import Dict, Any, List, Optional
import uuid

from akaal.orchestration.domain.identifiers import WorkflowId
from akaal.orchestration.repository.interfaces import WorkflowRepository
from akaal.orchestration.events.events import EventPublisher, ApprovalRequested


class ApprovalCoordinator:
    """
    Coordinates human / system approval requests and resolution.
    """

    def __init__(self, repository: WorkflowRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    def request_approval(
        self,
        workflow_id: WorkflowId,
        step_name: str,
        required_roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create and record an approval request."""
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        info = {
            "approval_id": approval_id,
            "workflow_id": str(workflow_id),
            "step_name": step_name,
            "required_roles": required_roles or ["ADMIN"],
            "status": "PENDING",
            "metadata": metadata or {},
        }
        self._repository.save_pending_approval(workflow_id, info)

        w_id = str(workflow_id)
        self._publisher.publish(
            ApprovalRequested(
                aggregate_id=w_id,
                workflow_id=w_id,
                approval_id=approval_id,
                step_name=step_name,
                required_roles=required_roles or ["ADMIN"],
            )
        )

        return approval_id

    def resolve_approval(self, workflow_id: WorkflowId, approval_id: str, approved: bool) -> None:
        """Resolve a pending approval request."""
        pending = self._repository.get_pending_approvals(workflow_id)
        for app in pending:
            if app.get("approval_id") == approval_id:
                if approved:
                    self._repository.remove_pending_approval(workflow_id, approval_id)
                    return
                else:
                    app["status"] = "REJECTED"
                    return
        raise KeyError(f"Pending approval '{approval_id}' not found for workflow '{workflow_id}'.")
