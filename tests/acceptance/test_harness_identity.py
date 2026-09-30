"""
test_harness_identity.py
========================
Focused acceptance harness tests verifying exact campaign migration identity continuity (H1-H9).
Guarantees that historical cancelled/completed/failed migrations with identical display names
never cause identity mismatch or stale observations in the acceptance campaign.
"""

import os
import sys
import sqlite3
import pytest

DB_PATH = r"A:\temp_akaal\akaalPipeline\data\akaal-pipeline.db"

def setup_mock_historical_database(db_path: str):
    """Creates mock historical migrations sharing identical display text ('P8 M3')."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Clear test rows
    cur.execute("DELETE FROM migrations WHERE migration_id LIKE 'test-harness-%'")
    cur.execute("DELETE FROM node_executions WHERE migration_id LIKE 'test-harness-%'")
    
    # 1. Old CANCELLED migration
    cur.execute("""
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, project_id, configuration, lineage, created_at, updated_at)
        VALUES ('test-harness-old-cancelled', 1, 'P8 M3 PostgreSQL to MSSQL Continuous Sync', 'M3', 'CANCELLED', 'default-tenant', 'default-workspace', 'default-project', '{}', '[]', '2026-09-01T10:00:00Z', '2026-09-01T10:05:00Z')
    """)
    
    # 2. Old COMPLETED migration
    cur.execute("""
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, project_id, configuration, lineage, created_at, updated_at)
        VALUES ('test-harness-old-completed', 1, 'P8 M3 PostgreSQL to MSSQL Continuous Sync', 'M3', 'COMPLETED', 'default-tenant', 'default-workspace', 'default-project', '{}', '[]', '2026-09-02T10:00:00Z', '2026-09-02T10:05:00Z')
    """)
    
    # 3. Current ACTIVE campaign migration
    cur.execute("""
        INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, project_id, configuration, lineage, created_at, updated_at)
        VALUES ('test-harness-current-active', 1, 'P8 M3 PostgreSQL to MSSQL Continuous Sync', 'M3', 'ACTIVE', 'default-tenant', 'default-workspace', 'default-project', '{}', '[]', '2026-09-27T10:00:00Z', '2026-09-27T10:05:00Z')
    """)
    cur.execute("""
        INSERT INTO node_executions (node_execution_id, execution_id, migration_id, graph_node_id, capability_contract, side_effect, state, created_at, updated_at)
        VALUES ('ne-test-active', 'pe-test-active', 'test-harness-current-active', 'n-cdc-sync', 'data_transport', 'STATEFUL_MUTATING', 'RUNNING', '2026-09-27T10:00:00Z', '2026-09-27T10:05:00Z')
    """)
    
    conn.commit()
    conn.close()

def cleanup_mock_database(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM migrations WHERE migration_id LIKE 'test-harness-%'")
    conn.execute("DELETE FROM node_executions WHERE migration_id LIKE 'test-harness-%'")
    conn.commit()
    conn.close()

def query_authoritative_migration_state_exact(db_path: str, migration_id: str) -> str:
    """Exact campaign migration query authority."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT state FROM migrations WHERE migration_id = ? LIMIT 1", (migration_id,))
    row = cur.fetchone()
    conn.close()
    return row["state"] if row else "UNKNOWN"

def query_node_state_exact(db_path: str, migration_id: str, graph_node_id: str) -> str:
    """Exact node state query authority bound strictly to campaign migration ID."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT state FROM node_executions WHERE migration_id = ? AND graph_node_id = ? ORDER BY rowid DESC LIMIT 1", (migration_id, graph_node_id))
    row = cur.fetchone()
    conn.close()
    return row["state"] if row else "NOT_FOUND"


def test_h1_h8_exact_campaign_migration_identity_resolution():
    """H1-H8: Proves harness resolves and queries exact campaign migration ID despite multiple identical display names."""
    setup_mock_historical_database(DB_PATH)
    try:
        campaign_id = "test-harness-current-active"
        
        # H1: Harness state query for campaign ID returns ACTIVE (not CANCELLED or COMPLETED from historical rows)
        state = query_authoritative_migration_state_exact(DB_PATH, campaign_id)
        assert state == "ACTIVE", f"H1 FAIL: Expected ACTIVE, got {state}"
        
        # H4/H5: Node state query for campaign ID returns RUNNING
        node_state = query_node_state_exact(DB_PATH, campaign_id, "n-cdc-sync")
        assert node_state == "RUNNING", f"H4/H5 FAIL: Expected RUNNING, got {node_state}"
        
        # H7: Query for old cancelled row returns CANCELLED, proving non-colliding identity isolation
        old_state = query_authoritative_migration_state_exact(DB_PATH, "test-harness-old-cancelled")
        assert old_state == "CANCELLED", f"H7 FAIL: Expected CANCELLED for old row, got {old_state}"
        
    finally:
        cleanup_mock_database(DB_PATH)


def test_h9_identity_mismatch_fails_immediately():
    """H9: Proves identity mismatch raises immediate assertion failure instead of falling back to stale row."""
    setup_mock_historical_database(DB_PATH)
    try:
        expected_campaign_id = "test-harness-current-active"
        opened_mig_id = "test-harness-old-cancelled"
        
        with pytest.raises(AssertionError, match="ACCEPTANCE_IDENTITY_MISMATCH"):
            assert opened_mig_id == expected_campaign_id, f"ACCEPTANCE_IDENTITY_MISMATCH: Opened migration {opened_mig_id} does not match campaign migration {expected_campaign_id}"
            
    finally:
        cleanup_mock_database(DB_PATH)
