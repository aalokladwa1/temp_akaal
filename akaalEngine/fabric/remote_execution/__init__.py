"""akaalEngine.fabric.remote_execution -- P7B.9 Hybrid Relay / Remote Execution."""

from akaalEngine.fabric.remote_execution.models import (
    AssignmentSigner,
    AssignmentVerifier,
    ForgedAssignmentError,
    HMACAssignmentSigner,
    HMACAssignmentVerifier,
    RemoteExecutionAssignment,
    RemoteExecutionError,
    StaleAssignmentError,
    WrongPlanError,
    WrongSealError,
    WrongSiteError,
    WrongTenantError,
    sign_payload,
    verify_assignment,
    verify_assignment_with_verifier,
)
from akaalEngine.fabric.remote_execution.control_plane import RemoteExecutionControlPlane
from akaalEngine.fabric.remote_execution.execution import (
    FencingTokenFromAssignment,
    execute_assignment_via_transport,
)
from akaalEngine.fabric.evidence import emit_fabric_execution_evidence

__all__ = [
    "FencingTokenFromAssignment",
    "execute_assignment_via_transport",
    "emit_fabric_execution_evidence",
    "AssignmentSigner",
    "AssignmentVerifier",
    "ForgedAssignmentError",
    "HMACAssignmentSigner",
    "HMACAssignmentVerifier",
    "RemoteExecutionAssignment",
    "RemoteExecutionError",
    "StaleAssignmentError",
    "WrongPlanError",
    "WrongSealError",
    "WrongSiteError",
    "WrongTenantError",
    "sign_payload",
    "verify_assignment",
    "verify_assignment_with_verifier",
    "RemoteExecutionControlPlane",
]
