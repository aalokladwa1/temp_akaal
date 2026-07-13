"""
Akaal — Schema Synchronization Engine Hardening Tests
=====================================================
Validates plan hashing determinism, DDL registry restrictions, ExecutionContext immutability,
sync/async hook safety, and DOT graph exporter scaling benchmarks.
"""

import asyncio
import time
import pickle
import threading
import unittest
from dataclasses import FrozenInstanceError
from typing import List, Dict, Any, Tuple
from akaal.core.models.enums import SystemType
from akaal.migration.models import (
    ObjectType,
    MigrationObject,
    Table,
    Column,
    Constraint,
    Index,
    MigrationOperation,
    MigrationPlan,
    DDLCommand,
    MigrationResult,
    ExecutionContext
)
from akaal.migration.hashing import calculate_plan_hash, canonicalize_metadata
from akaal.migration.ddl import DDLGeneratorRegistry, BaseDDLGenerator
from akaal.migration.dependency import DependencyResolver
from akaal.migration.workflow import SchemaSyncWorkflow


class DummyGen(BaseDDLGenerator):
    def get_dialect_name(self) -> str:
        return "dummy_dialect"
    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        return sql, rollback_sql


class TestPlanHashingHardening(unittest.TestCase):
    """Verifies that plan hashes are fully deterministic, structural, and ignore metadata noise."""

    def test_hash_determinism_and_dict_order(self) -> None:
        """Verify that dictionary insertion order and nested collections canonicalization yield deterministic hashes."""
        col = Column(name="status", data_type="VARCHAR(20)")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type="CREATE",
            target_object=col,
            depends_on=("op_dep",)
        )

        # Build metadata dicts with different insertion orders and nested sets
        meta_1 = {
            "author": "Aalok",
            "attributes": {"active": True, "tags": {"prod", "schema"}}
        }
        meta_2 = {
            "attributes": {"tags": {"schema", "prod"}, "active": True},
            "author": "Aalok"
        }

        hash_1 = calculate_plan_hash("src", "tgt", (op,), meta_1)
        hash_2 = calculate_plan_hash("src", "tgt", (op,), meta_2)

        self.assertEqual(hash_1, hash_2)
        self.assertEqual(len(hash_1), 64)

    def test_hash_ignores_uuid_and_timestamps(self) -> None:
        """Verify that runtime UUIDs, timestamps, and memory address markers do not affect hashes."""
        col_1 = Column(name="status", data_type="VARCHAR(20)")
        # col_1 and col_2 are structurally identical but will have different auto-generated object_id UUIDs
        col_2 = Column(name="status", data_type="VARCHAR(20)")
        self.assertNotEqual(col_1.object_id, col_2.object_id)

        op_1 = MigrationOperation(
            operation_id="op_1",
            operation_type="CREATE",
            target_object=col_1
        )
        op_2 = MigrationOperation(
            operation_id="op_1",
            operation_type="CREATE",
            target_object=col_2
        )

        # Hash with different runtime-generated timestamps and IDs in metadata
        hash_a = calculate_plan_hash("src", "tgt", (op_1,), {"timestamp": "2026-07-13T12:00:00Z", "run_id": "uuid-123"})
        hash_b = calculate_plan_hash("src", "tgt", (op_2,), {"timestamp": "2026-07-13T19:25:52Z", "run_id": "uuid-999"})

        self.assertEqual(hash_a, hash_b)

    def test_hash_structural_difference(self) -> None:
        """Verify that meaningful structural differences in columns/types yield different hashes."""
        col_a = Column(name="status", data_type="VARCHAR(20)")
        col_b = Column(name="status", data_type="INTEGER") # altered type

        op_a = MigrationOperation(
            operation_id="op_1",
            operation_type="CREATE",
            target_object=col_a
        )
        op_b = MigrationOperation(
            operation_id="op_1",
            operation_type="CREATE",
            target_object=col_b
        )

        hash_a = calculate_plan_hash("src", "tgt", (op_a,), {})
        hash_b = calculate_plan_hash("src", "tgt", (op_b,), {})

        self.assertNotEqual(hash_a, hash_b)


