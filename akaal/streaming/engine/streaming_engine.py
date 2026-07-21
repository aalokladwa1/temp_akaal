"""
StreamingExecutionEngine module for Platform 3.
Orchestrates stream buffers, memory pools, fused operators, watermarking, windowing, and backpressure flow control.
Contains ZERO CDC, migration logic, or database adapter code.
"""

from typing import List, Dict, Optional, Any, Tuple
from threading import RLock
import time
import logging

from akaal.streaming.domain.identifiers import StreamId, BatchId
from akaal.streaming.domain.models import (
    StreamRecord, Watermark, StreamWindow, StreamBatch, ColumnarBatch, StreamConfig
)
from akaal.streaming.domain.errors import StreamingExecutionError
from akaal.streaming.memory.pool import StreamMemoryPool
from akaal.streaming.memory.columnar import ColumnarMemoryPipeline
from akaal.streaming.time.watermark import BoundedOutOfOrdernessWatermark
from akaal.streaming.time.lateness import AllowedLateness
from akaal.streaming.windowing.operator import WindowOperator
from akaal.streaming.operators.base import StreamOperator
from akaal.streaming.operators.fusion import StreamGraphOptimizer
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.streaming.flow.adaptive import AdaptiveStreamTuner

logger = logging.getLogger("nexusforge.streaming.engine")


class StreamingExecutionEngine:
    """
    Core StreamingExecutionEngine orchestrating end-to-end generic stream execution pipelines.
    """

    def __init__(
        self,
        config: Optional[StreamConfig] = None,
        memory_pool: Optional[StreamMemoryPool] = None,
        watermark_generator: Optional[BoundedOutOfOrdernessWatermark] = None,
    ) -> None:
        self._lock = RLock()
        self.config = config or StreamConfig()
        self.memory_pool = memory_pool or StreamMemoryPool(max_pool_size_mb=self.config.max_buffer_size_mb)
        self.watermark_generator = watermark_generator or BoundedOutOfOrdernessWatermark(max_out_of_orderness_seconds=5.0)
        self.lateness_handler = AllowedLateness(allowed_lateness_seconds=self.config.allowed_lateness_seconds)
        
        self.backpressure_controller = BackpressureController(
            max_queue_capacity=self.config.batch_size * 2,
            high_watermark_ratio=self.config.high_watermark_threshold,
            low_watermark_ratio=self.config.low_watermark_threshold,
        )
        self.adaptive_tuner = AdaptiveStreamTuner(initial_batch_size=self.config.batch_size)

        self._operators: List[StreamOperator] = []
        self._fused_operator: Optional[StreamOperator] = None
        self._window_operator: Optional[WindowOperator] = None
        self._input_queue: List[StreamRecord] = []
        self._output_queue: List[StreamRecord] = []

    def register_operator(self, operator: StreamOperator) -> None:
        """Register an operator in the execution graph."""
        with self._lock:
            self._operators.append(operator)
            self._fused_operator = StreamGraphOptimizer.fuse_operators(self._operators)

    def set_window_operator(self, window_operator: WindowOperator) -> None:
        with self._lock:
            self._window_operator = window_operator

    def push_record(self, record: StreamRecord) -> bool:
        """Push a StreamRecord into the engine input queue."""
        with self._lock:
            self.backpressure_controller.check_and_update(len(self._input_queue))
            self.backpressure_controller.apply_throttling()

            # Check event-time watermark & allowed lateness
            current_wm = self.watermark_generator.current_watermark()
            if not self.lateness_handler.handle_record(record, current_wm):
                # Late record routed to side-output
                return False

            self.watermark_generator.on_record(record)
            self._input_queue.append(record)
            return True

    def process_batch(self) -> int:
        """Process pending batch in input queue through fused execution pipeline."""
        with self._lock:
            if not self._input_queue:
                return 0

            t0 = time.monotonic()
            batch_size = self.adaptive_tuner.current_batch_size
            to_process = self._input_queue[:batch_size]
            self._input_queue = self._input_queue[batch_size:]

            processed_count = 0
            for record in to_process:
                current_records = [record]

                # Pass through WindowOperator if registered
                if self._window_operator:
                    self._window_operator.process_record(record)

                # Pass through FusedStreamOperator
                if self._fused_operator:
                    out = self._fused_operator.process_element(record)
                    self._output_queue.extend(out)
                else:
                    self._output_queue.extend(current_records)

                processed_count += 1

            # Trigger Watermark evaluation
            current_wm = self.watermark_generator.current_watermark()
            if self._window_operator:
                triggered_windows = self._window_operator.trigger_watermark(current_wm)
                for window, win_records in triggered_windows:
                    logger.debug(f"Evaluated window '{window.window_id}' with {len(win_records)} records.")

            elapsed = time.monotonic() - t0
            self.adaptive_tuner.record_execution(processed_count, elapsed)
            return processed_count

    def pop_output_records(self) -> List[StreamRecord]:
        """Retrieve and clear output queue records."""
        with self._lock:
            out = list(self._output_queue)
            self._output_queue.clear()
            return out

    def get_columnar_batch(self) -> ColumnarBatch:
        """Extract output records as a ColumnarBatch."""
        with self._lock:
            records = self.pop_output_records()
            batch = StreamBatch(batch_id=BatchId.generate(), records=records, created_at=time.time())
            return ColumnarMemoryPipeline.to_columnar_batch(batch)
