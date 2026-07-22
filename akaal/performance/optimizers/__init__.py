"""
Optimizers Exports.
"""

from akaal.performance.optimizers.base import PluginOptimizer
from akaal.performance.optimizers.batch import AdaptiveBatchOptimizer
from akaal.performance.optimizers.parallel import ParallelExecutionManager
from akaal.performance.optimizers.scheduler import ResourceSchedulerOptimizer
from akaal.performance.optimizers.vector import VectorizedProcessingEngine
from akaal.performance.optimizers.memory import ZeroCopyMemoryPipeline
from akaal.performance.optimizers.compression import AdaptiveCompressionPipeline
from akaal.performance.optimizers.db import DatabaseAwareOptimizer
from akaal.performance.optimizers.pool import ConnectionPoolOptimizer
from akaal.performance.optimizers.load_balancer import PerformanceLoadBalancer
from akaal.performance.optimizers.backpressure import PerformanceBackpressureOptimizer

__all__ = [
    "PluginOptimizer",
    "AdaptiveBatchOptimizer",
    "ParallelExecutionManager",
    "ResourceSchedulerOptimizer",
    "VectorizedProcessingEngine",
    "ZeroCopyMemoryPipeline",
    "AdaptiveCompressionPipeline",
    "DatabaseAwareOptimizer",
    "ConnectionPoolOptimizer",
    "PerformanceLoadBalancer",
    "PerformanceBackpressureOptimizer",
]
