import unittest
import time
from typing import List
from akaal.migration.models import (
    ObjectType,
    OperationType,
    Table,
    Column,
    Constraint,
    Index,
    MigrationOperation,
    MigrationPlan,
    SchemaComparisonReport,
    ComparisonDifference,
    ExecutionContext
)
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities
from akaal.migration.reliability.context import ReliabilityContext, ValidationConfiguration, RuntimeMetadata
from akaal.migration.reliability.models.risk import RiskLevel, RiskAssessment
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.reports import ReliabilityReport
from akaal.migration.reliability.plugins import PluginRegistry, BaseValidatorPlugin
from akaal.migration.reliability.registry import ReliabilityEngineRegistry
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.validation import ValidationEngine, ObjectValidatorRegistry
from akaal.migration.reliability.health import HealthPrecheckEngine
from akaal.migration.reliability.simulation import DryRunSimulationEngine
from akaal.migration.reliability.certification import CertificationEngine
from akaal.migration.reliability.rollback import RollbackEngine
from akaal.migration.reliability.drift import DriftDetector

class MockValidatorPlugin(BaseValidatorPlugin):
    def validate(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        return [ReliabilityDiagnostic("Mock issue", "WARNING", "PLUGIN", "Fix it")]

class TestReliabilityPlatform(unittest.TestCase):
    def setUp(self):
        PluginRegistry.clear()
        
        # Build valid schema components
        col_id = Column(name="id", schema="public", data_type="INT")
        col_id.attributes["table_name"] = "users"
        col_name = Column(name="name", schema="public", data_type="VARCHAR(100)")
        col_name.attributes["table_name"] = "users"
        
        self.t_obj = Table(name="users", schema="public")
        self.diff = ComparisonDifference(
            difference_id="diff_1",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="users",
            new_object=self.t_obj
        )
        self.report = SchemaComparisonReport("src", "tgt", differences=[self.diff])
        
        self.op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=self.t_obj,
            estimated_duration_ms=120.0
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
            execution_context=ExecutionContext().with_metadata("execution_id", "test_exec_1"),
            runtime_metadata=RuntimeMetadata("test_exec_1", time.time(), "QA", "dev")
        )

    def test_registries_constraints(self):
        """Verify Registry duplicate checks and subclass verification."""
        class InvalidEngine:
            pass

        with self.assertRaises(TypeError):
            ReliabilityEngineRegistry.register_engine("invalid", InvalidEngine)  # type: ignore

        # Register plugin validator check
        plugin = MockValidatorPlugin()
        PluginRegistry.register_validator("mock_val", plugin)
        self.assertIn(plugin, PluginRegistry.get_validators())
        
        with self.assertRaises(ValueError):
            PluginRegistry.register_validator("mock_val", plugin)

    def test_validation_engine(self):
        """Verify ValidationEngine collects diagnostics and runs ObjectValidators."""
        engine = ValidationEngine()
        report = engine.execute_engine(self.context, lambda ctx: None, lambda ctx, r: None)
        self.assertTrue(report.success)
        self.assertEqual(report.risk.risk_level, RiskLevel.LOW)

    def test_health_precheck_engine(self):
        """Verify HealthPrecheckEngine runs checks."""
        engine = HealthPrecheckEngine()
        report = engine.execute_engine(self.context, lambda ctx: None, lambda ctx, r: None)
        self.assertIn("CAPACITY_RESOURCE_VERIFICATION", report.passed_checks)

    def test_dryrun_simulation_engine(self):
        """Verify DryRunSimulationEngine calculates cost, storage, and duration."""
        engine = DryRunSimulationEngine()
        report = engine.execute_engine(self.context, lambda ctx: None, lambda ctx, r: None)
        self.assertEqual(report.estimated_time_ms, 120.0)
        self.assertGreater(report.estimated_storage_bytes, 0)
        self.assertEqual(report.estimated_cost, 1.2)

    def test_certification_engine(self):
        """Verify compliance grading."""
        engine = CertificationEngine()
        report = engine.execute_engine(self.context, lambda ctx: None, lambda ctx, r: None)
        self.assertTrue(report.certified)
        self.assertEqual(report.compliance_grade, "A")

    def test_rollback_engine(self):
        """Verify rollback steps generation."""
        engine = RollbackEngine()
        report = engine.execute_engine(self.context, lambda ctx: None, lambda ctx, r: None)
        self.assertEqual(len(report.steps), 1)
        self.assertTrue(report.safe_to_rollback)
        self.assertEqual(report.steps[0], "DROP TABLE users")

    def test_drift_detector(self):
        """Verify drift detection scans ad-hoc differences."""
        # Add an unscheduled diff representing drift
        extra_table = Table(name="adhoc_table", schema="public")
        drift_diff = ComparisonDifference(
            difference_id="diff_drift",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="adhoc_table",
            new_object=extra_table
        )
        self.context.schema_report.differences.append(drift_diff)
        
        detector = DriftDetector()
        report = detector.execute_engine(self.context, lambda ctx: None, lambda ctx, r: None)
        self.assertTrue(report.has_drift)
        self.assertIn("Object 'adhoc_table' (type: ObjectType.TABLE) has ad-hoc difference: ADD", report.drifts[0])
