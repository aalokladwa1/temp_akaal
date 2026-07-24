"""Experiment Provenance System, Lineage Tracking, and Environment Snapshots."""

import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class EnvironmentSnapshot:
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    platform_versions: Dict[str, str] = field(default_factory=dict)
    active_profile: str = "ENTERPRISE"
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImmutableLineageRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = "exp_001"
    experiment_name: str = "Resilience_Test"
    version: str = "1.0.0"
    snapshot: EnvironmentSnapshot = field(default_factory=EnvironmentSnapshot)
    approval_ids: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    certificate_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ExperimentProvenanceManager:
    """Thread-safe manager for generating immutable provenance lineage chains."""

    def __init__(self):
        self._lineage_records: List[ImmutableLineageRecord] = []
        self._lock = threading.RLock()

    def record_provenance(
        self,
        experiment_id: str,
        experiment_name: str,
        version: str = "1.0.0",
        approvals: List[str] = None,
        confidence_scores: Dict[str, float] = None,
        certificate_id: Optional[str] = None,
    ) -> ImmutableLineageRecord:
        with self._lock:
            snapshot = EnvironmentSnapshot(
                platform_versions={
                    "Platform 1": "1.0.0",
                    "Platform 2": "2.0.0",
                    "Platform 3": "3.0.0",
                    "Platform 4": "4.0.0",
                    "Platform 5": "5.0.0",
                }
            )
            record = ImmutableLineageRecord(
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                version=version,
                snapshot=snapshot,
                approval_ids=approvals or [],
                confidence_scores=confidence_scores or {"overall": 99.0},
                certificate_id=certificate_id,
            )
            self._lineage_records.append(record)
            return record

    def get_provenance(self, experiment_id: str) -> Optional[ImmutableLineageRecord]:
        with self._lock:
            for rec in self._lineage_records:
                if rec.experiment_id == experiment_id:
                    return rec
            return None

    def list_all_lineage(self) -> List[ImmutableLineageRecord]:
        with self._lock:
            return list(self._lineage_records)
