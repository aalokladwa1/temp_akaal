#!/usr/bin/env python3
"""
Phase 2 ValidatorAgent.validate_table_data() test
==================================================
Proves that validate_table_data() correctly:
  (a) reports PASS when source == target (happy path from Phase 1 state)
  (b) reports FAIL / checksum_mismatch when one row is corrupted in target
  (c) reports FAIL / row_count_mismatch when one row is deleted from target
  (d) reports PASS again after target is restored to match source

Uses two real PostgreSQLAdapter instances; never touches OrchestratorV1.
"""

import asyncio
import os
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))

from akaal.agents.validator.validator_agent import ValidatorAgent

# ── stub minimal deps so ValidatorAgent can be constructed without full stack ──

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

# ── direct psycopg2 helpers (corruption / restore, NOT through Akaal) ──────────

def _direct_conn(cfg):
    return psycopg2.connect(
        host=cfg.host, port=cfg.port, dbname=cfg.database_name,
        user=cfg.username, password=cfg.password,
    )

def corrupt_one_email(cfg):
    """Change one customer's email on target — deliberate checksum corruption."""
    conn = _direct_conn(cfg)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TABLE} SET email = 'CORRUPTED@evil.com' "
            f"WHERE id = (SELECT MIN(id) FROM {TABLE})"
        )
        conn.commit()
    conn.close()

def delete_one_row(cfg):
    """Delete one row from target — deliberate row-count mismatch."""
    conn = _direct_conn(cfg)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(
            f"DELETE FROM {TABLE} "
            f"WHERE id = (SELECT MIN(id) FROM {TABLE})"
        )
        conn.commit()
    conn.close()

def restore_target_from_source():
    """Copy all source rows into target (truncate first) — restores matching state."""
    src_conn = _direct_conn(SOURCE_CFG)
    tgt_conn = _direct_conn(TARGET_CFG)
    src_conn.autocommit = False
    tgt_conn.autocommit = False
    with src_conn.cursor() as src_cur, tgt_conn.cursor() as tgt_cur:
        src_cur.execute(f"SELECT * FROM {TABLE} ORDER BY id")
        rows = src_cur.fetchall()
        src_cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position", (TABLE,))
        cols = [r[0] for r in src_cur.fetchall()]
        placeholders = ', '.join(['%s'] * len(cols))
        col_list = ', '.join([f'"{c}"' for c in cols])
        tgt_cur.execute(f"TRUNCATE {TABLE} RESTART IDENTITY CASCADE")
        import psycopg2.extras
        psycopg2.extras.execute_batch(
            tgt_cur,
            f"INSERT INTO {TABLE} ({col_list}) VALUES ({placeholders})",
            rows,
        )
        tgt_conn.commit()
    src_conn.close()
    tgt_conn.close()

# ── runner ─────────────────────────────────────────────────────────────────────

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
    agent = ValidatorAgent(_FakeState(), _FakeBus())

    failures = []

    # ── (a) happy path: source == target (Phase 1 already migrated this) ───────
    print("\n" + "=" * 62)
    print("(a) Happy path — source == target, expect PASS")
    print("=" * 62)
    result_a = await agent.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(result_a))
    assert result_a['status'] == 'PASS', f"(a) Expected PASS, got {result_a['status']}"
    assert result_a['reason'] is None, f"(a) Expected reason=None, got {result_a['reason']}"
    assert result_a['source_checksum'] == result_a['target_checksum']
    print("  => ASSERTION PASSED")

    # ── (b) corrupt one email in target → expect checksum_mismatch ────────────
    print("\n" + "=" * 62)
    print("(b) Corrupt one row email in target, expect FAIL/checksum_mismatch")
    print("=" * 62)
    corrupt_one_email(TARGET_CFG)
    result_b = await agent.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(result_b))
    assert result_b['status'] == 'FAIL', f"(b) Expected FAIL, got {result_b['status']}"
    assert result_b['reason'] == 'checksum_mismatch', f"(b) Expected checksum_mismatch, got {result_b['reason']}"
    assert result_b['source_checksum'] != result_b['target_checksum'], "(b) Checksums should differ"
    assert result_b['source_row_count'] == result_b['target_row_count'], "(b) Row counts should still match"
    print("  => ASSERTION PASSED")

    # ── (c) delete one row from target → expect row_count_mismatch ────────────
    print("\n" + "=" * 62)
    print("(c) Delete one row from target, expect FAIL/row_count_mismatch")
    print("=" * 62)
    # restore first so counts differ by exactly 1 (not compounding with (b))
    restore_target_from_source()
    delete_one_row(TARGET_CFG)
    result_c = await agent.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(result_c))
    assert result_c['status'] == 'FAIL', f"(c) Expected FAIL, got {result_c['status']}"
    assert result_c['reason'] == 'row_count_mismatch', f"(c) Expected row_count_mismatch, got {result_c['reason']}"
    assert result_c['source_row_count'] != result_c['target_row_count'], "(c) Counts should differ"
    assert result_c['source_checksum'] is None, "(c) Checksum should be None (skipped after count mismatch)"
    assert result_c['target_checksum'] is None, "(c) Checksum should be None (skipped after count mismatch)"
    print("  => ASSERTION PASSED")

    # ── (d) restore and confirm PASS again ────────────────────────────────────
    print("\n" + "=" * 62)
    print("(d) Restore target to match source, expect PASS again")
    print("=" * 62)
    restore_target_from_source()
    result_d = await agent.validate_table_data(SOURCE_CFG, TARGET_CFG, TABLE)
    print(fmt(result_d))
    assert result_d['status'] == 'PASS', f"(d) Expected PASS, got {result_d['status']}"
    assert result_d['source_checksum'] == result_d['target_checksum'], "(d) Checksums should match"
    print("  => ASSERTION PASSED")

    # ── summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("ALL FOUR CASES PASSED — Phase 2 validate_table_data verified.")
    print("=" * 62)

if __name__ == '__main__':
    asyncio.run(main())
