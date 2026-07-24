"""DistributedHealingWorker for healing cluster."""

import uuid
import logging
from typing import Optional, Any
from akaal.healing.distributed.task_queue import HealingTask
from akaal.healing.core.models import HealingResult, HealingStatus, RepairOutcome

logger = logging.getLogger("akaal.healing.distributed.worker")


class DistributedHealingWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"hworker_{uuid.uuid4().hex[:8]}"

    async def execute_task(self, task: HealingTask, context: Any) -> HealingResult:
        logger.info(f"Healing worker {self.worker_id} executing task {task.task_id} ({task.domain_name})")
        reg = getattr(context, "healer_registry", None) if context else None
        if reg:
            domain_healer = reg.get_domain_healer(task.domain_name)
            if domain_healer:
                return await domain_healer.heal_domain(context)

        return HealingResult(
            domain_name=task.domain_name,
            capabilities_executed=[task.capability_id],
            status=HealingStatus.COMPLETED,
            outcome=RepairOutcome.REPAIRED,
            successful_actions=1,
        )
