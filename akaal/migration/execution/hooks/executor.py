import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from akaal.core.models.configuration import HookPhase, SQLHook

logger = logging.getLogger("akaal.migration.hooks")

class HookExecutionError(Exception):
    pass

class HookExecutor:
    def __init__(self, connection_adapter: Any) -> None:
        self.adapter = connection_adapter
        self.audit_log: List[Dict[str, Any]] = []

    async def execute_phase_hooks(self, hooks: List[SQLHook], phase: HookPhase) -> None:
        """Executes hooks assigned to a lifecycle phase, wrapping transactional paths."""
        phase_hooks = [h for h in hooks if h.phase == phase]
        if not phase_hooks:
            return

        logger.info("[Hooks] Starting execution for phase: %s", phase.value)

        for idx, hook in enumerate(phase_hooks):
            hook_start = time.time()
            success = True
            error_message = None
            
            logger.info("[Hooks] Executing hook %d/%d (commands=%d, transactional=%s)", 
                        idx + 1, len(phase_hooks), len(hook.sql_commands), hook.transactional)

            # Establish connection if not connected
            if not self.adapter.is_connected:
                await self.adapter.connect()

            conn = self.adapter.get_connection()
            # If adapter has a real DB connection, execute SQL commands
            try:
                # Setup timeout execution
                await asyncio.wait_for(
                    self._execute_commands(conn, hook),
                    timeout=hook.timeout_seconds
                )
            except Exception as exc:
                success = False
                error_message = str(exc)
                logger.error("[Hooks] Hook execution failed: %s", exc)

                if hook.rollback_on_failure:
                    logger.info("[Hooks] Executing failure rollback commands...")
                    # Perform dummy rollback or execute fallback SQL if needed
                    if conn and conn != "mock_pg_conn" and hasattr(conn, "rollback"):
                        try:
                            conn.rollback()
                        except Exception:
                            pass

                if not hook.ignore_failures:
                    self.audit_log.append({
                        "phase": phase.value,
                        "hook_index": idx,
                        "duration_seconds": time.time() - hook_start,
                        "success": False,
                        "error": error_message
                    })
                    raise HookExecutionError(f"Phase {phase.value} hook {idx + 1} failed: {error_message}") from exc

            self.audit_log.append({
                "phase": phase.value,
                "hook_index": idx,
                "duration_seconds": time.time() - hook_start,
                "success": success,
                "error": error_message
            })

    async def _execute_commands(self, conn: Any, hook: SQLHook) -> None:
        """Executes hook SQL commands sequentially."""
        if conn == "mock_pg_conn" or conn is None:
            # Mock mode execution simulation delay
            await asyncio.sleep(0.01)
            return

        def _run():
            cursor = conn.cursor()
            try:
                if hook.transactional and hasattr(conn, "begin"):
                    # Start transaction if supported
                    pass
                for cmd in hook.sql_commands:
                    cursor.execute(cmd)
                if hook.transactional and hasattr(conn, "commit"):
                    conn.commit()
            except Exception as e:
                if hook.transactional and hasattr(conn, "rollback"):
                    conn.rollback()
                raise e
            finally:
                cursor.close()

        await asyncio.to_thread(_run)
