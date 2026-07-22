"""
Performance Engine Public Façade.
Single stable public entry point for AKAAL to interact with Platform 6.
"""

from typing import Dict, Any, List, Optional
from threading import RLock

from akaal.performance.event_bus.bus import PerformanceEventBus
from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType
from akaal.performance.discovery.capability import RuntimeCapabilityDiscovery
from akaal.performance.decision.rule_engine import RuleEngine, Recommendation
from akaal.performance.decision.policy_engine import PolicyEngine
from akaal.performance.config.profiles import PerformanceProfiles, ProfileType, PerformanceProfile
from akaal.performance.config.reload import ConfigurationHotReloader
from akaal.performance.governor.governor import ResourceGovernor
from akaal.performance.health.score import RuntimeHealthScore
from akaal.performance.telemetry.telemetry import PerformanceTelemetryCollector, TelemetryEvent
from akaal.performance.history.tracker import OptimizationHistoryTracker, AuditEvent
from akaal.performance.orchestration.coordinator import OptimizationSessionManager
from akaal.performance.orchestration.dependency_graph import OptimizationDependencyGraph
from akaal.performance.orchestration.snapshot import OptimizationSnapshotManager
from akaal.performance.orchestration.pipeline import OptimizationPipeline
from akaal.performance.orchestration.optimization_session import OptimizationSession
from akaal.performance.optimizers.base import PluginOptimizer


class PerformanceRuntimeV1:
    """Public contract for Platform 6 runtime optimizations."""
    pass


class DefaultPerformanceRuntimeV1(PerformanceRuntimeV1):
    """
    Default production implementation of PerformanceRuntimeV1.
    Integrates all sub-components into an enterprise performance manager.
    """

    def __init__(self, initial_profile: ProfileType = ProfileType.BALANCED) -> None:
        self._lock = RLock()
        
        # 1. Base config and Profile setup
        self.active_profile = PerformanceProfiles.get_profile(initial_profile)
        self.config_data = {
            "active_profile": self.active_profile.name.value,
            "limits": self.active_profile.limits,
            "thresholds": self.active_profile.thresholds,
            "batch_size": 100,
            "worker_count": 4,
            "memory_pool_enabled": True,
            "vector_enabled": True,
            "compression_codec": "raw",
            "bp_high_watermark": 1000
        }

        # 2. Setup Config Hot Reloader & Governor
        self.hot_reloader = ConfigurationHotReloader(self.config_data)
        self.governor = ResourceGovernor(self.config_data["limits"])
        self.hot_reloader.register_listener(self._on_config_refresh)

        # 3. Setup Decoupled Event Bus & Logging Trackers
        self.event_bus = PerformanceEventBus()
        self.telemetry = PerformanceTelemetryCollector(self.event_bus)
        self.history = OptimizationHistoryTracker(self.event_bus)

        # 4. Setup Discovery, Health Scores, and Dependency Sorting
        self.discovery = RuntimeCapabilityDiscovery()
        self.health_score = RuntimeHealthScore()
        self.dependency_graph = OptimizationDependencyGraph()

        # 5. Setup Decision Engines
        self.rule_engine = RuleEngine()
        self.policy_engine = PolicyEngine()

        # 6. Setup Orchestration coordinators & Snapshots
        self.session_manager = OptimizationSessionManager()
        self.snapshot_manager = OptimizationSnapshotManager()

        # 7. Initialize Optimizers
        from akaal.performance.optimizers import (
            AdaptiveBatchOptimizer,
            ParallelExecutionManager,
            ResourceSchedulerOptimizer,
            VectorizedProcessingEngine,
            ZeroCopyMemoryPipeline,
            AdaptiveCompressionPipeline,
            DatabaseAwareOptimizer,
            ConnectionPoolOptimizer,
            PerformanceLoadBalancer,
            PerformanceBackpressureOptimizer
        )
        self.optimizers: List[PluginOptimizer] = [
            AdaptiveBatchOptimizer(),
            ParallelExecutionManager(),
            ResourceSchedulerOptimizer(),
            VectorizedProcessingEngine(),
            ZeroCopyMemoryPipeline(),
            AdaptiveCompressionPipeline(),
            DatabaseAwareOptimizer(),
            ConnectionPoolOptimizer(),
            PerformanceLoadBalancer(),
            PerformanceBackpressureOptimizer()
        ]

        # 8. Setup Pipeline
        self.pipeline = OptimizationPipeline(
            rule_engine=self.rule_engine,
            policy_engine=self.policy_engine,
            governor=self.governor,
            health_score=self.health_score,
            snapshot_manager=self.snapshot_manager,
            session_manager=self.session_manager,
            apply_config_cb=self.apply_runtime_configuration,
            get_config_cb=self.get_active_configuration,
            get_metrics_cb=self.collect_system_metrics,
            optimizers=self.optimizers
        )

        # Mock runtime metrics storage
        self._mock_metrics = {
            "cpu_percent": 45.0,
            "memory_utilization_percent": 60.0,
            "disk_latency_ms": 12.0,
            "network_latency_ms": 15.0,
            "queue_depth": 0,
            "latency_ms": 8.0,
            "throughput_records_sec": 1000.0,
            "active_workers": 4
        }

    def _on_config_refresh(self, refreshed_config: Dict[str, Any]) -> None:
        """Listener executed upon Hot Reload trigger."""
        with self._lock:
            self.config_data = dict(refreshed_config)
            # Update governor caps
            if "limits" in self.config_data:
                self.governor.update_limits(self.config_data["limits"])

    def apply_runtime_configuration(self, new_config: Dict[str, Any]) -> None:
        self.hot_reloader.hot_reload(new_config)

    def get_active_configuration(self) -> Dict[str, Any]:
        return self.hot_reloader.get_config()

    def set_mock_metrics(self, key: str, val: Any) -> None:
        with self._lock:
            self._mock_metrics[key] = val

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Gathers runtime resource stats."""
        with self._lock:
            # Publish telemetries
            self.event_bus.publish(TelemetryEvent("sys_telemetry", self._mock_metrics))
            return dict(self._mock_metrics)

    def select_profile(self, profile_type: ProfileType) -> None:
        """Sets a pre-defined performance profile at runtime via Hot Reload."""
        with self._lock:
            profile = PerformanceProfiles.get_profile(profile_type)
            new_config = dict(self.config_data)
            new_config["active_profile"] = profile.name.value
            new_config["limits"] = profile.limits
            new_config["thresholds"] = profile.thresholds
            self.apply_runtime_configuration(new_config)

    def trigger_optimization_cycle(self, mode: str = "Auto") -> OptimizationSession:
        """Invokes the optimization pipeline."""
        session = self.pipeline.run_optimization_cycle(mode=mode)
        # Audit trace event
        self.event_bus.publish(AuditEvent(
            session_id=session.session_id,
            action=session.current_state.value,
            details={"improvement": session.overall_improvement, "executed": session.optimizers_executed}
        ))
        return session
