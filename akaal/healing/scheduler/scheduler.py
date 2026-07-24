"""RepairScheduler: Priority and SLA-aware scheduling engine."""

import logging
from typing import Any, List, Optional
from akaal.healing.scheduler.priority_queue import QueueManager
from akaal.healing.scheduler.sla import SLAEngine, MaintenanceWindow

logger = logging.getLogger("akaal.healing.scheduler")


class RepairScheduler:
    """Schedules and prioritizes self-healing workloads."""

    def __init__(self):
        self.queue_mgr = QueueManager()
        self.sla_engine = SLAEngine()
        self.maintenance_window = MaintenanceWindow()

    def schedule_repair(self, repair_id: str, plan: Any, criticality: str = "MEDIUM") -> None:
        """Schedule repair plan into priority queue."""
        score = self.sla_engine.calculate_priority_score(criticality)
        self.queue_mgr.queue.push(repair_id, plan, score)
        logger.info(f"Scheduled repair {repair_id} with priority score {score}")

    def get_next_repair(self) -> Optional[Any]:
        """Fetch next queued repair plan."""
        return self.queue_mgr.queue.pop()
