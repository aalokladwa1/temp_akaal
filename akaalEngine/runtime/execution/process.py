"""
akaalEngine.runtime.execution.process
======================================
ProcessPool isolated execution engine for CPU-heavy or isolated tasks with child failure detection.
"""

from concurrent.futures import ProcessPoolExecutor, Future
import logging
from threading import RLock
from typing import Any, Callable, Dict, Optional

from akaalEngine.runtime.models.errors import TaskExecutionError
from akaalEngine.runtime.models.task import TaskSpec

logger = logging.getLogger("akaalEngine.runtime.process")


class IsolatedProcessExecutor:
    """
    Isolated process-pool execution engine managing child process lifecycles,
    child crash/exit detection, and result propagation.
    """

    def __init__(self, max_processes: int = 4) -> None:
        self.max_processes = max_processes
        self._pool: Optional[ProcessPoolExecutor] = None
        self._futures: Dict[str, Future] = {}
        self._lock = RLock()

    def _ensure_pool(self) -> ProcessPoolExecutor:
        if self._pool is None:
            self._pool = ProcessPoolExecutor(max_workers=self.max_processes)
        return self._pool

    def submit(self, spec: TaskSpec, completion_callback: Optional[Callable[[str, Optional[Any], Optional[Exception]], None]] = None) -> Future:
        if spec.func is None:
            raise ValueError(f"TaskSpec '{spec.task_id}' has no callable function.")

        with self._lock:
            pool = self._ensure_pool()
            func = spec.func
            args = spec.args
            kwargs = spec.kwargs

            future = pool.submit(func, *args, **kwargs)
            self._futures[spec.task_id] = future

            if completion_callback:
                def _done_cb(f: Future) -> None:
                    try:
                        res = f.result()
                        completion_callback(spec.task_id, res, None)
                    except Exception as exc:
                        completion_callback(spec.task_id, None, exc)

                future.add_done_callback(_done_cb)

            return future

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            future = self._futures.get(task_id)
            if future and not future.done():
                return future.cancel()
            return False

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            if self._pool is not None:
                self._pool.shutdown(wait=wait)
                self._pool = None
