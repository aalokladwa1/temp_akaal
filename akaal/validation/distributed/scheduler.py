"""DistributedScheduler: Work partitioner and task scheduling engine."""

import uuid
from typing import List, Dict, Any
from akaal.validation.distributed.task_queue import DistributedTask


class DistributedScheduler:
    """Schedules and partitions validation workloads into distributed tasks."""

    def partition_table_validation(
        self, domain_name: str, capability_id: str, table_names: List[str], chunk_size: int = 10000
    ) -> List[DistributedTask]:
        """Partition validation workloads into tasks."""
        tasks = []
        for table in table_names:
            task_id = f"task_{domain_name}_{table}_{uuid.uuid4().hex[:6]}"
            tasks.append(
                DistributedTask(
                    task_id=task_id,
                    capability_id=capability_id,
                    domain_name=domain_name,
                    payload={"table_name": table, "chunk_size": chunk_size},
                )
            )
        return tasks
