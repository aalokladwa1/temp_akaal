"""
AKAAL Platform 5 — Enterprise Live Schema Evolution Platform

Root package exposing Platform 5 facade, domain models, and exception hierarchy.
"""

from akaal.schema.facade.platform5 import SchemaEvolutionPlatformV5
from akaal.schema.domain.errors import (
    SchemaEvolutionError,
    TransactionError,
    ValidationError,
    ReplayError,
    RecoveryError,
    MetadataError,
    ConcurrencyError,
    JournalIntegrityError,
    VersionConflictError,
    IncompatibleSchemaError,
    ExecutionError,
)

__all__ = [
    "SchemaEvolutionPlatformV5",
    "SchemaEvolutionError",
    "TransactionError",
    "ValidationError",
    "ReplayError",
    "RecoveryError",
    "MetadataError",
    "ConcurrencyError",
    "JournalIntegrityError",
    "VersionConflictError",
    "IncompatibleSchemaError",
    "ExecutionError",
]
