"""
Unit tests for Stage 4: Zero-Duplicate Migration Engine.
"""

import pytest
from akaal.migration.execution.deduplication import ZeroDuplicateMigrationEngine
from akaal.core.models.enums import SystemType


def test_zero_duplicate_source_filtering():
    engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.POSTGRESQL)
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 1, "name": "Alice"},  # Duplicate
        {"id": 3, "name": "Charlie"},
        {"id": 2, "name": "Bob"},    # Duplicate
    ]

    unique, filtered = engine.filter_batch_duplicates(records, pk_columns=["id"])
    assert len(unique) == 3
    assert filtered == 2
    assert [r["id"] for r in unique] == [1, 2, 3]


def test_zero_duplicate_upsert_statements():
    pg_engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.POSTGRESQL)
    pg_sql = pg_engine.generate_upsert_statement(
        table_name="users",
        columns=["id", "name", "email"],
        pk_columns=["id"],
    )
    assert "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email" in pg_sql

    mysql_engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.MYSQL)
    mysql_sql = mysql_engine.generate_upsert_statement(
        table_name="users",
        columns=["id", "name", "email"],
        pk_columns=["id"],
    )
    assert "ON DUPLICATE KEY UPDATE name = VALUES(name), email = VALUES(email)" in mysql_sql

    oracle_engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.ORACLE)
    oracle_sql = oracle_engine.generate_upsert_statement(
        table_name="users",
        columns=["id", "name", "email"],
        pk_columns=["id"],
    )
    assert "MERGE INTO users" in oracle_sql


def test_zero_duplicate_process_batch():
    engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.POSTGRESQL)
    records = [
        {"id": 10, "val": "x"},
        {"id": 10, "val": "x"},
    ]

    res = engine.process_batch(
        table_name="items",
        records=records,
        columns=["id", "val"],
        pk_columns=["id"],
    )

    assert res.total_input_rows == 2
    assert res.deduplicated_rows == 1
    assert res.duplicates_filtered == 1
    assert "ON CONFLICT (id)" in res.upsert_sql
