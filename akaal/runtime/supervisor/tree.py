"""
AKAAL Runtime V3 — Runtime Supervisor Tree
==========================================
OTP-style supervisor tree managing child process PIDs, crash detection, restart intensity tracking, and auto-spawning runtime daemons.
"""

import os
import sys
import time
import subprocess
import logging
from typing import Any, Dict, Optional
from akaal.runtime.process.daemon import MigrationRuntimeDaemon

logger = logging.getLogger("akaal.runtime.supervisor")


class RuntimeSupervisorTree:
    """Monitors and restarts isolated child runtime daemon processes."""

    def __init__(self, max_restarts: int = 3, restart_window_seconds: int = 60) -> None:
        self.max_restarts = max_restarts
        self.restart_window = restart_window_seconds
        self.active_processes: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, List[float]] = {}

    def spawn_runtime_daemon(self, migration_id: str, epoch: int, config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[RuntimeSupervisor] Spawning isolated runtime daemon for migration '{migration_id}' (Epoch: {epoch})...")
        
        # Instantiate in-process daemon runner or subprocess for isolation
        daemon = MigrationRuntimeDaemon(migration_id=migration_id, epoch=epoch, config=config)
        pid = daemon.pid

        self.active_processes[migration_id] = {
            "daemon": daemon,
            "pid": pid,
            "epoch": epoch,
            "spawned_at": time.time(),
            "config": config,
            "status": "RUNNING"
        }
        return self.active_processes[migration_id]

    def monitor_and_healthcheck(self, migration_id: str) -> Dict[str, Any]:
        info = self.active_processes.get(migration_id)
        if not info:
            return {"status": "NOT_FOUND", "is_healthy": False}

        daemon: MigrationRuntimeDaemon = info["daemon"]
        now = time.time()
        # Check heartbeat freshness (stale if > 15s)
        is_healthy = daemon.is_alive and (now - daemon.last_heartbeat < 15.0)

        if not is_healthy and daemon.status == "RUNNING":
            logger.warning(f"[RuntimeSupervisor] Detected crashed/stale runtime daemon for '{migration_id}'. Attempting restart...")
            return self._auto_restart_runtime(migration_id)

        return {
            "status": daemon.status,
            "is_healthy": is_healthy,
            "pid": info["pid"],
            "epoch": info["epoch"],
            "last_heartbeat": daemon.last_heartbeat
        }

    def _auto_restart_runtime(self, migration_id: str) -> Dict[str, Any]:
        now = time.time()
        history = self.restart_counts.get(migration_id, [])
        # Prune old restart timestamps
        history = [t for t in history if now - t < self.restart_window]
        
        if len(history) >= self.max_restarts:
            logger.error(f"[RuntimeSupervisor] Maximum restart threshold ({self.max_restarts}) exceeded for '{migration_id}'. Stopping supervisor auto-restart.")
            return {"status": "MAX_RESTARTS_EXCEEDED", "is_healthy": False}

        history.append(now)
        self.restart_counts[migration_id] = history

        old_info = self.active_processes[migration_id]
        new_epoch = old_info["epoch"] + 1
        logger.info(f"[RuntimeSupervisor] Respawning runtime daemon for '{migration_id}' with incremented Epoch: {new_epoch}...")
        
        return self.spawn_runtime_daemon(migration_id, new_epoch, old_info["config"])

    def terminate_runtime(self, migration_id: str) -> bool:
        info = self.active_processes.pop(migration_id, None)
        if info and "daemon" in info:
            daemon: MigrationRuntimeDaemon = info["daemon"]
            daemon.shutdown()
            logger.info(f"[RuntimeSupervisor] Successfully terminated runtime daemon for '{migration_id}'.")
            return True
        return False
