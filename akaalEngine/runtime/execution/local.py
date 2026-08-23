"""
akaalEngine.runtime.execution.local
====================================
Bounded local thread pool executor with exception capture and cancellation propagation.
"""

from concurrent.futures import ThreadPoolExecutor, Future
import logging
from threading import RLock
from typing import Any, Callable, Dict, Optional

from akaalEngine.runtime.execution.cancellation import CancellationToken, PauseGate
from akaalEngine.runtime.models.errors import TaskExecutionError
from akaalEngine.runtime.models.task import TaskSpec

logger = logging.getLogger("akaalEngine.runtime.local")


class BoundedThreadExecutor:
    """
    Bounded local thread execution engine managing local thread pools,
    cancellation tokens, pause gates, and exception capture.
    """

    def __init__(self, max_workers: int = 16) -> None:
        self.max_workers = max_workers
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="akaal-worker")
        self._tokens: Dict[str, CancellationToken] = {}
        self._gates: Dict[str, PauseGate] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = RLock()

    def get_token(self, task_id: str) -> CancellationToken:
        with self._lock:
            if task_id not in self._tokens:
                self._tokens[task_id] = CancellationToken(task_id)
            return self._tokens[task_id]

    def get_gate(self, task_id: str) -> PauseGate:
        with self._lock:
            if task_id not in self._gates:
                self._gates[task_id] = PauseGate(task_id)
            return self._gates[task_id]

    def submit(self, spec: TaskSpec, completion_callback: Optional[Callable[[str, Optional[Any], Optional[Exception]], None]] = None) -> Future:
        if spec.func is None:
            raise ValueError(f"TaskSpec '{spec.task_id}' has no callable function.")

        with self._lock:
            token = self.get_token(spec.task_id)
            gate = self.get_gate(spec.task_id)

            def _wrapped_execution() -> Any:
                token.check()
                gate.wait_if_paused()
                token.check()

                try:
                    result = spec.func(*spec.args, **spec.kwargs)
                    token.check()
                    if completion_callback:
                        completion_callback(spec.task_id, result, None)
                    return result
                except Exception as exc:
                    logger.error(f"[BoundedThreadExecutor] Task '{spec.task_id}' failed: {exc}")
                    if completion_callback:
                        completion_callback(spec.task_id, None, exc)
                    raise

            future = self._pool.submit(_wrapped_execution)
            self._futures[spec.task_id] = future
            return future

    def cancel(self, task_id: str, reason: str = "Cancellation requested") -> bool:
        with self._lock:
            token = self._tokens.get(task_id)
            if token:
                token.cancel(reason)
            future = self._futures.get(task_id)
            if future and not future.done():
                return future.cancel()
            return bool(token)

    def pause(self, task_id: str) -> None:
        with self._lock:
            gate = self.get_gate(task_id)
            gate.pause()

    def resume(self, task_id: str) -> None:
        with self._lock:
            gate = self.get_gate(task_id)
            gate.resume()

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            for token in self._tokens.values():
                token.cancel("Executor shutting down")
            for gate in self._gates.values():
                gate.resume()
            self._pool.shutdown(wait=wait)
