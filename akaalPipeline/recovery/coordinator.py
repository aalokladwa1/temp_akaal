"""akaalPipeline.recovery.coordinator
====================================
Pipeline-owned recovery coordinator.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Mapping, Optional
from akaalPipeline.contracts.enums import AttemptLifecycleState, OperationStatus, SideEffectClassification
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService


class RecoveryCoordinator:
    def __init__(
        self,
        lease_manager: LeaseManager,
        operation_service: OperationService,
    ) -> None:
        self.lease_manager = lease_manager
        self.operation_service = operation_service

    def evaluate_recovery(
        self,
        attempt_id: str,
        operation_id: str,
        side_effect: SideEffectClassification,
        conn: sqlite3.Connection,
    ) -> tuple[bool, str]:
        """Evaluates whether recovery is safe. Returns (can_recover, reason_str).
        If side_effect is IRREVERSIBLE or DESTRUCTIVE, automatic replay is forbidden.
        """
        if side_effect in (SideEffectClassification.IRREVERSIBLE, SideEffectClassification.DESTRUCTIVE):
            return (False, f"Side effect classification {side_effect.value!r} forbids automatic replay/recovery.")

        lease = self.lease_manager.get_lease(attempt_id, conn)
        if lease and not lease.is_expired():
            return (False, f"Attempt {attempt_id!r} still has an active unexpired lease.")

        return (True, "Recovery permitted: lease expired and side effects are safe for retry.")
