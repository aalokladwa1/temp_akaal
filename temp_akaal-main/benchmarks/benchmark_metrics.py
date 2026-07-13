# -*- coding: utf-8 -*-
"""
Akaal Metrics Subsystem Performance Benchmark Suite.
Run this script manually using:
    py benchmarks/benchmark_metrics.py
"""

import time
import os
import sys
from akaal.metrics.registry import MetricsRegistry

def run_benchmarks():
    print("======================================================================")
    print("Akaal Metrics Subsystem Performance Benchmarks")
    print("======================================================================")
    
    registry = MetricsRegistry()
    counter = registry.counter("benchmark.counter")
    gauge = registry.gauge("benchmark.gauge")
    histogram = registry.histogram("benchmark.histogram")
    
    results = {}
    
    # 1. Benchmark Counter.increment()
    print("Benchmarking Counter.increment()...")
    iterations = 500000
    start = time.perf_counter()
    worst = 0.0
    for _ in range(iterations):
        op_start = time.perf_counter()
        counter.increment()
        op_dur = time.perf_counter() - op_start
        if op_dur > worst:
            worst = op_dur
    total_dur = time.perf_counter() - start
    avg = total_dur / iterations
    tput = iterations / total_dur
    results["Counter.increment()"] = (avg, worst, tput)
    
    # 2. Benchmark Gauge.set()
    print("Benchmarking Gauge.set()...")
    start = time.perf_counter()
    worst = 0.0
    for i in range(iterations):
        op_start = time.perf_counter()
        gauge.set(i)
        op_dur = time.perf_counter() - op_start
        if op_dur > worst:
            worst = op_dur
    total_dur = time.perf_counter() - start
    avg = total_dur / iterations
    tput = iterations / total_dur
    results["Gauge.set()"] = (avg, worst, tput)
    
    # 3. Benchmark Histogram.record()
    print("Benchmarking Histogram.record()...")
    # Reduced iterations because of Algorithm R / list operations
    hist_iterations = 200000
    start = time.perf_counter()
    worst = 0.0
    for i in range(hist_iterations):
        op_start = time.perf_counter()
        histogram.record(float(i % 100))
        op_dur = time.perf_counter() - op_start
        if op_dur > worst:
            worst = op_dur
    total_dur = time.perf_counter() - start
    avg = total_dur / hist_iterations
    tput = hist_iterations / total_dur
    results["Histogram.record()"] = (avg, worst, tput)
    
    # 4. Benchmark Timer Context
    print("Benchmarking Timer context...")
    start = time.perf_counter()
    worst = 0.0
    for _ in range(hist_iterations):
        op_start = time.perf_counter()
        with registry.timer("benchmark.timer"):
            pass
        op_dur = time.perf_counter() - op_start
        if op_dur > worst:
            worst = op_dur
    total_dur = time.perf_counter() - start
    avg = total_dur / hist_iterations
    tput = hist_iterations / total_dur
    results["Timer Context"] = (avg, worst, tput)
    
    # 5. Benchmark Registry Lookup
    print("Benchmarking MetricsRegistry lookup...")
    start = time.perf_counter()
    worst = 0.0
    for i in range(iterations):
        op_start = time.perf_counter()
        registry.counter("benchmark.counter")
        op_dur = time.perf_counter() - op_start
        if op_dur > worst:
            worst = op_dur
    total_dur = time.perf_counter() - start
    avg = total_dur / iterations
    tput = iterations / total_dur
    results["Registry Lookup"] = (avg, worst, tput)
    
    # 6. Benchmark MetricsRegistry.snapshot()
    print("Benchmarking MetricsRegistry.snapshot()...")
    # Snapshot contains multiple registered metrics; repeat 5000 times
    snap_iterations = 5000
    start = time.perf_counter()
    worst = 0.0
    for _ in range(snap_iterations):
        op_start = time.perf_counter()
        registry.snapshot()
        op_dur = time.perf_counter() - op_start
        if op_dur > worst:
            worst = op_dur
    total_dur = time.perf_counter() - start
    avg = total_dur / snap_iterations
    tput = snap_iterations / total_dur
    results["Registry Snapshot"] = (avg, worst, tput)
    
    # Output the report
    report = []
    report.append("======================================================================")
    report.append("Akaal Metrics Subsystem Performance Benchmark Results")
    report.append("======================================================================")
    report.append(f"{'Metric Operation':<30} | {'Avg Latency (ns)':<20} | {'Worst Latency (ns)':<20} | {'Throughput (ops/s)':<20}")
    report.append("-" * 99)
    for op, (avg, worst, tput) in results.items():
        report.append(f"{op:<30} | {avg*1e9:<20.2f} | {worst*1e9:<20.2f} | {tput:<20.2f}")
    report.append("======================================================================")
    
    report_str = "\n".join(report)
    print(report_str)
    
    # Write report to docs
    os.makedirs("docs", exist_ok=True)
    with open("docs/metrics_benchmark_results.txt", "w", encoding="utf-8") as f:
        f.write(report_str)
    print("\nBenchmark results successfully written to docs/metrics_benchmark_results.txt\n")

if __name__ == "__main__":
    run_benchmarks()
