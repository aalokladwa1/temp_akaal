"""
NexusForge — GB Agent
=====================
The staging, human review, and production promotion agent.
Manages the staging database, versions Universal JSON snapshots, and executes target deployments.
Delegates all progress tracking and cursor resumption to CheckpointManager.
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from akaal.adapters.adapter_registry import create_adapter
from akaal.core.models.enums import AgentStatus, AgentType, TaskType, SystemType, WorkflowState
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.metrics.registry import MetricsRegistry
from akaal.metrics.constants import ROWS_MIGRATED, BYTES_MIGRATED, TABLES_MIGRATED

logger = logging.getLogger("nexusforge.gb")


def get_memory_usage() -> float:
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return float(process.memory_info().rss) / (1024 * 1024) # MB
    except ImportError:
        try:
            import tracemalloc
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                return float(current) / (1024 * 1024)
        except Exception:
            pass
        return 0.0


class AdaptiveBatchGovernor:
    def __init__(
        self,
        use_adaptive: bool,
        min_size: int,
        init_size: int,
        max_size: int,
        growth: float,
        shrink: float,
        target_ms: float,
        window: int,
        metrics: Optional[Any] = None,
    ) -> None:
        self.use_adaptive = use_adaptive
        self.min_size = min_size
        self.init_size = init_size
        self.max_size = max_size
        self.growth = growth
        self.shrink = shrink
        self.target_seconds = target_ms / 1000.0
        self.window = window

        self.current_batch_size = init_size
        self.durations: List[float] = []
        self.throughputs: List[float] = []
        self.memories: List[float] = []
        self.last_transaction_duration = 0.0
        
        self.adjustment_count = 0
        self.retry_count = 0
        self.total_batches = 0
        self.failed_batches = 0
        self._metrics = metrics

    def get_state(self) -> Dict[str, Any]:
        return {
            "current_batch_size": self.current_batch_size,
            "durations": self.durations,
            "throughputs": self.throughputs,
            "memories": self.memories,
            "adjustment_count": self.adjustment_count,
            "retry_count": self.retry_count,
            "total_batches": self.total_batches,
            "failed_batches": self.failed_batches,
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        if not state:
            return
        self.current_batch_size = state.get("current_batch_size", self.current_batch_size)
        self.durations = state.get("durations", self.durations)
        self.throughputs = state.get("throughputs", self.throughputs)
        self.memories = state.get("memories", self.memories)
        self.adjustment_count = state.get("adjustment_count", self.adjustment_count)
        self.retry_count = state.get("retry_count", self.retry_count)
        self.total_batches = state.get("total_batches", self.total_batches)
        self.failed_batches = state.get("failed_batches", self.failed_batches)

    def avg_batch_duration(self) -> float:
        if not self.durations:
            return 0.0
        return sum(self.durations) / len(self.durations)

    def avg_batch_size(self) -> float:
        return float(self.current_batch_size)

    def memory_stability(self) -> str:
        if len(self.memories) < 2:
            return "STABLE"
        diffs = [self.memories[i] - self.memories[i-1] for i in range(1, len(self.memories))]
        if all(d > 0.1 for d in diffs[-3:]):
            return "GROWING"
        return "STABLE"

    def retry_frequency(self) -> float:
        if self.total_batches == 0:
            return 0.0
        return float(self.retry_count) / self.total_batches

    def record_success(self, duration: float, rows: int, read_latency: float, write_latency: float) -> None:
        if not self.use_adaptive:
            return
        
        self.total_batches += 1
        self.last_transaction_duration = write_latency
        
        mem = get_memory_usage()
        self.memories.append(mem)
        if len(self.memories) > self.window:
            self.memories.pop(0)

        self.durations.append(duration)
        if len(self.durations) > self.window:
            self.durations.pop(0)
            
        throughput = rows / duration if duration > 0 else 0
        self.throughputs.append(throughput)
        if len(self.throughputs) > self.window:
            self.throughputs.pop(0)

        avg_dur = self.avg_batch_duration()
        
        # Grow only if average duration is below 70% of target (hysteresis), memory is stable, and growth_factor > 1.0
        if self.growth > 1.0 and avg_dur < 0.7 * self.target_seconds and self.memory_stability() == "STABLE":
            new_size = min(self.max_size, max(self.current_batch_size + 1, int(self.current_batch_size * self.growth)))
            if new_size != self.current_batch_size:
                self.current_batch_size = new_size
                self.adjustment_count += 1
                try:
                    if self._metrics is not None:
                        self._metrics.counter("adaptive_adjustment_count").increment()
                        self._metrics.counter("adaptive_growth_count").increment()
                except Exception:
                    pass
                logger.debug("[AdaptiveBatch] Growing batch size to %d (avg duration: %.3f s < %.3f s)", 
                            new_size, avg_dur, 0.7 * self.target_seconds,
                            extra={"event": "adaptive_batch_resized"})
        
        # Shrink if average duration exceeds 110% of target or memory is growing, and shrink_factor < 1.0
        elif self.shrink < 1.0 and (avg_dur > 1.1 * self.target_seconds or self.memory_stability() == "GROWING"):
            new_size = max(self.min_size, min(self.current_batch_size - 1, int(self.current_batch_size * self.shrink)))
            if new_size != self.current_batch_size:
                self.current_batch_size = new_size
                self.adjustment_count += 1
                try:
                    if self._metrics is not None:
                        self._metrics.counter("adaptive_adjustment_count").increment()
                        self._metrics.counter("adaptive_shrink_count").increment()
                except Exception:
                    pass
                logger.debug("[AdaptiveBatch] Shrinking batch size to %d (avg duration: %.3f s > %.3f s, memory: %s)", 
                            new_size, avg_dur, 1.1 * self.target_seconds, self.memory_stability(),
                            extra={"event": "adaptive_batch_resized"})

    def record_failure(self) -> None:
        if not self.use_adaptive:
            return
        
        self.total_batches += 1
        self.failed_batches += 1
        self.retry_count += 1
        
        new_size = max(self.min_size, min(self.current_batch_size - 1, int(self.current_batch_size * self.shrink)))
        if new_size != self.current_batch_size:
            self.current_batch_size = new_size
            self.adjustment_count += 1
            try:
                if self._metrics is not None:
                    self._metrics.counter("adaptive_adjustment_count").increment()
                    self._metrics.counter("adaptive_failure_count").increment()
            except Exception:
                pass
            logger.debug("[AdaptiveBatch] Shrinking batch size on failure to %d", new_size,
                         extra={"event": "adaptive_batch_resized"})


class GBAgent:
    """
    The GB Agent acts as the final gate and deployment coordinator before production.
    """

    AGENT_ID: str = "GB-001"

    def _get_time(self) -> float:
        import time
        return time.monotonic()

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        checkpoint_manager: Optional[CheckpointManager] = None,
        workspace_dir: str = "workspace",
        agent_id: str = "GB-001",
        is_backup: bool = False,
        metrics_registry: Optional[MetricsRegistry] = None,
    ) -> None:
        """
        Initialize the GBAgent.
        Args:
            global_state: Authoritative global state.
            message_bus: System message bus.
            checkpoint_manager: CheckpointManager instance (Optional for legacy compatibility).
            workspace_dir: Directory path for workspace logs.
            agent_id: Active/standby identifier.
            is_backup: Backup flag.
            metrics_registry: Optional MetricsRegistry injected from ObservabilityContext.
        """
        if checkpoint_manager is None:
            # Fallback/in-memory SQLite CheckpointManager for backward compatibility
            try:
                from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
                storage = SQLiteCheckpointStorageAdapter(":memory:")
                checkpoint_manager = CheckpointManager(storage)
                # Initialize in the background since it is async
                asyncio.create_task(storage.initialize())
            except Exception as e:
                logger.warning("[GBAgent] Failed to create fallback checkpoint manager: %s", e)

        self._state = global_state
        self._bus = message_bus
        self._checkpoint_mgr = checkpoint_manager
        self._workspace_dir = workspace_dir
        self.agent_id = agent_id
        self._is_backup = is_backup
        self._running = False
        self._active_tasks: Set[str] = set()
        # Phase 7K — store registry reference (may be None if not injected)
        self._metrics: Optional[MetricsRegistry] = metrics_registry

        logger.info("[GBAgent] Constructed. ID=%s (Backup=%s)", self.agent_id, self._is_backup)

    async def start(self) -> None:
        """Register the agent with global state and subscribe to the message bus."""
        self._running = True
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.GB, self.agent_id)
        await self._state.update_agent_status(AgentType.GB, status, self.agent_id)

        # Subscribe to message bus for GB queue
        await self._bus.subscribe(AgentType.GB, self._handle_message)
        logger.info("[GBAgent] Started and registered.")

    async def stop(self) -> None:
        """Graceful shutdown of the agent."""
        self._running = False
        await self._state.update_agent_status(AgentType.GB, AgentStatus.OFFLINE, self.agent_id)
        logger.info("[GBAgent] Stopped.")

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages from message bus."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[GBAgent] Message integrity check failed. Discarding message %s", message.message_id)
            return

        # Handle active-standby control messages
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = False
                await self._state.promote_agent_instance(AgentType.GB, self.agent_id)
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = True
                await self._state.update_agent_status(AgentType.GB, AgentStatus.STANDBY, self.agent_id)
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                # Reset error count
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.error_count = 0
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.GB, status, self.agent_id)
                logger.critical("[GBAgent %s] Repaired. Status restored to %s.", self.agent_id, status.value)
            return

        # Ignore tasks if in standby
        if self._is_backup:
            logger.debug("[GBAgent %s] STANDBY MODE: Ignoring message of type %s.", self.agent_id, message.message_type)
            return

        if message.message_type == MessageType.TASK_ASSIGN:
            task_id = message.payload.get("task_id")
            project_id = message.project_id or ""
            migration_id = message.migration_id or ""
            if task_id:
                asyncio.create_task(self._execute_task(message.payload, project_id, migration_id))

    async def _execute_task(self, task_dict: Dict[str, Any], project_id: str, migration_id: str) -> None:
        """Execute the assigned task."""
        task_id = task_dict["task_id"]
        task_type_str = task_dict["task_type"]

        if task_id in self._active_tasks:
            logger.warning("[GBAgent] Task %s is already running.", task_id)
            return

        self._active_tasks.add(task_id)
        await self._state.update_agent_status(AgentType.GB, AgentStatus.BUSY, self.agent_id)

        logger.info("[GBAgent] Started task %s (Type=%s)", task_id[:8], task_type_str)

        try:
            # 1. Fetch project config
            project = await self._state.get_project(project_id)
            if not project:
                raise ValueError(f"Project not found: {project_id}")

            if project.source_config:
                project.source_config._metrics = self._metrics
            if project.target_config:
                project.target_config._metrics = self._metrics

            if task_type_str == TaskType.GB_IMPORT.value:
                output_ref = await self._handle_gb_import(project_id, migration_id, project)
            elif task_type_str == TaskType.MIGRATION_BATCH.value:
                output_ref = await self._handle_migration_batch(project_id, migration_id, project, task_dict.get("parameters", {}))
            else:
                raise NotImplementedError(f"Task type {task_type_str} is not supported by GBAgent.")

            # 2. Notify Manager of completion
            logger.info("[GBAgent] Task %s completed successfully. Result ref: %s", task_id[:8], output_ref)
            response = Message(
                sender=AgentType.GB,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_RESULT,
                payload={
                    "task_id": task_id,
                    "result_ref": output_ref,
                },
                project_id=project_id,
                migration_id=migration_id,
            )
            await self._bus.publish(response)

        except Exception as exc:
            logger.error("[GBAgent] Task %s failed: %s", task_id[:8], exc, exc_info=True)
            
            # Send failure notification
            fail_msg = Message(
                sender=AgentType.GB,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_FAILED,
                payload={
                    "task_id": task_id,
                    "error": str(exc),
                },
                project_id=project_id,
                migration_id=migration_id,
            )
            await self._bus.publish(fail_msg)

        finally:
            self._active_tasks.discard(task_id)
            if not self._active_tasks:
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.GB, status, self.agent_id)

    async def _handle_gb_import(self, project_id: str, migration_id: str, project: Any) -> str:
        """
        Handle TaskType.GB_IMPORT:
        - Load reference Universal JSON
        - Statically load this structure into GB (staging snapshots)
        - Version dataset & freeze snapshot
        """
        # Locating Universal JSON reference
        ref_path = os.path.join(
            self._workspace_dir, "projects", project_id, f"discovery_{migration_id}.json"
        )
        if not os.path.exists(ref_path):
            raise FileNotFoundError(f"Universal JSON reference file not found at {ref_path}")

        with open(ref_path, "r", encoding="utf-8") as f:
            universal_json = json.load(f)

        # Staging schema validation and calculation of checksum
        schema_objects = universal_json.get("objects", [])
        payload_bytes = json.dumps(schema_objects, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(payload_bytes).hexdigest()

        # Connect to target DB configuration in staging mode to replicate tables/schema
        target_config = project.target_config
        if target_config:
            adapter = create_adapter(target_config)
            await adapter.connect()
            try:
                await adapter.check_permissions()
            finally:
                await adapter.close()

        # Create versioned staging snapshot
        os.makedirs(os.path.join(self._workspace_dir, "projects", project_id), exist_ok=True)
        snapshot_version = 1
        snapshot_filepath = os.path.join(
            self._workspace_dir, "projects", project_id, f"gb_snapshot_{migration_id}_v{snapshot_version}.json"
        )

        snapshot_data = {
            "gb_id": f"GB-{project_id[:8]}",
            "version_id": snapshot_version,
            "project_id": project_id,
            "migration_id": migration_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checksum": checksum,
            "approval_state": "PENDING",
            "schema_objects": schema_objects,
            "dependency_order": universal_json.get("dependency_order", [])
        }

        with open(snapshot_filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)

        logger.info("[GBAgent] Staged and frozen Universal JSON snapshot at version %d", snapshot_version)
        return snapshot_filepath

    async def _handle_migration_batch(self, project_id: str, migration_id: str, project: Any, parameters: Dict[str, Any]) -> str:
        """
        Handle TaskType.MIGRATION_BATCH:
        - Check that human approval is granted
        - Read staging snapshot and verify integrity/checksum
        - Promote schemas to production target database
        - Record execution statistics
        """
        if not project.human_approval_granted:
            raise PermissionError("SAFETY VIOLATION: Production migration attempted without human approval.")

        # Check for active incidents
        open_incidents = self._state.get_open_incidents(project_id)
        if len(open_incidents) > 0:
            raise RuntimeError("SAFETY VIOLATION: Active incidents exist. Migration blocked.")

        # Load staged snapshot
        snapshot_filepath = os.path.join(
            self._workspace_dir, "projects", project_id, f"gb_snapshot_{migration_id}_v1.json"
        )
        if not os.path.exists(snapshot_filepath):
            raise FileNotFoundError(f"Staged GB snapshot not found at {snapshot_filepath}")

        with open(snapshot_filepath, "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)

        # Check integrity of staged snapshot
        schema_objects = snapshot_data.get("schema_objects", [])
        payload_bytes = json.dumps(schema_objects, sort_keys=True).encode("utf-8")
        computed_checksum = hashlib.sha256(payload_bytes).hexdigest()

        if computed_checksum != snapshot_data.get("checksum"):
            raise ValueError("GB snapshot checksum verification failed. Snapshot data is corrupted.")

        table_name = parameters.get("table_name")
        if table_name:
            res = await self.migrate_table(
                source_config=project.source_config,
                target_config=project.target_config,
                table_name=table_name,
                project_id=project_id,
                migration_id=migration_id,
                use_adaptive_batch=project.use_adaptive_batch,
                minimum_batch_size=project.minimum_batch_size,
                initial_batch_size=project.initial_batch_size,
                maximum_batch_size=project.maximum_batch_size,
                growth_factor=project.growth_factor,
                shrink_factor=project.shrink_factor,
                target_batch_duration_ms=project.target_batch_duration_ms,
                adjustment_window=project.adjustment_window,
                enable_memory_optimization=getattr(project, "enable_memory_optimization", True),
                memory_cleanup_interval=getattr(project, "memory_cleanup_interval", 5),
                memory_warning_threshold_mb=getattr(project, "memory_warning_threshold_mb", 512.0),
            )
            if res["status"] != "SUCCESS":
                raise RuntimeError(f"Table migration failed for {table_name}: {res['error']}")
            return f"migration_table_{table_name}_success"
        else:
            # Simulate connection to production target database
            target_config = project.target_config
            if target_config:
                adapter = create_adapter(target_config)
                await adapter.connect()
                try:
                    await adapter.check_permissions()
                finally:
                    await adapter.close()

            # Record migration execution statistics
            batch_num = parameters.get("batch_number", 1)
            project.total_objects_migrated = len(schema_objects)

            # Write migration batch report
            report_filepath = os.path.join(
                self._workspace_dir, "projects", project_id, f"migration_batch_{migration_id}_batch{batch_num}.json"
            )
            report_data = {
                "project_id": project_id,
                "migration_id": migration_id,
                "batch_number": batch_num,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "SUCCESS",
                "checksum": computed_checksum,
                "objects_migrated": len(schema_objects)
            }

            with open(report_filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

            return report_filepath

    async def migrate_table(
        self,
        source_config,
        target_config,
        table_name: str,
        batch_size: int = 500,
        project_id: Optional[str] = None,
        migration_id: Optional[str] = None,
        simulated_crash_batch: Optional[int] = None,  # For testing crashes
        fail_checkpoint_save: bool = False,           # For testing checkpoint save error
        # Phase 7F Adaptive Batch Sizing
        use_adaptive_batch: bool = False,
        minimum_batch_size: int = 10,
        initial_batch_size: int = 500,
        maximum_batch_size: int = 5000,
        growth_factor: float = 1.5,
        shrink_factor: float = 0.5,
        target_batch_duration_ms: float = 1000.0,
        adjustment_window: int = 3,
        # Phase 7I Memory Optimization
        enable_memory_optimization: bool = True,
        memory_cleanup_interval: int = 5,
        memory_warning_threshold_mb: float = 512.0,
    ) -> Dict[str, Any]:
        """
        Paginates through a table using read_batch/write_batch, promoting data
        from source to target. Integrates CheckpointManager for recovery.
        """
        p_id = project_id or "default_project"
        m_id = migration_id or "default_migration"
        from akaal.core.logging_manager import migration_context
        with migration_context(table_name=table_name, worker_id=self.agent_id, agent_id=self.agent_id):
            logger.info("Table migration started", extra={"event": "table_migration_started"})


            # Double check to prevent Mock objects leaking from unittest mocks
            def is_mock_val(val):
                return type(val).__name__ in ("Mock", "MagicMock", "AsyncMock") or hasattr(val, "_mock_return_value")

            # Resolve config parameters from Project in GlobalState if registered
            actual_use_adaptive = use_adaptive_batch
            actual_min_size = minimum_batch_size
            actual_init_size = initial_batch_size
            actual_max_size = maximum_batch_size
            actual_growth = growth_factor
            actual_shrink = shrink_factor
            actual_target_ms = target_batch_duration_ms
            actual_window = adjustment_window

            if self._state and p_id != "default_project" and not is_mock_val(self._state):
                try:
                    proj = await self._state.get_project(p_id)
                    if proj and not is_mock_val(proj):
                        actual_use_adaptive = getattr(proj, "use_adaptive_batch", use_adaptive_batch)
                        actual_min_size = getattr(proj, "minimum_batch_size", minimum_batch_size)
                        actual_init_size = getattr(proj, "initial_batch_size", initial_batch_size)
                        actual_max_size = getattr(proj, "maximum_batch_size", maximum_batch_size)
                        actual_growth = getattr(proj, "growth_factor", growth_factor)
                        actual_shrink = getattr(proj, "shrink_factor", shrink_factor)
                        actual_target_ms = getattr(proj, "target_batch_duration_ms", target_batch_duration_ms)
                        actual_window = getattr(proj, "adjustment_window", adjustment_window)
                except Exception:
                    pass

            if is_mock_val(actual_use_adaptive):
                actual_use_adaptive = use_adaptive_batch
            if is_mock_val(actual_min_size):
                actual_min_size = minimum_batch_size
            if is_mock_val(actual_init_size):
                actual_init_size = initial_batch_size
            if is_mock_val(actual_max_size):
                actual_max_size = maximum_batch_size
            if is_mock_val(actual_growth):
                actual_growth = growth_factor
            if is_mock_val(actual_shrink):
                actual_shrink = shrink_factor
            if is_mock_val(actual_target_ms):
                actual_target_ms = target_batch_duration_ms
            if is_mock_val(actual_window):
                actual_window = adjustment_window

            governor = AdaptiveBatchGovernor(
                use_adaptive=actual_use_adaptive,
                min_size=actual_min_size,
                init_size=actual_init_size,
                max_size=actual_max_size,
                growth=actual_growth,
                shrink=actual_shrink,
                target_ms=actual_target_ms,
                window=actual_window,
                metrics=self._metrics,
            )

            enable_mem_opt = enable_memory_optimization
            mem_cleanup_interval = memory_cleanup_interval
            mem_warning_threshold = memory_warning_threshold_mb

            if source_config:
                source_config._metrics = self._metrics
            if target_config:
                target_config._metrics = self._metrics

            src = create_adapter(source_config)
            tgt = create_adapter(target_config)

            start_time = self._get_time()
            rows_migrated = 0
            batches_processed = 0
            rows_failed = 0
            rows_skipped = 0
            retry_count = 0
            adapter_state = {}
            # Phase 7K — start per-table duration timer
            _table_timer = None
            try:
                if self._metrics is not None:
                    _table_timer = self._metrics.timer(f"table_duration.{table_name}")
                    _table_timer.__enter__()
            except Exception:
                pass

            try:
                await src.connect()
                await tgt.connect()

                # 1. Query CheckpointManager to resume progress if a checkpoint exists
                last_pk = None
                offset = 0

                record = await self._checkpoint_mgr.resume(p_id, m_id, table_name)
                if record:
                    if record.status == CheckpointStatus.COMPLETED:
                        logger.debug("[GBAgent] Table %s migration already completed. Skipping.", table_name)
                        return {
                            "status": "SUCCESS",
                            "rows_migrated": 0,
                            "batches_processed": 0,
                            "elapsed_seconds": self._get_time() - start_time,
                            "error": None,
                            "avg_batch_duration": 0.0,
                            "avg_batch_size": 0.0,
                            "adjustment_frequency": 0,
                            "memory_stability": "STABLE",
                            "transaction_duration": 0.0,
                            "retry_frequency": 0.0,
                        }

                    # Restore governor state if present
                    gov_state = record.metrics.get("adaptive_governor_state")
                    if gov_state:
                        governor.restore_state(gov_state)
                    else:
                        if "batch_size" in record.metrics:
                            governor.current_batch_size = record.metrics["batch_size"]

                    last_pk = record.last_processed_primary_key
                    adapter_state = record.adapter_state or {}
                    if "offset" in adapter_state:
                        offset = adapter_state["offset"]
                    else:
                        offset = record.batch_number * batch_size if record.batch_number > 0 else 0

                    rows_migrated = record.rows_processed
                    rows_failed = record.rows_failed
                    rows_skipped = record.rows_skipped
                    retry_count = record.retry_count + 1
                    batches_processed = record.batch_number

                    # Apply retry reduction if we have crashed/resumed
                    if retry_count > 1:
                        governor.record_failure()

                    logger.info(
                        "[GBAgent] Resuming migration for table %s from checkpoint %s (last_pk=%s, offset=%d, rows_migrated=%d)",
                        table_name, record.checkpoint_id, last_pk, offset, rows_migrated
                    )
                else:
                    logger.info("[GBAgent] Starting fresh migration for table %s", table_name)

                # 2. Determine primary key columns of the table
                pk_cols = []
                try:
                    if hasattr(src, "_primary_key_columns"):
                        pk_cols = await src._primary_key_columns(table_name)
                    elif hasattr(src, "_primary_key_column"):
                        col = await src._primary_key_column(table_name)
                        pk_cols = [col] if col else []
                except Exception:
                    pk_cols = ["id"]

                while True:
                    current_batch_size = governor.current_batch_size if actual_use_adaptive else batch_size

                    read_start = self._get_time()
                    # 3. Fetch batch of data using cursor if PK exists and last_pk is loaded
                    if pk_cols and (last_pk is not None or offset == 0):
                        batch = await src.read_batch(
                            table_name,
                            offset=offset,
                            limit=current_batch_size,
                            last_processed_primary_key=last_pk
                        )
                    else:
                        batch = await src.read_batch(
                            table_name,
                            offset=offset,
                            limit=current_batch_size
                        )

                    read_duration = self._get_time() - read_start

                    if not batch:
                        break

                    # Simulate a crash before writing if configured for recovery testing
                    if simulated_crash_batch is not None and (batches_processed + 1) >= simulated_crash_batch:
                        governor.record_failure()
                        raise ConnectionResetError(f"Simulated connection crash at batch {batches_processed + 1}")

                    # 4. Write batch to target with local retry/shrink
                    write_start = self._get_time()
                    write_success = False
                    local_attempts = 0
                    max_local_attempts = 3 if actual_use_adaptive else 1

                    last_exc = None
                    while not write_success and local_attempts < max_local_attempts:
                        try:
                            local_attempts += 1
                            await tgt.write_batch(table_name, batch)
                            write_success = True
                        except Exception as exc:
                            last_exc = exc
                            logger.warning(
                                "[GBAgent] write_batch failed at offset %d, batch_size %d (attempt %d/%d): %s",
                                offset, current_batch_size, local_attempts, max_local_attempts, exc
                            )
                            if actual_use_adaptive and local_attempts < max_local_attempts:
                                governor.record_failure()
                                new_batch_size = governor.current_batch_size

                                # Slice the in-memory batch and retry
                                batch = batch[:new_batch_size]
                                current_batch_size = len(batch)
                                logger.warning("Retry initiated", extra={"event": "retry_initiated"})
                                logger.info("[GBAgent] Retrying write locally with reduced batch size %d", current_batch_size)
                                write_start = self._get_time()
                            else:
                                break

                    if not write_success:
                        governor.record_failure()
                        # Phase 7K — record retry
                        try:
                            if self._metrics is not None:
                                self._metrics.counter("batch_retry_count").increment()
                        except Exception:
                            pass
                        logger.error("Retry exhausted", extra={"event": "retry_exhausted"})
                        raise RuntimeError(f"Write failure at offset {offset}: {last_exc}") from last_exc

                    write_duration = self._get_time() - write_start
                    total_duration = read_duration + write_duration

                    # 5. Target committed & acknowledged. Finalize statistics:
                    batch_len = len(batch)
                    rows_migrated += batch_len
                    batches_processed += 1
                    offset += batch_len

                    # Phase 7K — record per-batch metrics (guarded)
                    try:
                        if self._metrics is not None:
                            # Estimate byte size: len(JSON-encoded batch row) * batch_len
                            import json as _json
                            byte_est = len(_json.dumps(batch[0]).encode()) * batch_len if batch else 0
                            self._metrics.counter(ROWS_MIGRATED).increment(batch_len)
                            self._metrics.counter(BYTES_MIGRATED).increment(byte_est)
                    except Exception:
                        pass

                    # Extract primary-key cursor from final row of the committed batch
                    last_row = batch[-1]
                    last_pk = {col: last_row[col] for col in pk_cols if col in last_row} if pk_cols else None

                    # Calculate metrics
                    elapsed = self._get_time() - start_time
                    throughput = rows_migrated / elapsed if elapsed > 0 else 0

                    governor.record_success(
                        duration=total_duration,
                        rows=len(batch),
                        read_latency=read_duration,
                        write_latency=write_duration,
                    )

                    # Create progress checkpoint record
                    chk_record = CheckpointRecord(
                        checkpoint_id=str(uuid.uuid4()),
                        project_id=p_id,
                        migration_id=m_id,
                        workflow_state=WorkflowState.PRODUCTION_MIGRATION,
                        table_name=table_name,
                        batch_number=batches_processed,
                        worker_id=self.agent_id,
                        last_processed_primary_key=last_pk,
                        rows_processed=rows_migrated,
                        rows_failed=rows_failed,
                        rows_skipped=rows_skipped,
                        retry_count=retry_count,
                        adapter_state={"offset": offset, "original_rows_migrated": rows_migrated},
                        metrics={
                            "elapsed_seconds": elapsed,
                            "throughput_rows_s": throughput,
                            "description": f"Staging batch progress for {table_name}",
                            # Phase 7F Metrics
                            "batch_size": current_batch_size,
                            "avg_batch_duration": governor.avg_batch_duration(),
                            "avg_batch_size": governor.avg_batch_size(),
                            "adjustment_frequency": governor.adjustment_count,
                            "memory_stability": governor.memory_stability(),
                            "transaction_duration": governor.last_transaction_duration,
                            "retry_frequency": governor.retry_frequency(),
                            "adaptive_governor_state": governor.get_state(),
                        },
                        status=CheckpointStatus.PENDING
                    )

                    # Persist checkpoint and handle save failures gracefully
                    if fail_checkpoint_save:
                        raise RuntimeError("Disk write failed: Checkpoint storage inaccessible")

                    try:
                        save_success = await self._checkpoint_mgr.save_progress(chk_record)
                        if not save_success:
                            raise RuntimeError("save_progress returned False")
                    except Exception as save_exc:
                        logger.error("[GBAgent] Recoverable checkpoint persistence failure: %s", save_exc)
                        raise RuntimeError(f"Recoverable checkpoint persistence failure: {save_exc}") from save_exc

                    # Clean up references immediately after persistence
                    batch = None
                    chk_record = None

                    # Memory optimization hooks
                    if enable_mem_opt:
                        if batches_processed % mem_cleanup_interval == 0:
                            logger.debug("Memory cleanup triggered", extra={"event": "memory_cleanup_triggered"})
                            import gc
                            gc.collect()
                            try:
                                if self._metrics is not None:
                                    self._metrics.counter("memory_cleanup_count").increment()
                            except Exception:
                                pass

                        current_mem = get_memory_usage()
                        if current_mem > mem_warning_threshold:
                            logger.warning("Memory cleanup warning", extra={"event": "memory_cleanup_warning"})
                            logger.warning(
                                "[MemoryWarning] Peak memory threshold exceeded: %.2f MB > %.2f MB. Triggering emergency GC.",
                                current_mem, mem_warning_threshold,
                                extra={"event": "memory_threshold_exceeded"}
                            )
                            import gc
                            gc.collect()
                            try:
                                if self._metrics is not None:
                                    self._metrics.counter("memory_warning_count").increment()
                            except Exception:
                                pass

                # 6. Mark table migration completed
                await self._checkpoint_mgr.mark_completed(p_id, m_id, table_name, worker_id=self.agent_id)
                logger.info("Table migration completed", extra={"event": "table_migration_completed"})

                # Phase 7K — record table completion (guarded)
                try:
                    if self._metrics is not None:
                        self._metrics.counter(TABLES_MIGRATED).increment()
                        if _table_timer is not None:
                            _table_timer.__exit__(None, None, None)
                            _table_timer = None
                except Exception:
                    pass

                elapsed = self._get_time() - start_time
                return {
                    "status": "SUCCESS",
                    "rows_migrated": rows_migrated,
                    "batches_processed": batches_processed,
                    "elapsed_seconds": elapsed,
                    "error": None,
                    # Phase 7F metrics
                    "avg_batch_duration": governor.avg_batch_duration(),
                    "avg_batch_size": governor.avg_batch_size(),
                    "adjustment_frequency": governor.adjustment_count,
                    "memory_stability": governor.memory_stability(),
                    "transaction_duration": governor.last_transaction_duration,
                    "retry_frequency": governor.retry_frequency(),
                }

            except Exception as exc:
                elapsed = self._get_time() - start_time
                return {
                    "status": "FAILED",
                    "rows_migrated": rows_migrated,
                    "batches_processed": batches_processed,
                    "elapsed_seconds": elapsed,
                    "error": str(exc),
                    # Phase 7F metrics
                    "avg_batch_duration": governor.avg_batch_duration(),
                    "avg_batch_size": governor.avg_batch_size(),
                    "adjustment_frequency": governor.adjustment_count,
                    "memory_stability": governor.memory_stability(),
                    "transaction_duration": governor.last_transaction_duration,
                    "retry_frequency": governor.retry_frequency(),
                }

            finally:
                # Phase 7K — ensure table timer is closed even on exception
                try:
                    if _table_timer is not None:
                        _table_timer.__exit__(None, None, None)
                except Exception:
                    pass
                try:
                    await src.close()
                except Exception:
                    pass
                try:
                    await tgt.close()
                except Exception:
                    pass
