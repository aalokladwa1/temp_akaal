"""
Unit tests for Pipeline Fusion and AdaptiveStreamTuner.
"""

from akaal.streaming.domain.models import StreamRecord
from akaal.streaming.operators.base import MapOperator, FilterOperator
from akaal.streaming.operators.fusion import StreamGraphOptimizer, FusedStreamOperator
from akaal.streaming.flow.adaptive import AdaptiveStreamTuner


def test_pipeline_fusion_execution():
    op1 = MapOperator(fn=lambda d: {"v": d["v"] * 2})
    op2 = FilterOperator(predicate=lambda d: d["v"] > 10)
    op3 = MapOperator(fn=lambda d: {"v": d["v"] + 1})

    fused = StreamGraphOptimizer.fuse_operators([op1, op2, op3])
    assert isinstance(fused, FusedStreamOperator)

    # Test record payload v=3 -> map1 -> 6 -> filter (fails > 10) -> []
    res1 = fused.process_element(StreamRecord(payload={"v": 3}, event_time=1.0))
    assert len(res1) == 0

    # Test record payload v=8 -> map1 -> 16 -> filter (passes > 10) -> map2 -> 17
    res2 = fused.process_element(StreamRecord(payload={"v": 8}, event_time=1.0))
    assert len(res2) == 1
    assert res2[0].payload["v"] == 17


def test_adaptive_stream_tuner():
    tuner = AdaptiveStreamTuner(initial_batch_size=100, min_batch_size=10, max_batch_size=1000)
    assert tuner.current_batch_size == 100

    # High latency (0.2s) -> scale down batch size
    b1 = tuner.record_execution(processed_records_count=100, latency_seconds=0.2)
    assert b1 < 100

    # Low latency (0.001s) -> scale up batch size
    b2 = tuner.record_execution(processed_records_count=100, latency_seconds=0.001)
    assert b2 > b1
