"""
AKAAL Engine Telemetry & Observability Subsystem
=================================================
Emits structured JSON telemetry snapshots independent of Desktop UI.
"""

import time
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("akaal.engine.telemetry")


class TelemetryEmitter:
    """Broadcasting structured JSON events for runtime progress monitoring."""

    def __init__(self, migration_id: str):
        self.migration_id = migration_id
        self.start_time = time.time()

    def build_snapshot(
        self,
        state: str,
        total_tables: int,
        completed_tables: int,
        total_rows: int,
        migrated_rows: int,
        active_workers: int,
        peak_throughput: float = 0.0,
    ) -> Dict[str, Any]:
        elapsed = max(0.001, time.time() - self.start_time)
        throughput = migrated_rows / elapsed
        remaining_rows = max(0, total_rows - migrated_rows)
        eta = (remaining_rows / throughput) if throughput > 0 else 0.0

        snapshot = {
            "event_type": "TELEMETRY_SNAPSHOT",
            "migration_id": self.migration_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": state,
            "total_tables": total_tables,
            "completed_tables": completed_tables,
            "total_rows": total_rows,
            "migrated_rows": migrated_rows,
            "throughput_rows_sec": round(throughput, 2),
            "peak_throughput_rows_sec": round(max(throughput, peak_throughput), 2),
            "active_workers": active_workers,
            "elapsed_seconds": round(elapsed, 2),
            "eta_seconds": round(eta, 2),
        }

        logger.info(f"[TELEMETRY] {json.dumps(snapshot)}")
        return snapshot
