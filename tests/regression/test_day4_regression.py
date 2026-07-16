import unittest
from akaal.core.models.enums import SystemType
from akaal.migration.models import ObjectType, OperationType, Table, Column
from akaal.migration.planner import SynchronizationPlanner
from akaal.migration.dependency import DependencyResolver
from akaal.migration.ddl import DDLGeneratorRegistry
from akaal.migration.execution.batching import TransactionBatcher

class TestDay4Regression(unittest.TestCase):
    """
    Regression protection suite ensuring that Day 1-3 baseline synchronization flow,
    generators, resolver sorting, and batcher capabilities remain unbroken.
    """
    def test_ddl_generation_regression(self) -> None:
        table = Table(
            name="users",
            columns=[
                Column(name="id", data_type="INT", nullable=False),
                Column(name="username", data_type="VARCHAR(255)", nullable=True)
            ]
        )
        pg_gen = DDLGeneratorRegistry.get_generator(SystemType.POSTGRESQL)
        ops = pg_gen.generate_commands([])
        self.assertEqual(len(ops), 0)

    def test_transaction_batching_regression(self) -> None:
        pg_gen = DDLGeneratorRegistry.get_generator(SystemType.POSTGRESQL)
        from akaal.migration.models import MigrationOperation
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=Table(name="users")
        )
        cmds = pg_gen.generate_commands([op])
        self.assertEqual(len(cmds), 1)
        
        batcher = TransactionBatcher()
        batches = batcher.batch_commands(cmds)
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 1)

    def test_dependency_resolver_regression(self) -> None:
        resolver = DependencyResolver()
        from akaal.migration.models import MigrationPlan, MigrationOperation
        op1 = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=Table(name="users")
        )
        op2 = MigrationOperation(
            operation_id="op_2",
            operation_type=OperationType.CREATE,
            target_object=Table(name="orders"),
            depends_on=("op_1",)
        )
        plan = MigrationPlan(
            planner_version="1.0",
            plan_version="1.0.0",
            generated_at="2026-07-15",
            source_database="src",
            target_database="tgt",
            operations=(op1, op2)
        )
        sorted_ops = resolver.resolve(plan)
        self.assertEqual(sorted_ops[0].operation_id, "op_1")
        self.assertEqual(sorted_ops[1].operation_id, "op_2")
