"""
Akaal — Risk Context
====================
Immutable execution context passed to analyzers and engines in Risk Platform.
Consumes ONLY CanonicalMigrationModel without direct Rulebook or database connection dependencies.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel


@dataclass(frozen=True)
class RiskContext:
    """Immutable execution context wrapping CanonicalMigrationModel."""
    canonical_model: CanonicalMigrationModel
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    configuration: Dict[str, Any] = field(default_factory=dict)
    simulation_mode: bool = False
    risk_schema_version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
