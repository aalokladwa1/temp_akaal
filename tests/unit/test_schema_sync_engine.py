import unittest
import asyncio
from dataclasses import FrozenInstanceError, replace
from typing import List
from akaal.core.models.enums import SystemType
from akaal.migration.models import (
    ObjectType,
    MigrationObject,
    Table,
    Column,
    Constraint,
    Index,
    View,
    MaterializedView,
    Trigger,
    Function,
    Procedure,
    Sequence,
    Partition,
    Synonym,
    ComparisonDifference,
    SchemaComparisonReport,
    OperationType,
    MigrationOperation,
    MigrationPlan,
    DDLCommand,
    MigrationResult
)
from akaal.migration.planner import SynchronizationPlanner
from akaal.migration.dependency import DependencyResolver
from akaal.migration.ddl import PostgreSQLDDLGenerator, MySQLDDLGenerator
from akaal.migration.executor import SchemaSyncExecutor
from akaal.migration.workflow import SchemaSyncWorkflow

class TestSchemaSyncEngine(unittest.TestCase):

    def test_migration_object_inheritance(self):
        """
        Verify that all 12 object subclasses inherit from MigrationObject,
        generate UUIDs, and establish stable object_keys.
        """
        table = Table(name="users", schema="public")
        column = Column(name="email", schema="public", data_type="VARCHAR(255)")
        constraint = Constraint(name="pk_users", schema="public", constraint_type="PRIMARY KEY")
        idx = Index(name="idx_users_email", schema="public")
        view = View(name="active_users", schema="public")
        mv = MaterializedView(name="users_summary", schema="public")
        trig = Trigger(name="trg_audit_users", schema="public", table_name="users")
        func = Function(name="calculate_hash", schema="public")
        proc = Procedure(name="archive_old", schema="public")
        seq = Sequence(name="user_id_seq", schema="public")
        part = Partition(name="users_p1", schema="public", table_name="users")
        syn = Synonym(name="usr", schema="public", object_name="users")

        objects = [table, column, constraint, idx, view, mv, trig, func, proc, seq, part, syn]

        for obj in objects:
            self.assertTrue(isinstance(obj, MigrationObject))
            self.assertIsNotNone(obj.object_id)
            self.assertTrue(len(obj.object_id) > 0)
            self.assertTrue(obj.object_key.startswith("public."))
            self.assertTrue(obj.object_key.endswith(obj.name))

    def test_migration_plan_immutability(self):
        """
        Assert that MigrationPlan and MigrationOperation are frozen and raise exceptions on mutation.
        """
        col = Column(name="id", schema="dbo")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=col
        )
        plan = MigrationPlan(
            planner_version="1.0.0",
            plan_version="1.0.0",
            generated_at="2026-07-13T00:00:00Z",
            source_database="src",
            target_database="tgt",
            operations=(op,)
        )

        with self.assertRaises(FrozenInstanceError):
            op.priority = 10  # type: ignore

        with self.assertRaises(FrozenInstanceError):
            plan.plan_version = "2.0.0"  # type: ignore

    def test_planner_determinism(self):
        """
        Verify that the Planner produces identical plans given identical comparison reports.
        """
        planner = SynchronizationPlanner()
        
        diff1 = ComparisonDifference(
            difference_id="1",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="orders",
            schema_name="public",
            new_object=Table(name="orders", schema="public")
        )
        diff2 = ComparisonDifference(
            difference_id="2",
            diff_type="ADD",
            object_type=ObjectType.COLUMN,
            object_name="orders.total",
            schema_name="public",
            new_object=Column(name="total", schema="public")
        )
        
        report = SchemaComparisonReport(
            source_schema="src",
            target_schema="tgt",
            differences=[diff1, diff2]
        )

        plan_a = planner.plan(report)
        plan_b = planner.plan(report)

        self.assertEqual(plan_a.planner_version, plan_b.planner_version)
        self.assertEqual(len(plan_a.operations), len(plan_b.operations))
        self.assertEqual(plan_a.operations[0].operation_id, plan_b.operations[0].operation_id)
        self.assertEqual(plan_a.operations[0].depends_on, plan_b.operations[0].depends_on)
        self.assertEqual(plan_a.operations[1].depends_on, plan_b.operations[1].depends_on)

    def test_planner_dependency_assignment(self):
        """
        Verify that the planner correctly populates semantic fields like depends_on and stage.
        """
        planner = SynchronizationPlanner()

        # Let's create a report where a column addition depends on table creation
        t_obj = Table(name="customers", schema="public")
        c_obj = Column(name="phone", schema="public")
        c_obj.attributes["table_name"] = "customers" # or parent parsed via customer.phone

        diff_t = ComparisonDifference(
            difference_id="t1",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="customers",
            new_object=t_obj
        )
        diff_c = ComparisonDifference(
            difference_id="c1",
            diff_type="ADD",
            object_type=ObjectType.COLUMN,
            object_name="customers.phone",
            new_object=c_obj
        )

        report = SchemaComparisonReport(
            source_schema="src",
            target_schema="tgt",
            differences=[diff_t, diff_c]
        )

        plan = planner.plan(report)
        
        self.assertEqual(len(plan.operations), 2)
        op_t = next(op for op in plan.operations if op.target_object.object_type == ObjectType.TABLE)
        op_c = next(op for op in plan.operations if op.target_object.object_type == ObjectType.COLUMN)

        self.assertIn(op_t.operation_id, op_c.depends_on)
        self.assertEqual(op_t.stage, "STAGE_TABLES")
        self.assertEqual(op_c.stage, "STAGE_COLUMNS")

    def test_dependency_resolver_cycle_detection(self):
        """
        Verify that topological sorter correctly raises ValueError on cyclic dependencies.
        """
        resolver = DependencyResolver()
        col = Column(name="temp", schema="public")

        op_a = MigrationOperation(
            operation_id="op_a",
            operation_type=OperationType.CREATE,
            target_object=col,
            depends_on=("op_b",)
        )
        op_b = MigrationOperation(
            operation_id="op_b",
            operation_type=OperationType.CREATE,
            target_object=col,
            depends_on=("op_a",)
        )

        plan = MigrationPlan(
            planner_version="1.0", plan_version="1.0", generated_at="now",
            source_database="src", target_database="tgt",
            operations=(op_a, op_b)
        )

        with self.assertRaises(ValueError) as ctx:
            resolver.resolve(plan)
        
        self.assertIn("Cyclic dependency detected", str(ctx.exception))

    def test_dependency_resolver_generic_sorting(self):
        """
        Verify that resolver sorts strictly using depends_on fields without looking at object types.
        """
        resolver = DependencyResolver()
        col = Column(name="temp", schema="public")

        op_1 = MigrationOperation(
            operation_id="op_1", operation_type=OperationType.CREATE, target_object=col, depends_on=("op_3",)
        )
        op_2 = MigrationOperation(
            operation_id="op_2", operation_type=OperationType.CREATE, target_object=col, depends_on=("op_1",)
        )
        op_3 = MigrationOperation(
            operation_id="op_3", operation_type=OperationType.CREATE, target_object=col, depends_on=()
        )

        plan = MigrationPlan(
            planner_version="1.0", plan_version="1.0", generated_at="now",
            source_database="src", target_database="tgt",
            operations=(op_1, op_2, op_3)
        )

        sorted_ops = resolver.resolve(plan)
        
        self.assertEqual(len(sorted_ops), 3)
        self.assertEqual(sorted_ops[0].operation_id, "op_3")
        self.assertEqual(sorted_ops[1].operation_id, "op_1")
        self.assertEqual(sorted_ops[2].operation_id, "op_2")

    def test_ddl_command_structure(self):
        """
        Verify that DDL generator compiles abstract operations into DDLCommand objects.
        """
        generator = PostgreSQLDDLGenerator()
        col = Column(name="age", schema="public", data_type="INT")
        col.attributes["table_name"] = "users"

        op = MigrationOperation(
            operation_id="op_c",
            operation_type=OperationType.CREATE,
            target_object=col,
            estimated_duration_ms=150.0,
            context={"table_name": "users"}
        )

        cmds = generator.generate_commands([op])
        
        self.assertEqual(len(cmds), 1)
        cmd = cmds[0]
        self.assertTrue(isinstance(cmd, DDLCommand))
        self.assertEqual(cmd.dialect, "postgresql")
        self.assertEqual(cmd.sql, 'ALTER TABLE "public"."users" ADD COLUMN "age" INT')
        self.assertEqual(cmd.rollback_sql, 'ALTER TABLE "public"."users" DROP COLUMN "age"')
        self.assertEqual(cmd.estimated_duration, 0.15)
        self.assertEqual(cmd.execution_order, 0)

    def test_workflow_hook_sequencing(self):
        """
        Verify that pre/post hooks run in sequence and capture plan and command context.
        """
        workflow = SchemaSyncWorkflow()
        
        t_obj = Table(name="logs", schema="public")
        diff = ComparisonDifference(
            difference_id="d_logs",
            diff_type="ADD",
            object_type=ObjectType.TABLE,
            object_name="logs",
            new_object=t_obj
        )
        report = SchemaComparisonReport(
            source_schema="src",
            target_schema="tgt",
            differences=[diff]
        )

        hook_seq = []

        def pre_hook(plan, commands):
            hook_seq.append(("pre", len(commands)))

        def post_hook(plan, result):
            hook_seq.append(("post", result.success))

        workflow.register_pre_hook(pre_hook)
        workflow.register_post_hook(post_hook)

        result = asyncio.run(workflow.run_sync(report, SystemType.POSTGRESQL))

        self.assertTrue(result.success)
        self.assertEqual(hook_seq, [("pre", 1), ("post", True)])
        self.assertEqual(len(result.executed_commands), 1)
        self.assertEqual(result.executed_commands[0].sql, 'CREATE TABLE "public"."logs" (id INT PRIMARY KEY)')

    def test_executor_isolation(self):
        """
        Verify that executor does not reorder or alter command arrays.
        """
        executor = SchemaSyncExecutor()
        cmd_1 = DDLCommand(sql="SQL 1", execution_order=0, dialect="sqlite")
        cmd_2 = DDLCommand(sql="SQL 2", execution_order=1, dialect="sqlite")

        result = asyncio.run(executor.execute([cmd_2, cmd_1]))

        # The executor should sort by execution_order internally before execution,
        # but shouldn't corrupt the DDLCommand object metadata.
        self.assertTrue(result.success)
        self.assertEqual(len(result.executed_commands), 2)
        self.assertEqual(result.executed_commands[0].sql, "SQL 1")
        self.assertEqual(result.executed_commands[1].sql, "SQL 2")
        self.assertEqual(result.statistics["commands_count"], 2)

    def test_ddl_generator_registry(self):
        """
        Verify that DDLGeneratorRegistry resolves expected generators and supports custom registrations.
        """
        from akaal.migration.ddl import DDLGeneratorRegistry, PostgreSQLDDLGenerator, BaseDDLGenerator
        
        # Test default registration lookup
        pg_gen = DDLGeneratorRegistry.get_generator(SystemType.POSTGRESQL)
        self.assertTrue(isinstance(pg_gen, PostgreSQLDDLGenerator))
        self.assertEqual(pg_gen.get_dialect_name(), "postgresql")

        # Test custom generator registration
        class DummyGenerator(BaseDDLGenerator):
            def get_dialect_name(self) -> str:
                return "dummy"
            def _format_dialect_sql(self, sql, rollback_sql, op):
                return sql, rollback_sql

        DDLGeneratorRegistry.register(SystemType.GENERIC, DummyGenerator)
        dummy_gen = DDLGeneratorRegistry.get_generator(SystemType.GENERIC)
        self.assertTrue(isinstance(dummy_gen, DummyGenerator))
        self.assertEqual(dummy_gen.get_dialect_name(), "dummy")

    def test_ddl_command_optional_metadata(self):
        """
        Verify that DDLCommand supports and preserves checksum and metadata attributes.
        """
        cmd = DDLCommand(sql="SELECT 1", checksum="abc-123", metadata={"test": "ok"})
        self.assertEqual(cmd.checksum, "abc-123")
        self.assertEqual(cmd.metadata, {"test": "ok"})

    def test_execution_context_support(self):
        """
        Verify that the executor accepts an ExecutionContext without affecting run success.
        """
        from akaal.migration.models import ExecutionContext
        executor = SchemaSyncExecutor()
        cmd = DDLCommand(sql="CREATE TABLE dummy", execution_order=0, dialect="sqlite")
        context = ExecutionContext(transaction_required=False, audit_context={"user": "Aalok"})

        result = asyncio.run(executor.execute([cmd], context=context))
        self.assertTrue(result.success)
        self.assertEqual(len(result.executed_commands), 1)

    def test_plan_hash_determinism(self):
        """
        Verify that deterministic SHA-256 plan hashes are generated and stable for identical setups.
        """
        from akaal.migration.hashing import calculate_plan_hash
        col = Column(name="status", schema="public")
        op = MigrationOperation(
            operation_id="op_status",
            operation_type=OperationType.CREATE,
            target_object=col
        )
        
        hash_1 = calculate_plan_hash("src", "tgt", (op,), {"user": "Aalok"})
        hash_2 = calculate_plan_hash("src", "tgt", (op,), {"user": "Aalok"})
        hash_diff_db = calculate_plan_hash("src_other", "tgt", (op,), {"user": "Aalok"})

        self.assertEqual(hash_1, hash_2)
        self.assertNotEqual(hash_1, hash_diff_db)
        self.assertEqual(len(hash_1), 64) # SHA-256 length

    def test_dot_graph_export(self):
        """
        Verify that DependencyResolver.to_dot outputs a valid GraphViz DOT string representation.
        """
        resolver = DependencyResolver()
        tbl = Table(name="age", schema="public")
        col = Column(name="age", schema="public")
        op_t = MigrationOperation(operation_id="op_table", operation_type=OperationType.CREATE, target_object=tbl)
        op_c = MigrationOperation(operation_id="op_col", operation_type=OperationType.CREATE, target_object=col, depends_on=("op_table",))

        plan = MigrationPlan(
            planner_version="1.0.0", plan_version="1.0.0", generated_at="now",
            source_database="src", target_database="tgt",
            operations=(op_t, op_c)
        )

        dot_output = resolver.to_dot(plan)
        
        self.assertIn("digraph G {", dot_output)
        self.assertIn('"op_table" [label="CREATE TABLE age"];', dot_output)
        self.assertIn('"op_table" -> "op_col";', dot_output)
        self.assertIn("}", dot_output)

    def test_table_drop_self_dependency_defect(self):
        """
        Verify that a Table drop does not depend on itself when the table name 
        matches its schema name, confirming the fix for the self-comparison defect.
        """
        planner = SynchronizationPlanner()
        # Create a table where schema name equals table name
        t_obj = Table(name="users", schema="users")
        
        diff = ComparisonDifference(
            difference_id="drop_users",
            diff_type="REMOVE",
            object_type=ObjectType.TABLE,
            object_name="users",
            old_object=t_obj
        )
        report = SchemaComparisonReport(
            source_schema="src",
            target_schema="tgt",
            differences=[diff]
        )
        
        # Generates the plan. Under the bug, the operation will contain itself in depends_on.
        plan = planner.plan(report)
        self.assertEqual(len(plan.operations), 1)
        op = plan.operations[0]
        
        # Assert that the operation does NOT depend on itself
        self.assertNotIn(op.operation_id, op.depends_on)
