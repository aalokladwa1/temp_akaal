"""
Enterprise Benchmark & Profiling Framework.
Supports repeatable synthetic and database workloads, profiling, and trend metrics.
"""

import time
from typing import Dict, Any, List, Callable


class BenchmarkResult:
    """Stores execution metrics for a specific benchmark run."""

    def __init__(self, name: str, throughput: float, average_latency: float, min_latency: float, max_latency: float) -> None:
        self.name = name
        self.throughput = throughput
        self.average_latency = average_latency
        self.min_latency = min_latency
        self.max_latency = max_latency


class BenchmarkingFramework:
    """Runs performance benchmarking campaigns."""

    @staticmethod
    def run_benchmark(name: str, task: Callable[[], Any], iterations: int = 1000) -> BenchmarkResult:
        """Executes task for a fixed iteration count, measuring throughput and latencies."""
        latencies = []
        
        # Warmup
        for _ in range(10):
            task()

        start_time = time.perf_counter()
        for _ in range(iterations):
            t_start = time.perf_counter()
            task()
            latencies.append((time.perf_counter() - t_start) * 1000.0)  # ms

        total_duration = time.perf_counter() - start_time  # seconds
        throughput = iterations / total_duration if total_duration > 0 else 0.0
        avg_latency = sum(latencies) / len(latencies)
        
        return BenchmarkResult(
            name=name,
            throughput=round(throughput, 2),
            average_latency=round(avg_latency, 4),
            min_latency=round(min(latencies), 4) if latencies else 0.0,
            max_latency=round(max(latencies), 4) if latencies else 0.0
        )
