"""
Unit Tests for Optimizers.
"""

from akaal.performance.optimizers.batch import AdaptiveBatchOptimizer
from akaal.performance.optimizers.parallel import ParallelExecutionManager
from akaal.performance.optimizers.compression import AdaptiveCompressionPipeline
from akaal.performance.optimizers.db import DatabaseAwareOptimizer


def test_batch_optimizer():
    opt = AdaptiveBatchOptimizer()
    
    # 1. Scaling up batch size on idle CPU
    res1 = opt.optimize(
        metrics={"cpu_percent": 20.0, "queue_depth": 200},
        current_config={"batch_size": 100}
    )
    assert res1 is not None
    assert res1["batch_size"] == 150

    # 2. Scaling down batch size on high memory load
    res2 = opt.optimize(
        metrics={"memory_utilization_percent": 90.0},
        current_config={"batch_size": 100}
    )
    assert res2 is not None
    assert res2["batch_size"] == 70


def test_parallel_optimizer():
    opt = ParallelExecutionManager()
    
    # Scaling down concurrency to resolve thread contention
    res1 = opt.optimize(
        metrics={"cpu_percent": 95.0},
        current_config={"worker_count": 8}
    )
    assert res1 is not None
    assert res1["worker_count"] == 7


def test_compression_optimizer():
    opt = AdaptiveCompressionPipeline()
    
    # Low speed network => ZSTD compression
    res = opt.optimize(
        metrics={"network_latency_ms": 150.0, "network_bandwidth_mbps": 5.0},
        current_config={"compression_codec": "raw"}
    )
    assert res is not None
    assert res["compression_codec"] == "zstd"


def test_db_optimizer_hints():
    opt = DatabaseAwareOptimizer()
    
    # Consume Postgres adapter hint
    res = opt.optimize(
        metrics={},
        current_config={"db_adapter_hints": {"db_type": "postgresql"}}
    )
    assert res is not None
    assert res["db_write_method"] == "COPY"
    assert res["postgresql_wal_tuning"] is True
