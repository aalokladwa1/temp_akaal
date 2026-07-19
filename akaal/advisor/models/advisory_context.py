"""
Akaal — Advisory Context
========================
Immutable environment and operational context for Advisor Platform analysis.
Enforces deep immutability via MappingProxyType for dictionary metadata.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class AdvisoryContext:
    """Immutable context metadata passed into Advisor Platform."""
    environment: str = "production"
    database_type: str = "generic"
    migration_type: str = "online"
    plan_id: str = ""
    target_tier: str = "enterprise"
    tags: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict:
        return {
            "environment": self.environment,
            "database_type": self.database_type,
            "migration_type": self.migration_type,
            "plan_id": self.plan_id,
            "target_tier": self.target_tier,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }
