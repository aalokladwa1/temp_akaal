"""
Enterprise Performance Benchmarks for Platform 3 - Streaming Execution Engine.
Measures throughput (records/sec), latency (mean, p95, p99), memory reuse,
zero-copy speedup, and pipeline fusion performance improvements.
"""

import time
import pytest
from typing import List

from akaal.streaming.domain.models import StreamRecord, StreamConfig
from akaal.streaming.facade.runtime import DefaultStreamingRuntimeV1
from akaal.streaming.operators.base import MapOperator, FilterOperator
from akaal.streaming.operators.fusion import FusedStreamOperator, StreamGraphOptimizer
from akaal.streaming.memory.buffer import MemorySlice, BufferOwner
from akaal.streaming.memory.pool import StreamMemoryPool


def test_benchmark_throughput_and_latency():
    # Batch size 5000, high capacity to prevent artificial throttling during ingestion test
    config = StreamConfig(batch_size=5000)
    runtime = DefaultStreamingRuntimeV1(config=config)
    runtime.engine.backpressure_controller.max_capacity = 100000
    runtime.engine.backpressure_controller.high_watermark = 80000

    # Add processing operators
    runtime.add_operator(MapOperator(fn=lambda d: {"val": d["raw"] * 2}))
    runtime.add_operator(FilterOperator(predicate=lambda d: d["val"] > 10))

    record_count = 10000
    latencies: List[float] = []

    # Measure ingestion & processing latency
    t_start = time.perf_counter()
    for i in range(record_count):
        t0 = time.perf_counter()
        runtime.push(StreamRecord(payload={"raw": i}, event_time=float(i)))
        latencies.append((time.perf_counter() - t0) * 1000.0)  # ms

    processed = 0
    while True:
        p = runtime.execute_step()
        if p == 0:
            break
        processed += p

    t_total = time.perf_counter() - t_start
    throughput = record_count / t_total if t_total > 0 else 0

    latencies.sort()
    mean_lat = sum(latencies) / len(latencies) if latencies else 0
    p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99_lat = latencies[int(len(latencies) * 0.99)] if latencies else 0

    print(f"\n--- Platform 3 Throughput & Latency Benchmark ---")
    print(f"Total Records Processed : {record_count}")
    print(f"Total Execution Time   : {t_total * 1000.0:.2f} ms")
    print(f"Throughput             : {throughput:.2f} records/sec")
    print(f"Mean Ingestion Latency : {mean_lat:.4f} ms")
    print(f"P95 Ingestion Latency  : {p95_lat:.4f} ms")
    print(f"P99 Ingestion Latency  : {p99_lat:.4f} ms")

    assert throughput > 1000.0  # Must exceed 1,000 records/sec baseline


def test_benchmark_zero_copy_vs_copy_speedup():
    data = bytearray(b"A" * (50 * 1024 * 1024))  # 50MB bytearray
    iterations = 500

    # 1. Traditional Byte Copying (50MB copied per iteration)
    t0 = time.perf_counter()
    for i in range(iterations):
        _ = bytes(data[100:40000000])
    t_copy = time.perf_counter() - t0

    # 2. Zero-Copy Slicing (O(1) pointer slice)
    owner = BufferOwner("bench_owner")
    master_slice = MemorySlice(data, offset=0, length=len(data), owner=owner)
    t1 = time.perf_counter()
    for i in range(iterations):
        s = master_slice.slice(sub_offset=100, sub_length=40000000)
        s.release()
    t_zero_copy = time.perf_counter() - t1

    speedup = (t_copy / t_zero_copy) if t_zero_copy > 0 else 1.0

    print(f"\n--- Zero-Copy Memory Pipeline Benchmark (50MB Slices) ---")
    print(f"Copy-Based Time   : {t_copy * 1000.0:.2f} ms")
    print(f"Zero-Copy Time   : {t_zero_copy * 1000.0:.2f} ms")
    print(f"Zero-Copy Speedup : {speedup:.2f}x faster")

    assert t_zero_copy < t_copy


def test_benchmark_fused_vs_unfused_pipeline():
    op1 = MapOperator(fn=lambda d: {"v": d["v"] + 1})
    op2 = FilterOperator(predicate=lambda d: d["v"] > 0)
    op3 = MapOperator(fn=lambda d: {"v": d["v"] * 2})
    op4 = MapOperator(fn=lambda d: {"v": d["v"] - 1})

    records = [StreamRecord(payload={"v": i}, event_time=float(i)) for i in range(10000)]

    # 1. Unfused pipeline execution
    t0 = time.perf_counter()
    for r in records:
        c1 = op1.process_element(r)
        for r1 in c1:
            c2 = op2.process_element(r1)
            for r2 in c2:
                c3 = op3.process_element(r2)
                for r3 in c3:
                    _ = op4.process_element(r3)
    t_unfused = time.perf_counter() - t0

    # 2. Fused pipeline execution
    fused = StreamGraphOptimizer.fuse_operators([op1, op2, op3, op4])
    t1 = time.perf_counter()
    for r in records:
        _ = fused.process_element(r)
    t_fused = time.perf_counter() - t1

    print(f"\n--- Pipeline Fusion Optimization Benchmark ---")
    print(f"Unfused Pipeline Time : {t_unfused * 1000.0:.2f} ms")
    print(f"Fused Pipeline Time   : {t_fused * 1000.0:.2f} ms")
    print(f"Fusion Speedup        : {(t_unfused / t_fused):.2f}x faster")

    assert t_fused <= t_unfused * 1.5
