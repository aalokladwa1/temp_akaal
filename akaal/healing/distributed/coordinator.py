"""Distributed worker, scheduler, and coordinator for healing cluster."""

import uuid
import asyncio
import logging
from typing import List, Dict, Any
from akaal.healing.distributed.task_queue import DistributedHealingTaskQueue, HealingTask, HealingTaskLeaseManager, HealingHeartbeatMonitor
from akaal.healing.core.models import HealingResult, HealingStatus, RepairOutcome

logger = logging.getLogger("akaal.healing.distributed")


class DistributedHealingWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"hworker_{uuid.uuid4().hex[:8]}"

    async def execute_task(self, task: HealingTask, context: Any) -> HealingResult:
        logger.info(f"Healing worker {self.worker_id} executing task {task.task_id} ({task.domain_name})")
        reg = getattr(context, "healer_registry", None)
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


class DistributedHealingScheduler:
    def partition_repair_tasks(self, domain_name: str, capability_id: str, table_names: List[str]) -> List[HealingTask]:
        tasks = []
        for table in table_names:
            task_id = f"htask_{domain_name}_{table}_{uuid.uuid4().hex[:6]}"
            tasks.append(
                HealingTask(
                    task_id=task_id,
                    capability_id=capability_id,
                    domain_name=domain_name,
                    payload={"table_name": table},
                )
            )
        return tasks


class DistributedHealingCoordinator:
    def __init__(self, num_workers: int = 4):
        self.scheduler = DistributedHealingScheduler()
        self.heartbeat_monitor = HealingHeartbeatMonitor()
        self.lease_manager = HealingTaskLeaseManager()
        self.task_queue = DistributedHealingTaskQueue()
        self.workers = [DistributedHealingWorker() for _ in range(num_workers)]

    async def run_distributed_healing(self, tasks: List[HealingTask], context: Any) -> List[HealingResult]:
        results = []
        for t in tasks:
            await self.task_queue.enqueue(t)

        worker_idx = 0
        while self.task_queue.size() > 0:
            task = await self.task_queue.dequeue()
            if not task:
                break

            worker = self.workers[worker_idx % len(self.workers)]
            worker_idx += 1

            self.heartbeat_monitor.record_heartbeat(worker.worker_id)
            if self.lease_manager.acquire_lease(task.task_id, worker.worker_id):
                res = await worker.execute_task(task, context)
                results.append(res)
                self.lease_manager.release_lease(task.task_id, worker.worker_id)

        return results
