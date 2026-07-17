import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from akaal.migration.models.cdc import (
    CDCEvent,
    CDCCheckpoint,
    SynchronizationMetrics,
    SynchronizationHealth,
    SynchronizationConfiguration,
    CDCSessionState,
    ConflictResolutionPolicy,
    CDCOperationType
)
from akaal.migration.ddl.planning.cdc_planner import CDCPlanner

logger = logging.getLogger("akaal.cdc.executor")

class CDCEventBuffer:
    """
    Thread-safe Event Buffer abstraction with high/low watermark flow control backpressure management.
    """
    def __init__(self, max_depth: int):
        self.max_depth = max_depth
        self.queue: List[CDCEvent] = []
        self.paused = False
        self.hwm = int(max_depth * 0.85)
        self.lwm = int(max_depth * 0.30)
        self.lock = asyncio.Lock()

    async def push(self, event: CDCEvent) -> bool:
        async with self.lock:
            if len(self.queue) >= self.max_depth:
                # Queue overflow behavior
                logger.warning("[CDCEventBuffer] Buffer Overflow. Dropping event: %s", event.event_id)
                return False
            
            self.queue.append(event)
            if len(self.queue) >= self.hwm and not self.paused:
                self.paused = True
                logger.warning("[CDCEventBuffer] High-water mark reached (%d/%d). Ingestion paused.", len(self.queue), self.max_depth)
            return True

    async def pop_batch(self, batch_size: int) -> List[CDCEvent]:
        async with self.lock:
            batch = self.queue[:batch_size]
            self.queue = self.queue[batch_size:]
            
            if self.paused and len(self.queue) <= self.lwm:
                self.paused = False
                logger.info("[CDCEventBuffer] Low-water mark reached (%d/%d). Ingestion resumed.", len(self.queue), self.max_depth)
            return batch

    def depth(self) -> int:
        return len(self.queue)


class CDCExecutor:
    """
    Executes transaction batches on the target database, resolves conflicts, and writes checkpoints.
    """
    def __init__(self, config: SynchronizationConfiguration, metrics: SynchronizationMetrics):
        self.config = config
        self.metrics = metrics
        self.checkpoint_store: Dict[str, CDCCheckpoint] = {}

    async def execute_batch(self, events: List[CDCEvent], target_state: Dict[str, Dict[str, Any]]) -> Optional[CDCCheckpoint]:
        """
        Executes events, detects conflicts (comparing target values against before images), 
        and updates checkpoints.
        """
        if not events:
            return None

        # Build plan via planner
        planned_batch = CDCPlanner.plan_batch(events)
        
        last_event = planned_batch[-1]
        
        for event in planned_batch:
            table_key = f"{event.schema_name}.{event.table_name}"
            pk_str = str(event.primary_key_values)
            
            # Conflict Detection
            current_target_row = target_state.get(table_key, {}).get(pk_str, None)
            
            conflict_detected = False
            if event.operation == CDCOperationType.UPDATE or event.operation == CDCOperationType.DELETE:
                if current_target_row and event.before_image:
                    # Conflict if target state doesn't match expected before image values
                    for k, v in event.before_image.items():
                        if current_target_row.get(k) != v:
                            conflict_detected = True
                            break

            if conflict_detected:
                self.metrics.conflict_count += 1
                logger.warning(
                    "[CDCExecutor] Audit: Conflict detected on table %s, key %s. Resolution Policy: %s",
                    table_key, pk_str, self.config.conflict_policy.value
                )
                
                if self.config.conflict_policy == ConflictResolutionPolicy.ABORT:
                    raise RuntimeError(f"Synchronization aborted due to conflict on {table_key} for key {pk_str}")
                elif self.config.conflict_policy == ConflictResolutionPolicy.TARGET_WINS:
                    # Ignore event, target state remains
                    continue
                elif self.config.conflict_policy == ConflictResolutionPolicy.SKIP:
                    # Log conflict and skip event
                    continue
                # SOURCE_WINS falls through to apply source change

            # Apply change (simulate database write)
            if table_key not in target_state:
                target_state[table_key] = {}
            
            if event.operation == CDCOperationType.DELETE:
                if pk_str in target_state[table_key]:
                    del target_state[table_key][pk_str]
            else:
                target_state[table_key][pk_str] = event.after_image or {}

            self.metrics.events_processed += 1
            # Simple length-based byte calculation
            self.metrics.bytes_processed += len(str(event.after_image))

        # Write checkpoint
        checkpoint = CDCCheckpoint(
            session_id=self.config.session_id,
            last_processed_event_id=last_event.event_id,
            last_processed_lsn=last_event.lsn_offset or 0,
            last_processed_tx_id=last_event.tx_id,
            last_processed_timestamp=last_event.timestamp
        )
        self.checkpoint_store[self.config.session_id] = checkpoint
        
        logger.info(
            "[CDCExecutor] Audit: Checkpoint written for session %s at LSN %d",
            self.config.session_id, checkpoint.last_processed_lsn
        )
        return checkpoint


class CDCSyncSupervisor:
    """
    Coordinates session state loops, flow control, retry recovery buffers, and health diagnostics.
    """
    def __init__(self, config: SynchronizationConfiguration):
        self.config = config
        self.config.validate()
        
        self.state = CDCSessionState.INITIALIZING
        self.metrics = SynchronizationMetrics()
        self.health = SynchronizationHealth(last_heartbeat=datetime.now(timezone.utc))
        self.buffer = CDCEventBuffer(config.max_queue_depth)
        self.executor = CDCExecutor(config, self.metrics)
        
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self.state = CDCSessionState.CATCHING_UP
        self._running = True
        logger.info("[CDCSyncSupervisor] Audit: Continuous sync session starting: %s", self.config.session_id)

    async def stop(self, target_state: Dict[str, Dict[str, Any]]) -> None:
        """
        Graceful shutdown sequence: drains buffer work, updates final checkpoint, teardown resources.
        """
        logger.info("[CDCSyncSupervisor] Audit: Graceful shutdown initiated.")
        self._running = False
        
        # 1. Drain the remaining buffer
        if self.buffer.depth() > 0:
            remaining_events = await self.buffer.pop_batch(self.buffer.depth())
            await self.executor.execute_batch(remaining_events, target_state)
            
        self.state = CDCSessionState.COMPLETED
        logger.info("[CDCSyncSupervisor] Audit: Continuous sync session stopped successfully.")

    def update_heartbeat(self) -> None:
        self.health.last_heartbeat = datetime.now(timezone.utc)
        self.health.is_healthy = True

    def simulate_failure(self, err_msg: str) -> None:
        self.state = CDCSessionState.FAILED
        self.health.is_healthy = False
        self.health.last_error_message = err_msg
        logger.error("[CDCSyncSupervisor] Audit: Session entered failure state: %s", err_msg)
