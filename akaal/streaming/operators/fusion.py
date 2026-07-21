"""
Pipeline Fusion & StreamGraphOptimizer module.
Fuses linear chains of StreamOperators into a single FusedStreamOperator block,
minimizing intermediate memory materializations and object allocations.
"""

from typing import List, Optional
import logging

from akaal.streaming.domain.identifiers import OperatorId
from akaal.streaming.domain.models import StreamRecord, Watermark
from akaal.streaming.operators.base import StreamOperator

logger = logging.getLogger("nexusforge.streaming.fusion")


class FusedStreamOperator(StreamOperator):
    """
    Fused operator wrapping a sequence of linear operators into a single fused execution block.
    """

    def __init__(self, operators: List[StreamOperator], operator_id: Optional[OperatorId] = None) -> None:
        super().__init__(operator_id=operator_id)
        self.operators = operators

    def process_element(self, record: StreamRecord) -> List[StreamRecord]:
        current_records = [record]
        for op in self.operators:
            next_records: List[StreamRecord] = []
            for r in current_records:
                out = op.process_element(r)
                next_records.extend(out)
            current_records = next_records
            if not current_records:
                break
        return current_records

    def process_watermark(self, watermark: Watermark) -> List[StreamRecord]:
        out_records: List[StreamRecord] = []
        for op in self.operators:
            res = op.process_watermark(watermark)
            out_records.extend(res)
        return out_records

    def open(self) -> None:
        for op in self.operators:
            op.open()

    def close(self) -> None:
        for op in self.operators:
            op.close()


class StreamGraphOptimizer:
    """
    Optimizes stream operator execution graphs by fusing consecutive linear operators.
    """

    @staticmethod
    def fuse_operators(operators: List[StreamOperator]) -> StreamOperator:
        """Compress list of linear operators into a FusedStreamOperator."""
        if not operators:
            raise ValueError("Cannot fuse empty operator list.")
        if len(operators) == 1:
            return operators[0]

        logger.info(f"Fused {len(operators)} operators into a single FusedStreamOperator.")
        return FusedStreamOperator(operators=operators)
