"""Shared helpers for M1-M8 fixture builders."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from generator.schema_builder import build_schema, create_table_sql
from config.domains import ALL_TABLES

DATA_DIR = os.path.join(HERE, "data")
MODES_DIR = os.path.join(DATA_DIR, "modes")


def mode_dir(mode: str) -> str:
    d = os.path.join(MODES_DIR, mode)
    os.makedirs(d, exist_ok=True)
    return d


def build_empty_schema_shell(db_path: str, tables=None) -> str:
    """Creates a fresh SQLite file with the estate DDL applied and zero rows.
    Returns a deterministic DDL fingerprint (sha256 of the concatenated,
    sorted CREATE TABLE statements) so later tests can prove no unexpected
    DDL was executed against this target."""
    tables = tables if tables is not None else ALL_TABLES
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    build_schema(conn, tables)
    conn.close()

    ddl_statements = sorted(create_table_sql(t) for t in tables)
    ddl_fingerprint = hashlib.sha256("\n".join(ddl_statements).encode("utf-8")).hexdigest()
    return ddl_fingerprint


def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
