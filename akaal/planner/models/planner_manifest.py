"""
Akaal — Expanded Planner Manifest
==================================
Expanded manifest embedding versions for Planner Schema, Strategy, Registry, Risk Model,
Serialization, and model SHA-256 checksum.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class PlannerManifest:
    manifest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    planner_schema_version: str = "1.0.0"
    planning_strategy_version: str = "1.0.0"
    registry_version: str = "1.0.0"
    risk_model_version: str = "1.0.0"
    serialization_version: str = "1.0.0"
    planner_version: str = "planner-1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_checksum: str = ""

    def compute_model_checksum(self, model_dict: Dict[str, Any]) -> str:
        s = json.dumps(model_dict, default=str, sort_keys=True)
        self.model_checksum = hashlib.sha256(s.encode("utf-8")).hexdigest()
        return self.model_checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "planner_schema_version": self.planner_schema_version,
            "planning_strategy_version": self.planning_strategy_version,
            "registry_version": self.registry_version,
            "risk_model_version": self.risk_model_version,
            "serialization_version": self.serialization_version,
            "planner_version": self.planner_version,
            "timestamp": self.timestamp,
            "model_checksum": self.model_checksum,
        }
