"""
Base StreamOperator interface for Platform 3 - Streaming Execution Engine.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any

from akaal.streaming.domain.identifiers import OperatorId
from akaal.streaming.domain.enums import StreamOperatorType
from akaal.streaming.domain.models import StreamRecord, Watermark


class StreamOperator(ABC):
    """Abstract StreamOperator interface."""

    def __init__(self, operator_id: Optional[OperatorId] = None) -> None:
        self.operator_id = operator_id or OperatorId.generate()

    @abstractmethod
    def process_element(self, record: StreamRecord) -> List[StreamRecord]:
        """Process a single record element. Returns output records."""
        pass

    def process_watermark(self, watermark: Watermark) -> List[StreamRecord]:
        """Process watermark arrival. Default returns empty list."""
        return []

    def open(self) -> None:
        """Lifecycle hook called before processing."""
        pass

    def close(self) -> None:
        """Lifecycle hook called after processing."""
        pass


class MapOperator(StreamOperator):
    """Generic element transformation operator."""

    def __init__(self, fn: Any, operator_id: Optional[OperatorId] = None) -> None:
        super().__init__(operator_id=operator_id)
        self.fn = fn

    def process_element(self, record: StreamRecord) -> List[StreamRecord]:
        new_payload = self.fn(record.payload)
        return [
            StreamRecord(
                payload=new_payload,
                event_time=record.event_time,
                key=record.key,
                metadata=record.metadata,
            )
        ]


class FilterOperator(StreamOperator):
    """Generic element filter operator."""

    def __init__(self, predicate: Any, operator_id: Optional[OperatorId] = None) -> None:
        super().__init__(operator_id=operator_id)
        self.predicate = predicate

    def process_element(self, record: StreamRecord) -> List[StreamRecord]:
        if self.predicate(record.payload):
            return [record]
        return []
