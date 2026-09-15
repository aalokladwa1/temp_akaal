"""Declarative schema model for the simulated 1,000,000-row AKAAL estate.

This module defines the data structures used to describe schemas, tables,
columns, keys and constraints. It contains no data generation logic and no
row counts beyond what is declared here -- generation lives under
``tests/fixtures/estate/generator/``.

Datatype tags approximate Oracle source semantics (per build spec section 8).
They are mapped to SQLite storage affinities by ``generator/schema_builder.py``;
the *declared* semantic type is preserved in the source manifest so later
tests can reason about Oracle-shaped types even though SQLite is the physical
storage substrate for this simulated estate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ColType(str, Enum):
    # Exact numeric
    NUMBER = "NUMBER"
    NUMBER_38 = "NUMBER_38"
    NUMBER_P_S = "NUMBER_P_S"
    INTEGER = "INTEGER"
    # Approximate numeric
    FLOAT = "FLOAT"
    BINARY_FLOAT = "BINARY_FLOAT"
    BINARY_DOUBLE = "BINARY_DOUBLE"
    # Character
    VARCHAR2 = "VARCHAR2"
    NVARCHAR2 = "NVARCHAR2"
    CHAR = "CHAR"
    NCHAR = "NCHAR"
    # Temporal
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMP_TZ = "TIMESTAMP_TZ"
    TIMESTAMP_LTZ = "TIMESTAMP_LTZ"
    INTERVAL_YM = "INTERVAL_YM"
    INTERVAL_DS = "INTERVAL_DS"
    # Binary
    RAW = "RAW"
    # LOB
    CLOB = "CLOB"
    NCLOB = "NCLOB"
    BLOB = "BLOB"
    # Structured
    JSON = "JSON"
    XMLTYPE = "XMLTYPE"


# Storage affinity used in SQLite DDL for each declared type.
SQLITE_AFFINITY = {
    ColType.NUMBER: "NUMERIC",
    ColType.NUMBER_38: "TEXT",          # stored as exact decimal text, no float rounding
    ColType.NUMBER_P_S: "TEXT",         # stored as exact decimal text
    ColType.INTEGER: "INTEGER",
    ColType.FLOAT: "REAL",
    ColType.BINARY_FLOAT: "REAL",
    ColType.BINARY_DOUBLE: "REAL",
    ColType.VARCHAR2: "TEXT",
    ColType.NVARCHAR2: "TEXT",
    ColType.CHAR: "TEXT",
    ColType.NCHAR: "TEXT",
    ColType.DATE: "TEXT",               # ISO date text, deterministic
    ColType.TIMESTAMP: "TEXT",
    ColType.TIMESTAMP_TZ: "TEXT",
    ColType.TIMESTAMP_LTZ: "TEXT",
    ColType.INTERVAL_YM: "TEXT",
    ColType.INTERVAL_DS: "TEXT",
    ColType.RAW: "BLOB",
    ColType.CLOB: "TEXT",
    ColType.NCLOB: "TEXT",
    ColType.BLOB: "BLOB",
    ColType.JSON: "TEXT",
    ColType.XMLTYPE: "TEXT",
}

LOB_TYPES = {ColType.CLOB, ColType.NCLOB, ColType.BLOB}


class PKStyle(str, Enum):
    SURROGATE = "surrogate"        # single-column autoincrement-like integer
    NATURAL = "natural"            # single-column natural business key
    COMPOSITE = "composite"        # multi-column PK
    UUID_LIKE = "uuid_like"        # single-column deterministic UUID-shaped text
    ALPHANUMERIC = "alphanumeric"  # single-column structured alphanumeric code
    NONE = "none"                  # intentional no-PK table


class TableKind(str, Enum):
    POPULATED = "populated"
    EMPTY = "empty"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: ColType
    precision: Optional[int] = None
    scale: Optional[int] = None
    length: Optional[int] = None
    nullable: bool = True
    default: Optional[str] = None
    unicode_profile: Optional[str] = None
    lob_band: Optional[str] = None  # "tiny"|"small"|"medium"|"large"|"very_large" for LOB columns
    check: Optional[str] = None
    identity: bool = False          # sequence/identity-driven surrogate key


@dataclass(frozen=True)
class ForeignKeySpec:
    columns: tuple
    ref_table: str          # "SCHEMA.TABLE"
    ref_columns: tuple
    self_referencing: bool = False
    cross_schema: bool = False


@dataclass
class TableSpec:
    schema: str
    name: str
    columns: list
    primary_key: Optional[tuple] = None
    pk_style: PKStyle = PKStyle.SURROGATE
    foreign_keys: list = field(default_factory=list)
    unique_constraints: list = field(default_factory=list)
    row_count: int = 0
    kind: TableKind = TableKind.POPULATED

    @property
    def qualified_name(self) -> str:
        return f"{self.schema}.{self.name}"

    @property
    def has_pk(self) -> bool:
        return self.primary_key is not None and len(self.primary_key) > 0


def distribute(total: int, weights: list) -> list:
    """Split `total` into len(weights) non-negative integers proportional to
    `weights`, using the largest-remainder method so the sum is always
    exactly `total` (required for §4's exact-1,000,000 reconciliation)."""
    if not weights:
        return []
    wsum = sum(weights)
    if wsum == 0:
        base = [0] * len(weights)
        base[0] = total
        return base
    raw = [total * w / wsum for w in weights]
    floors = [int(x) for x in raw]
    remainder = total - sum(floors)
    fracs = sorted(range(len(weights)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in range(remainder):
        floors[fracs[i % len(fracs)]] += 1
    return floors


# ---- Reusable column templates -------------------------------------------------

def col(name, type_, **kw) -> ColumnSpec:
    return ColumnSpec(name=name, type=type_, **kw)


def surrogate_id(name: str = "id") -> ColumnSpec:
    return col(name, ColType.NUMBER_38, nullable=False, identity=True)


def uuid_like(name: str = "id") -> ColumnSpec:
    return col(name, ColType.CHAR, length=36, nullable=False)


def audit_columns() -> list:
    return [
        col("created_at", ColType.TIMESTAMP, nullable=False),
        col("updated_at", ColType.TIMESTAMP, nullable=True),
        col("created_by", ColType.VARCHAR2, length=64, nullable=True),
    ]


def money_column(name: str) -> ColumnSpec:
    return col(name, ColType.NUMBER_P_S, precision=18, scale=2, nullable=False)
