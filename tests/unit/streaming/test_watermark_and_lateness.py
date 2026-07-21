"""
Unit tests for WatermarkGenerator and AllowedLateness.
"""

from akaal.streaming.domain.models import StreamRecord, Watermark
from akaal.streaming.time.watermark import BoundedOutOfOrdernessWatermark
from akaal.streaming.time.lateness import AllowedLateness


def test_bounded_out_of_orderness_watermark():
    wm_gen = BoundedOutOfOrdernessWatermark(max_out_of_orderness_seconds=5.0)
    assert wm_gen.current_watermark().timestamp == 0.0

    r1 = StreamRecord(payload={"a": 1}, event_time=10.0)
    wm1 = wm_gen.on_record(r1)
    assert wm1 is not None
    assert wm1.timestamp == 5.0

    # Out-of-order record within bounds
    r2 = StreamRecord(payload={"a": 2}, event_time=8.0)
    wm2 = wm_gen.on_record(r2)
    assert wm2 is None  # Watermark does not regress or advance

    # Higher event_time record
    r3 = StreamRecord(payload={"a": 3}, event_time=20.0)
    wm3 = wm_gen.on_record(r3)
    assert wm3 is not None
    assert wm3.timestamp == 15.0


def test_allowed_lateness_side_output_routing():
    lateness = AllowedLateness(allowed_lateness_seconds=5.0)
    current_wm = Watermark(timestamp=20.0)

    # Record at event_time 18 (lateness 2s <= 5s) -> Processed
    r_on_time = StreamRecord(payload={"v": 1}, event_time=18.0)
    assert lateness.handle_record(r_on_time, current_wm) is True

    # Record at event_time 10 (lateness 10s > 5s) -> Routed to side-output
    r_very_late = StreamRecord(payload={"v": 2}, event_time=10.0)
    assert lateness.handle_record(r_very_late, current_wm) is False

    side_outputs = lateness.get_and_clear_late_side_outputs()
    assert len(side_outputs) == 1
    assert side_outputs[0].payload["v"] == 2
