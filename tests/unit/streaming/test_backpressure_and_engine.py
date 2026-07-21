"""
Unit tests for BackpressureController, StreamingExecutionEngine, and StreamingRuntimeV1.
"""

from akaal.streaming.domain.models import StreamRecord, StreamConfig
from akaal.streaming.domain.enums import BackpressureState
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.streaming.facade.runtime import DefaultStreamingRuntimeV1
from akaal.streaming.operators.base import MapOperator


def test_backpressure_controller_states():
    bp = BackpressureController(max_queue_capacity=100, high_watermark_ratio=0.8, low_watermark_ratio=0.2)
    assert bp.state == BackpressureState.NORMAL

    # Normal state
    bp.check_and_update(10)
    assert bp.state == BackpressureState.NORMAL

    # High watermark state
    bp.check_and_update(85)
    assert bp.state == BackpressureState.HIGH_WATERMARK

    # Throttled state
    bp.check_and_update(100)
    assert bp.state == BackpressureState.THROTTLED

    # Return to normal
    bp.check_and_update(10)
    assert bp.state == BackpressureState.NORMAL


def test_streaming_runtime_facade_and_engine():
    runtime = DefaultStreamingRuntimeV1(config=StreamConfig(batch_size=10))
    runtime.add_operator(MapOperator(fn=lambda p: {"transformed": p["num"] * 10}))

    # Push records into streaming engine
    for i in range(5):
        runtime.push(StreamRecord(payload={"num": i}, event_time=float(i)))

    # Execute batch processing step
    processed = runtime.execute_step()
    assert processed == 5

    # Collect outputs
    outputs = runtime.collect_output()
    assert len(outputs) == 5
    assert outputs[0].payload["transformed"] == 0
    assert outputs[4].payload["transformed"] == 40