class TestDDLGeneratorRegistryHardening(unittest.TestCase):
    """Verifies DDL Registry duplicate protection and lookup robustness."""

    def setUp(self) -> None:
        # Save a backup of the registry
        self._registry_backup = DDLGeneratorRegistry._registry.copy()

    def tearDown(self) -> None:
        # Restore registry
        DDLGeneratorRegistry._registry = self._registry_backup

    def test_successful_registration_and_lookup(self) -> None:
        """Verify external registration of a custom dialect generator works."""
        custom_type = SystemType.GENERIC
        if custom_type in DDLGeneratorRegistry._registry:
            del DDLGeneratorRegistry._registry[custom_type]
            
        DDLGeneratorRegistry.register(custom_type, DummyGen)
        gen = DDLGeneratorRegistry.get_generator(custom_type)
        self.assertTrue(isinstance(gen, DummyGen))
        self.assertEqual(gen.get_dialect_name(), "dummy_dialect")

    def test_duplicate_registration_raises_error(self) -> None:
        """Verify duplicate registrations raise a clear ValueError."""
        custom_type = SystemType.GENERIC
        if custom_type in DDLGeneratorRegistry._registry:
            del DDLGeneratorRegistry._registry[custom_type]
            
        DDLGeneratorRegistry.register(custom_type, DummyGen)
        with self.assertRaises(ValueError) as ctx:
            DDLGeneratorRegistry.register(custom_type, DummyGen)
        self.assertIn("already registered", str(ctx.exception))

    def test_unknown_dialect_lookup(self) -> None:
        """Verify unknown dialect lookup throws an informative KeyError."""
        with self.assertRaises(KeyError) as ctx:
            DDLGeneratorRegistry.get_generator("unknown_db")
        self.assertIn("Unknown database dialect", str(ctx.exception))

    def test_case_insensitive_dialect_lookup(self) -> None:
        """Verify lookup resolved case-insensitively via string inputs."""
        gen = DDLGeneratorRegistry.get_generator("pOsTgReSqL")
        self.assertEqual(gen.get_dialect_name(), "postgresql")


