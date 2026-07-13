from typing import Callable, List, Dict
from akaal.core.models.enums import SystemType
from akaal.migration.models import SchemaComparisonReport, MigrationPlan, MigrationResult, DDLCommand
from akaal.migration.planner import SynchronizationPlanner
from akaal.migration.dependency import DependencyResolver
from akaal.migration.ddl import BaseDDLGenerator, DDLGeneratorRegistry
from akaal.migration.executor import SchemaSyncExecutor

class SchemaSyncWorkflow:
    """
    Orchestrator for the Schema Synchronization Engine.
    Exposes only run_sync() as the single public orchestration entry point.
    Supports dynamic pre-execution and post-execution hooks.
    """

    def __init__(
        self,
        planner: SynchronizationPlanner = None,
        resolver: DependencyResolver = None,
        executor: SchemaSyncExecutor = None
    ) -> None:
        self.planner = planner or SynchronizationPlanner()
        self.resolver = resolver or DependencyResolver()
        self.executor = executor or SchemaSyncExecutor()
        self._pre_hooks: List[Callable[[MigrationPlan, List[DDLCommand]], None]] = []
        self._post_hooks: List[Callable[[MigrationPlan, MigrationResult], None]] = []

    def register_pre_hook(self, callback: Callable[[MigrationPlan, List[DDLCommand]], None]) -> None:
        """Register a callback to run before commands are executed."""
        self._pre_hooks.append(callback)

    def register_post_hook(self, callback: Callable[[MigrationPlan, MigrationResult], None]) -> None:
        """Register a callback to run after commands are executed."""
        self._post_hooks.append(callback)

    async def run_sync(self, report: SchemaComparisonReport, target_dialect: SystemType) -> MigrationResult:
        """
        Orchestrates schema synchronization:
        Planner -> Dependency Resolver -> DDL Generator -> Pre-Hooks -> Executor -> Post-Hooks
        """
        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_PLAN_START]
        # Future event emitter slot. Will publish: {"report": report, "dialect": target_dialect}

        # 1. Semantic Planning
        plan = self.planner.plan(report)

        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_PLAN_COMPLETE]
        # Future event emitter slot. Will publish: {"plan": plan, "plan_hash": plan.plan_hash}

        # 2. Dependency Resolution (Topological Sort)
        sorted_ops = self.resolver.resolve(plan)

        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_RESOLVE_COMPLETE]
        # Future event emitter slot. Will publish: {"sorted_operations": sorted_ops}

        # 3. DDL Command Generation
        generator = self._get_generator(target_dialect)
        commands = generator.generate_commands(sorted_ops)

        # 4. Pre-Execution Hooks
        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_PRE_EXECUTION_HOOKS_START]
        for pre_hook in self._pre_hooks:
            pre_hook(plan, commands)

        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_EXECUTE_START]
        # Future event emitter slot. Will publish: {"commands_count": len(commands)}

        # 5. Execution
        result = await self.executor.execute(commands)

        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_EXECUTE_COMPLETE]
        # Future event emitter slot. Will publish: {"result": result, "elapsed_ms": result.elapsed_time_ms}

        # 6. Post-Execution Hooks
        # [LIFECYCLE HOOK: EVENT_PUBLISHER - ON_POST_EXECUTION_HOOKS_START]
        for post_hook in self._post_hooks:
            post_hook(plan, result)

        return result

    def _get_generator(self, dialect: SystemType) -> BaseDDLGenerator:
        """Resolves the dialect generator from the centralized DDL Generator Registry."""
        return DDLGeneratorRegistry.get_generator(dialect)
