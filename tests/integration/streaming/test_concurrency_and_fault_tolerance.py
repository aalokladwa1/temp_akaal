"""
Integration tests for Platform 3 Concurrency, Multi-threaded Record Pushing, and Backpressure.
"""

import concurrent.futures
from akaal.streaming.facade.runtime import DefaultStreamingRuntimeV1
from akaal.streaming.domain.models import StreamRecord, StreamConfig
from akaal.streaming.operators.base import MapOperator, FilterOperator
from akaal.streaming.windowing.assigner import TumblingWindowAssigner
from akaal.streaming.windowing.operator import WindowOperator


def test_concurrent_streaming_pipeline_execution():
    config = StreamConfig(batch_size=50, max_buffer_size_mb=128.0)
    runtime = DefaultStreamingRuntimeV1(config=config)

    # Add Map and Filter operators
    runtime.add_operator(MapOperator(fn=lambda d: {"val": d["raw"] * 2}))
    runtime.add_operator(FilterOperator(predicate=lambda d: d["val"] > 100))

    # Push 200 records concurrently across 5 worker threads
    def push_worker(start_idx: int):
        pushed = 0
        for j in range(40):
            idx = start_idx + j
            rec = StreamRecord(payload={"raw": idx}, event_time=float(idx))
            if runtime.push(rec):
                pushed += 1
        return pushed

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(push_worker, i * 40) for i in range(5)]
        results = [f.result() for f in futures]

    assert sum(results) > 0

    # Process all batches
    total_processed = 0
    while True:
        processed = runtime.execute_step()
        if processed == 0:
            break
        total_processed += processed

    assert total_processed > 0

    # Verify outputs filtered (val > 100 => raw > 50)
    outputs = runtime.collect_output()
    assert all(o.payload["val"] > 100 for o in outputs)
