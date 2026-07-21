"""
StreamingRuntimeV1 Public Entry Point Facade for Platform 3.
Provides a clean, Arrow-independent, generic streaming execution facade for external caller applications.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from threading import RLock
import logging

from akaal.streaming.domain.models import StreamRecord, StreamConfig, ColumnarBatch
from akaal.streaming.domain.enums import BackpressureState
from akaal.streaming.engine.streaming_engine import StreamingExecutionEngine
from akaal.streaming.operators.base import StreamOperator

logger = logging.getLogger("nexusforge.streaming.runtime")


class StreamingRuntimeV1(ABC):
    """Abstract StreamingRuntimeV1 public facade interface."""

    @abstractmethod
    def add_operator(self, operator: StreamOperator) -> None: pass

    @abstractmethod
    def push(self, record: StreamRecord) -> bool: pass

    @abstractmethod
    def execute_step(self) -> int: pass

    @abstractmethod
    def collect_output(self) -> List[StreamRecord]: pass

    @abstractmethod
    def get_backpressure_state(self) -> BackpressureState: pass


class DefaultStreamingRuntimeV1(StreamingRuntimeV1):
    """
    Default production implementation of StreamingRuntimeV1.
    """

    def __init__(self, config: Optional[StreamConfig] = None) -> None:
        self._lock = RLock()
        self.config = config or StreamConfig()
        self.engine = StreamingExecutionEngine(config=self.config)

    def add_operator(self, operator: StreamOperator) -> None:
        with self._lock:
            self.engine.register_operator(operator)

    def push(self, record: StreamRecord) -> bool:
        return self.engine.push_record(record)

    def execute_step(self) -> int:
        return self.engine.process_batch()

    def collect_output(self) -> List[StreamRecord]:
        return self.engine.pop_output_records()

    def collect_columnar_batch(self) -> ColumnarBatch:
        return self.engine.get_columnar_batch()

    def get_backpressure_state(self) -> BackpressureState:
        return self.engine.backpressure_controller.state
