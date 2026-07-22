"""
Operations Control Plane.
Delegates operational control actions directly to target platform public facades.
"""

from typing import Dict, Any, Optional
from threading import RLock

from akaal.operations.security.rbac import SecurityEngine, Role
from akaal.operations.policy.engine import OperationsPolicyEngine
from akaal.operations.governance.audit import GovernanceAuditCenter
from akaal.operations.session.manager import OperationsSessionManager


class OperationsControlPlane:
    """Secure operational control facade delegating commands to public platform contracts."""

    def __init__(
        self,
        security_engine: SecurityEngine,
        policy_engine: OperationsPolicyEngine,
        audit_center: GovernanceAuditCenter,
        session_manager: OperationsSessionManager
    ) -> None:
        self._lock = RLock()
        self.security_engine = security_engine
        self.policy_engine = policy_engine
        self.audit_center = audit_center
        self.session_manager = session_manager

    def pause_job(self, job_id: str, operator_id: str, workflow_engine=None, signature: str = "") -> bool:
        """Delegates pause_job command to Platform 1 Workflow Engine facade."""
        with self._lock:
            if not self.security_engine.is_authorized(operator_id, "control"):
                raise PermissionError(f"User '{operator_id}' not authorized to pause jobs.")

            # Record audit
            self.audit_center.record_action(operator_id, "PAUSE_JOB", {"job_id": job_id})

            # Delegate to public facade if provided
            if workflow_engine and hasattr(workflow_engine, "pause_job"):
                return workflow_engine.pause_job(job_id)
            return True

    def drain_worker(self, worker_id: str, operator_id: str, distributed_runtime=None) -> bool:
        """Delegates drain_worker command to Platform 2 Distributed Runtime facade."""
        with self._lock:
            if not self.security_engine.is_authorized(operator_id, "drain"):
                raise PermissionError(f"User '{operator_id}' not authorized to drain workers.")

            self.audit_center.record_action(operator_id, "DRAIN_WORKER", {"worker_id": worker_id})

            if distributed_runtime and hasattr(distributed_runtime, "drain_worker"):
                return distributed_runtime.drain_worker(worker_id)
            return True

    def emergency_stop(self, operator_id: str, distributed_runtime=None) -> bool:
        """Executes emergency stop across the cluster via public facades."""
        with self._lock:
            if not self.security_engine.is_authorized(operator_id, "emergency_stop"):
                raise PermissionError(f"User '{operator_id}' not authorized to execute emergency stop.")

            self.audit_center.record_action(operator_id, "EMERGENCY_STOP", {})

            if distributed_runtime and hasattr(distributed_runtime, "emergency_stop"):
                distributed_runtime.emergency_stop()
            return True
