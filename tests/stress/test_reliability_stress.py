import unittest
import time
import concurrent.futures
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
from akaal.migration.reliability.utilities.hashing import generate_plan_hash

class TestReliabilityStress(unittest.TestCase):
    def test_concurrent_pipeline_runs(self):
        """Stress: Run 100 concurrent validation pipeline workflows on distinct threads."""
        pipeline = ReliabilityPipeline()

        def worker(idx: int):
            t_obj = Table(name=f"users_{idx}", schema="public")
            diff = ComparisonDifference(
                difference_id=f"diff_{idx}",
                diff_type="ADD",
                object_type=ObjectType.TABLE,
                object_name=f"users_{idx}",
                new_object=t_obj
            )
            report = SchemaComparisonReport("src", "tgt", differences=[diff])
            
            op = MigrationOperation(
                operation_id=f"op_{idx}",
                operation_type=OperationType.CREATE,
                target_object=t_obj,
                estimated_duration_ms=150.0
            )
            plan = MigrationPlan(
                planner_version="1.0",
                plan_version="1.0.0",
                generated_at="2026-07-15T00:00:00Z",
                source_database="src_db",
                target_database="tgt_db",
                operations=(op,)
            )
            
            context = ReliabilityContext(
                migration_plan=plan,
                schema_report=report,
                validation_config=ValidationConfiguration(strict_naming=True),
                capabilities=DialectCapabilities(supports_sequence_increment=True),
                execution_context=ExecutionContext().with_metadata("execution_id", f"stress_exec_{idx}"),
                runtime_metadata=RuntimeMetadata(f"stress_exec_{idx}", time.time(), "QA", "dev")
            )
            
            h = generate_plan_hash(plan)
            res = pipeline.run(context)
            return h, res

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

        self.assertEqual(len(results), 100)
        # Check plan hash is distinct per context
        hashes = [item[0] for item in results]
        self.assertEqual(len(set(hashes)), 100)
