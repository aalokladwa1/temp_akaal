"""Workflow Scheduler and Dependency Resolver Loop."""

import threading
from typing import Dict, List, Optional
from akaal.workflow.planning.planner import ExecutionPlan
from akaal.workflow.queues.interfaces import IWorkflowQueue, StepExecutionTask
from akaal.workflow.queues.in_memory import InMemoryWorkflowQueue
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.id_generator import IIdGenerator, UUIDIdGenerator


class WorkflowScheduler:
    """Enterprise workflow scheduler popping ready tasks and routing to queues."""

    def __init__(
        self,
        queue: IWorkflowQueue | None = None,
        clock: IClock | None = None,
        id_generator: IIdGenerator | None = None,
    ) -> None:
        self._queue = queue or InMemoryWorkflowQueue()
        self._clock = clock or SystemClock()
        self._id_generator = id_generator or UUIDIdGenerator()
        self._scheduled_tasks: List[StepExecutionTask] = []
        self._lock = threading.Lock()

    def submit_plan(
        self,
        plan: ExecutionPlan,
        step_types: Dict[str, str] | None = None,
        tenant_id: str = "default",
        priority: int = 40,
    ) -> List[StepExecutionTask]:
        """Submit an execution plan, enqueueing Stage 0 ready tasks."""
        with self._lock:
            tasks: List[StepExecutionTask] = []
            if not plan.stages:
                return tasks

            types_map = step_types or {}
            # Stage 0 steps are immediately ready
            stage0 = plan.stages[0]
            for step_id in stage0.step_ids:
                task_id = self._id_generator.generate_uuid()
                step_type = types_map.get(step_id, "ReferencePassStep")
                task = StepExecutionTask(
                    task_id=task_id,
                    workflow_id=plan.workflow_id,
                    run_id="run_1",
                    step_id=step_id,
                    step_type=step_type,
                    tenant_id=tenant_id,
                    priority=priority,
                    enqueued_at=self._clock.now_utc(),
                )
                self._queue.enqueue(task)
                tasks.append(task)
                self._scheduled_tasks.append(task)
            return tasks

    def pop_next_task(self) -> Optional[StepExecutionTask]:
        """Pop the next ready task from the queue."""
        return self._queue.dequeue()

    def acknowledge_task(self, task_id: str) -> bool:
        return self._queue.acknowledge(task_id)

    def size(self) -> int:
        return self._queue.size()
