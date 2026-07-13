#!/usr/bin/env python3
"""
Phase 3 Idempotency and GBAgent.migrate_table() test
===================================================
Proves that migrate_table() works paginated and is idempotent:
  (a) Runs migration of 250 rows to clean empty target -> PASS
  (b) Re-runs migrate_table() over existing target -> count stays 250 and PASS
  (c) Mutates a row in target, re-runs migrate_table() -> ON CONFLICT restores target to match source, PASS
"""

import asyncio
import os
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))

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

PG_USER     = os.environ.get('AKAAL_PG_USER', 'postgres')
PG_PASSWORD = os.environ.get('AKAAL_PG_PASSWORD', 'postgres')

SOURCE_CFG = Cfg('localhost', 5432, 'source_db', PG_USER, PG_PASSWORD)
TARGET_CFG = Cfg('localhost', 5432, 'target_db', PG_USER, PG_PASSWORD)

TABLE = 'customers'

# ── helpers ────────────────────────────────────────────────────────────────────

def _direct_conn(cfg):
    return psycopg2.connect(
        host=cfg.host, port=cfg.port, dbname=cfg.database_name,
        user=cfg.username, password=cfg.password,
    )

def clear_target():
    conn = _direct_conn(TARGET_CFG)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {TABLE} RESTART IDENTITY CASCADE")
    conn.close()

def modify_target_row_balance():
    """Modify lifetime_spend directly on target (e.g. set id=10 spend to 99999.99)."""
    conn = _direct_conn(TARGET_CFG)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE} SET lifetime_spend = 99999.99 WHERE id = 10")
    conn.close()
    print("  [direct DB] Set customer id=10 lifetime_spend = 99999.99 on target directly.")

def fetch_target_row_spend(customer_id=10):
    conn = _direct_conn(TARGET_CFG)
    with conn.cursor() as cur:
        cur.execute(f"SELECT lifetime_spend FROM {TABLE} WHERE id = %s", (customer_id,))
        res = cur.fetchone()
    conn.close()
    return res[0] if res else None

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
    # 0. Set up database tables (Phase 1 seed needs to run first or we assume it has run)
    # We will trigger a seed via phase1_migration_test's seed_source to make this script self-contained
    import importlib
    sys.path.insert(0, os.path.dirname(__file__))
    p1 = importlib.import_module("phase1_migration_test")
    p1.seed_source(SOURCE_CFG)
    clear_target()

    gb = GBAgent(_FakeState(), _FakeBus())
    val = ValidatorAgent(_FakeState(), _FakeBus())

    # ── (a) Clean migration run ──
    print("\n" + "=" * 62)
    print("(a) Clean Migration Run (Target empty) - Expect SUCCESS & PASS")
    print("=" * 62)
    res_a = await gb.migrate_table(SOURCE_CFG, TARGET_CFG, TABLE, batch_size=50)
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

    # ── (b) Re-run over populated target (simulate resume/duplicate attempt) ──
    print("\n" + "=" * 62)
    print("(b) Re-run migrate_table() over existing target - Expect count 250, PASS")
    print("=" * 62)
    res_b = await gb.migrate_table(SOURCE_CFG, TARGET_CFG, TABLE, batch_size=50)
    print(f"  migration status : {res_b['status']}")
    print(f"  rows migrated    : {res_b['rows_migrated']}")
    print(f"  batches          : {res_b['batches_processed']}")

    val_b = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(val_b))
    assert res_b['status'] == 'SUCCESS'
    assert val_b['status'] == 'PASS'
    assert val_b['target_row_count'] == 250  # Check it didn't double to 500!
    print("  => ASSERTION PASSED")

    # ── (c) Mutate row directly, verify checksum mismatch, re-migrate to fix ──
    print("\n" + "=" * 62)
    print("(c) Mutate target row, verify FAIL, run migrate_table() to fix -> PASS")
    print("=" * 62)
    modify_target_row_balance()
    
    # Verify it now fails validation
    val_fail = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print("  [validation pre-fix]")
    print(fmt(val_fail))
    assert val_fail['status'] == 'FAIL'
    assert val_fail['reason'] == 'checksum_mismatch'
    
    # Re-run migrate_table to fix
    print("  [running migrate_table to fix...]")
    res_c = await gb.migrate_table(SOURCE_CFG, TARGET_CFG, TABLE, batch_size=50)
    print(f"  migration status : {res_c['status']}")
    
    # Verify validation passes again
    val_c = await val.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print("  [validation post-fix]")
    print(fmt(val_c))
    assert val_c['status'] == 'PASS'
    
    # Verify the value was actually restored
    current_spend = fetch_target_row_spend(10)
    print(f"  Restored customer id=10 lifetime_spend in target to: {current_spend}")
    assert current_spend != 99999.99, "Expected target spend to be overwritten back to original value"
    print("  => ASSERTION PASSED")

    print("\n" + "=" * 62)
    print("ALL MIGRATION LOOP & IDEMPOTENCY TESTS PASSED.")
    print("=" * 62)


if __name__ == '__main__':
    asyncio.run(main())
