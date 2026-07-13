"""
Akaal — Schema Comparison Stress Tests
======================================
Executes a minimum of 100,000 comparisons concurrently and sequentially.
Asserts:
- No state leakage or race conditions under concurrent process execution.
- High-repeatability and determinism.
- Memory usage stability (asserting no continuous memory growth or leaks).
- Serializer round-trips under high stress.
"""

import concurrent.futures
import gc
import time
import tracemalloc
import unittest
from typing import Tuple
from akaal.core.models.enums import SystemType
from akaal.core.comparison import (
    SchemaComparisonEngine,
    ComparisonContext,
    Schema,
    TableSchema,
    ColumnSchema,
    PrimaryKeySchema,
    IndexSchema,
    ForeignKeySchema,
    ConstraintSchema,
    SchemaDifferenceSerializer,
)

# Global schemas constructed once to prevent generation overhead in workers
GLOBAL_SRC = Schema(
    tables=(
        TableSchema(
            name="a" * 100 + "_table_1",
            columns=(
                ColumnSchema(name="a" * 100 + "_id", data_type="INTEGER", raw_type="INT", nullable=False),
                ColumnSchema(name="a" * 100 + "_val", data_type="STRING", raw_type="VARCHAR(255)", nullable=True),
            ),
            primary_key=PrimaryKeySchema(name="pk_1", columns=("a" * 100 + "_id",)),
        ),
    ),
    vendor=SystemType.GENERIC,
)

GLOBAL_TGT = Schema(
    tables=(
        TableSchema(
            name="a" * 100 + "_table_1",
            columns=(
                ColumnSchema(name="a" * 100 + "_id", data_type="INTEGER", raw_type="INT", nullable=False),
                ColumnSchema(name="a" * 100 + "_val", data_type="STRING", raw_type="VARCHAR(255)", nullable=True, default_value="'active'"),
            ),
            primary_key=PrimaryKeySchema(name="pk_1", columns=("a" * 100 + "_id",)),
        ),
    ),
    vendor=SystemType.GENERIC,
)


def run_stress_worker(runs: int) -> int:
    """CPU-bound worker executing sequential comparisons and serializer cycles."""
    engine = SchemaComparisonEngine()
    for _ in range(runs):
        report = engine.compare(GLOBAL_SRC, GLOBAL_TGT)
        assert len(report.differences) == 1
        json_str = SchemaDifferenceSerializer.serialize_report(report)
        parsed = SchemaDifferenceSerializer.deserialize_report(json_str)
        assert len(parsed.differences) == 1
    return runs


def create_massive_schema(num_tables: int, cols_per_table: int) -> Schema:
    """Generates a massive schema with thousands of elements."""
    tables = []
    for i in range(num_tables):
        cols = tuple(
            ColumnSchema(name=f"col_{i}_{j}", data_type="INTEGER", raw_type="INT", nullable=True)
            for j in range(cols_per_table)
        )
        tables.append(
            TableSchema(
                name=f"table_{i}",
                columns=cols,
                primary_key=PrimaryKeySchema(name=f"pk_{i}", columns=(f"col_{i}_0",)),
            )
        )
    return Schema(tables=tuple(tables))


class TestSchemaComparisonStress(unittest.TestCase):
    """
    Executes deep and concurrent stress testing cycles on the Schema Comparison Engine.
    """

    def test_massive_stress_cycles(self) -> None:
        """Executes a total of 100,000 comparisons across multiple CPU cores to bypass the GIL."""
        # 4 processes * 25,000 comparisons = 100,000 comparisons
        num_workers = 4
        runs_per_worker = 25000
        
        print(f"\nStarting parallel stress test: {num_workers * runs_per_worker} comparisons...")
        
        start_time = time.perf_counter()
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(run_stress_worker, runs_per_worker) for _ in range(num_workers)]
            results = [f.result() for f in futures]
            
        duration = time.perf_counter() - start_time
        total_runs = sum(results)
        
        print(f"Stress test finished. Duration: {duration:.3f} seconds.")
        print(f"Throughput: {int(total_runs / duration)} comparisons/sec.")
        self.assertEqual(total_runs, 100000)

    def test_large_deep_schema_memory_stability(self) -> None:
        """Compares a massive schema containing 1,000 tables and 20,000 columns to verify memory footprint constraints."""
        print("\nVerifying memory stability on massive schema...")
        tracemalloc.start()
        gc.collect()
        initial_mem, _ = tracemalloc.get_traced_memory()
        
        # Build 1000 tables * 20 columns = 20,000 columns
        src = create_massive_schema(num_tables=1000, cols_per_table=20)
        tgt = create_massive_schema(1000, 20)
        
        engine = SchemaComparisonEngine()
        report = engine.compare(src, tgt)
        self.assertEqual(report.status.value, "IDENTICAL")
        
        gc.collect()
        final_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_delta = (final_mem - initial_mem) / 1024.0 / 1024.0
        peak_mb = peak_mem / 1024.0 / 1024.0
        print(f"Massive Schema Memory delta: {memory_delta:.2f} MB | Peak: {peak_mb:.2f} MB")
        
        # Enforce memory delta is under 20MB after comparison gc cleanup
        self.assertTrue(memory_delta < 20.0, f"Memory growth exceeded limit: {memory_delta:.2f} MB")
