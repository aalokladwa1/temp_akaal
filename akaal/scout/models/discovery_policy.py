"""
Akaal — Discovery Policy & Profile Models
=========================================
Configurable policies and reusable profiles for Scout discovery.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DiscoveryProfile(str, Enum):
    QUICK = "QUICK"          # Pre-sales fast discovery
    STANDARD = "STANDARD"    # Normal migration assessment
    DEEP = "DEEP"            # Enterprise migration planning
    COMPLIANCE = "COMPLIANCE"# Audit & governance profiling


@dataclass
class DiscoveryPolicy:
    """Configurable Discovery Policy controls discovery scope & caps."""
    include_schemas: List[str] = field(default_factory=list)
    exclude_schemas: List[str] = field(default_factory=list)
    include_tables: List[str] = field(default_factory=list)
    exclude_tables: List[str] = field(default_factory=list)
    include_object_types: List[str] = field(default_factory=list)
    exclude_object_types: List[str] = field(default_factory=list)

    skip_system_objects: bool = True
    skip_temporary_objects: bool = True
    skip_internal_objects: bool = True

    maximum_metadata_queries: int = 10000
    maximum_runtime_seconds: int = 3600
    maximum_parallelism: int = 4
    maximum_recursion_depth: int = 10

    stop_on_first_error: bool = False
    continue_on_partial_failure: bool = True
    read_only_required: bool = True

    collect_storage_statistics: bool = True
    collect_cluster_information: bool = True
    collect_capabilities: bool = True
    collect_object_inventory: bool = True

    policy_overrides: Dict[str, Any] = field(default_factory=dict)

    def is_schema_allowed(self, schema_name: str) -> bool:
        if self.skip_system_objects and schema_name.lower() in ("information_schema", "pg_catalog", "sys", "system", "mysql", "performance_schema"):
            return False
        if self.include_schemas and schema_name not in self.include_schemas:
            return False
        if self.exclude_schemas and schema_name in self.exclude_schemas:
            return False
        return True

    def is_table_allowed(self, table_name: str) -> bool:
        if self.skip_temporary_objects and ("temp" in table_name.lower() or "tmp" in table_name.lower()):
            return False
        if self.include_tables and table_name not in self.include_tables:
            return False
        if self.exclude_tables and table_name in self.exclude_tables:
            return False
        return True

    @classmethod
    def from_profile(cls, profile: DiscoveryProfile, **overrides: Any) -> "DiscoveryPolicy":
        """Generate policy preset based on DiscoveryProfile."""
        if profile == DiscoveryProfile.QUICK:
            policy = cls(
                collect_storage_statistics=False,
                collect_cluster_information=False,
                collect_object_inventory=False,
                maximum_metadata_queries=1000,
                maximum_runtime_seconds=300,
            )
        elif profile == DiscoveryProfile.STANDARD:
            policy = cls(
                collect_storage_statistics=True,
                collect_cluster_information=True,
                collect_object_inventory=True,
                maximum_metadata_queries=5000,
            )
        elif profile == DiscoveryProfile.DEEP:
            policy = cls(
                collect_storage_statistics=True,
                collect_cluster_information=True,
                collect_object_inventory=True,
                maximum_metadata_queries=50000,
                maximum_runtime_seconds=7200,
            )
        elif profile == DiscoveryProfile.COMPLIANCE:
            policy = cls(
                skip_system_objects=False,
                collect_storage_statistics=True,
                collect_cluster_information=True,
                collect_object_inventory=True,
                maximum_metadata_queries=20000,
            )
        else:
            policy = cls()

        for k, v in overrides.items():
            if hasattr(policy, k):
                setattr(policy, k, v)
        return policy
