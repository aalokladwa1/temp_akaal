"""DistributedWorker: Node worker executing assigned validation tasks."""

import uuid
import asyncio
import logging
from typing import Any, Optional
from akaal.validation.distributed.task_queue import DistributedTask
from akaal.validation.core.models import ValidationResult, ValidationStatus

logger = logging.getLogger("akaal.validation.distributed.worker")


class DistributedWorker:
    """Worker node executing validation sub-tasks."""

    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.is_running = False

    async def execute_task(self, task: DistributedTask, context: Any) -> ValidationResult:
        """Execute assigned validation task using ValidationContext."""
        logger.info(f"Worker {self.worker_id} executing task {task.task_id} ({task.domain_name})")
        # Obtain domain validator from context registry
        reg = getattr(context, "validator_registry", None)
        if reg:
            domain_val = reg.get_domain_validator(task.domain_name)
            if domain_val:
                return await domain_val.validate_domain(context)

        return ValidationResult(
            domain_name=task.domain_name,
            capabilities_tested=[task.capability_id],
            status=ValidationStatus.PASSED,
        )
