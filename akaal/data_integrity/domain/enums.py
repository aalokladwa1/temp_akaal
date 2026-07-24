"""
AKAAL Platform 8 — Enterprise Data Integrity Domain Enums.
"""

from enum import Enum


class IntegrityStatus(str, Enum):
    VALIDATED = "VALIDATED"
    INCONSISTENT = "INCONSISTENT"
    CHECKING = "CHECKING"
    FAILED = "FAILED"


class ConsistencyMode(str, Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    SNAPSHOT = "SNAPSHOT"
    TRANSACTIONAL = "TRANSACTIONAL"
