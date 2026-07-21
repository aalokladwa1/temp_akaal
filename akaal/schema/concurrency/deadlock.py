"""
AKAAL Platform 5 — Deadlock Detector

Detects cycles in lock wait-for graphs to prevent deadlock deadlocks during concurrent schema operations.
"""

from typing import Dict, Set, List, Optional
import threading


class DeadlockDetector:
    """Thread-safe graph cycle deadlock detector."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._wait_for_graph: Dict[str, Set[str]] = {}  # waiter_tx -> set of holder_txs

    def add_wait_edge(self, waiter_tx: str, holder_tx: str) -> None:
        with self._mutex:
            if waiter_tx not in self._wait_for_graph:
                self._wait_for_graph[waiter_tx] = set()
            self._wait_for_graph[waiter_tx].add(holder_tx)

    def remove_waiter(self, waiter_tx: str) -> None:
        with self._mutex:
            self._wait_for_graph.pop(waiter_tx, None)
            for waiter, holders in self._wait_for_graph.items():
                holders.discard(waiter_tx)

    def detect_deadlock(self, start_tx: str) -> Optional[List[str]]:
        """Returns cycle list if deadlock exists, else None."""
        with self._mutex:
            visited = set()
            path = []

            def dfs(node: str) -> Optional[List[str]]:
                if node in path:
                    idx = path.index(node)
                    return path[idx:] + [node]
                if node in visited:
                    return None
                visited.add(node)
                path.append(node)
                for neighbor in self._wait_for_graph.get(node, []):
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                path.pop()
                return None

            return dfs(start_tx)
