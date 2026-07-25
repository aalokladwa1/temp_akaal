"""
Unit tests for Stage 8: High-Speed Database Expansion Engine.
"""

import pytest
from akaal.migration.execution.expansion_engine import DatabaseExpansionEngine
from akaal.core.models.enums import SystemType


def test_expansion_engine_partition_chunks():
    engine = DatabaseExpansionEngine()
    chunks = engine.compute_partition_chunks(
        table_name="orders",
        pk_column="order_id",
        min_id=1,
        max_id=1000,
        num_chunks=4,
    )

    assert len(chunks) == 4
    assert chunks[0].lower_bound == 1
    assert chunks[0].upper_bound == 250
    assert chunks[3].upper_bound == 1000
    assert "orders.order_id >= 1 AND orders.order_id <= 250" in chunks[0].where_clause


def test_expansion_engine_bulk_load_sql():
    pg_engine = DatabaseExpansionEngine(target_dialect=SystemType.POSTGRESQL)
    pg_sql = pg_engine.generate_bulk_load_command("orders", "/data/orders.csv")
    assert "COPY orders FROM '/data/orders.csv'" in pg_sql

    mysql_engine = DatabaseExpansionEngine(target_dialect=SystemType.MYSQL)
    mysql_sql = mysql_engine.generate_bulk_load_command("orders", "/data/orders.csv")
    assert "LOAD DATA INFILE '/data/orders.csv' INTO TABLE orders" in mysql_sql


def test_expansion_engine_benchmark_dataset_fk_integrity():
    engine = DatabaseExpansionEngine()
    schema = {"id": "INTEGER", "user_id": "INTEGER", "amount": "DECIMAL"}
    fk_refs = {"user_id": [10, 20, 30]}

    rows = engine.generate_benchmark_dataset(
        table_name="orders",
        schema_fields=schema,
        row_count=5,
        fk_references=fk_refs,
    )

    assert len(rows) == 5
    assert rows[0]["id"] == 1
    assert rows[0]["user_id"] == 10
    assert rows[1]["user_id"] == 20
    assert rows[3]["user_id"] == 10  # Wraps cleanly around valid FK domain list
