"""DistributedHealingScheduler for partitioning healing tasks."""

import uuid
from typing import List
from akaal.healing.distributed.task_queue import HealingTask


class DistributedHealingScheduler:
    """Partitions self-healing workloads into tasks for distributed workers."""

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
