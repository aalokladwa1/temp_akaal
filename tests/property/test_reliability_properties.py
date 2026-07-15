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
from akaal.migration.reliability.utilities.metrics import calculate_complexity

class TestReliabilityProperties(unittest.TestCase):
    def setUp(self):
        self.t_obj = Table(name="payments", schema="public")
        self.diff = ComparisonDifference(
            difference_id="diff_amt",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="payments",
            new_object=self.t_obj
        )
        self.report = SchemaComparisonReport("src", "tgt", differences=[self.diff])
        
        self.op = MigrationOperation(
            operation_id="op_amt",
            operation_type=OperationType.CREATE,
            target_object=self.t_obj,
            estimated_duration_ms=250.0
        )
        self.plan = MigrationPlan(
            planner_version="1.0",
            plan_version="1.0.0",
            generated_at="2026-07-15T00:00:00Z",
            source_database="src_db",
            target_database="tgt_db",
            operations=(self.op,)
        )
        
        self.context = ReliabilityContext(
            migration_plan=self.plan,
            schema_report=self.report,
            validation_config=ValidationConfiguration(strict_naming=True),
            capabilities=DialectCapabilities(supports_sequence_increment=True),
            execution_context=ExecutionContext().with_metadata("execution_id", "prop_exec_1"),
            runtime_metadata=RuntimeMetadata("prop_exec_1", time.time(), "QA", "dev")
        )

    def test_report_immutability(self):
        """Property: Reports must be frozen and throw exceptions on mutation attempts."""
        pipeline = ReliabilityPipeline()
        report = pipeline.run(self.context)
        
        with self.assertRaises(Exception):
            report.validation.success = False  # type: ignore

    def test_pipeline_determinism(self):
        """Property: Running the validation pipeline on identical plans must yield identical scores."""
        pipeline = ReliabilityPipeline()
        report_1 = pipeline.run(self.context)
        
        # Reset context diagnostics
        self.context.diagnostics.clear()
        report_2 = pipeline.run(self.context)
        
        self.assertEqual(report_1.overall_risk.confidence_score, report_2.overall_risk.confidence_score)
        self.assertEqual(report_1.overall_risk.risk_score, report_2.overall_risk.risk_score)
        self.assertEqual(report_1.overall_risk.risk_level, report_2.overall_risk.risk_level)

    def test_complexity_bounds(self):
        """Property: Plan complexity metrics must fall within [0.0, 10.0] range."""
        complexity = calculate_complexity(self.plan)
        self.assertTrue(0.0 <= complexity <= 10.0)

        # Scale with 100 operations to check bounds safety
        ops = tuple([self.op] * 100)
        large_plan = MigrationPlan(
            planner_version="1.0",
            plan_version="2.0.0",
            generated_at="2026-07-15T00:00:00Z",
            source_database="src_db",
            target_database="tgt_db",
            operations=ops
        )
        large_complexity = calculate_complexity(large_plan)
        self.assertEqual(large_complexity, 10.0)
