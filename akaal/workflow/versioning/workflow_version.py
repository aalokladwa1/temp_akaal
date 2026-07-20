"""Workflow Version Manager supporting concurrent v1/v2/v3 execution."""

import threading
from typing import Dict, Optional
from akaal.workflow.models.metadata import WorkflowManifest


class WorkflowVersionManager:
    """Manages concurrent workflow definition versions (v1, v2, v3)."""

    def __init__(self) -> None:
        self._manifests: Dict[str, Dict[str, WorkflowManifest]] = {}  # workflow_name -> {version: manifest}
        self._lock = threading.Lock()

    def register_version(self, manifest: WorkflowManifest) -> None:
        with self._lock:
            name = manifest.metadata.workflow_name
            ver = manifest.metadata.version
            if name not in self._manifests:
                self._manifests[name] = {}
            self._manifests[name][ver] = manifest

    def get_manifest(self, workflow_name: str, version: str = "1.0.0") -> Optional[WorkflowManifest]:
        with self._lock:
            return self._manifests.get(workflow_name, {}).get(version)
