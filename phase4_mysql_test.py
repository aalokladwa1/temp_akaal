#!/usr/bin/env python3
"""
Phase 4 MySQL adapter, GBAgent.migrate_table() and ValidatorAgent test
======================================================================
Proves that MySQLAdapter connects, queries catalog, paginates, writes idempotently via
ON DUPLICATE KEY UPDATE, and integrates cleanly with ValidatorAgent.validate_table_data() 
and GBAgent.migrate_table() without changing any code in those agents.

Cases:
  (a) Clean migration of 250 rows to empty target. Expect SUCCESS & PASS.
  (b) Re-run migrate_table() over existing target. Expect target count stays 250, PASS.
  (c) Directly corrupt target row balance via raw pymysql. Expect FAIL / checksum_mismatch.
  (d) Re-run migrate_table() to self-heal target back to original source values. Expect PASS.
  (e) Delete one row directly in target. Expect FAIL / row_count_mismatch.
"""

import asyncio
import os
import sys
import random
import string
from datetime import date, timedelta
from decimal import Decimal

import pymysql

sys.path.insert(0, os.path.dirname(__file__))

from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
from akaal.agents.gb.gb_agent import GBAgent
from akaal.agents.validator.validator_agent import ValidatorAgent

# ── stub minimal deps so GBAgent and ValidatorAgent can be constructed ──

class _FakeState:
    async def register_agent(self, *a): pass
    async def update_agent_status(self, *a): pass
    def get_agent_health(self, *a): return None

class _FakeBus:
    async def subscribe(self, *a): pass
    async def publish(self, *a): pass

# ── connection config ──────────────────────────────────────────────────────────

class Cfg:
    def __init__(self, host, port, database_name, username, password):
        self.host = host
        self.port = port
        self.database_name = database_name
        self.username = username
        self.password = password

SOURCE_CFG = Cfg('localhost', 3307, 'source_db', 'root', 'test')
TARGET_CFG = Cfg('localhost', 3308, 'target_db', 'root', 'test')

TABLE = 'customers'
NUM_ROWS = 250
BATCH_SIZE = 50

# ── helpers ────────────────────────────────────────────────────────────────────

def _direct_conn(cfg):
    return pymysql.connect(
        host=cfg.host, port=cfg.port, database=cfg.database_name,
        user=cfg.username, password=cfg.password,
        cursorclass=pymysql.cursors.DictCursor
    )

def rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def rand_email():
    return f"{rand_str(6)}@{rand_str(4)}.com"

def rand_date():
    return date(2018, 1, 1) + timedelta(days=random.randint(0, 2000))

CREATE_DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    first_name    VARCHAR(60)    NOT NULL,
    last_name     VARCHAR(60)    NOT NULL,
    email         VARCHAR(120)   NOT NULL UNIQUE,
    country       VARCHAR(60)    NOT NULL,
    signup_date   DATE           NOT NULL,
    lifetime_spend DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    is_active     TINYINT(1)     NOT NULL DEFAULT 1
);
"""

def seed_source():
    """Directly insert 250 rows into MySQL source database."""
    conn = _direct_conn(SOURCE_CFG)
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
        cur.execute(CREATE_DDL)
        
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
                random.choice([1, 0])
            ))
        
        insert_sql = f"""
            INSERT INTO {TABLE} 
            (first_name, last_name, email, country, signup_date, lifetime_spend, is_active) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.executemany(insert_sql, rows)
        conn.commit()
    conn.close()
    print(f"[seed] Seeded {NUM_ROWS} rows on MySQL source.")

def setup_empty_target():
    """Ensure target table is created and empty."""
    conn = _direct_conn(TARGET_CFG)
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
        cur.execute(CREATE_DDL)
        conn.commit()
    conn.close()
    print("[setup] MySQL target table initialized empty.")

def corrupt_target_row():
    """Mutate target row id=15 directly to create data drift."""
    conn = _direct_conn(TARGET_CFG)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE} SET lifetime_spend = 12345.67 WHERE id = 15")
        conn.commit()
    conn.close()
    print("  [direct MySQL] Set customer id=15 lifetime_spend = 12345.67 directly on target.")

def fetch_target_row_spend(customer_id=15):
    conn = _direct_conn(TARGET_CFG)
    with conn.cursor() as cur:
        cur.execute(f"SELECT lifetime_spend FROM {TABLE} WHERE id = %s", (customer_id,))
        row = cur.fetchone()
    conn.close()
    return row["lifetime_spend"] if row else None

