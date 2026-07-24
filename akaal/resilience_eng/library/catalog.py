"""Resilience Experiment Library and Template Catalog."""

import threading
from typing import Dict, Any, List, Optional


class ExperimentTemplateCatalog:
    DEFAULT_TEMPLATES = [
        "Regional Outage",
        "Primary Database Failure",
        "Replica Failure",
        "Split Brain",
        "Slow Storage",
        "Storage Corruption",
        "High Latency WAN",
        "Worker Crash",
        "Dependency Timeout",
        "Service Cascade",
        "Message Queue Failure",
        "API Gateway Failure",
    ]


class ResilienceExperimentLibrary:
    """Enterprise Experiment Library storing reusable resilience scenarios."""

    def __init__(self):
        self._templates: Dict[str, Dict[str, Any]] = {
            t: {"name": t, "version": "1.0.0", "category": "ENTERPRISE"}
            for t in ExperimentTemplateCatalog.DEFAULT_TEMPLATES
        }
        self._lock = threading.RLock()

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._templates.get(name)

    def list_templates(self) -> List[str]:
        with self._lock:
            return list(self._templates.keys())
