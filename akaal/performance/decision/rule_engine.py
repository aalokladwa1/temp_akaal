"""
Rule Engine for Decision Layer.
Evaluates local system metrics and generates optimization recommendations.
"""

from typing import Dict, Any, List, Optional
from threading import RLock

from akaal.performance.decision.confidence import ConfidenceEngine, OptimizationConfidence


class OptimizationRule:
    """Represents a rule targeting specific metric limits."""
    def __init__(self, rule_id: str, metric_name: str, threshold: float, comparator: str, recommended_type: str, recommendation: Dict[str, Any]) -> None:
        self.rule_id = rule_id
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparator = comparator  # ">", "<", "=="
        self.recommended_type = recommended_type
        self.recommendation = recommendation

    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        val = metrics.get(self.metric_name)
        if val is None:
            return False

        if self.comparator == ">":
            return val > self.threshold
        elif self.comparator == "<":
            return val < self.threshold
        elif self.comparator == "==":
            return val == self.threshold
        return False


class Recommendation:
    """A generated suggestion to optimize a component."""
    def __init__(self, rule_id: str, recommended_type: str, params: Dict[str, Any], confidence: OptimizationConfidence) -> None:
        self.rule_id = rule_id
        self.recommended_type = recommended_type
        self.params = params
        self.confidence = confidence


class RuleEngine:
    """Evaluates rules against target metrics to recommend changes."""

    def __init__(self, initial_rules: Optional[List[OptimizationRule]] = None) -> None:
        self._lock = RLock()
        self._rules = initial_rules or self._get_default_rules()
        self.version = "1.0.0"

    def _get_default_rules(self) -> List[OptimizationRule]:
        return [
            # High queue depth => recommend parallel partition processing
            OptimizationRule(
                rule_id="rule_high_queue",
                metric_name="queue_depth",
                threshold=100.0,
                comparator=">",
                recommended_type="parallelism",
                recommendation={"worker_count": 8, "chunks": 4}
            ),
            # Latency spike => decrease batch size to lower memory strain
            OptimizationRule(
                rule_id="rule_high_latency",
                metric_name="latency_ms",
                threshold=50.0,
                comparator=">",
                recommended_type="batch_sizing",
                recommendation={"batch_size": 50}
            ),
            # Underutilized CPU & high queue => increase batch size
            OptimizationRule(
                rule_id="rule_low_cpu_high_queue",
                metric_name="cpu_percent",
                threshold=30.0,
                comparator="<",
                recommended_type="batch_sizing",
                recommendation={"batch_size": 500}
            ),
            # Low throughput + high network latency => compress network payloads
            OptimizationRule(
                rule_id="rule_high_net_latency",
                metric_name="network_latency_ms",
                threshold=80.0,
                comparator=">",
                recommended_type="compression",
                recommendation={"codec": "lz4"}
            )
        ]

    def get_rules(self) -> List[OptimizationRule]:
        with self._lock:
            return list(self._rules)

    def update_rules(self, rules: List[OptimizationRule], version: str) -> None:
        with self._lock:
            self._rules = list(rules)
            self.version = version

    def evaluate_metrics(self, metrics: Dict[str, Any]) -> List[Recommendation]:
        """Analyzes active metrics and creates structured Recommendations with Confidence score."""
        with self._lock:
            recommendations = []
            for rule in self._rules:
                if rule.evaluate(metrics):
                    # Calculate deterministic confidence
                    confidence = ConfidenceEngine.calculate(
                        metric_delta=0.25,
                        success_history=0.88,
                        risk_factor=0.15
                    )
                    rec = Recommendation(
                        rule_id=rule.rule_id,
                        recommended_type=rule.recommended_type,
                        params=rule.recommendation,
                        confidence=confidence
                    )
                    recommendations.append(rec)
            return recommendations
