"""akaalPipeline.health.explainable
==================================
Explainable Root-Cause Health Derivation Service for P6.3.
Synthesizes signals from authoritative subsystem health evaluators, CDC lag/retention,
and runtime execution into an explainable causal chain with explicit confidence levels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger("akaalPipeline.health")


class HealthConfidenceLevel(str, Enum):
    """Truthful confidence levels for derived health explanations."""
    OBSERVED_CONDITION = "OBSERVED_CONDITION"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    LIKELY_CAUSE = "LIKELY_CAUSE"
    CONFIRMED_CAUSE = "CONFIRMED_CAUSE"
    UNKNOWN = "UNKNOWN"


class MigrationHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HealthCausalLink:
    """A link in the explainable health causal chain."""
    subsystem: str
    observed_signal: str
    condition: str
    confidence: HealthConfidenceLevel
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "observed_signal": self.observed_signal,
            "condition": self.condition,
            "confidence": self.confidence.value,
            "details": self.details,
        }


@dataclass(frozen=True)
class ExplainableHealthReport:
    """Complete explainable health snapshot with root-cause derivation."""
    migration_id: str
    overall_health: MigrationHealthStatus
    summary_reason: str
    causal_chain: List[HealthCausalLink]
    subsystem_signals: Dict[str, Any]
    captured_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "overall_health": self.overall_health.value,
            "summary_reason": self.summary_reason,
            "causal_chain": [c.to_dict() for c in self.causal_chain],
            "subsystem_signals": self.subsystem_signals,
            "captured_at": self.captured_at,
        }


class ExplainableHealthService:
    """
    Synthesizes physical subsystem observations into an explainable health report.
    Does NOT fabricate root cause; when causality is unobservable, reports UNKNOWN.
    """

    DEFAULT_LAG_THRESHOLD_SECONDS = 300.0
    DEFAULT_BACKLOG_THRESHOLD_BYTES = 500 * 1024 * 1024  # 500 MB

    @classmethod
    def evaluate(
        cls,
        migration_id: str,
        migration_state: str,
        cdc_snapshot: Optional[Mapping[str, Any]] = None,
        runtime_snapshot: Optional[Mapping[str, Any]] = None,
        engine_health_snapshot: Optional[Mapping[str, Any]] = None,
        captured_at: Optional[str] = None,
        lag_threshold_seconds: Optional[float] = None,
        backlog_threshold_bytes: Optional[float] = None,
    ) -> ExplainableHealthReport:
        from datetime import datetime, timezone
        now_str = captured_at or datetime.now(timezone.utc).isoformat()
        lag_thresh = lag_threshold_seconds or cls.DEFAULT_LAG_THRESHOLD_SECONDS
        backlog_thresh = backlog_threshold_bytes or cls.DEFAULT_BACKLOG_THRESHOLD_BYTES

        causal_chain: List[HealthCausalLink] = []
        overall_health = MigrationHealthStatus.HEALTHY
        reasons: List[str] = []

        cdc_data = dict(cdc_snapshot or {})
        rt_data = dict(runtime_snapshot or {})
        eng_data = dict(engine_health_snapshot or {})

        # Check 1: Explicit Terminal Failure on Aggregate
        if migration_state in ("FAILED", "CANCELLATION_PENDING"):
            overall_health = MigrationHealthStatus.FAILED
            reasons.append(f"Migration execution is in {migration_state} state.")
            causal_chain.append(
                HealthCausalLink(
                    subsystem="PipelineAggregate",
                    observed_signal=f"state={migration_state}",
                    condition="Migration execution failed or cancelled",
                    confidence=HealthConfidenceLevel.CONFIRMED_CAUSE,
                )
            )

        # Check 2: Explicit Worker Task Errors (Direct causal evidence from partition workers)
        if rt_data:
            tasks = rt_data.get("task_snapshots", [])
            failed_tasks = [t for t in tasks if isinstance(t, dict) and t.get("state") == "FAILED"]
            if failed_tasks:
                overall_health = MigrationHealthStatus.CRITICAL
                reasons.append(f"{len(failed_tasks)} runtime partition task(s) failed.")
                causal_chain.append(
                    HealthCausalLink(
                        subsystem="RuntimeAuthority.TaskExecutor",
                        observed_signal=f"failed_task_count={len(failed_tasks)}",
                        condition="Partition worker terminated with unhandled exception",
                        confidence=HealthConfidenceLevel.CONFIRMED_CAUSE,
                        details={"sample_error": failed_tasks[0].get("error_message")},
                    )
                )

        # Check 3: Source Retention Exhaustion vs Lag
        if cdc_data:
            raw_lag = cdc_data.get("replication_lag_seconds")
            lag_sec = float(raw_lag) if raw_lag is not None else None
            raw_backlog = cdc_data.get("backlog_bytes")
            backlog_bytes = float(raw_backlog) if raw_backlog is not None else None
            retention_state = str(cdc_data.get("retention_state", "HEALTHY")).upper()
            raw_rem = cdc_data.get("retention_remaining_sec")
            rem_sec = float(raw_rem) if raw_rem is not None else None

            if retention_state in ("CRITICAL", "EXHAUSTED") or (rem_sec is not None and rem_sec <= 0):
                if overall_health != MigrationHealthStatus.FAILED:
                    overall_health = MigrationHealthStatus.CRITICAL
                reasons.append("Source CDC log retention is exhausted or approaching limit.")
                causal_chain.append(
                    HealthCausalLink(
                        subsystem="CDCAuthority.RetentionMonitor",
                        observed_signal=f"retention_state={retention_state}, remaining={rem_sec}s",
                        condition="Source transaction log position near cutoff boundary",
                        confidence=HealthConfidenceLevel.CONFIRMED_CAUSE if (rem_sec is not None and rem_sec <= 0) else HealthConfidenceLevel.LIKELY_CAUSE,
                        details={"retention_remaining_sec": rem_sec},
                    )
                )
            elif (lag_sec is not None and lag_sec > lag_thresh) or (backlog_bytes is not None and backlog_bytes > backlog_thresh):
                if overall_health not in (MigrationHealthStatus.CRITICAL, MigrationHealthStatus.FAILED):
                    overall_health = MigrationHealthStatus.DEGRADED
                reasons.append(f"CDC replication lag elevated ({lag_sec:.1f}s / {backlog_bytes / (1024*1024):.1f}MB).")
                causal_chain.append(
                    HealthCausalLink(
                        subsystem="CDCAuthority.BacklogBuffer",
                        observed_signal=f"lag_seconds={lag_sec:.1f}, backlog_bytes={backlog_bytes}",
                        condition="Change capture rate exceeds apply rate or target write latency is elevated",
                        confidence=HealthConfidenceLevel.LIKELY_CAUSE,
                    )
                )

        # Check 4: Subsystem Health Signals
        if eng_data:
            subsystems = eng_data.get("subsystems") or eng_data.get("modules") or {}
            for sub_name, sub_info in subsystems.items():
                if isinstance(sub_info, dict):
                    c_state = str(sub_info.get("state", "HEALTHY")).upper()
                    if c_state in ("UNHEALTHY", "CRITICAL", "FAILED"):
                        if overall_health not in (MigrationHealthStatus.CRITICAL, MigrationHealthStatus.FAILED):
                            overall_health = MigrationHealthStatus.DEGRADED
                        causal_chain.append(
                            HealthCausalLink(
                                subsystem=sub_name,
                                observed_signal=f"state={c_state}",
                                condition=sub_info.get("reason", "Subsystem reported abnormal health status"),
                                confidence=HealthConfidenceLevel.OBSERVED_CONDITION,
                            )
                        )

        # Fallback if no signals attached or unobserved
        has_real_cdc = bool(cdc_data and (cdc_data.get("replication_lag_seconds") is not None or cdc_data.get("events_captured_total", 0) > 0))
        has_real_rt = bool(rt_data and rt_data.get("task_snapshots"))
        has_real_eng = bool(eng_data and (eng_data.get("subsystems") or eng_data.get("modules")))

        if not has_real_cdc and not has_real_rt and not has_real_eng and overall_health == MigrationHealthStatus.HEALTHY:
            overall_health = MigrationHealthStatus.UNKNOWN
            reasons.append("No physical telemetry signals currently available to derive health status.")
            causal_chain.append(
                HealthCausalLink(
                    subsystem="Observability",
                    observed_signal="no_signals",
                    condition="Physical authority probes unattached, inactive, or unobserved",
                    confidence=HealthConfidenceLevel.UNKNOWN,
                )
            )

        summary_reason = " ".join(reasons) if reasons else "Migration and all underlying subsystems operating normally."

        return ExplainableHealthReport(
            migration_id=migration_id,
            overall_health=overall_health,
            summary_reason=summary_reason,
            causal_chain=causal_chain,
            subsystem_signals={"cdc": cdc_data, "runtime": rt_data, "engine": eng_data},
            captured_at=now_str,
        )
