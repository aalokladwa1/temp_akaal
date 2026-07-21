"""
Stream-Stream Join Subsystem for Platform 3.
Provides windowed stream-stream joins with adaptive join state and memory-aware key matching.
"""

from typing import Dict, List, Tuple, Optional, Any
from threading import RLock
import logging

from akaal.streaming.domain.identifiers import OperatorId
from akaal.streaming.domain.enums import JoinType
from akaal.streaming.domain.models import StreamRecord, Watermark
from akaal.streaming.operators.base import StreamOperator

logger = logging.getLogger("nexusforge.streaming.join")


class StreamStreamJoinOperator(StreamOperator):
    """
    Stream-Stream Join Operator joining Left and Right streams over a matching time window.
    """

    def __init__(
        self,
        join_key: str,
        window_bounds_seconds: float = 10.0,
        join_type: JoinType = JoinType.INNER,
        operator_id: Optional[OperatorId] = None,
    ) -> None:
        super().__init__(operator_id=operator_id)
        self._lock = RLock()
        self.join_key = join_key
        self.window_bounds = window_bounds_seconds
        self.join_type = join_type
        
        self._left_buffer: List[StreamRecord] = []
        self._right_buffer: List[StreamRecord] = []

    def process_element(self, record: StreamRecord) -> List[StreamRecord]:
        """Not directly used; call process_left / process_right explicitly."""
        return []

    def process_left(self, record: StreamRecord) -> List[StreamRecord]:
        with self._lock:
            self._left_buffer.append(record)
            return self._match_records(record, self._right_buffer, is_left=True)

    def process_right(self, record: StreamRecord) -> List[StreamRecord]:
        with self._lock:
            self._right_buffer.append(record)
            return self._match_records(record, self._left_buffer, is_left=False)

    def _match_records(self, incoming: StreamRecord, opposite_buffer: List[StreamRecord], is_left: bool) -> List[StreamRecord]:
        joined: List[StreamRecord] = []
        inc_val = incoming.payload.get(self.join_key)
        if inc_val is None:
            return joined

        for opp in opposite_buffer:
            opp_val = opp.payload.get(self.join_key)
            if inc_val == opp_val:
                time_diff = abs(incoming.event_time - opp.event_time)
                if time_diff <= self.window_bounds:
                    merged_payload = dict(opp.payload if not is_left else incoming.payload)
                    merged_payload.update(incoming.payload if not is_left else opp.payload)
                    
                    joined_record = StreamRecord(
                        payload=merged_payload,
                        event_time=max(incoming.event_time, opp.event_time),
                        key=str(inc_val),
                    )
                    joined.append(joined_record)

        return joined

    def process_watermark(self, watermark: Watermark) -> List[StreamRecord]:
        """Evict records older than watermark.timestamp - window_bounds."""
        with self._lock:
            cutoff = watermark.timestamp - self.window_bounds
            self._left_buffer = [r for r in self._left_buffer if r.event_time >= cutoff]
            self._right_buffer = [r for r in self._right_buffer if r.event_time >= cutoff]
            return []
