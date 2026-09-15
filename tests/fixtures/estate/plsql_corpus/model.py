"""Shared PL/SQL corpus object model (build-spec §10-§13)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PLSQLObject:
    object_id: str            # "<KIND>.<SCHEMA>.<NAME>"
    kind: str                 # VIEW | MATERIALIZED_VIEW | SEQUENCE | TRIGGER | PROCEDURE | FUNCTION | PACKAGE_SPEC | PACKAGE_BODY
    schema: str
    name: str
    source_sql: str
    complexity_band: str       # simple | moderate | complex | very_complex
    constructs: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    parameters: list = field(default_factory=list)   # [{"name","mode","type"}]
    returns: str = None

    @property
    def source_loc(self) -> int:
        return self.source_sql.count("\n") + 1

    @property
    def source_bytes(self) -> int:
        return len(self.source_sql.encode("utf-8"))
