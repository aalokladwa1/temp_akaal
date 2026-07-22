"""
Intelligent Alert & Notification Engine.
Deduplicates, suppresses during maintenance windows, groups, and dispatches alerts.
"""

from typing import Dict, List, Any, Optional
from threading import RLock
import time

from akaal.operations.plugins.framework import NotificationProvider
from akaal.operations.event_bus.bus import OperationsEventBus, AlertRaisedEvent


class AlertRule:
    def __init__(self, rule_id: str, name: str, metric_name: str, threshold: float, comparison: str = ">", severity: str = "HIGH") -> None:
        self.rule_id = rule_id
        self.name = name
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
        self.severity = severity


class ActiveAlert:
    def __init__(self, alert_id: str, rule_name: str, message: str, severity: str) -> None:
        self.alert_id = alert_id
        self.rule_name = rule_name
        self.message = message
        self.severity = severity
        self.timestamp = time.time()
        self.status = "TRIGGERED"  # TRIGGERED, SUPPRESSED, ACKNOWLEDGED, RESOLVED


class AlertEngine:
    """Enterprise Alerting Engine."""

    def __init__(self, event_bus: Optional[OperationsEventBus] = None) -> None:
        self._lock = RLock()
        self.event_bus = event_bus
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, ActiveAlert] = {}
        self.notifiers: List[NotificationProvider] = []
        self.maintenance_mode = False

    def add_notifier(self, notifier: NotificationProvider) -> None:
        with self._lock:
            self.notifiers.append(notifier)

    def set_maintenance_mode(self, enabled: bool) -> None:
        with self._lock:
            self.maintenance_mode = enabled

    def raise_alert(self, rule_name: str, message: str, severity: str = "HIGH") -> ActiveAlert:
        with self._lock:
            # Deduplication key
            dedup_key = f"{rule_name}:{message}"
            if dedup_key in self.active_alerts and self.active_alerts[dedup_key].status != "RESOLVED":
                return self.active_alerts[dedup_key]

            alert_id = f"alt_{time.time_ns()}_{len(self.active_alerts)}"
            alert = ActiveAlert(alert_id, rule_name, message, severity)

            if self.maintenance_mode:
                alert.status = "SUPPRESSED"
            else:
                # Dispatch to notifiers
                for notifier in self.notifiers:
                    try:
                        notifier.send_notification(rule_name, message, severity, {})
                    except Exception:
                        pass
                
                # Publish on event bus if present
                if self.event_bus:
                    self.event_bus.publish(AlertRaisedEvent(alert_id, rule_name, message, severity))

            self.active_alerts[dedup_key] = alert
            return alert
