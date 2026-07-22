"""
Optimization Pipeline Orchestrator.
Runs metrics analysis, rule/policy checks, and applies optimizations with validation and rollback.
"""

from typing import Dict, Any, List, Optional, Callable
from threading import RLock

from akaal.performance.orchestration.optimization_session import OptimizationSession, OptimizationState
from akaal.performance.orchestration.snapshot import OptimizationSnapshotManager
from akaal.performance.orchestration.rollback import OptimizationRollbackController
from akaal.performance.orchestration.validation import PostOptimizationValidator
from akaal.performance.decision.rule_engine import RuleEngine, Recommendation
from akaal.performance.decision.policy_engine import PolicyEngine
from akaal.performance.governor.governor import ResourceGovernor
from akaal.performance.health.score import RuntimeHealthScore
from akaal.performance.optimizers.base import PluginOptimizer
from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType


from akaal.performance.orchestration.coordinator import OptimizationSessionManager

class OptimizationPipeline:
    """Orchestrates Stage 1-6 performance cycles."""

    def __init__(
        self,
        rule_engine: RuleEngine,
        policy_engine: PolicyEngine,
        governor: ResourceGovernor,
        health_score: RuntimeHealthScore,
        snapshot_manager: OptimizationSnapshotManager,
        session_manager: OptimizationSessionManager,
        apply_config_cb: Callable[[Dict[str, Any]], None],
        get_config_cb: Callable[[], Dict[str, Any]],
        get_metrics_cb: Callable[[], Dict[str, Any]],
        optimizers: List[PluginOptimizer]
    ) -> None:
        self._lock = RLock()
        self.rule_engine = rule_engine
        self.policy_engine = policy_engine
        self.governor = governor
        self.health_score = health_score
        self.snapshot_manager = snapshot_manager
        self.session_manager = session_manager
        self.get_config_cb = get_config_cb
        self.get_metrics_cb = get_metrics_cb

        # Setup Rollback Controller
        self.rollback_controller = OptimizationRollbackController(snapshot_manager, apply_config_cb)
        self.optimizers = {opt.name: opt for opt in optimizers}
        self.pending_sessions: Dict[str, OptimizationSession] = {}
        self.pending_updates: Dict[str, Dict[str, Any]] = {}

    def run_optimization_cycle(self, mode: str = "Auto") -> OptimizationSession:
        """Runs the metrics collection, analysis, rules & policies checking flow."""
        with self._lock:
            session = self.session_manager.start_session(run_mode=mode)
            metrics = self.get_metrics_cb()
            session.collected_metrics = metrics
            session.baseline_metrics = dict(metrics)

            session.transition_to(OptimizationState.BASELINE_CAPTURED)

            # Capture Pre-Optimization Snapshot
            current_config = self.get_config_cb()
            self.health_score.update_metrics(
                cpu_util=metrics.get("cpu_percent", 50.0),
                memory_util=metrics.get("memory_utilization_percent", 50.0),
                disk_latency_ms=metrics.get("disk_latency_ms", 10.0),
                net_latency_ms=metrics.get("network_latency_ms", 10.0),
                active_workers=metrics.get("active_workers", 4),
                max_workers=self.governor.get_limits().get("max_workers", 16),
                rollbacks=len(session.rollback_events)
            )
            overall_health = self.health_score.calculate_overall_health()

            self.snapshot_manager.capture_snapshot(
                session_id=session.session_id,
                snapshot_type="Pre-Optimization",
                runtime_config=current_config,
                active_profile=current_config.get("active_profile", "Balanced"),
                active_rules=[r.rule_id for r in self.rule_engine.get_rules()],
                active_policies=[self.policy_engine.get_active_policy().policy_id],
                resource_limits=self.governor.get_limits(),
                metrics=metrics,
                health_score=overall_health,
                optimizer_states={opt_name: opt.is_enabled() for opt_name, opt in self.optimizers.items()}
            )

            session.transition_to(OptimizationState.ANALYZING)

            # Rule evaluation
            recs = self.rule_engine.evaluate_metrics(metrics)
            session.rules_evaluated = [r.rule_id for r in recs]
            session.transition_to(OptimizationState.RULES_EVALUATED)

            # Filter recommendations using Policy Engine & Resource Governor
            allowed_updates: Dict[str, Any] = {}
            for rec in recs:
                if self.policy_engine.is_permitted(rec.recommended_type, rec.params):
                    # Check governor bounds
                    try:
                        if "cpu_percent" in rec.params:
                            self.governor.enforce_cpu(rec.params["cpu_percent"])
                        if "ram_bytes" in rec.params:
                            self.governor.enforce_ram(rec.params["ram_bytes"])
                        if "worker_count" in rec.params:
                            self.governor.enforce_concurrency(rec.params["worker_count"])
                        
                        allowed_updates.update(rec.params)
                        session.optimizers_executed.append(rec.recommended_type)
                    except PerformanceEngineError as e:
                        # Exceeded governor limit, skip optimization
                        session.optimizers_skipped.append(f"{rec.recommended_type} (Governor Block: {e.message})")
                else:
                    session.optimizers_skipped.append(f"{rec.recommended_type} (Policy Block)")

            # Execute optimizations based on mode
            if not allowed_updates:
                # Nothing to optimize, complete session directly
                session.transition_to(OptimizationState.COMPLETED, "No recommendations or all skipped.")
                return session

            if mode == "Safe":
                # Safe Mode: queue changes and wait for approval
                self.pending_sessions[session.session_id] = session
                self.pending_updates[session.session_id] = allowed_updates
                session.transition_to(OptimizationState.WAITING_APPROVAL)
            else:
                # Auto Mode: apply changes directly
                self._apply_and_validate(session, allowed_updates)

            return session

    def approve_recommendation(self, session_id: str) -> None:
        """Manually applies updates queued for approval in Safe Mode."""
        with self._lock:
            session = self.pending_sessions.pop(session_id, None)
            updates = self.pending_updates.pop(session_id, None)
            if not session or not updates:
                raise PerformanceEngineError(
                    PerformanceFailureType.CONFIGURATION,
                    f"No pending optimization session found for ID '{session_id}'."
                )

            session.transition_to(OptimizationState.EXECUTING)
            self._apply_and_validate(session, updates)

    def _apply_and_validate(self, session: OptimizationSession, updates: Dict[str, Any]) -> None:
        """Applies configuration updates, gathers metrics, validates, and rolls back if necessary."""
        try:
            if session.current_state != OptimizationState.EXECUTING:
                session.transition_to(OptimizationState.EXECUTING)

            # Merge config values using our callback
            merged_config = dict(self.get_config_cb())
            merged_config.update(updates)
            self.rollback_controller.apply_config_cb(merged_config)

            session.transition_to(OptimizationState.VALIDATING)

            # Capture Post-Optimization Snapshot
            post_metrics = self.get_metrics_cb()
            session.final_metrics = post_metrics
            overall_health = self.health_score.calculate_overall_health()

            self.snapshot_manager.capture_snapshot(
                session_id=session.session_id,
                snapshot_type="Post-Optimization",
                runtime_config=merged_config,
                active_profile=merged_config.get("active_profile", "Balanced"),
                active_rules=[r.rule_id for r in self.rule_engine.get_rules()],
                active_policies=[self.policy_engine.get_active_policy().policy_id],
                resource_limits=self.governor.get_limits(),
                metrics=post_metrics,
                health_score=overall_health,
                optimizer_states={opt_name: opt.is_enabled() for opt_name, opt in self.optimizers.items()}
            )

            # Validate metrics delta
            valid = PostOptimizationValidator.validate(session.baseline_metrics, post_metrics)
            
            # Compute improvement percent (e.g. latency improvement)
            base_lat = session.baseline_metrics.get("latency_ms", 1.0)
            post_lat = post_metrics.get("latency_ms", 1.0)
            if base_lat > 0.0:
                session.overall_improvement = round(((base_lat - post_lat) / base_lat) * 100.0, 2)

            if not valid:
                self.rollback_controller.execute_rollback(session, "Validated degradation detected in system latency/throughput.")
            else:
                session.transition_to(OptimizationState.COMPLETED, "Optimization validated successfully.")

        except Exception as e:
            session.transition_to(OptimizationState.FAILED, f"Failed during execution: {str(e)}")
            raise e
