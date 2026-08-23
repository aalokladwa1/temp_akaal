"""
akaalEngine.discovery.models.context
====================================
Discovery scope, depth, and context models.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence, Tuple
from types import MappingProxyType


class DiscoveryDepth(str, Enum):
    """Execution depth for discovery operations."""
    QUICK = "QUICK"                # Basic endpoint identity, version, catalog/schema list
    STANDARD = "STANDARD"          # Full schema inventory, columns, PKs, FKs, catalog estimates
    DEEP = "DEEP"                  # Programmables, partitions, subpartitions, LOB stats, topology, CDC prereqs
    COMPLIANCE = "COMPLIANCE"      # Full deep discovery plus exact permissions and security audits


@dataclass(frozen=True)
class DiscoveryScope:
    """
    Scope filter defining what namespaces and objects to include or exclude during discovery.
    Deeply immutable with efficient pattern matching.
    """
    catalogs: Tuple[str, ...] = field(default_factory=tuple)
    schemas: Tuple[str, ...] = field(default_factory=tuple)
    tables: Tuple[str, ...] = field(default_factory=tuple)
    include_patterns: Tuple[str, ...] = field(default_factory=tuple)
    exclude_patterns: Tuple[str, ...] = field(default_factory=tuple)
    object_types: Tuple[str, ...] = field(default_factory=tuple)
    prefixes: Tuple[str, ...] = field(default_factory=tuple)
    include_system_objects: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.catalogs, tuple):
            object.__setattr__(self, "catalogs", tuple(self.catalogs))
        if not isinstance(self.schemas, tuple):
            object.__setattr__(self, "schemas", tuple(self.schemas))
        if not isinstance(self.tables, tuple):
            object.__setattr__(self, "tables", tuple(self.tables))
        if not isinstance(self.include_patterns, tuple):
            object.__setattr__(self, "include_patterns", tuple(self.include_patterns))
        if not isinstance(self.exclude_patterns, tuple):
            object.__setattr__(self, "exclude_patterns", tuple(self.exclude_patterns))
        if not isinstance(self.object_types, tuple):
            object.__setattr__(self, "object_types", tuple(self.object_types))
        if not isinstance(self.prefixes, tuple):
            object.__setattr__(self, "prefixes", tuple(self.prefixes))

    def is_schema_allowed(self, schema_name: str) -> bool:
        """Determines if a schema is within the allowed scope."""
        if not schema_name:
            return True
        # Check explicit exclusions first
        for pat in self.exclude_patterns:
            if fnmatch.fnmatch(schema_name, pat):
                return False
        # If schemas list is specified, schema must match one
        if self.schemas:
            for s in self.schemas:
                if fnmatch.fnmatch(schema_name, s):
                    return True
            return False
        return True

    def is_table_allowed(self, schema_name: str, table_name: str) -> bool:
        """Determines if a table is within the allowed scope."""
        if not self.is_schema_allowed(schema_name):
            return False
        full_name = f"{schema_name}.{table_name}" if schema_name else table_name
        # Check explicit exclusions
        for pat in self.exclude_patterns:
            if fnmatch.fnmatch(table_name, pat) or fnmatch.fnmatch(full_name, pat):
                return False
        # Check explicit inclusions
        if self.include_patterns:
            matched = False
            for pat in self.include_patterns:
                if fnmatch.fnmatch(table_name, pat) or fnmatch.fnmatch(full_name, pat):
                    matched = True
                    break
            if not matched:
                return False
        # Check explicit tables list
        if self.tables:
            for t in self.tables:
                if fnmatch.fnmatch(table_name, t) or fnmatch.fnmatch(full_name, t):
                    return True
            return False
        return True

    def is_prefix_allowed(self, prefix: str) -> bool:
        """Determines if a storage prefix or topic pattern is allowed."""
        if not self.prefixes:
            return True
        for p in self.prefixes:
            if prefix.startswith(p) or fnmatch.fnmatch(prefix, p):
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalogs": list(self.catalogs),
            "schemas": list(self.schemas),
            "tables": list(self.tables),
            "include_patterns": list(self.include_patterns),
            "exclude_patterns": list(self.exclude_patterns),
            "object_types": list(self.object_types),
            "prefixes": list(self.prefixes),
            "include_system_objects": self.include_system_objects,
        }


@dataclass(frozen=True)
class DiscoveryContext:
    """
    Immutable execution context passed to discovery strategies and orchestration pipeline.
    """
    scope: DiscoveryScope = field(default_factory=DiscoveryScope)
    depth: DiscoveryDepth = DiscoveryDepth.STANDARD
    timeout_seconds: float = 60.0
    concurrency_limit: int = 4
    allow_exact_counts: bool = False
    sample_records: bool = False
    sample_size: int = 100
    max_sampled_tables: int = 10
    max_objects: int = 50000
    extra_options: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra_options, MappingProxyType):
            object.__setattr__(self, "extra_options", MappingProxyType(dict(self.extra_options)))

    def to_cache_identity_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope.to_dict(),
            "depth": self.depth.value,
            "allow_exact_counts": self.allow_exact_counts,
            "sample_records": self.sample_records,
            "sample_size": self.sample_size,
            "max_sampled_tables": self.max_sampled_tables,
            "extra_options": dict(self.extra_options),
        }
