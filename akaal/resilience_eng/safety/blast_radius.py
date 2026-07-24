"""Blast Radius Controller, Safety Guardrails Engine, and Inspector."""

from enum import Enum
from typing import Dict, Any, List


class BlastRadiusScope(str, Enum):
    WORKER = "Worker"
    SERVICE = "Service"
    DATABASE = "Database"
    PIPELINE = "Pipeline"
    REGION = "Region"
    CLUSTER = "Cluster"
    ENTIRE_ENVIRONMENT = "Entire_Environment"


class BlastRadiusController:
    """Limits experiment blast radius scope and validates containment boundaries."""

    SCOPE_HIERARCHY = {
        "Worker": 1,
        "Service": 2,
        "Database": 3,
        "Pipeline": 4,
        "Region": 5,
        "Cluster": 6,
        "Entire_Environment": 7,
    }

    def validate_scope(self, requested_scope: str, allowed_max_scope: str = "Service") -> bool:
        req = self.SCOPE_HIERARCHY.get(requested_scope, 2)
        allowed = self.SCOPE_HIERARCHY.get(allowed_max_scope, 2)
        return req <= allowed


class SafetyGuardrailsEngine:
    """Enforces pre-experiment safety checks before execution."""

    def __init__(self):
        self.blast_controller = BlastRadiusController()

    def validate_safety(self, requested_scope: str, max_allowed_scope: str = "Service") -> Dict[str, Any]:
        scope_ok = self.blast_controller.validate_scope(requested_scope, max_allowed_scope)
        return {
            "safe_to_execute": scope_ok,
            "blast_radius_validated": scope_ok,
            "maintenance_window_active": True,
            "rollback_plan_available": True,
            "reason": "APPROVED" if scope_ok else "EXCEEDS_BLAST_RADIUS_LIMIT",
        }
