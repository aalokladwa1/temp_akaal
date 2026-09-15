"""Batched, memory-bounded population of the 1,000,000-row baseline.

Tables are populated in FK-dependency order (topological sort). For each
table, PK values and FK references are generated deterministically; FK
values are drawn from an in-memory pool of previously-generated parent
keys (bounded: at most one entry per already-generated row, a few MB total
across the whole estate -- not a concern at this scale). LOB columns are
generated, hashed and inserted one at a time via generator/lob_factory.py
so peak memory is bounded by the single largest LOB currently being
written, not by the estate as a whole (build-spec §30).
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict, deque

from config.schema_spec import ColType, LOB_TYPES, PKStyle, TableSpec
from config.domains import ALL_TABLES
from generator.schema_builder import physical_table_name, qi
from generator.seed import rng_for
from generator.value_factory import generate_scalar_value, ascii_text
from generator.lob_factory import (
    LobAllocator, generate_clob_payload, generate_blob_payload, sha256_hex,
)

BATCH_SIZE = 2000
NULL_PROB_DEFAULT = 0.15


def topo_order(tables: list) -> list:
    by_name = {t.qualified_name: t for t in tables}
    deps = defaultdict(set)
    for t in tables:
        for fkspec in t.foreign_keys:
            if fkspec.ref_table != t.qualified_name and fkspec.ref_table in by_name:
                deps[t.qualified_name].add(fkspec.ref_table)
    indegree = {name: len(deps[name]) for name in by_name}
    queue = deque(sorted(n for n, d in indegree.items() if d == 0))
    order = []
    remaining = dict(indegree)
    dependents = defaultdict(list)
    for name, dep_set in deps.items():
        for d in dep_set:
            dependents[d].append(name)
    while queue:
        n = queue.popleft()
        order.append(n)
        for dep in sorted(dependents.get(n, [])):
            remaining[dep] -= 1
            if remaining[dep] == 0:
                queue.append(dep)
    if len(order) != len(tables):
        missing = set(by_name) - set(order)
        raise RuntimeError(f"cyclic non-self-referencing FK dependency among: {missing}")
    return [by_name[n] for n in order]


def _natural_key(prefix: str, i: int) -> str:
    return f"{prefix}-{i:08d}"


def _table_prefix(name: str) -> str:
    return "".join(w[0] for w in name.split("_")).upper()[:6] or "T"


def build_baseline(conn: sqlite3.Connection, tables=None, progress=None) -> dict:
    tables = tables if tables is not None else ALL_TABLES
    ordered = topo_order(tables)

    pk_pool: dict = {}          # qualified_name -> list of key values (or tuples for composite)
    lob_hashes: dict = defaultdict(list)  # band -> list of {table, column, row_key, sha256, bytes}

    total_lob_slots = sum(
        t.row_count for t in tables for c in t.columns if c.type in LOB_TYPES
    )
    lob_allocator = LobAllocator(total_lob_slots)

    stats = {"tables": {}, "total_rows": 0}

    for spec in ordered:
        phys = physical_table_name(spec.schema, spec.name)
        col_names = [c.name for c in spec.columns]
        insert_sql = f'INSERT INTO {qi(phys)} ({", ".join(qi(n) for n in col_names)}) VALUES ({", ".join(["?"] * len(col_names))})'

        single_fk_cols = {}
        for fkspec in spec.foreign_keys:
            if len(fkspec.columns) == 1:
                single_fk_cols[fkspec.columns[0]] = fkspec

        pk_cols = set(spec.primary_key) if spec.primary_key else set()
        # Any textual column participating in ANY unique constraint (single- or multi-column)
        # is made row-index-unique so the whole tuple is guaranteed unique regardless of the
        # other components' distribution (avoids relying on a small random-text vocabulary).
        unique_single_cols = {col for uq in spec.unique_constraints for col in uq}
        fk_col_names = {fkspec.columns[0] for fkspec in spec.foreign_keys if len(fkspec.columns) == 1}
        unique_single_cols -= fk_col_names
        unique_single_cols -= pk_cols
        generated_keys = []
        seen_pk = set()
        prefix = _table_prefix(spec.name)
        surrogate_counter = 1

        rng = rng_for(spec.qualified_name, "table")
        batch = []
        row_count = spec.row_count

        for i in range(row_count):
            row_rng = rng_for(spec.qualified_name, i)
            row = {}
            for c in spec.columns:
                if c.type in LOB_TYPES:
                    band = lob_allocator.next_band()
                    if band is None:
                        row[c.name] = None
                        continue
                    if c.type == ColType.BLOB:
                        payload = generate_blob_payload(row_rng, band)
                    else:
                        payload = generate_clob_payload(row_rng, band)
                    h = sha256_hex(payload)
                    lob_hashes[band].append({
                        "table": spec.qualified_name, "column": c.name, "row_index": i,
                        "sha256": h, "byte_length": len(payload) if isinstance(payload, (bytes, bytearray)) else len(payload.encode("utf-8")),
                    })
                    row[c.name] = payload
                    continue

                if c.name in single_fk_cols:
                    fkspec = single_fk_cols[c.name]
                    self_ref = fkspec.self_referencing
                    if self_ref:
                        pool_source = generated_keys
                    else:
                        pool_source = pk_pool.get(fkspec.ref_table, [])
                    nullable = c.nullable
                    if self_ref and (not pool_source or row_rng.random() < 0.2) and nullable:
                        row[c.name] = None
                    elif not pool_source:
                        row[c.name] = None if nullable else (row_rng.choice(pk_pool.get(fkspec.ref_table, [1])) if pk_pool.get(fkspec.ref_table) else 1)
                    else:
                        row[c.name] = row_rng.choice(pool_source)
                    continue

                if spec.primary_key and c.name in pk_cols and spec.pk_style in (PKStyle.SURROGATE,) and len(spec.primary_key) == 1:
                    row[c.name] = surrogate_counter
                    continue
                if spec.primary_key and c.name in pk_cols and spec.pk_style == PKStyle.UUID_LIKE and len(spec.primary_key) == 1:
                    h = rng_for(spec.qualified_name, "uuid", i).getrandbits(128).to_bytes(16, "big").hex()
                    row[c.name] = f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
                    continue
                if spec.primary_key and c.name in pk_cols and spec.pk_style in (PKStyle.NATURAL, PKStyle.ALPHANUMERIC) and len(spec.primary_key) == 1:
                    row[c.name] = _natural_key(prefix, i)
                    continue

                if c.name in unique_single_cols and c.type in (ColType.VARCHAR2, ColType.NVARCHAR2, ColType.CHAR, ColType.NCHAR):
                    if c.name == "email":
                        row[c.name] = f"user{i:08d}@example.test"
                    else:
                        tag = "".join(w[0] for w in c.name.split("_")).upper()[:4] or "U"
                        row[c.name] = f"{tag}-{i:08d}"
                    continue

                if c.nullable and c.default is None and c.name not in unique_single_cols and row_rng.random() < NULL_PROB_DEFAULT and c.name not in pk_cols:
                    row[c.name] = None
                    continue

                row[c.name] = generate_scalar_value(row_rng, c)

            if spec.primary_key and len(spec.primary_key) > 1:
                attempts = 0
                while attempts < 25:
                    key_tuple = tuple(row[k] for k in spec.primary_key)
                    if key_tuple not in seen_pk:
                        seen_pk.add(key_tuple)
                        break
                    for c in spec.columns:
                        if c.name in spec.primary_key and c.name not in single_fk_cols:
                            row[c.name] = generate_scalar_value(rng_for(spec.qualified_name, i, attempts), c)
                        elif c.name in spec.primary_key and c.name in single_fk_cols:
                            fkspec = single_fk_cols[c.name]
                            pool_source = generated_keys if fkspec.self_referencing else pk_pool.get(fkspec.ref_table, [])
                            if pool_source:
                                row[c.name] = rng_for(spec.qualified_name, i, attempts, c.name).choice(pool_source)
                    attempts += 1
                key_tuple = tuple(row[k] for k in spec.primary_key)
                seen_pk.add(key_tuple)
                generated_keys.append(key_tuple)
            elif spec.primary_key and len(spec.primary_key) == 1:
                pk_col = spec.primary_key[0]
                generated_keys.append(row[pk_col])

            batch.append(tuple(row[n] for n in col_names))
            if spec.pk_style == PKStyle.SURROGATE and len(spec.primary_key or ()) == 1:
                surrogate_counter += 1

            if len(batch) >= BATCH_SIZE:
                conn.executemany(insert_sql, batch)
                batch = []

        if batch:
            conn.executemany(insert_sql, batch)
        conn.commit()

        if spec.primary_key:
            pk_pool[spec.qualified_name] = generated_keys

        stats["tables"][spec.qualified_name] = row_count
        stats["total_rows"] += row_count
        if progress:
            progress(spec.qualified_name, row_count)

    stats["lob_band_counts"] = {b: len(v) for b, v in lob_hashes.items()}
    stats["lob_hashes"] = dict(lob_hashes)
    return stats