def delete_target_row():
    """Delete a row directly from target to simulate a deletion drift."""
    conn = _direct_conn(TARGET_CFG)
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE} WHERE id = 15")
        conn.commit()
    conn.close()
    print("  [direct MySQL] Deleted customer id=15 directly on target.")

def fmt(result: dict) -> str:
    lines = [
        f"  status           : {result['status']}",
        f"  table            : {result['table']}",
        f"  source_row_count : {result['source_row_count']}",
        f"  target_row_count : {result['target_row_count']}",
        f"  source_checksum  : {result['source_checksum']}",
        f"  target_checksum  : {result['target_checksum']}",
        f"  reason           : {result['reason']}",
    ]
    return '\n'.join(lines)

async def main():
    # Setup databases
    seed_source()
    setup_empty_target()

    # Stub agents
    gb = GBAgent(_FakeState(), _FakeBus())
    val = ValidatorAgent(_FakeState(), _FakeBus())

    # ── (a) Clean Migration Run ──
    print("\n" + "=" * 62)
    print("(a) Clean MySQL Migration Run - Expect SUCCESS & PASS")
    print("=" * 62)
    res_a = await gb.migrate_table(SOURCE_CFG, TARGET_CFG, TABLE, batch_size=BATCH_SIZE)
    print(f"  migration status : {res_a['status']}")
    print(f"  rows migrated    : {res_a['rows_migrated']}")
    print(f"  batches          : {res_a['batches_processed']}")
    
    val_a = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(val_a))
    assert res_a['status'] == 'SUCCESS'
    assert val_a['status'] == 'PASS'
    assert val_a['source_row_count'] == 250
    assert val_a['target_row_count'] == 250
    print("  => ASSERTION PASSED")

    # ── (b) Re-run over target ──
    print("\n" + "=" * 62)
    print("(b) Re-run migrate_table() over existing target - Expect count 250, PASS")
    print("=" * 62)
    res_b = await gb.migrate_table(SOURCE_CFG, TARGET_CFG, TABLE, batch_size=BATCH_SIZE)
    print(f"  migration status : {res_b['status']}")
    print(f"  rows migrated    : {res_b['rows_migrated']}")
    print(f"  batches          : {res_b['batches_processed']}")

    val_b = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(val_b))
    assert res_b['status'] == 'SUCCESS'
    assert val_b['status'] == 'PASS'
    assert val_b['target_row_count'] == 250
    print("  => ASSERTION PASSED")

    # ── (c) Mutate row directly to cause checksum mismatch ──
    print("\n" + "=" * 62)
    print("(c) Mutate target row directly, expect FAIL / checksum_mismatch")
    print("=" * 62)
    corrupt_target_row()
    val_c = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(val_c))
    assert val_c['status'] == 'FAIL'
    assert val_c['reason'] == 'checksum_mismatch'
    print("  => ASSERTION PASSED")

    # ── (d) Re-migrate to self-heal ──
    print("\n" + "=" * 62)
    print("(d) Re-run migrate_table() to self-heal target - Expect PASS")
    print("=" * 62)
    res_d = await gb.migrate_table(SOURCE_CFG, TARGET_CFG, TABLE, batch_size=BATCH_SIZE)
    print(f"  migration status : {res_d['status']}")
    
    val_d = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(val_d))
    assert res_d['status'] == 'SUCCESS'
    assert val_d['status'] == 'PASS'
    
    restored_spend = fetch_target_row_spend(15)
    print(f"  Restored customer id=15 lifetime_spend on target to: {restored_spend}")
    assert restored_spend != Decimal('12345.67')
    print("  => ASSERTION PASSED")

    # ── (e) Delete target row directly ──
    print("\n" + "=" * 62)
    print("(e) Delete target row directly, expect FAIL / row_count_mismatch")
    print("=" * 62)
    delete_target_row()
    val_e = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(val_e))
    assert val_e['status'] == 'FAIL'
    assert val_e['reason'] == 'row_count_mismatch'
    print("  => ASSERTION PASSED")

    print("\n" + "=" * 62)
    print("ALL MYSQL MIGRATION, IDEMPOTENCY & VALIDATOR TESTS PASSED.")
    print("=" * 62)


if __name__ == '__main__':
    asyncio.run(main())
