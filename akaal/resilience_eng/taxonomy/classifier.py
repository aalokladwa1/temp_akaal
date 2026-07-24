"""Failure Taxonomy Categories and Classifier."""

from enum import Enum
from typing import Dict, Any, List


class FailureCategory(str, Enum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    DATABASE = "DATABASE"
    STORAGE = "STORAGE"
    NETWORK = "NETWORK"
    SECURITY = "SECURITY"
    CONFIGURATION = "CONFIGURATION"
    PERFORMANCE = "PERFORMANCE"
    CAPACITY = "CAPACITY"
    DEPENDENCY = "DEPENDENCY"
    REPLICATION = "REPLICATION"
    VALIDATION = "VALIDATION"
    RECOVERY = "RECOVERY"
    APPLICATION = "APPLICATION"
    EXTERNAL_SERVICES = "EXTERNAL_SERVICES"
    HUMAN_ERROR = "HUMAN_ERROR"
    UNKNOWN = "UNKNOWN"


class FailureTaxonomyClassifier:
    """Classifies failures into standardized enterprise categories."""

    def classify_failure(self, error_message: str) -> FailureCategory:
        msg = error_message.lower()
        if "network" in msg or "socket" in msg or "wan" in msg:
            return FailureCategory.NETWORK
        elif "database" in msg or "sql" in msg or "postgres" in msg:
            return FailureCategory.DATABASE
        elif "disk" in msg or "storage" in msg or "io" in msg:
            return FailureCategory.STORAGE
        elif "timeout" in msg or "latency" in msg:
            return FailureCategory.PERFORMANCE
        elif "auth" in msg or "permission" in msg or "security" in msg:
            return FailureCategory.SECURITY
        else:
            return FailureCategory.INFRASTRUCTURE
