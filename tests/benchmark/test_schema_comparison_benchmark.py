"""
Akaal — Schema Comparison Benchmarks
====================================
Validates memory allocation scaling and execution latency across varying schema sizes.
"""

import cProfile
import time
import tracemalloc
import unittest
from typing import Tuple
from akaal.core.comparison import (
    SchemaComparisonEngine,
    Schema,
    TableSchema,
    ColumnSchema,
    PrimaryKeySchema,
    IndexSchema,
    ComparisonContext,
)


def generate_synthetic_schema(num_tables: int, cols_per_table: int) -> Schema:
    """Generates an immutable synthetic Schema structure of a given size."""
    tables = []
    for i in range(num_tables):
        columns = []
        for j in range(cols_per_table):
            columns.append(
                ColumnSchema(
                    name=f"col_{j}",
                    data_type="INTEGER" if j == 0 else "STRING",
                    raw_type="INT" if j == 0 else "VARCHAR(255)",
                    nullable=(j > 0),
                    default_value="NULL" if j > 0 else None,
                )
            )
        tables.append(
            TableSchema(
                name=f"table_{i}",
                columns=tuple(columns),
                primary_key=PrimaryKeySchema(f"pk_table_{i}", ("col_0",)),
                indexes=(
                    IndexSchema(f"idx_table_{i}_col1", ("col_1",), False),
                ),
            )
        )
    return Schema(tables=tuple(tables))


class TestSchemaComparisonBenchmark(unittest.TestCase):
    """
    Benchmarks memory allocations and computational durations for the comparison engine.
    """

    def setUp(self) -> None:
        self.engine = SchemaComparisonEngine(ComparisonContext())

    def run_benchmark_on_size(self, num_tables: int, cols_per_table: int) -> Tuple[float, float]:
        """Runs comparison on synthetic schemas of a specific scale, returning (time_sec, peak_mem_kb)."""
        src = generate_synthetic_schema(num_tables, cols_per_table)
        
        # Introduce a few differences in target to ensure matching logic runs fully
        tables_list = list(src.tables)
        # Drop last table
        if len(tables_list) > 1:
            tables_list.pop()
        # Modify first table first column
        if tables_list:
            first_table = tables_list[0]
            new_columns = list(first_table.columns)
            new_columns[0] = ColumnSchema("id_modified", "INTEGER", "INT", False)
            tables_list[0] = TableSchema(
                name=first_table.name,
                columns=tuple(new_columns),
                primary_key=PrimaryKeySchema("pk_table_0", ("id_modified",)),
            )
        tgt = Schema(tables=tuple(tables_list))

        tracemalloc.start()
        start_time = time.perf_counter()
        
        # Execute comparison
        self.engine.compare(src, tgt)
        
        duration = time.perf_counter() - start_time
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_kb = peak / 1024.0
        return duration, peak_kb

    def test_performance_scaling(self) -> None:
        """Benchmarks scaling across 10, 100, and 1,000 tables."""
        scales = [10, 100, 1000]
        results = {}

        print("\n=== Akaal Schema Comparison Engine Performance Profile ===")
        for size in scales:
            duration, peak_mem = self.run_benchmark_on_size(size, cols_per_table=15)
            results[size] = (duration, peak_mem)
            print(
                f"Scale: {size:5d} tables | Duration: {duration * 1000:7.2f} ms | "
                f"Peak Memory: {peak_mem:8.2f} KB"
            )

        # Assert time complexity scales close to linear O(N log N)
        # 1000 tables should complete under 3.0 seconds on typical developer/CI machines
        self.assertTrue(results[1000][0] < 3.0, f"Comparison took too long: {results[1000][0]:.2f} seconds")
        # 1000 tables memory footprint should remain well within 50MB
        self.assertTrue(results[1000][1] < 50000, f"Memory usage exceeded limit: {results[1000][1]:.2f} KB")

    def test_engine_profile(self) -> None:
        """Profiles engine execution on 500 tables to capture internal hot-paths."""
        src = generate_synthetic_schema(500, 15)
        tgt = generate_synthetic_schema(480, 15)

        pr = cProfile.Profile()
        pr.enable()
        self.engine.compare(src, tgt)
        pr.disable()
        
        print("\n=== Profiling Hot-Paths ===")
        pr.print_stats(sort="cumulative")
