"""
AKAAL Platform — Adaptive Throughput Optimizer.
==============================================
Unified optimizer combining AdaptiveBatchOptimizer, AdaptiveStreamTuner, and BackpressureController.
Dynamically tunes batch_size, fetch_size, and commit_interval based on continuous telemetry signals.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from threading import RLock

from akaal.performance.optimizers.base import PluginOptimizer
from akaal.performance.optimizers.batch import AdaptiveBatchOptimizer
from akaal.streaming.flow.adaptive import AdaptiveStreamTuner
from akaal.streaming.flow.backpressure import BackpressureController


@dataclass
class ThroughputOptimizationSpec:
    """Calculated optimal execution parameters for high-throughput migration."""
    batch_size: int
    fetch_size: int
    commit_interval_ms: int
    throttle_delay_sec: float
    optimization_reason: str


class AdaptiveThroughputOptimizer(PluginOptimizer):
    """
    Enterprise Unified Adaptive Throughput Optimizer.
    Continuously balances throughput and resource pressure by dynamically tuning
    extraction fetch size, batch size, and transaction commit interval.
    """

    def __init__(
        self,
        batch_optimizer: Optional[AdaptiveBatchOptimizer] = None,
        stream_tuner: Optional[AdaptiveStreamTuner] = None,
        backpressure_controller: Optional[BackpressureController] = None,
    ) -> None:
        super().__init__("throughput")
        self.version = "2.0.0"
        self._lock = RLock()
        self.batch_optimizer = batch_optimizer or AdaptiveBatchOptimizer()
        self.stream_tuner = stream_tuner or AdaptiveStreamTuner()
        self.backpressure_controller = backpressure_controller or BackpressureController()

        # Current state
        self.current_batch_size = 500
        self.current_fetch_size = 1000
        self.current_commit_interval_ms = 1000

    def optimize_throughput(
        self,
        telemetry: Dict[str, Any],
        current_config: Optional[Dict[str, Any]] = None,
    ) -> ThroughputOptimizationSpec:
        """
        Calculates dynamic batch_size, fetch_size, and commit_interval from continuous telemetry signals.
        Evaluates CPU, RAM, Network Latency, Source Latency, Target Latency, Queue Depth, and Retry Frequency.
        """
        with self._lock:
            cfg = current_config or {}
            c_batch = cfg.get("batch_size", self.current_batch_size)
            c_fetch = cfg.get("fetch_size", self.current_fetch_size)
            c_commit = cfg.get("commit_interval_ms", self.current_commit_interval_ms)

            # Continuous telemetry inputs
            cpu = telemetry.get("cpu_percent", 50.0)
            mem = telemetry.get("memory_utilization_pct", 50.0)
            net_lat = telemetry.get("network_latency_ms", 10.0)
            src_lat = telemetry.get("source_latency_ms", 5.0)
            tgt_lat = telemetry.get("target_latency_ms", 15.0)
            queue_depth = telemetry.get("queue_depth", 0)
            retry_freq = telemetry.get("retry_frequency", 0.0)

            # Check backpressure state via composed BackpressureController
            bp_state = self.backpressure_controller.check_and_update(queue_depth)
            throttle_delay = self.backpressure_controller.apply_throttling() if queue_depth > 800 else 0.0

            # Dynamic continuous proportional adjustment factor
            # Higher pressure -> factor < 1.0 (scale down); Lower pressure -> factor > 1.0 (scale up)
            pressure_score = (
                (cpu / 100.0) * 0.3
                + (mem / 100.0) * 0.3
                + min(tgt_lat / 100.0, 1.0) * 0.2
                + min(retry_freq, 1.0) * 0.2
            )

            reasons = []
            new_batch = c_batch
            new_fetch = c_fetch
            new_commit = c_commit

            if pressure_score > 0.7:
                # High system pressure -> shrink batch & fetch sizes, decrease commit interval
                scale_down = max(0.5, 1.0 - (pressure_score - 0.7))
                new_batch = max(50, int(c_batch * scale_down))
                new_fetch = max(100, int(c_fetch * scale_down))
                new_commit = max(200, int(c_commit * scale_down))
                reasons.append(f"System pressure high ({pressure_score:.2f}); scaled down batch/fetch.")
            elif pressure_score < 0.3 and queue_depth > 50:
                # Low system pressure & active queue -> scale up for maximum throughput
                scale_up = min(1.5, 1.0 + (0.3 - pressure_score))
                new_batch = min(5000, int(c_batch * scale_up))
                new_fetch = min(10000, int(c_fetch * scale_up))
                new_commit = min(5000, int(c_commit * scale_up))
                reasons.append(f"System headroom available ({pressure_score:.2f}); scaled up batch/fetch.")
            else:
                reasons.append("System operating in equilibrium; parameters steady.")

            # Record in stream tuner
            self.stream_tuner.record_execution(new_batch, tgt_lat / 1000.0)

            self.current_batch_size = new_batch
            self.current_fetch_size = new_fetch
            self.current_commit_interval_ms = new_commit

            return ThroughputOptimizationSpec(
                batch_size=new_batch,
                fetch_size=new_fetch,
                commit_interval_ms=new_commit,
                throttle_delay_sec=throttle_delay,
                optimization_reason="; ".join(reasons),
            )

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        spec = self.optimize_throughput(metrics, current_config)
        return {
            "batch_size": spec.batch_size,
            "fetch_size": spec.fetch_size,
            "commit_interval_ms": spec.commit_interval_ms,
        }
