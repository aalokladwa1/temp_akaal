"""Enterprise 3-Gate Human Approval Engine."""

import threading
from typing import Dict, List, Optional
from akaal.audit.audit_logger import AuditLogger, AuditEventType
from akaal.workflow.approval.models import (
    ApprovalDecision,
    ApprovalDelegation,
    ApprovalPrincipal,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalToken,
)
from akaal.workflow.events.dispatcher import IEventDispatcher
from akaal.workflow.events.events import WorkflowEvent
from akaal.workflow.exceptions import WorkflowException
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.id_generator import IIdGenerator, UUIDIdGenerator


class ApprovalEngine:
    """Thread-safe human approval engine managing ordered approval gates (Gates 1, 2, 3)."""

    def __init__(
        self,
        event_dispatcher: Optional[IEventDispatcher] = None,
        clock: Optional[IClock] = None,
        id_generator: Optional[IIdGenerator] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self._event_dispatcher = event_dispatcher
        self._clock = clock or SystemClock()
        self._id_generator = id_generator or UUIDIdGenerator()
        self._audit_logger = audit_logger or AuditLogger()
        self._requests: Dict[str, ApprovalRequest] = {}
        self._tokens: Dict[str, ApprovalToken] = {}  # key: f"{workflow_id}:gate_{gate_number}"
        self._decisions: List[ApprovalDecision] = []
        self._delegations: List[ApprovalDelegation] = []
        self._lock = threading.Lock()

    def request_approval(
        self,
        workflow_id: str,
        gate_number: int,
        gate_name: str,
        assigned_principal: ApprovalPrincipal,
        timeout_seconds: float = 3600.0,
    ) -> ApprovalRequest:
        """Create a new approval request for an ordered gate (1, 2, or 3)."""
        with self._lock:
            # Enforce gate ordering: Gate N requires Gate N-1 token approved if N > 1
            if gate_number > 1:
                prev_key = f"{workflow_id}:gate_{gate_number - 1}"
                prev_token = self._tokens.get(prev_key)
                if not prev_token or prev_token.status != ApprovalStatus.APPROVED:
                    raise WorkflowException(
                        f"Cannot request Approval #{gate_number} before Approval #{gate_number - 1} is approved."
                    )

            request_id = self._id_generator.generate_uuid()
            req = ApprovalRequest(
                request_id=request_id,
                workflow_id=workflow_id,
                gate_number=gate_number,
                gate_name=gate_name,
                assigned_principal=assigned_principal,
                timeout_seconds=timeout_seconds,
                status=ApprovalStatus.PENDING,
                requested_at=self._clock.now_utc(),
            )
            self._requests[request_id] = req

            # Audit & Event dispatch
            self._audit_logger.log(
                event_type=AuditEventType.APPROVAL_REQUESTED,
                actor="APPROVAL_ENGINE",
                description=f"Approval #{gate_number} ({gate_name}) requested",
                project_id=workflow_id,
                details={
                    "request_id": request_id,
                    "gate_number": gate_number,
                    "gate_name": gate_name,
                    "assigned_principal": assigned_principal.to_dict(),
                },
            )
            if self._event_dispatcher:
                self._event_dispatcher.dispatch(
                    WorkflowEvent(
                        event_id=self._id_generator.generate_uuid(),
                        event_type="APPROVAL_REQUESTED",
                        workflow_id=workflow_id,
                        timestamp=self._clock.now_utc(),
                        payload=req.to_dict(),
                    )
                )
            return req

    def approve(
        self,
        request_id: str,
        acting_principal: ApprovalPrincipal,
        reason: str = "Approved by principal",
    ) -> ApprovalToken:
        """Approve a pending approval request and generate an immutable token."""
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                raise WorkflowException(f"Approval request '{request_id}' not found.")
            if req.status != ApprovalStatus.PENDING and req.status != ApprovalStatus.DELEGATED:
                raise WorkflowException(
                    f"Cannot approve request '{request_id}' with status '{req.status.value}'."
                )

            token_id = self._id_generator.generate_uuid()
            decision_id = self._id_generator.generate_uuid()

            decision = ApprovalDecision(
                decision_id=decision_id,
                request_id=request_id,
                acting_principal=acting_principal,
                status=ApprovalStatus.APPROVED,
                reason=reason,
                decided_at=self._clock.now_utc(),
            )
            self._decisions.append(decision)

            token = ApprovalToken(
                token_id=token_id,
                request_id=request_id,
                workflow_id=req.workflow_id,
                gate_number=req.gate_number,
                approved_by=acting_principal,
                status=ApprovalStatus.APPROVED,
                decided_at=self._clock.now_utc(),
            )
            token_key = f"{req.workflow_id}:gate_{req.gate_number}"
            self._tokens[token_key] = token

            # Update request status
            updated_req = ApprovalRequest(
                request_id=req.request_id,
                workflow_id=req.workflow_id,
                gate_number=req.gate_number,
                gate_name=req.gate_name,
                assigned_principal=req.assigned_principal,
                timeout_seconds=req.timeout_seconds,
                status=ApprovalStatus.APPROVED,
                requested_at=req.requested_at,
            )
            self._requests[request_id] = updated_req

            # Audit & Event dispatch
            self._audit_logger.log(
                event_type=AuditEventType.APPROVAL_GRANTED,
                actor=acting_principal.principal_id,
                description=f"Approval #{req.gate_number} ({req.gate_name}) granted",
                project_id=req.workflow_id,
                details={
                    "request_id": request_id,
                    "token_id": token_id,
                    "gate_number": req.gate_number,
                    "acting_principal": acting_principal.to_dict(),
                    "reason": reason,
                },
            )
            if self._event_dispatcher:
                self._event_dispatcher.dispatch(
                    WorkflowEvent(
                        event_id=self._id_generator.generate_uuid(),
                        event_type="APPROVAL_GRANTED",
                        workflow_id=req.workflow_id,
                        timestamp=self._clock.now_utc(),
                        payload=token.to_dict(),
                    )
                )
            return token

    def reject(
        self,
        request_id: str,
        acting_principal: ApprovalPrincipal,
        reason: str = "Rejected by principal",
    ) -> ApprovalDecision:
        """Reject a pending approval request, stopping workflow progression."""
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                raise WorkflowException(f"Approval request '{request_id}' not found.")
            if req.status != ApprovalStatus.PENDING and req.status != ApprovalStatus.DELEGATED:
                raise WorkflowException(
                    f"Cannot reject request '{request_id}' with status '{req.status.value}'."
                )

            decision_id = self._id_generator.generate_uuid()
            decision = ApprovalDecision(
                decision_id=decision_id,
                request_id=request_id,
                acting_principal=acting_principal,
                status=ApprovalStatus.REJECTED,
                reason=reason,
                decided_at=self._clock.now_utc(),
            )
            self._decisions.append(decision)

            updated_req = ApprovalRequest(
                request_id=req.request_id,
                workflow_id=req.workflow_id,
                gate_number=req.gate_number,
                gate_name=req.gate_name,
                assigned_principal=req.assigned_principal,
                timeout_seconds=req.timeout_seconds,
                status=ApprovalStatus.REJECTED,
                requested_at=req.requested_at,
            )
            self._requests[request_id] = updated_req

            self._audit_logger.log(
                event_type=AuditEventType.APPROVAL_REJECTED,
                actor=acting_principal.principal_id,
                description=f"Approval #{req.gate_number} ({req.gate_name}) rejected",
                project_id=req.workflow_id,
                details={
                    "request_id": request_id,
                    "gate_number": req.gate_number,
                    "acting_principal": acting_principal.to_dict(),
                    "reason": reason,
                },
            )
            if self._event_dispatcher:
                self._event_dispatcher.dispatch(
                    WorkflowEvent(
                        event_id=self._id_generator.generate_uuid(),
                        event_type="APPROVAL_REJECTED",
                        workflow_id=req.workflow_id,
                        timestamp=self._clock.now_utc(),
                        payload=decision.to_dict(),
                    )
                )
            return decision

    def delegate(
        self,
        request_id: str,
        from_principal: ApprovalPrincipal,
        to_principal: ApprovalPrincipal,
        delegated_by: str,
        reason: str = "Delegated authority",
    ) -> ApprovalDelegation:
        """Delegate approval authority for a pending request."""
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                raise WorkflowException(f"Approval request '{request_id}' not found.")
            if req.status != ApprovalStatus.PENDING:
                raise WorkflowException(f"Cannot delegate request '{request_id}' with status '{req.status.value}'.")

            delegation_id = self._id_generator.generate_uuid()
            delegation = ApprovalDelegation(
                delegation_id=delegation_id,
                request_id=request_id,
                from_principal=from_principal,
                to_principal=to_principal,
                delegated_by=delegated_by,
                reason=reason,
                delegated_at=self._clock.now_utc(),
            )
            self._delegations.append(delegation)

            updated_req = ApprovalRequest(
                request_id=req.request_id,
                workflow_id=req.workflow_id,
                gate_number=req.gate_number,
                gate_name=req.gate_name,
                assigned_principal=to_principal,
                timeout_seconds=req.timeout_seconds,
                status=ApprovalStatus.DELEGATED,
                requested_at=req.requested_at,
            )
            self._requests[request_id] = updated_req
            return delegation

    def handle_timeout(self, request_id: str) -> ApprovalRequest:
        """Handle timeout on an unresolved approval request."""
        with self._lock:
            req = self._requests.get(request_id)
            if not req or req.status not in (ApprovalStatus.PENDING, ApprovalStatus.DELEGATED):
                return req

            updated_req = ApprovalRequest(
                request_id=req.request_id,
                workflow_id=req.workflow_id,
                gate_number=req.gate_number,
                gate_name=req.gate_name,
                assigned_principal=req.assigned_principal,
                timeout_seconds=req.timeout_seconds,
                status=ApprovalStatus.EXPIRED,
                requested_at=req.requested_at,
            )
            self._requests[request_id] = updated_req

            if self._event_dispatcher:
                self._event_dispatcher.dispatch(
                    WorkflowEvent(
                        event_id=self._id_generator.generate_uuid(),
                        event_type="APPROVAL_EXPIRED",
                        workflow_id=req.workflow_id,
                        timestamp=self._clock.now_utc(),
                        payload=updated_req.to_dict(),
                    )
                )
            return updated_req

    def get_token(self, workflow_id: str, gate_number: int) -> Optional[ApprovalToken]:
        with self._lock:
            return self._tokens.get(f"{workflow_id}:gate_{gate_number}")

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self._requests.get(request_id)
