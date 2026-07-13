import time
from typing import List, Dict, Any, Optional
from akaal.migration.models import DDLCommand, MigrationResult, ExecutionContext

class SchemaSyncExecutor:
    """
    Execution-only engine for schema migration commands.
    Guarantees no modifications to command order or plan structure.
    Only runs DDLCommands, captures failures/warnings, records timings, and returns result.
    """

    async def execute(
        self,
        commands: List[DDLCommand],
        context: Optional[ExecutionContext] = None
    ) -> MigrationResult:
        """
        Executes a sequence of compiled DDL commands under an execution context.
        Returns a MigrationResult summary.
        """
        # If no execution context is supplied, create a default transaction/retry context.
        exec_context = context or ExecutionContext()
        start_time = time.perf_counter()
        executed: List[DDLCommand] = []
        failed: List[DDLCommand] = []
        warnings: List[str] = []
        success = True

        # Sort commands by execution_order to ensure order is preserved during execution
        sorted_commands = sorted(commands, key=lambda c: c.execution_order)

        for cmd in sorted_commands:
            try:
                # Stub execution layer: commands would normally run against database connection.
                # In Day 1 baseline, we capture all statements as executed successfully.
                for w in cmd.warnings:
                    warnings.append(w)
                executed.append(cmd)
            except Exception as e:
                success = False
                failed.append(cmd)
                warnings.append(f"Command execution error: {str(e)}")
                # Fail-fast execution model
                break

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return MigrationResult(
            success=success,
            executed_commands=executed,
            failed_commands=failed,
            warnings=warnings,
            elapsed_time_ms=elapsed_ms,
            statistics={
                "commands_count": len(sorted_commands),
                "executed_count": len(executed),
                "failed_count": len(failed)
            },
            rollback_information={
                "rollback_commands": [c.rollback_sql for c in reversed(executed) if c.rollback_sql]
            }
        )
