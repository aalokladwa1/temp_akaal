"""
AKAAL Platform 6 — Human Verification Checkpoint Manager.
"""

from typing import Dict, Optional
import datetime
import uuid

from akaal.governance.domain.models import HumanCheckpoint
from akaal.governance.domain.enums import ApprovalStatus


class HumanCheckpointManager:
    """Manages human verification sign-offs and operational checkpoints."""

    def __init__(self) -> None:
        self._checkpoints: Dict[str, HumanCheckpoint] = {}

    def create_checkpoint(self, workflow_id: str, verification_type: str) -> HumanCheckpoint:
        cp_id = f"chk-{uuid.uuid4().hex[:8]}"
        cp = HumanCheckpoint(
            checkpoint_id=cp_id,
            workflow_id=workflow_id,
            verification_type=verification_type,
            verifier_id=None,
            status=ApprovalStatus.PENDING,
            signed_off_at=None,
        )
        self._checkpoints[cp_id] = cp
        return cp

    def sign_off(self, checkpoint_id: str, verifier_id: str, approved: bool) -> HumanCheckpoint:
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            raise ValueError(f"Checkpoint '{checkpoint_id}' not found.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        updated = HumanCheckpoint(
            checkpoint_id=cp.checkpoint_id,
            workflow_id=cp.workflow_id,
            verification_type=cp.verification_type,
            verifier_id=verifier_id,
            status=status,
            signed_off_at=now,
        )
        self._checkpoints[checkpoint_id] = updated
        return updated
