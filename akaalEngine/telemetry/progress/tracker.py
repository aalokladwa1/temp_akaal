"""
akaalEngine.telemetry.progress.tracker
=======================================
Truthful ProgressTracker managing migration progress snapshots.
Enforces that unknown totals produce UNKNOWN remaining, UNKNOWN percentage, and UNKNOWN ETA.
Mined from `akaal/execution/monitoring/tracker.py`.
"""

import logging
from threading import RLock
import time
from typing import Dict, Optional

from akaalEngine.telemetry.models.progress import UNKNOWN_TOTAL, ProgressSnapshot

logger = logging.getLogger("akaalEngine.telemetry.progress.tracker")


class ProgressTracker:
    """
    Truthful progress tracking engine for active migrations.
    """

    def __init__(self) -> None:
        self._start_times: Dict[str, float] = {}
        self._snapshots: Dict[str, ProgressSnapshot] = {}
        self._lock = RLock()

    def initialize_migration(
        self,
        migration_id: str,
        objects_total: int = UNKNOWN_TOTAL,
        rows_total: int = UNKNOWN_TOTAL,
        bytes_total: int = UNKNOWN_TOTAL,
        chunks_total: int = UNKNOWN_TOTAL,
    ) -> ProgressSnapshot:
        with self._lock:
            now = time.time()
            self._start_times[migration_id] = now
            snap = ProgressSnapshot(
                migration_id=migration_id,
                objects_completed=0,
                objects_total=objects_total,
                rows_processed=0,
                rows_total=rows_total,
                bytes_processed=0,
                bytes_total=bytes_total,
                chunks_completed=0,
                chunks_total=chunks_total,
                elapsed_seconds=0.0,
            )
            self._snapshots[migration_id] = snap
            return snap

    def update_progress(
        self,
        migration_id: str,
        add_objects: int = 0,
        add_rows: int = 0,
        add_bytes: int = 0,
        add_chunks: int = 0,
        rows_total_override: Optional[int] = None,
    ) -> ProgressSnapshot:
        with self._lock:
            start_t = self._start_times.setdefault(migration_id, time.time())
            curr_snap = self._snapshots.get(migration_id)

            if not curr_snap:
                curr_snap = ProgressSnapshot(migration_id=migration_id)

            now = time.time()
            elapsed = max(0.001, now - start_t)

            new_objects = curr_snap.objects_completed + add_objects
            new_rows = curr_snap.rows_processed + add_rows
            new_bytes = curr_snap.bytes_processed + add_bytes
            new_chunks = curr_snap.chunks_completed + add_chunks
            rows_tot = rows_total_override if rows_total_override is not None else curr_snap.rows_total

            rows_per_sec = round(new_rows / elapsed, 2)
            bytes_per_sec = round(new_bytes / elapsed, 2)

            snap = ProgressSnapshot(
                migration_id=migration_id,
                objects_completed=new_objects,
                objects_total=curr_snap.objects_total,
                rows_processed=new_rows,
                rows_total=rows_tot,
                bytes_processed=new_bytes,
                bytes_total=curr_snap.bytes_total,
                chunks_completed=new_chunks,
                chunks_total=curr_snap.chunks_total,
                elapsed_seconds=round(elapsed, 2),
                rows_per_second=rows_per_sec,
                bytes_per_second=bytes_per_sec,
            )
            self._snapshots[migration_id] = snap
            return snap

    def get_snapshot(self, migration_id: str) -> ProgressSnapshot:
        with self._lock:
            snap = self._snapshots.get(migration_id)
            if not snap:
                return ProgressSnapshot(migration_id=migration_id)
            return snap
