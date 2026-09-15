"""Emits SQLite DDL from declarative TableSpecs and creates the physical tables.

SQLite has no schema namespaces usable the way Oracle/Postgres do, so each
schema.table pair is physically named "{SCHEMA}__{table}" in one SQLite
file. All identifiers are double-quoted uniformly so mixed-case / reserved
word / space-containing identifiers (COMPATIBILITY_LAB.Quoted_Case_Table)
round-trip correctly.
"""
from __future__ import annotations

import sqlite3

from config.schema_spec import SQLITE_AFFINITY, TableSpec


def physical_table_name(schema: str, table: str) -> str:
    return f"{schema}__{table}"


def qi(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def qualified_physical(table_spec: TableSpec) -> str:
    return qi(physical_table_name(table_spec.schema, table_spec.name))


def _column_ddl(c) -> str:
    affinity = SQLITE_AFFINITY[c.type]
    parts = [qi(c.name), affinity]
    if not c.nullable:
        parts.append("NOT NULL")
    if c.default is not None:
        parts.append(f"DEFAULT {c.default}")
    return " ".join(parts)


def create_table_sql(spec: TableSpec) -> str:
    lines = [_column_ddl(c) for c in spec.columns]
    if spec.primary_key:
        pk_cols = ", ".join(qi(c) for c in spec.primary_key)
        lines.append(f"PRIMARY KEY ({pk_cols})")
    for uq in spec.unique_constraints:
        uq_cols = ", ".join(qi(c) for c in uq)
        lines.append(f"UNIQUE ({uq_cols})")
    for fkspec in spec.foreign_keys:
        fk_cols = ", ".join(qi(c) for c in fkspec.columns)
        ref_schema, ref_table = fkspec.ref_table.split(".")
        ref_phys = qi(physical_table_name(ref_schema, ref_table))
        ref_cols = ", ".join(qi(c) for c in fkspec.ref_columns)
        lines.append(f"FOREIGN KEY ({fk_cols}) REFERENCES {ref_phys} ({ref_cols})")
    body = ",\n    ".join(lines)
    table_name = qi(physical_table_name(spec.schema, spec.name))
    return f"CREATE TABLE {table_name} (\n    {body}\n);"


def build_schema(conn: sqlite3.Connection, tables: list) -> None:
    conn.execute("PRAGMA foreign_keys = OFF;")  # off during bulk load, verified ON post-load
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    for spec in tables:
        conn.execute(create_table_sql(spec))
    conn.commit()
