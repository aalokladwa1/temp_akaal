"""akaalPipeline.execution.cancellation
=======================================
Cancellation coordinator for in-flight attempts.
"""

from __future__ import annotations

import sqlite3
from typing import Optional
from akaalPipeline.contracts.enums import AttemptLifecycleState, OperationStatus
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.service import OperationService


class CancellationCoordinator:
    def __init__(self, operation_service: OperationService) -> None:
        self.operation_service = operation_service

    def cancel_operation(
        self,
        operation_id: str,
        reason: str,
        conn: sqlite3.Connection,
    ) -> None:
        op = self.operation_service.get_by_id(operation_id, conn)
        if op is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Operation {operation_id!r} not found.")

        if op.status in (OperationStatus.SUCCEEDED, OperationStatus.FAILED, OperationStatus.CANCELLED):
            return

        self.operation_service.update_status(
            operation_id,
            OperationStatus.CANCELLED,
            conn,
            error={"reason": reason, "code": "CANCELLED"},
        )
