#!/usr/bin/env python3
"""
Phase 1 migration test script.
- Creates 250-row customers table on pg_source (port 5432)
- Reads in 50-row batches via PostgreSQLAdapter.read_batch()
- Writes each batch to pg_target (port 5433) via PostgreSQLAdapter.write_batch()
- Verifies row counts match
- Computes compute_checksum() independently on both ends and asserts they match
"""

import asyncio
import os
import sys
import random
import string
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import psycopg2.extras
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter

# ── connection config ──────────────────────────────────────────────────────────

class Cfg:
    def __init__(self, host, port, database_name, username, password):
        self.host = host
        self.port = port
        self.database_name = database_name
        self.username = username
        self.password = password

PG_USER     = os.environ.get('AKAAL_PG_USER', 'postgres')
PG_PASSWORD = os.environ.get('AKAAL_PG_PASSWORD', 'postgres')

SOURCE_CFG = Cfg(host='localhost', port=5432, database_name='source_db',
                 username=PG_USER, password=PG_PASSWORD)
TARGET_CFG = Cfg(host='localhost', port=5432, database_name='target_db',
                 username=PG_USER, password=PG_PASSWORD)

TABLE      = 'customers'
NUM_ROWS   = 250
BATCH_SIZE = 50

# ── helpers ────────────────────────────────────────────────────────────────────

def rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def rand_email():
    return f"{rand_str(6)}@{rand_str(4)}.com"

def rand_date():
    return date(2018, 1, 1) + timedelta(days=random.randint(0, 2000))

CREATE_DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id            SERIAL PRIMARY KEY,
    first_name    VARCHAR(60)    NOT NULL,
    last_name     VARCHAR(60)    NOT NULL,
    email         VARCHAR(120)   NOT NULL UNIQUE,
    country       VARCHAR(60)    NOT NULL,
    signup_date   DATE           NOT NULL,
    lifetime_spend NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    is_active     BOOLEAN        NOT NULL DEFAULT TRUE
);
"""

def seed_source(cfg):
    conn = psycopg2.connect(host=cfg.host, port=cfg.port,
                            dbname=cfg.database_name,
                            user=cfg.username, password=cfg.password)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(CREATE_DDL)
        cur.execute(f"TRUNCATE {TABLE} RESTART IDENTITY CASCADE")
        countries = ['India', 'USA', 'UK', 'Germany', 'France', 'Brazil', 'Japan', 'Canada']
        rows = []
        for i in range(NUM_ROWS):
            rows.append((
                rand_str(7).capitalize(),
                rand_str(8).capitalize(),
                rand_email(),
                random.choice(countries),
                rand_date(),
                round(random.uniform(0, 9999.99), 2),
                random.choice([True, False]),
            ))
        psycopg2.extras.execute_batch(cur,
            f"INSERT INTO {TABLE} "
            "(first_name, last_name, email, country, signup_date, lifetime_spend, is_active) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            rows
        )
        conn.commit()
    conn.close()
    print(f"[seed] Inserted {NUM_ROWS} rows into source:{TABLE}")


def create_target_table(cfg):
    conn = psycopg2.connect(host=cfg.host, port=cfg.port,
                            dbname=cfg.database_name,
                            user=cfg.username, password=cfg.password)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(CREATE_DDL)
        cur.execute(f"TRUNCATE {TABLE} RESTART IDENTITY CASCADE")
        conn.commit()
    conn.close()
    print(f"[setup] Target table {TABLE} ready (empty).")


async def run_test():
    print("=" * 60)
    print("Phase 1 — PostgreSQL adapter real I/O test")
    print("=" * 60)

    seed_source(SOURCE_CFG)
    create_target_table(TARGET_CFG)

    src = PostgreSQLAdapter(SOURCE_CFG)
    tgt = PostgreSQLAdapter(TARGET_CFG)
    await src.connect()
    await tgt.connect()
    print("[connect] Both adapters connected.")

    total_written = 0
    offset = 0
    batch_num = 0
    while True:
        batch = await src.read_batch(TABLE, offset=offset, limit=BATCH_SIZE)
        if not batch:
            break
        batch_num += 1
        written = await tgt.write_batch(TABLE, batch)
        total_written += written
        print(f"[batch {batch_num}] read {len(batch)} rows @ offset {offset} -> wrote {written}")
        offset += BATCH_SIZE

    print(f"\n[migration] Total rows written: {total_written}")

    src_count = await src.get_row_count(TABLE)
    tgt_count = await tgt.get_row_count(TABLE)
    count_ok = src_count == tgt_count == NUM_ROWS
    print(f"\n[verify] source row count : {src_count}")
    print(f"[verify] target row count : {tgt_count}")
    print(f"[verify] row count match  : {'PASS' if count_ok else 'FAIL'}")

    src_checksum = await src.compute_checksum(TABLE)
    tgt_checksum = await tgt.compute_checksum(TABLE)
    checksum_ok = src_checksum == tgt_checksum
    print(f"\n[checksum] source : {src_checksum}")
    print(f"[checksum] target : {tgt_checksum}")
    print(f"[checksum] match  : {'PASS' if checksum_ok else 'FAIL'}")

    await src.close()
    await tgt.close()

    print("\n" + "=" * 60)
    if count_ok and checksum_ok:
        print("RESULT: ALL CHECKS PASSED - Phase 1 complete.")
    else:
        print("RESULT: ONE OR MORE CHECKS FAILED.")
        sys.exit(1)
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(run_test())
