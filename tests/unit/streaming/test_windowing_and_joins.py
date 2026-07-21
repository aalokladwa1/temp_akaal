"""
Unit tests for WindowAssigners, WindowOperator, and StreamStreamJoinOperator.
"""

from akaal.streaming.domain.models import StreamRecord, Watermark
from akaal.streaming.windowing.assigner import (
    TumblingWindowAssigner, SlidingWindowAssigner, SessionWindowAssigner
)
from akaal.streaming.windowing.operator import WindowOperator
from akaal.streaming.operators.join import StreamStreamJoinOperator


def test_window_assigners():
    r = StreamRecord(payload={"v": 1}, event_time=12.0)

    # Tumbling (size 10) -> [10, 20)
    tumbling = TumblingWindowAssigner(window_size_seconds=10.0).assign_windows(r)
    assert len(tumbling) == 1
    assert tumbling[0].start_time == 10.0
    assert tumbling[0].end_time == 20.0

    # Sliding (size 10, slide 5) -> [10, 20) and [5, 15)
    sliding = SlidingWindowAssigner(window_size_seconds=10.0, slide_seconds=5.0).assign_windows(r)
    assert len(sliding) == 2

    # Session (gap 5) -> [12, 17)
    session = SessionWindowAssigner(session_gap_seconds=5.0).assign_windows(r)
    assert len(session) == 1
    assert session[0].start_time == 12.0
    assert session[0].end_time == 17.0


def test_window_operator_triggering():
    assigner = TumblingWindowAssigner(window_size_seconds=10.0)
    win_op = WindowOperator(assigner)

    r1 = StreamRecord(payload={"id": 1}, event_time=3.0)
    r2 = StreamRecord(payload={"id": 2}, event_time=7.0)
    win_op.process_record(r1)
    win_op.process_record(r2)

    # Watermark at 5.0 -> Window [0, 10) not yet expired
    triggered1 = win_op.trigger_watermark(Watermark(timestamp=5.0))
    assert len(triggered1) == 0

    # Watermark at 10.0 -> Window [0, 10) triggers!
    triggered2 = win_op.trigger_watermark(Watermark(timestamp=10.0))
    assert len(triggered2) == 1
    win, records = triggered2[0]
    assert win.start_time == 0.0
    assert win.end_time == 10.0
    assert len(records) == 2


def test_stream_stream_join_operator():
    join_op = StreamStreamJoinOperator(join_key="user_id", window_bounds_seconds=5.0)

    left_rec = StreamRecord(payload={"user_id": 100, "action": "click"}, event_time=10.0)
    right_rec = StreamRecord(payload={"user_id": 100, "item": "laptop"}, event_time=12.0)

    # Push left record first
    res1 = join_op.process_left(left_rec)
    assert len(res1) == 0  # no right match yet

    # Push right record
    res2 = join_op.process_right(right_rec)
    assert len(res2) == 1
    assert res2[0].payload["action"] == "click"
    assert res2[0].payload["item"] == "laptop"
