"""
Enterprise Failure Classification for Platform 6.
Enforces categorized exceptions for all Performance Engine errors.
"""

from enum import Enum


class PerformanceFailureType(str, Enum):
    MEMORY = "MEMORY"
    CPU = "CPU"
    STORAGE = "STORAGE"
    DATABASE = "DATABASE"
    NETWORK = "NETWORK"
    CONFIGURATION = "CONFIGURATION"
    CAPABILITY_UNSUPPORTED = "CAPABILITY_UNSUPPORTED"
    RULE_CONFLICT = "RULE_CONFLICT"
    ROLLBACK_FAILURE = "ROLLBACK_FAILURE"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"


class PerformanceEngineError(Exception):
    """Base exception for all Platform 6 performance errors."""
    def __init__(self, failure_type: PerformanceFailureType, message: str, details: dict = None) -> None:
        self.failure_type = failure_type
        self.message = message
        self.details = details or {}
        super().__init__(f"[{failure_type.value}] {message}")
