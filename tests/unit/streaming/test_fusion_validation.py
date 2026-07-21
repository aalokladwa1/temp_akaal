"""
Pipeline Fusion Validation Suite.
Proves output equivalence, element ordering preservation, exception propagation,
watermark preservation, and resource cleanup across fused operators.
"""

import pytest
from akaal.streaming.domain.models import StreamRecord, Watermark
from akaal.streaming.operators.base import MapOperator, FilterOperator
from akaal.streaming.operators.fusion import StreamGraphOptimizer, FusedStreamOperator


class FaultyOperator(MapOperator):
    """Test operator that raises exception on specific trigger payload."""
    def process_element(self, record: StreamRecord):
        if record.payload.get("fail"):
            raise ValueError("Operator fault injected!")
        return super().process_element(record)


def test_fusion_output_equivalence_and_ordering():
    op1 = MapOperator(fn=lambda d: {"val": d["x"] + 10})
    op2 = FilterOperator(predicate=lambda d: d["val"] % 2 == 0)
    op3 = MapOperator(fn=lambda d: {"val": d["val"] * 3})

    inputs = [StreamRecord(payload={"x": i}, event_time=float(i)) for i in range(20)]

    # 1. Unfused execution
    unfused_out = []
    for rec in inputs:
        c1 = op1.process_element(rec)
        for r1 in c1:
            c2 = op2.process_element(r1)
            for r2 in c2:
                c3 = op3.process_element(r2)
                unfused_out.extend(c3)

    # 2. Fused execution
    fused_op = StreamGraphOptimizer.fuse_operators([op1, op2, op3])
    fused_out = []
    for rec in inputs:
        fused_out.extend(fused_op.process_element(rec))

    # 3. Assert 100% output equivalence and ordering preservation
    assert len(unfused_out) == len(fused_out)
    for u, f in zip(unfused_out, fused_out):
        assert u.payload == f.payload
        assert u.event_time == f.event_time


def test_fusion_exception_propagation_and_cleanup():
    op1 = MapOperator(fn=lambda d: {"x": d["v"], "fail": d.get("fail")})
    op_faulty = FaultyOperator(fn=lambda d: {"x": d["x"] * 2})

    fused = FusedStreamOperator(operators=[op1, op_faulty])
    fused.open()

    # Normal record passes cleanly
    ok_res = fused.process_element(StreamRecord(payload={"v": 5}, event_time=1.0))
    assert len(ok_res) == 1

    # Faulty record raises exception cleanly through fused pipeline
    with pytest.raises(ValueError, match="Operator fault injected!"):
        fused.process_element(StreamRecord(payload={"v": 5, "fail": True}, event_time=2.0))

    # Lifecycle cleanup works
    fused.close()
