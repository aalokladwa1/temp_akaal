"""
Enterprise Approval Manager.
Enforces authorization approval workflows for sensitive operational actions.
"""

from typing import Dict, List, Optional, Any
from threading import RLock
import time


class ApprovalRequest:
    def __init__(self, request_id: str, action_name: str, requester: str, required_approvers: int = 1, timeout_seconds: float = 3600.0) -> None:
        self.request_id = request_id
        self.action_name = action_name
        self.requester = requester
        self.required_approvers = required_approvers
        self.timeout_seconds = timeout_seconds
        self.created_at = time.time()
        self.approvals: List[str] = []
        self.status = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, OVERRIDDEN


class ApprovalManager:
    """Manages multi-approver workflows and emergency overrides."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._requests: Dict[str, ApprovalRequest] = {}

    def create_request(self, action_name: str, requester: str, required_approvers: int = 1) -> ApprovalRequest:
        with self._lock:
            req_id = f"appr_{time.time_ns()}_{len(self._requests)}"
            req = ApprovalRequest(req_id, action_name, requester, required_approvers)
            self._requests[req_id] = req
            return req

    def approve(self, request_id: str, approver_id: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if not req or req.status != "PENDING":
                return False
            
            # Check timeout
            if time.time() - req.created_at > req.timeout_seconds:
                req.status = "EXPIRED"
                return False

            if approver_id not in req.approvals:
                req.approvals.append(approver_id)

            if len(req.approvals) >= req.required_approvers:
                req.status = "APPROVED"

            return True

    def emergency_override(self, request_id: str, admin_id: str, justification: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return False
            req.status = "OVERRIDDEN"
            req.approvals.append(f"OVERRIDE:{admin_id}")
            return True

    def is_approved(self, request_id: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return False
            return req.status in ["APPROVED", "OVERRIDDEN"]
