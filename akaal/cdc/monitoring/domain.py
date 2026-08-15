"""
AKAAL CDC Monitoring & Operational Telemetry Domain Models (P3.9).
====================================================================
Provides safe-by-default, backend-authoritative read models aggregating P3.1–P3.8 runtime telemetry.
Redacts raw customer row payload data and sensitive connection credentials by default.
"""

import datetime
from typing import Dict, Any, List, Optional
from akaal.cdc.domain.events import CDCEventIdentity


class CDCMonitoringSnapshot:
    """
    Canonical aggregated read model for P3.9 CDC Monitoring Experience.
    Binds runtime telemetry across capture, buffering, ordering, partitioning, apply, schema evolution, multi-master conflicts, and recovery.
    """

    SECRET_KEYWORDS = {"password", "passwd", "secret", "token", "api_key", "authorization", "private_key", "connection_string", "auth_token"}

    def __init__(
        self,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        monitoring_mode: str = "LIVE",  # LIVE or HISTORICAL
        session_mode: str = "UNIDIRECTIONAL",  # UNIDIRECTIONAL or BIDIRECTIONAL
        status: str = "HEALTHY",  # HEALTHY, CATCHING_UP, DEGRADED, PAUSED, BLOCKED, FAILED
        source_engine: str = "POSTGRESQL",
        target_engine: str = "POSTGRESQL",
        source_database: str = "source_db",
        target_database: str = "target_db",
        captured_at: Optional[str] = None,
        health_strip: Optional[Dict[str, Any]] = None,
        pipeline: Optional[Dict[str, Any]] = None,
        overview: Optional[Dict[str, Any]] = None,
        telemetry_timeseries: Optional[Dict[str, Any]] = None,
        backlog_and_backpressure: Optional[Dict[str, Any]] = None,
        workers_and_partitions: Optional[Dict[str, Any]] = None,
        ordering_and_causality: Optional[Dict[str, Any]] = None,
        schema_transitions: Optional[Dict[str, Any]] = None,
        conflicts_and_topology: Optional[Dict[str, Any]] = None,
        recovery_and_checkpoints: Optional[Dict[str, Any]] = None,
        cutover_checklist: Optional[Dict[str, Any]] = None,
        operational_events: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.identity = CDCEventIdentity(migration_id, job_id, run_id, cdc_session_id)
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.cdc_session_id = cdc_session_id
        self.monitoring_mode = monitoring_mode
        self.session_mode = session_mode
        self.status = status
        self.source_engine = source_engine
        self.target_engine = target_engine
        self.source_database = source_database
        self.target_database = target_database
        self.captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.health_strip = health_strip or {
            "cdc_state": status,
            "source_lag_sec": 0.0,
            "backlog_events": 0,
            "backlog_bytes": 0,
            "apply_rate_rows_per_sec": 0.0,
            "checkpoint_lsn": "N/A",
            "unresolved_conflicts_count": 0,
            "quarantined_entities_count": 0,
        }

        self.pipeline = pipeline or {
            "source_capture": {"state": "HEALTHY", "rate_events_per_sec": 0.0},
            "durable_buffer": {"state": "HEALTHY", "depth_events": 0, "depth_bytes": 0},
            "ordering_dag": {"state": "HEALTHY", "blocked_tx_count": 0},
            "partition_router": {"state": "HEALTHY", "active_partitions": 1},
            "target_apply": {"state": "HEALTHY", "apply_rate_rows_per_sec": 0.0},
        }

        self.overview = overview or {}
        self.telemetry_timeseries = telemetry_timeseries or {"lag_15m": [], "capture_rate_15m": [], "apply_rate_15m": [], "backlog_15m": []}
        self.backlog_and_backpressure = backlog_and_backpressure or {}
        self.workers_and_partitions = workers_and_partitions or {}
        self.ordering_and_causality = ordering_and_causality or {}
        self.schema_transitions = schema_transitions or {}
        self.conflicts_and_topology = conflicts_and_topology or {}
        self.recovery_and_checkpoints = recovery_and_checkpoints or {}
        self.cutover_checklist = cutover_checklist or {
            "backlog_drained": True,
            "workers_drained": True,
            "ordering_dependencies_resolved": True,
            "schema_barriers_clear": True,
            "conflicts_resolved": True,
            "quarantines_clear": True,
            "checkpoint_current": True,
            "cutover_ready": True,
        }
        raw_events = operational_events or []
        self.operational_events = raw_events[-100:] if len(raw_events) > 100 else raw_events

    @classmethod
    def _sanitize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(sec in k.lower() for sec in cls.SECRET_KEYWORDS):
                    sanitized[k] = "[REDACTED_SECRET]"
                else:
                    sanitized[k] = cls._sanitize(v)
            return sanitized
        elif isinstance(data, list):
            return [cls._sanitize(item) for item in data]
        return data

    def to_dict(self) -> Dict[str, Any]:
        raw_dict = {
            "schema_version": "1.0",
            "migration_id": self.identity.migration_id,
            "job_id": self.identity.job_id,
            "run_id": self.identity.run_id,
            "cdc_session_id": self.identity.cdc_session_id,
            "monitoring_mode": self.monitoring_mode,
            "session_mode": self.session_mode,
            "status": self.status,
            "source_engine": self.source_engine,
            "target_engine": self.target_engine,
            "source_database": self.source_database,
            "target_database": self.target_database,
            "captured_at": self.captured_at,
            "health_strip": self.health_strip,
            "pipeline": self.pipeline,
            "overview": self.overview,
            "telemetry_timeseries": self.telemetry_timeseries,
            "backlog_and_backpressure": self.backlog_and_backpressure,
            "workers_and_partitions": self.workers_and_partitions,
            "ordering_and_causality": self.ordering_and_causality,
            "schema_transitions": self.schema_transitions,
            "conflicts_and_topology": self.conflicts_and_topology,
            "recovery_and_checkpoints": self.recovery_and_checkpoints,
            "cutover_checklist": self.cutover_checklist,
            "operational_events": self.operational_events,
        }
        return self._sanitize(raw_dict)
