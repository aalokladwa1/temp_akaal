"""akaalPipeline.operations.capacity
=================================
P6.6 Capacity, Storage & Resource Intelligence Authority.
Observes, derives, and forecasts resource capacity and risks without mutating runtime.
Distinguishes MEASURED, DERIVED, ESTIMATED, and UNKNOWN/UNAVAILABLE evidence.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.enums import (
    CapacityRiskLevel,
    PipelineErrorCode,
    ResourceEvidenceKind,
    ResourceType,
)
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.operations.capacity")


@dataclass(frozen=True)
class ResourceObservation:
    """Truthful observation of a system or operational resource."""
    observation_id: str
    tenant_id: str
    resource_type: ResourceType
    value: float
    units: str
    evidence_kind: ResourceEvidenceKind
    source_authority: str
    freshness_sec: float = 0.0
    workspace_id: str = "default-workspace"
    project_id: Optional[str] = None
    node_id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    timestamp_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "node_id": self.node_id,
            "resource_type": self.resource_type.value,
            "value": self.value,
            "units": self.units,
            "evidence_kind": self.evidence_kind.value,
            "source_authority": self.source_authority,
            "freshness_sec": self.freshness_sec,
            "provenance": self.provenance or {},
            "timestamp_iso": self.timestamp_iso,
        }


@dataclass(frozen=True)
class StorageBreakdown:
    """Authoritative storage consumption without double-counting."""
    total_bytes: int
    free_bytes: int
    used_bytes: int
    staging_bytes: int
    checkpoint_bytes: int
    journal_bytes: int
    untracked_bytes: int
    evidence_kind: ResourceEvidenceKind
    canonical_root: str
    observed_at_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_bytes": self.total_bytes,
            "free_bytes": self.free_bytes,
            "used_bytes": self.used_bytes,
            "staging_bytes": self.staging_bytes,
            "checkpoint_bytes": self.checkpoint_bytes,
            "journal_bytes": self.journal_bytes,
            "untracked_bytes": self.untracked_bytes,
            "evidence_kind": self.evidence_kind.value,
            "canonical_root": self.canonical_root,
            "observed_at_iso": self.observed_at_iso,
        }


@dataclass(frozen=True)
class CapacityForecast:
    """Mathematically defensible capacity exhaustion forecast."""
    forecast_id: str
    tenant_id: str
    resource_type: ResourceType
    target_metric: str
    current_value: float
    projected_exhaustion_time_iso: Optional[str]
    growth_rate_per_sec: float
    sample_count: int
    observation_window_sec: float
    evidence_kind: ResourceEvidenceKind
    confidence_score: Optional[float]
    assumptions: List[str]
    created_at_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type.value,
            "target_metric": self.target_metric,
            "current_value": self.current_value,
            "projected_exhaustion_time_iso": self.projected_exhaustion_time_iso,
            "growth_rate_per_sec": self.growth_rate_per_sec,
            "sample_count": self.sample_count,
            "observation_window_sec": self.observation_window_sec,
            "evidence_kind": self.evidence_kind.value,
            "confidence_score": self.confidence_score,
            "assumptions": self.assumptions,
            "created_at_iso": self.created_at_iso,
        }


@dataclass(frozen=True)
class CapacityRecommendation:
    """Operational capacity recommendation. Does NOT mutate runtime directly."""
    recommendation_id: str
    tenant_id: str
    resource_type: ResourceType
    risk_level: CapacityRiskLevel
    message: str
    suggested_action: str
    created_at_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type.value,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "created_at_iso": self.created_at_iso,
        }


@dataclass(frozen=True)
class CapacityReport:
    """Comprehensive snapshot of capacity, storage, and resource intelligence."""
    tenant_id: str
    risk_level: CapacityRiskLevel
    observations: List[ResourceObservation]
    storage_breakdown: Optional[StorageBreakdown]
    recommendations: List[CapacityRecommendation]
    forecasts: List[CapacityForecast]
    generated_at_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "risk_level": self.risk_level.value,
            "observations": [o.to_dict() for o in self.observations],
            "storage_breakdown": self.storage_breakdown.to_dict() if self.storage_breakdown else None,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "forecasts": [f.to_dict() for f in self.forecasts],
            "generated_at_iso": self.generated_at_iso,
        }


class CapacityIntelligenceService:
    """P6.6 Backend Authority for Capacity, Storage & Resource Intelligence."""

    def sample_os_resources(
        self,
        node_id: str = "node-local",
        tenant_id: str = "default-tenant",
    ) -> List[ResourceObservation]:
        """Observes CPU, Memory, and Disk for the local host truthfully."""
        now_iso = datetime.now(timezone.utc).isoformat()
        observations: List[ResourceObservation] = []

        # 1. Memory Observation
        try:
            import psutil  # type: ignore
            mem = psutil.virtual_memory()
            observations.append(
                ResourceObservation(
                    observation_id=f"obs-mem-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    node_id=node_id,
                    resource_type=ResourceType.MEMORY,
                    value=float(mem.percent),
                    units="percent",
                    evidence_kind=ResourceEvidenceKind.MEASURED,
                    source_authority="psutil.virtual_memory",
                    provenance={"total_bytes": mem.total, "available_bytes": mem.available},
                    timestamp_iso=now_iso,
                )
            )
        except Exception:
            observations.append(
                ResourceObservation(
                    observation_id=f"obs-mem-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    node_id=node_id,
                    resource_type=ResourceType.MEMORY,
                    value=0.0,
                    units="percent",
                    evidence_kind=ResourceEvidenceKind.UNKNOWN,
                    source_authority="os_unsupported",
                    timestamp_iso=now_iso,
                )
            )

        # 2. CPU Observation
        try:
            import psutil  # type: ignore
            cpu_pct = float(psutil.cpu_percent(interval=0.0))
            observations.append(
                ResourceObservation(
                    observation_id=f"obs-cpu-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    node_id=node_id,
                    resource_type=ResourceType.CPU,
                    value=cpu_pct,
                    units="percent",
                    evidence_kind=ResourceEvidenceKind.MEASURED,
                    source_authority="psutil.cpu_percent",
                    timestamp_iso=now_iso,
                )
            )
        except Exception:
            observations.append(
                ResourceObservation(
                    observation_id=f"obs-cpu-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    node_id=node_id,
                    resource_type=ResourceType.CPU,
                    value=0.0,
                    units="percent",
                    evidence_kind=ResourceEvidenceKind.UNKNOWN,
                    source_authority="os_unsupported",
                    timestamp_iso=now_iso,
                )
            )

        # 3. Disk Observation
        try:
            disk_usage = shutil.disk_usage(os.getcwd())
            pct = (disk_usage.used / disk_usage.total) * 100.0 if disk_usage.total > 0 else 0.0
            observations.append(
                ResourceObservation(
                    observation_id=f"obs-disk-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    node_id=node_id,
                    resource_type=ResourceType.DISK,
                    value=round(pct, 2),
                    units="percent",
                    evidence_kind=ResourceEvidenceKind.MEASURED,
                    source_authority="shutil.disk_usage",
                    provenance={"total_bytes": disk_usage.total, "free_bytes": disk_usage.free, "used_bytes": disk_usage.used},
                    timestamp_iso=now_iso,
                )
            )
        except Exception:
            observations.append(
                ResourceObservation(
                    observation_id=f"obs-disk-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    node_id=node_id,
                    resource_type=ResourceType.DISK,
                    value=0.0,
                    units="percent",
                    evidence_kind=ResourceEvidenceKind.UNKNOWN,
                    source_authority="os_unsupported",
                    timestamp_iso=now_iso,
                )
            )

        return observations

    def sample_storage_breakdown(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        db_path: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
        staging_dir: Optional[str] = None,
    ) -> StorageBreakdown:
        """Measures authoritative storage consumption without scanning arbitrary directories."""
        canonical_root = os.path.dirname(db_path) if db_path else os.getcwd()
        try:
            disk_usage = shutil.disk_usage(canonical_root)
            total_b = disk_usage.total
            free_b = disk_usage.free
            used_b = disk_usage.used
            kind = ResourceEvidenceKind.MEASURED
        except Exception:
            total_b = 0
            free_b = 0
            used_b = 0
            kind = ResourceEvidenceKind.UNKNOWN

        # Authoritative journal/database file size
        journal_b = 0
        if db_path and os.path.exists(db_path):
            try:
                journal_b = os.path.getsize(db_path)
            except Exception:
                journal_b = 0

        # Authoritative checkpoint size
        checkpoint_b = 0
        if checkpoint_dir and os.path.isdir(checkpoint_dir):
            try:
                for entry in os.scandir(checkpoint_dir):
                    if entry.is_file():
                        checkpoint_b += entry.stat().st_size
            except Exception:
                checkpoint_b = 0

        # Authoritative staging size
        staging_b = 0
        if staging_dir and os.path.isdir(staging_dir):
            try:
                for entry in os.scandir(staging_dir):
                    if entry.is_file():
                        staging_b += entry.stat().st_size
            except Exception:
                staging_b = 0

        # Double count prevention
        tracked_sum = journal_b + checkpoint_b + staging_b
        untracked_b = max(0, used_b - tracked_sum)

        return StorageBreakdown(
            total_bytes=total_b,
            free_bytes=free_b,
            used_bytes=used_b,
            staging_bytes=staging_b,
            checkpoint_bytes=checkpoint_b,
            journal_bytes=journal_b,
            untracked_bytes=untracked_b,
            evidence_kind=kind,
            canonical_root=canonical_root,
        )

    def sample_cdc_and_backlog(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
    ) -> List[ResourceObservation]:
        """Observes CDC backlog and queue depth from authoritative pipeline tables."""
        now_iso = datetime.now(timezone.utc).isoformat()
        obs_list: List[ResourceObservation] = []

        try:
            cur = conn.execute(
                "SELECT COUNT(*) as cnt FROM outbox_events WHERE tenant_id = ? AND status = 'PENDING'",
                (tenant_id,),
            )
            row = cur.fetchone()
            backlog_count = row["cnt"] if row else 0
            obs_list.append(
                ResourceObservation(
                    observation_id=f"obs-backlog-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    resource_type=ResourceType.CDC_BACKLOG,
                    value=float(backlog_count),
                    units="events",
                    evidence_kind=ResourceEvidenceKind.MEASURED,
                    source_authority="outbox_events.pending_count",
                    timestamp_iso=now_iso,
                )
            )
        except Exception:
            obs_list.append(
                ResourceObservation(
                    observation_id=f"obs-backlog-{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    resource_type=ResourceType.CDC_BACKLOG,
                    value=0.0,
                    units="events",
                    evidence_kind=ResourceEvidenceKind.UNKNOWN,
                    source_authority="outbox_events_unavailable",
                    timestamp_iso=now_iso,
                )
            )

        return obs_list

    def record_observation(
        self,
        obs: ResourceObservation,
        conn: sqlite3.Connection,
    ) -> None:
        """Persists a resource observation into durable SQLite storage."""
        conn.execute(
            """
            INSERT INTO capacity_observations (
                observation_id, tenant_id, workspace_id, project_id, node_id,
                resource_type, value, units, evidence_kind, source_authority,
                freshness_sec, provenance, timestamp, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs.observation_id,
                obs.tenant_id,
                obs.workspace_id,
                obs.project_id,
                obs.node_id,
                obs.resource_type.value,
                obs.value,
                obs.units,
                obs.evidence_kind.value,
                obs.source_authority,
                obs.freshness_sec,
                json.dumps(obs.provenance or {}),
                obs.timestamp_iso,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def get_history(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        conn: sqlite3.Connection,
        limit: int = 100,
    ) -> List[ResourceObservation]:
        """Retrieves durable resource observation history."""
        cur = conn.execute(
            """
            SELECT * FROM capacity_observations
            WHERE tenant_id = ? AND resource_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (tenant_id, resource_type.value, limit),
        )
        results: List[ResourceObservation] = []
        for row in cur.fetchall():
            results.append(
                ResourceObservation(
                    observation_id=row["observation_id"],
                    tenant_id=row["tenant_id"],
                    workspace_id=row["workspace_id"],
                    project_id=row["project_id"],
                    node_id=row["node_id"],
                    resource_type=ResourceType(row["resource_type"]),
                    value=float(row["value"]),
                    units=row["units"],
                    evidence_kind=ResourceEvidenceKind(row["evidence_kind"]),
                    source_authority=row["source_authority"],
                    freshness_sec=float(row["freshness_sec"]),
                    provenance=json.loads(row["provenance"]) if row["provenance"] else {},
                    timestamp_iso=row["timestamp"],
                )
            )
        return results

    def generate_forecast(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        conn: sqlite3.Connection,
        target_capacity: Optional[float] = None,
        min_samples: int = 3,
        observation_window_sec: float = 3600.0,
    ) -> CapacityForecast:
        """Produces a mathematically defensible exhaustion forecast. Returns INSUFFICIENT_DATA if evidence is lacking."""
        forecast_id = f"fcst-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        history = self.get_history(tenant_id, resource_type, conn, limit=50)

        # Filter to valid measured samples
        valid_samples = [h for h in history if h.evidence_kind in (ResourceEvidenceKind.MEASURED, ResourceEvidenceKind.DERIVED)]

        if len(valid_samples) < min_samples:
            return CapacityForecast(
                forecast_id=forecast_id,
                tenant_id=tenant_id,
                resource_type=resource_type,
                target_metric="exhaustion_horizon",
                current_value=valid_samples[0].value if valid_samples else 0.0,
                projected_exhaustion_time_iso=None,
                growth_rate_per_sec=0.0,
                sample_count=len(valid_samples),
                observation_window_sec=observation_window_sec,
                evidence_kind=ResourceEvidenceKind.INSUFFICIENT_DATA,
                confidence_score=None,
                assumptions=["Insufficient observation count for linear regression (minimum 3 required)."],
            )

        # Sort by timestamp ascending
        sorted_samples = sorted(valid_samples, key=lambda s: s.timestamp_iso)
        t0 = datetime.fromisoformat(sorted_samples[0].timestamp_iso)
        t_last = datetime.fromisoformat(sorted_samples[-1].timestamp_iso)
        delta_sec = (t_last - t0).total_seconds()

        if delta_sec <= 0:
            return CapacityForecast(
                forecast_id=forecast_id,
                tenant_id=tenant_id,
                resource_type=resource_type,
                target_metric="exhaustion_horizon",
                current_value=sorted_samples[-1].value,
                projected_exhaustion_time_iso=None,
                growth_rate_per_sec=0.0,
                sample_count=len(sorted_samples),
                observation_window_sec=0.0,
                evidence_kind=ResourceEvidenceKind.INSUFFICIENT_DATA,
                confidence_score=None,
                assumptions=["Degenerate observation window (all samples have identical timestamps)."],
            )

        v0 = sorted_samples[0].value
        v_last = sorted_samples[-1].value
        growth_rate_per_sec = (v_last - v0) / delta_sec

        target_cap = target_capacity if target_capacity is not None else 100.0
        projected_iso = None
        confidence = 0.85

        if v_last >= target_cap:
            # Already exhausted
            projected_iso = t_last.isoformat()
            confidence = 1.0
            assumptions = [f"Resource already at or exceeds target capacity ({v_last} >= {target_cap})."]
        elif growth_rate_per_sec > 0:
            remaining_headroom = max(0.0, target_cap - v_last)
            secs_to_exhaustion = remaining_headroom / growth_rate_per_sec
            from datetime import timedelta
            projected_dt = t_last + timedelta(seconds=secs_to_exhaustion)
            projected_iso = projected_dt.isoformat()
            assumptions = [f"Linear growth rate ({round(growth_rate_per_sec, 6)}/s) calculated across {len(sorted_samples)} observations over {round(delta_sec, 1)}s window."]
        else:
            confidence = 1.0  # Stable or shrinking
            projected_iso = None
            assumptions = ["Resource growth rate is zero or negative; no exhaustion projected within observation window."]

        fcst = CapacityForecast(
            forecast_id=forecast_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            target_metric=f"exhaustion_at_{target_cap}",
            current_value=v_last,
            projected_exhaustion_time_iso=projected_iso,
            growth_rate_per_sec=round(growth_rate_per_sec, 6),
            sample_count=len(sorted_samples),
            observation_window_sec=delta_sec,
            evidence_kind=ResourceEvidenceKind.DERIVED,
            confidence_score=confidence,
            assumptions=assumptions,
        )

        # Persist forecast
        conn.execute(
            """
            INSERT INTO capacity_forecasts (
                forecast_id, tenant_id, resource_type, target_metric, current_value,
                growth_rate_per_sec, projected_exhaustion_time, sample_count,
                observation_window_sec, evidence_kind, confidence_score, assumptions, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fcst.forecast_id,
                fcst.tenant_id,
                fcst.resource_type.value,
                fcst.target_metric,
                fcst.current_value,
                fcst.growth_rate_per_sec,
                fcst.projected_exhaustion_time_iso,
                fcst.sample_count,
                fcst.observation_window_sec,
                fcst.evidence_kind.value,
                fcst.confidence_score,
                json.dumps(fcst.assumptions),
                fcst.created_at_iso,
            ),
        )
        return fcst

    def evaluate_recommendations(
        self,
        tenant_id: str,
        observations: List[ResourceObservation],
        storage_breakdown: Optional[StorageBreakdown] = None,
    ) -> List[CapacityRecommendation]:
        """Evaluates risks and emits non-mutating operational recommendations."""
        recommendations: List[CapacityRecommendation] = []

        # Check storage disk pressure
        if storage_breakdown and storage_breakdown.total_bytes > 0:
            pct_used = (storage_breakdown.used_bytes / storage_breakdown.total_bytes) * 100.0
            if pct_used >= 95.0:
                recommendations.append(
                    CapacityRecommendation(
                        recommendation_id=f"rec-disk-{uuid.uuid4().hex[:8]}",
                        tenant_id=tenant_id,
                        resource_type=ResourceType.DISK,
                        risk_level=CapacityRiskLevel.CRITICAL,
                        message=f"Disk utilization is critical ({pct_used:.1f}% used).",
                        suggested_action="OPERATOR_PAUSE_OR_STAGING_PRUNE_REQUIRED",
                    )
                )
            elif pct_used >= 85.0:
                recommendations.append(
                    CapacityRecommendation(
                        recommendation_id=f"rec-disk-{uuid.uuid4().hex[:8]}",
                        tenant_id=tenant_id,
                        resource_type=ResourceType.DISK,
                        risk_level=CapacityRiskLevel.ELEVATED,
                        message=f"Disk utilization is elevated ({pct_used:.1f}% used).",
                        suggested_action="THROTTLE_OR_RETENTION_CLEANUP_RECOMMENDED",
                    )
                )

        # Check CDC backlog pressure
        for obs in observations:
            if obs.resource_type == ResourceType.CDC_BACKLOG and obs.value > 1000:
                recommendations.append(
                    CapacityRecommendation(
                        recommendation_id=f"rec-backlog-{uuid.uuid4().hex[:8]}",
                        tenant_id=tenant_id,
                        resource_type=ResourceType.CDC_BACKLOG,
                        risk_level=CapacityRiskLevel.ELEVATED,
                        message=f"CDC backlog is high ({int(obs.value)} pending events).",
                        suggested_action="SCALE_INGEST_THROTTLE_RECOMMENDED",
                    )
                )

        return recommendations

    def get_capacity_report(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        db_path: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
        staging_dir: Optional[str] = None,
    ) -> CapacityReport:
        """Generates comprehensive capacity report."""
        os_obs = self.sample_os_resources(tenant_id=tenant_id)
        cdc_obs = self.sample_cdc_and_backlog(tenant_id, conn)
        all_obs = os_obs + cdc_obs

        # Persist observations
        for o in all_obs:
            self.record_observation(o, conn)

        storage = self.sample_storage_breakdown(
            tenant_id=tenant_id,
            conn=conn,
            db_path=db_path,
            checkpoint_dir=checkpoint_dir,
            staging_dir=staging_dir,
        )
        recs = self.evaluate_recommendations(tenant_id, all_obs, storage)

        # Forecasts
        forecasts = [
            self.generate_forecast(tenant_id, ResourceType.DISK, conn),
            self.generate_forecast(tenant_id, ResourceType.CDC_BACKLOG, conn),
        ]

        # Overall risk level
        risk = CapacityRiskLevel.NOMINAL
        if any(r.risk_level == CapacityRiskLevel.CRITICAL for r in recs):
            risk = CapacityRiskLevel.CRITICAL
        elif any(r.risk_level == CapacityRiskLevel.ELEVATED for r in recs):
            risk = CapacityRiskLevel.ELEVATED

        return CapacityReport(
            tenant_id=tenant_id,
            risk_level=risk,
            observations=all_obs,
            storage_breakdown=storage,
            recommendations=recs,
            forecasts=forecasts,
        )
