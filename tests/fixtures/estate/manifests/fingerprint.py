"""Deterministic sha256 fingerprints for corruption detection (build-spec §27)."""
from __future__ import annotations

import hashlib
import sqlite3


def _canon(v) -> str:
    if v is None:
        return "\x00NULL\x00"
    if isinstance(v, (bytes, bytearray)):
        return "B:" + v.hex()
    return "V:" + str(v)


def row_fingerprint(values) -> str:
    joined = "\x1f".join(_canon(v) for v in values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def table_fingerprint(conn: sqlite3.Connection, physical_table: str, order_cols=None) -> dict:
    """Order-independent table fingerprint: sha256 of the sorted list of
    per-row fingerprints, plus row count. Works for PK and no-PK tables alike
    (no-PK tables use the full row content as their canonical identity, per
    build-spec §27's 'canonical row-fingerprint strategy' requirement)."""
    cur = conn.execute(f'SELECT * FROM "{physical_table}"')
    row_hashes = sorted(row_fingerprint(row) for row in cur.fetchall())
    combined = hashlib.sha256("\n".join(row_hashes).encode("utf-8")).hexdigest()
    return {"table": physical_table, "row_count": len(row_hashes), "fingerprint": combined}


def estate_fingerprint(table_fingerprints: dict) -> str:
    parts = [f"{name}:{info['fingerprint']}:{info['row_count']}" for name, info in sorted(table_fingerprints.items())]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
