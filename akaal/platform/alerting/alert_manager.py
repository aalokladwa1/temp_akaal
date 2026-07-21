"""
AKAAL Platform Part 6 - Alerting Subsystem.
Alert Rules, Routing, Cascading Suppression, and Multi-Tier Escalation.
"""

from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable, Dict, List, Optional


class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


@dataclass
class AlertPayload:
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    source_subsystem: str
    node_id: str
    description: str
    timestamp_ms: int
    suppressed: bool = False


class AlertRules:
    """Evaluates threshold metric rules against current health signals."""

    def evaluate_rule(self, rule_name: str, current_value: float, threshold: float) -> Optional[AlertPayload]:
        if current_value > threshold:
            return AlertPayload(
                alert_id=f"alert-{rule_name}-{int(time.time()*1000)}",
                rule_name=rule_name,
                severity=AlertSeverity.CRITICAL if current_value > (threshold * 1.5) else AlertSeverity.WARNING,
                source_subsystem="metric-evaluator",
                node_id="node-local",
                description=f"Rule {rule_name} breached: value {current_value} > threshold {threshold}",
                timestamp_ms=int(time.time() * 1000),
            )
        return None


class AlertRouter:
    """Routes alerts to registered handlers (PagerDuty, Slack, Email)."""

    def __init__(self) -> None:
        self._handlers: List[Callable[[AlertPayload], None]] = []

    def register_handler(self, handler: Callable[[AlertPayload], None]) -> None:
        self._handlers.append(handler)

    def route_alert(self, alert: AlertPayload) -> None:
        if alert.suppressed:
            return
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception:
                pass


class AlertSuppression:
    """Suppresses downstream cascading alerts during root cause incidents."""

    def __init__(self) -> None:
        self._suppressed_nodes: List[str] = []

    def suppress_node(self, node_id: str) -> None:
        if node_id not in self._suppressed_nodes:
            self._suppressed_nodes.append(node_id)

    def clear_suppression(self, node_id: str) -> None:
        if node_id in self._suppressed_nodes:
            self._suppressed_nodes.remove(node_id)

    def is_suppressed(self, node_id: str) -> bool:
        return node_id in self._suppressed_nodes


class AlertManager:
    """Master controller managing alert rules, routing, and suppression."""

    def __init__(self) -> None:
        self.rules = AlertRules()
        self.router = AlertRouter()
        self.suppression = AlertSuppression()
        self.dispatched_alerts: List[AlertPayload] = []

    def dispatch(self, alert: AlertPayload) -> bool:
        if self.suppression.is_suppressed(alert.node_id):
            alert.suppressed = True
        else:
            self.router.route_alert(alert)
        self.dispatched_alerts.append(alert)
        return not alert.suppressed
