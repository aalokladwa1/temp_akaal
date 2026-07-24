"""DistributedCoordinator: Cluster coordinator for horizontal worker orchestration."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from akaal.validation.distributed.scheduler import DistributedScheduler
from akaal.validation.distributed.worker import DistributedWorker
from akaal.validation.distributed.heartbeat import HeartbeatMonitor
from akaal.validation.distributed.leases import TaskLeaseManager
from akaal.validation.distributed.task_queue import DistributedTaskQueue, DistributedTask
from akaal.validation.core.models import ValidationResult, ValidationStatus

logger = logging.getLogger("akaal.validation.distributed.coordinator")


class DistributedCoordinator:
    """Cluster coordinator managing workers, task scheduling, leases, heartbeats, and failover."""

    def __init__(self, num_workers: int = 4):
        self.scheduler = DistributedScheduler()
        self.heartbeat_monitor = HeartbeatMonitor()
        self.lease_manager = TaskLeaseManager()
        self.task_queue = DistributedTaskQueue()
        self.workers: List[DistributedWorker] = [DistributedWorker() for _ in range(num_workers)]

    async def run_distributed_pipeline(self, tasks: List[DistributedTask], context: Any) -> List[ValidationResult]:
        """Distribute tasks across workers and collect results."""
        results: List[ValidationResult] = []
        for t in tasks:
            await self.task_queue.enqueue(t)

        # Process queued tasks
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
            else:
                # Re-queue on lock failure
                await self.task_queue.enqueue(task)

        return results
