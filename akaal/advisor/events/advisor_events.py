"""
Akaal — Advisor Events
======================
Lifecycle event publisher and listener management for Advisor Platform.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from akaal.advisor.models.advisory_event import AdvisoryEvent


class AdvisorEvents:
    """Enterprise Lifecycle Event Manager for Advisor Platform."""

    _listeners: List[Callable[[AdvisoryEvent], None]] = []

    @classmethod
    def subscribe(cls, listener: Callable[[AdvisoryEvent], None]) -> None:
        """Subscribe a callback listener for advisory platform events."""
        if listener not in cls._listeners:
            cls._listeners.append(listener)

    @classmethod
    def unsubscribe(cls, listener: Callable[[AdvisoryEvent], None]) -> None:
        """Unsubscribe a callback listener."""
        if listener in cls._listeners:
            cls._listeners.remove(listener)

    @classmethod
    def clear_listeners(cls) -> None:
        """Remove all subscribed event listeners."""
        cls._listeners.clear()

    @classmethod
    def publish(cls, event_type: str, payload: Dict[str, Any]) -> AdvisoryEvent:
        """Publish an event to all subscribed listeners."""
        event_id = f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.now(timezone.utc).isoformat()
        event = AdvisoryEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            payload=payload,
            source="AdvisorPlatform",
        )

        for listener in list(cls._listeners):
            try:
                listener(event)
            except Exception:
                # Isolate listener failure to protect main execution pipeline
                pass

        return event

    @classmethod
    def publish_platform_started(cls, plan_id: str) -> AdvisoryEvent:
        return cls.publish("PlatformStarted", {"plan_id": plan_id})

    @classmethod
    def publish_analyzer_started(cls, analyzer_name: str) -> AdvisoryEvent:
        return cls.publish("AnalyzerStarted", {"analyzer_name": analyzer_name})

    @classmethod
    def publish_analyzer_completed(
        cls, analyzer_name: str, count: int, duration_ms: float
    ) -> AdvisoryEvent:
        return cls.publish(
            "AnalyzerCompleted",
            {"analyzer_name": analyzer_name, "recommendation_count": count, "duration_ms": duration_ms},
        )

    @classmethod
    def publish_platform_completed(cls, advisory_id: str, total_recommendations: int) -> AdvisoryEvent:
        return cls.publish(
            "PlatformCompleted",
            {"advisory_id": advisory_id, "total_recommendations": total_recommendations},
        )

    @classmethod
    def publish_validation_failed(cls, errors: List[str]) -> AdvisoryEvent:
        return cls.publish("ValidationFailed", {"errors": errors})