class TestExecutionContextHardening(unittest.TestCase):
    """Verifies ExecutionContext immutability, thread-safety, and serialization."""

    def test_immutability_and_dataclass_replace(self) -> None:
        """Verify ExecutionContext is frozen and cannot be directly mutated."""
        ctx = ExecutionContext(transaction_required=True)
        with self.assertRaises(FrozenInstanceError):
            ctx.transaction_required = False # type: ignore

    def test_thread_safe_metadata_propagation(self) -> None:
        """Verify concurrent metadata attachment is thread-safe and isolated."""
        ctx = ExecutionContext()
        
        def worker(key: str, val: int):
            # Non-mutating copy-on-write pattern
            new_ctx = ctx.with_metadata(key, val)
            self.assertEqual(new_ctx.get_metadata(key), val)
            self.assertIsNone(ctx.get_metadata(key))

        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(f"thread_{i}", i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    def test_pickling_serialization(self) -> None:
        """Verify ExecutionContext can be successfully pickled/deserialized without Lock issues."""
        ctx = ExecutionContext(transaction_required=True).with_metadata("user", "Aalok")
        serialized = pickle.dumps(ctx)
        deserialized = pickle.loads(serialized)
        
        self.assertEqual(deserialized.transaction_required, ctx.transaction_required)
        self.assertEqual(deserialized.get_metadata("user"), "Aalok")
        # Ensure lock is reconstructed and active
        new_ctx = deserialized.with_metadata("active", True)
        self.assertTrue(new_ctx.get_metadata("active"))


class TestWorkflowHookHardening(unittest.TestCase):
    """Verifies workflow pre/post hook execution robustness."""

    def test_deterministic_hook_ordering(self) -> None:
        """Verify hooks execute in the exact deterministic registration order."""
        workflow = SchemaSyncWorkflow()
        order_list = []

        workflow.register_pre_hook(lambda plan, cmds: order_list.append("pre_1"))
        workflow.register_pre_hook(lambda plan, cmds: order_list.append("pre_2"))
        
        from akaal.migration.models import SchemaComparisonReport
        report = SchemaComparisonReport(source_schema="src", target_schema="tgt")
        
        asyncio.run(workflow.run_sync(report, SystemType.POSTGRESQL))
        self.assertEqual(order_list, ["pre_1", "pre_2"])

    def test_hook_mixed_sync_async(self) -> None:
        """Verify mixed sync and async hooks execute and complete successfully."""
        workflow = SchemaSyncWorkflow()
        hook_ran = []

        async def async_pre(plan, cmds):
            await asyncio.sleep(0.001)
            hook_ran.append("async_pre")

        def sync_pre(plan, cmds):
            hook_ran.append("sync_pre")

        workflow.register_pre_hook(async_pre)
        workflow.register_pre_hook(sync_pre)

        from akaal.migration.models import SchemaComparisonReport
        report = SchemaComparisonReport(source_schema="src", target_schema="tgt")
        
        asyncio.run(workflow.run_sync(report, SystemType.POSTGRESQL))
        self.assertEqual(hook_ran, ["async_pre", "sync_pre"])

    def test_hook_failure_no_corruption(self) -> None:
        """Verify that a failing hook does not crash or corrupt the migration pipeline."""
        workflow = SchemaSyncWorkflow()
        
        def bad_hook(plan, cmds):
            raise RuntimeError("Injected hook error")

        workflow.register_pre_hook(bad_hook)
        
        from akaal.migration.models import SchemaComparisonReport
        report = SchemaComparisonReport(source_schema="src", target_schema="tgt")
        
        result = asyncio.run(workflow.run_sync(report, SystemType.POSTGRESQL))
        self.assertTrue(result.success) # Executor still ran successfully
        self.assertTrue(any("Hook execution failed: Injected hook error" in w for w in result.warnings))


class TestDependencyGraphHardening(unittest.TestCase):
    """Verifies GraphViz syntax escaping and performance benchmarks."""

    def test_to_dot_escaping(self) -> None:
        """Verify that special characters and quotes are properly escaped in GraphViz format."""
        resolver = DependencyResolver()
        tbl = Table(name='users"table\\name', schema="public")
        op = MigrationOperation(operation_id='op_"users"', operation_type="CREATE", target_object=tbl)
        
        plan = MigrationPlan(
            planner_version="1.0.0", plan_version="1.0.0", generated_at="now",
            source_database="src", target_database="tgt",
            operations=(op,)
        )

        dot = resolver.to_dot(plan)
        # Should be escaped quotes and backslashes in label and ID
        self.assertIn('"op_\\"users\\""', dot)
        self.assertIn('label="CREATE TABLE users\\"table\\\\name"', dot)

    def test_to_dot_benchmark_large_graph(self) -> None:
        """Benchmark DOT generation efficiency for large graphs with 2,000 nodes and 2,000 edges."""
        resolver = DependencyResolver()
        operations = []
        
        for i in range(2000):
            tbl = Table(name=f"table_{i}", schema="public")
            dep = (f"op_{i-1}",) if i > 0 else ()
            op = MigrationOperation(
                operation_id=f"op_{i}",
                operation_type="CREATE",
                target_object=tbl,
                depends_on=dep
            )
            operations.append(op)

        plan = MigrationPlan(
            planner_version="1.0.0", plan_version="1.0.0", generated_at="now",
            source_database="src", target_database="tgt",
            operations=tuple(operations)
        )

        start_time = time.perf_counter()
        dot_out = resolver.to_dot(plan)
        duration = time.perf_counter() - start_time
        
        print(f"\nDOT Exporter Benchmark: 2,000 nodes processed in {duration*1000:.2f} ms")
        self.assertTrue(duration < 0.25, f"DOT generation too slow: {duration*1000:.2f} ms")
        self.assertTrue(len(dot_out) > 0)
