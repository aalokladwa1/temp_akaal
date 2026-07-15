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
from akaal.migration.reliability.reports import ReliabilityReport

class TestValidationPipeline(unittest.TestCase):
    def setUp(self):
        t_obj = Table(name="payments", schema="public")
        diff = ComparisonDifference(
            difference_id="diff_amt",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="payments",
            new_object=t_obj
        )
        report = SchemaComparisonReport("src", "tgt", differences=[diff])
        
        op = MigrationOperation(
            operation_id="op_amt",
            operation_type=OperationType.CREATE,
            target_object=t_obj,
            estimated_duration_ms=250.0
        )
        plan = MigrationPlan(
            planner_version="1.0",
            plan_version="1.0.0",
            generated_at="2026-07-15T00:00:00Z",
            source_database="src_db",
            target_database="tgt_db",
            operations=(op,)
        )
        
        self.context = ReliabilityContext(
            migration_plan=plan,
            schema_report=report,
            validation_config=ValidationConfiguration(strict_naming=True),
            capabilities=DialectCapabilities(supports_sequence_increment=True),
            execution_context=ExecutionContext().with_metadata("execution_id", "pipeline_exec_1"),
            runtime_metadata=RuntimeMetadata("pipeline_exec_1", time.time(), "QA", "dev")
        )

    def test_pipeline_workflow_execution(self):
        """Verify that ReliabilityPipeline executes and aggregates reports sequentially."""
        pipeline = ReliabilityPipeline()
        report = pipeline.run(self.context)
        
        self.assertIsInstance(report, ReliabilityReport)
        self.assertIsNotNone(report.validation)
        self.assertIsNotNone(report.health)
        self.assertIsNotNone(report.simulation)
        self.assertIsNotNone(report.certification)
        self.assertIsNotNone(report.rollback)
        self.assertIsNotNone(report.drift)

    def test_pipeline_step_configuration(self):
        """Verify pipeline selective step execution using enabled_steps filter."""
        pipeline = ReliabilityPipeline(enabled_steps=["validation", "simulation"])
        report = pipeline.run(self.context)
        
        self.assertIsNotNone(report.validation)
        self.assertIsNotNone(report.simulation)
        self.assertIsNone(report.health)
        self.assertIsNone(report.certification)
        self.assertIsNone(report.rollback)
        self.assertIsNone(report.drift)
