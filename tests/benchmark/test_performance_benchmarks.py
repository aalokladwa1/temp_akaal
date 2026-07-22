"""
Performance Benchmarking Tests.
"""

from akaal.performance.benchmarking.framework import BenchmarkingFramework


def test_framework_benchmark_execution():
    counter = 0

    def sample_workload():
        nonlocal counter
        counter += 1
        # Inefficient loop simulation
        x = sum(i * 2 for i in range(100))

    result = BenchmarkingFramework.run_benchmark(
        name="test_workload_opt",
        task=sample_workload,
        iterations=500
    )

    assert result.name == "test_workload_opt"
    assert result.throughput > 0.0
    assert result.average_latency >= 0.0
    assert result.min_latency >= 0.0
    assert result.max_latency >= 0.0
