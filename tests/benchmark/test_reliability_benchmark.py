import unittest
import time
from akaal.migration.models import (
    ObjectType,
    OperationType,
    Table,
    Column,
    MigrationOperation,
    MigrationPlan,
    SchemaComparisonReport,
    ComparisonDifference,
    ExecutionContext
)
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities
from akaal.migration.reliability.context import ReliabilityContext, ValidationConfiguration, RuntimeMetadata
from akaal.migration.reliability.pipeline import ReliabilityPipeline

class TestReliabilityBenchmark(unittest.TestCase):
    def test_pipeline_benchmark_scaling(self):
        """Benchmark: Profile pipeline run-times across 100, 500, 1000, 5000 operation scales."""
        pipeline = ReliabilityPipeline()
        scales = [100, 500, 1000, 5000]

        print("\n=== Reliability Pipeline Performance Benchmark ===")
        for scale in scales:
            differences = []
            operations = []
            
            t_obj = Table(name="perf_table", schema="public")
            differences.append(
                ComparisonDifference(
                    difference_id="diff_t",
                    diff_type="ADD",
                    object_type=ObjectType.TABLE,
                    object_name="perf_table",
                    new_object=t_obj
                )
            )
            operations.append(
                MigrationOperation(
                    operation_id="op_t",
                    operation_type=OperationType.CREATE,
                    target_object=t_obj
                )
            )

            for i in range(1, scale):
                col = Column(name=f"col_{i}", schema="public", data_type="VARCHAR(255)")
                col.attributes["table_name"] = "perf_table"
                differences.append(
                    ComparisonDifference(
                        difference_id=f"diff_c_{i}",
                        diff_type="ADD",
                        object_type=ObjectType.COLUMN,
                        object_name=f"perf_table.col_{i}",
                        new_object=col
                    )
                )
                operations.append(
                    MigrationOperation(
                        operation_id=f"op_c_{i}",
                        operation_type=OperationType.CREATE,
                        target_object=col
                    )
                )

            report = SchemaComparisonReport("src", "tgt", differences=differences)
            plan = MigrationPlan(
                planner_version="1.0",
                plan_version="1.0.0",
                generated_at="2026-07-15T00:00:00Z",
                source_database="src_db",
                target_database="tgt_db",
                operations=tuple(operations)
            )
            
            context = ReliabilityContext(
                migration_plan=plan,
                schema_report=report,
                validation_config=ValidationConfiguration(strict_naming=True),
                capabilities=DialectCapabilities(supports_sequence_increment=True),
                execution_context=ExecutionContext().with_metadata("execution_id", f"bench_exec_{scale}"),
                runtime_metadata=RuntimeMetadata(f"bench_exec_{scale}", time.time(), "QA", "dev")
            )

            start = time.perf_counter()
            res = pipeline.run(context)
            duration_ms = (time.perf_counter() - start) * 1000.0
            throughput = scale / (duration_ms / 1000.0)

            print(f"  Scale: {scale:4d} ops | Time: {duration_ms:8.2f} ms | Throughput: {throughput:10.2f} ops/sec")
            self.assertIsNotNone(res)
