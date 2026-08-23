"""
akaalEngine.schema.ddl.emitter
==============================
Target DDL emitter abstract contracts, structured statement containers, and multi-stage packaging.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
)
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalView
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import ConversionSafety, freeze_deep


class UnsupportedTargetEngineError(ValueError):
    """Raised when target database engine is unsupported or incapable of relational DDL generation."""
    pass


class DDLStage(str, Enum):
    """Deterministic stages for multi-stage DDL execution."""
    SCHEMAS = "SCHEMAS"
    TYPES = "TYPES"
    SEQUENCES = "SEQUENCES"
    TABLES = "TABLES"
    PRIMARY_KEYS = "PRIMARY_KEYS"
    INDEXES = "INDEXES"
    FOREIGN_KEYS = "FOREIGN_KEYS"
    VIEWS = "VIEWS"
    ROUTINES = "ROUTINES"
    TRIGGERS = "TRIGGERS"


@dataclass(frozen=True)
class StructuredDDLArtifact:
    """A single structured DDL statement with stage, safety, and dependency metadata."""
    object_type: str  # TABLE, PRIMARY_KEY, FOREIGN_KEY, UNIQUE_CONSTRAINT, CHECK_CONSTRAINT, INDEX, SEQUENCE, VIEW, ROUTINE, TRIGGER, UDT, SCHEMA
    object_name: str
    schema_name: str
    sql: str
    target_engine: str
    stage: DDLStage = DDLStage.TABLES
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    safety: ConversionSafety = ConversionSafety.EXACT
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    source_fingerprint: str = ""
    is_idempotent: bool = True
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.dependencies, tuple):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "extra", freeze_deep(self.extra))
        if not self.source_fingerprint and self.sql:
            h = hashlib.sha256(self.sql.strip().encode("utf-8")).hexdigest()
            object.__setattr__(self, "source_fingerprint", h)

    @property
    def qualified_name(self) -> str:
        if self.schema_name:
            return f"{self.schema_name}.{self.object_name}"
        return self.object_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "sql": self.sql,
            "target_engine": self.target_engine,
            "stage": self.stage.value,
            "dependencies": list(self.dependencies),
            "safety": self.safety.value,
            "warnings": list(self.warnings),
            "source_fingerprint": self.source_fingerprint,
            "is_idempotent": self.is_idempotent,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class StagedDDLPackage:
    """Container grouping all structured DDL statements segregated by execution stage."""
    target_engine: str
    artifacts: Tuple[StructuredDDLArtifact, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.artifacts, tuple):
            object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def get_stage_artifacts(self, stage: DDLStage) -> List[StructuredDDLArtifact]:
        return [a for a in self.artifacts if a.stage == stage]

    def get_all_sql(self) -> str:
        """Returns all DDL statements ordered by stage and statement."""
        order = [
            DDLStage.SCHEMAS,
            DDLStage.TYPES,
            DDLStage.SEQUENCES,
            DDLStage.TABLES,
            DDLStage.PRIMARY_KEYS,
            DDLStage.INDEXES,
            DDLStage.FOREIGN_KEYS,
            DDLStage.VIEWS,
            DDLStage.ROUTINES,
            DDLStage.TRIGGERS,
        ]
        statements = []
        for st in order:
            stage_items = self.get_stage_artifacts(st)
            if stage_items:
                statements.append(f"-- ========================================================")
                statements.append(f"-- STAGE: {st.value}")
                statements.append(f"-- ========================================================\n")
                for art in stage_items:
                    statements.append(art.sql)
                    if not art.sql.endswith(";"):
                        statements[-1] += ";"
                    statements.append("")
        return "\n".join(statements)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_engine": self.target_engine,
            "total_artifacts": len(self.artifacts),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "extra": dict(self.extra),
        }


class BaseTargetDDLEmitter(ABC):
    """Abstract base contract for provider-specific DDL emitters."""

    def __init__(self, target_engine: str):
        self.target_engine = target_engine.strip().upper()

    @abstractmethod
    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        """Emit DDL to create a namespace / schema."""
        pass

    @abstractmethod
    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        """Emit DDL for a table, splitting deferred FK constraints and indexes into proper stages."""
        pass

    @abstractmethod
    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        """Emit DDL for a view or materialized view."""
        pass

    @abstractmethod
    def emit_sequence_artifacts(self, sequence: CanonicalSequence) -> List[StructuredDDLArtifact]:
        """Emit DDL for an independent sequence."""
        pass

    @abstractmethod
    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        """Emit DDL for a User-Defined Type or enum."""
        pass

    def emit_routine_artifacts(
        self,
        routine: CanonicalRoutine,
        converted_sql: Optional[str] = None,
        conversion_state: Optional[str] = None,
        source_engine: str = "GENERIC",
    ) -> List[StructuredDDLArtifact]:
        """Emit DDL for a stored procedure or function with strict zero-leakage safety."""
        # 1. If successfully converted SQL is provided, emit it
        valid_states = ("TRANSPILED", "CONVERTED", "SYNTACTICALLY_CHECKED", "COMPATIBILITY_WRAPPED")
        if converted_sql and (conversion_state in valid_states or conversion_state is None):
            return [
                StructuredDDLArtifact(
                    object_type="ROUTINE",
                    object_name=routine.name,
                    schema_name=routine.schema_name,
                    sql=converted_sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.ROUTINES,
                    is_idempotent=True,
                )
            ]

        # 2. If target engine matches source engine (same vendor), native definition_sql is valid
        if source_engine.strip().upper() == self.target_engine.strip().upper() and routine.definition_sql:
            return [
                StructuredDDLArtifact(
                    object_type="ROUTINE",
                    object_name=routine.name,
                    schema_name=routine.schema_name,
                    sql=routine.definition_sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.ROUTINES,
                    is_idempotent=True,
                )
            ]

        # 3. Target engine differs and routine failed or requires manual rewrite:
        # DO NOT leak raw foreign SQL into executable target DDL! Emit safe commented diagnostic stub.
        if routine.definition_sql:
            state_str = conversion_state or "MANUAL_REWRITE_REQUIRED"
            commented_stub = (
                f"-- ==========================================================================\n"
                f"-- [MANUAL REWRITE REQUIRED]: Routine '{routine.qualified_name}'\n"
                f"-- Source Engine: {source_engine} -> Target Engine: {self.target_engine}\n"
                f"-- Conversion State: {state_str}\n"
                f"-- Incompatible procedural constructs require manual operator rewrite.\n"
                f"-- Original source SQL preserved below for reference:\n"
                f"-- ==========================================================================\n"
                f"/*\n{routine.definition_sql}\n*/\n"
            )
            return [
                StructuredDDLArtifact(
                    object_type="ROUTINE",
                    object_name=routine.name,
                    schema_name=routine.schema_name,
                    sql=commented_stub,
                    target_engine=self.target_engine,
                    stage=DDLStage.ROUTINES,
                    is_idempotent=False,
                    extra={"manual_rewrite_required": True, "conversion_state": state_str},
                )
            ]

        return []

    def emit_trigger_artifacts(
        self,
        trigger: CanonicalTrigger,
        converted_sql: Optional[str] = None,
        conversion_state: Optional[str] = None,
        source_engine: str = "GENERIC",
    ) -> List[StructuredDDLArtifact]:
        """Emit DDL for a trigger with strict zero-leakage safety."""
        valid_states = ("TRANSPILED", "CONVERTED", "SYNTACTICALLY_CHECKED", "COMPATIBILITY_WRAPPED")
        if converted_sql and (conversion_state in valid_states or conversion_state is None):
            return [
                StructuredDDLArtifact(
                    object_type="TRIGGER",
                    object_name=trigger.name,
                    schema_name=trigger.schema_name,
                    sql=converted_sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.TRIGGERS,
                    is_idempotent=True,
                )
            ]

        if source_engine.strip().upper() == self.target_engine.strip().upper() and trigger.definition_sql:
            return [
                StructuredDDLArtifact(
                    object_type="TRIGGER",
                    object_name=trigger.name,
                    schema_name=trigger.schema_name,
                    sql=trigger.definition_sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.TRIGGERS,
                    is_idempotent=True,
                )
            ]

        if trigger.definition_sql:
            state_str = conversion_state or "MANUAL_REWRITE_REQUIRED"
            commented_stub = (
                f"-- ==========================================================================\n"
                f"-- [MANUAL REWRITE REQUIRED]: Trigger '{trigger.name}' on '{trigger.schema_name}.{trigger.table_name}'\n"
                f"-- Source Engine: {source_engine} -> Target Engine: {self.target_engine}\n"
                f"-- Conversion State: {state_str}\n"
                f"-- Trigger definition requires manual adaptation for target engine.\n"
                f"-- Original source trigger SQL preserved below for reference:\n"
                f"-- ==========================================================================\n"
                f"/*\n{trigger.definition_sql}\n*/\n"
            )
            return [
                StructuredDDLArtifact(
                    object_type="TRIGGER",
                    object_name=trigger.name,
                    schema_name=trigger.schema_name,
                    sql=commented_stub,
                    target_engine=self.target_engine,
                    stage=DDLStage.TRIGGERS,
                    is_idempotent=False,
                    extra={"manual_rewrite_required": True, "conversion_state": state_str},
                )
            ]

        return []
