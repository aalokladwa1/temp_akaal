"""
AKAAL CDC Parallel Multi-Stream Sharding, Partition Routing & High-Throughput Replay Module (P3.6).
"""

from akaal.cdc.sharding.domain import (
    CDCPartitionKey,
    CDCRoutedTransaction,
    CDCPartitionState,
    CDCRouteGeneration,
    CDCBoundaryStatus,
)
from akaal.cdc.sharding.router import CDCPartitionRouter
from akaal.cdc.sharding.barrier import CDCCrossPartitionOrderingBarrier
from akaal.cdc.sharding.guard import CDCSplitBrainShardGuard
from akaal.cdc.sharding.frontier import CDCCheckpointFrontierTracker
from akaal.cdc.sharding.parallel_engine import CDCParallelApplyEngine

__all__ = [
    "CDCPartitionKey",
    "CDCRoutedTransaction",
    "CDCPartitionState",
    "CDCRouteGeneration",
    "CDCBoundaryStatus",
    "CDCPartitionRouter",
    "CDCCrossPartitionOrderingBarrier",
    "CDCSplitBrainShardGuard",
    "CDCCheckpointFrontierTracker",
    "CDCParallelApplyEngine",
]
