import asyncio
import unittest
from akaal.core.models.configuration import HookPhase, SQLHook
from akaal.migration.execution.hooks.executor import HookExecutor, HookExecutionError

class MockConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.committed = False
        self.executed = []

    def cursor(self):
        return self

    def execute(self, sql):
        self.executed.append(sql)
        if "FAIL" in sql:
            raise ValueError("SQL failed")

    def rollback(self):
        self.rolled_back = True

    def commit(self):
        self.committed = True

    def close(self):
        pass

class MockAdapter:
    def __init__(self) -> None:
        self.is_connected = False
        self.conn = MockConnection()

    async def connect(self):
        self.is_connected = True

    def get_connection(self):
        return self.conn

class TestMultiPhaseHooks(unittest.TestCase):
    async def run_successful_transactional_hook(self):
        adapter = MockAdapter()
        executor = HookExecutor(adapter)
        
        hook = SQLHook(
            sql_commands=["INSERT 1", "INSERT 2"],
            phase=HookPhase.BEFORE_DISCOVERY,
            transactional=True
        )

        await executor.execute_phase_hooks([hook], HookPhase.BEFORE_DISCOVERY)

        self.assertEqual(adapter.conn.executed, ["INSERT 1", "INSERT 2"])
        self.assertTrue(adapter.conn.committed)
        self.assertFalse(adapter.conn.rolled_back)
        self.assertEqual(len(executor.audit_log), 1)
        self.assertTrue(executor.audit_log[0]["success"])

    async def run_failed_hook_raises_and_rolls_back(self):
        adapter = MockAdapter()
        executor = HookExecutor(adapter)

        hook = SQLHook(
            sql_commands=["INSERT 1", "FAIL COMMAND"],
            phase=HookPhase.BEFORE_DATA_MIGRATION,
            transactional=True,
            ignore_failures=False,
            rollback_on_failure=True
        )

        with self.assertRaises(HookExecutionError):
            await executor.execute_phase_hooks([hook], HookPhase.BEFORE_DATA_MIGRATION)

        self.assertTrue(adapter.conn.rolled_back)
        self.assertEqual(len(executor.audit_log), 1)
        self.assertFalse(executor.audit_log[0]["success"])

    async def run_failed_hook_ignored_failsafe(self):
        adapter = MockAdapter()
        executor = HookExecutor(adapter)

        hook = SQLHook(
            sql_commands=["FAIL COMMAND"],
            phase=HookPhase.BEFORE_DATA_MIGRATION,
            transactional=True,
            ignore_failures=True,
            rollback_on_failure=True
        )

        # Should not raise exception
        await executor.execute_phase_hooks([hook], HookPhase.BEFORE_DATA_MIGRATION)
        self.assertEqual(len(executor.audit_log), 1)
        self.assertFalse(executor.audit_log[0]["success"])

    def test_run_async(self):
        import asyncio
        asyncio.run(self.run_successful_transactional_hook())
        asyncio.run(self.run_failed_hook_raises_and_rolls_back())
        asyncio.run(self.run_failed_hook_ignored_failsafe())
