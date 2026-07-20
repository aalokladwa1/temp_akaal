"""Chaos Engine for Built-in Fault Injection and Reliability Simulation."""

import threading
from typing import Dict


class ChaosEngine:
    """Built-in fault injection subsystem simulating node crashes, partition drops, and lock loss."""

    def __init__(self) -> None:
        self._faults: Dict[str, bool] = {
            "worker_crash": False,
            "queue_failure": False,
            "lock_loss": False,
            "network_partition": False,
            "clock_skew": False,
        }
        self._lock = threading.Lock()

    def inject_fault(self, fault_name: str) -> None:
        with self._lock:
            self._faults[fault_name] = True

    def clear_fault(self, fault_name: str) -> None:
        with self._lock:
            self._faults[fault_name] = False

    def is_fault_active(self, fault_name: str) -> bool:
        with self._lock:
            return self._faults.get(fault_name, False)
