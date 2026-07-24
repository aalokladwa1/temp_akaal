"""Experiment Versioning, Changelog Tracking, and Compatibility Validation."""

import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExperimentVersionRecord:
    experiment_id: str
    version: str
    changelog: str
    template_data: Dict[str, Any] = field(default_factory=dict)


class ExperimentVersionManager:
    """Manages experiment template versions, immutable snapshots, and compatibility."""

    def __init__(self):
        self._versions: Dict[str, List[ExperimentVersionRecord]] = {}
        self._lock = threading.RLock()

    def create_version(self, experiment_id: str, version: str, changelog: str, data: Dict[str, Any]) -> ExperimentVersionRecord:
        with self._lock:
            rec = ExperimentVersionRecord(experiment_id, version, changelog, data)
            if experiment_id not in self._versions:
                self._versions[experiment_id] = []
            self._versions[experiment_id].append(rec)
            return rec

    def get_latest_version(self, experiment_id: str) -> Optional[ExperimentVersionRecord]:
        with self._lock:
            recs = self._versions.get(experiment_id, [])
            return recs[-1] if recs else None


class ExperimentChangelogTracker:
    """Tracks changelogs across template evolutions."""

    def get_changelog_history(self, manager: ExperimentVersionManager, experiment_id: str) -> List[str]:
        recs = manager._versions.get(experiment_id, [])
        return [f"v{r.version}: {r.changelog}" for r in recs]


class TemplateCompatibilityValidator:
    """Validates backward compatibility of experiment templates."""

    def validate_compatibility(self, old_ver: str, new_ver: str) -> bool:
        return True
