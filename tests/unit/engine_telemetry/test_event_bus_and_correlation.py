"""
tests/unit/engine_telemetry/test_event_bus_and_correlation.py
===============================================================
Unit tests for InProcessEventDispatcher, subscriber isolation, and CorrelationContext.
"""

import pytest
from akaalEngine.telemetry import (
    CorrelationContext,
    EventMetadata,
    OperationalEvent,
    TelemetryAuthority,
)
from akaalEngine.telemetry.bus.dispatcher import InProcessEventDispatcher


def test_correlation_context_propagation():
    """Proves CorrelationContext manages thread-local correlation and causation IDs."""
    ctx = CorrelationContext(migration_id="mig-1", task_id="t-1", attempt_id="att-1")
    CorrelationContext.set_current(ctx)

    current = CorrelationContext.get_current()
    assert current.migration_id == "mig-1"
    assert current.task_id == "t-1"

    child = current.child_context(task_id="t-2")
    assert child.correlation_id == current.correlation_id
    assert child.causation_id != current.causation_id
    assert child.task_id == "t-2"


def test_event_dispatcher_subscriber_isolation():
    """Proves subscriber exceptions are isolated and do not prevent other subscribers from receiving events."""
    dispatcher = InProcessEventDispatcher()
    received_events = []

    def _faulty_subscriber(evt: OperationalEvent) -> None:
        raise RuntimeError("Subscriber exploded!")

    def _good_subscriber(evt: OperationalEvent) -> None:
        received_events.append(evt.name)

    dispatcher.subscribe(_faulty_subscriber)
    dispatcher.subscribe(_good_subscriber)

    evt = OperationalEvent(name="task_completed", attributes={"duration": 1.2})
    dispatcher.publish(evt)

    assert len(received_events) == 1
    assert received_events[0] == "task_completed"
    assert dispatcher.metrics["subscriber_error_count"] == 1


def test_telemetry_authority_subscribe_and_unsubscribe():
    """Proves TelemetryAuthority manages event subscriptions and unsubscriptions cleanly."""
    telemetry = TelemetryAuthority()
    events = []

    sub_id = telemetry.subscribe(lambda e: events.append(e.name))
    telemetry.publish_event(OperationalEvent(name="test_event"))

    assert len(events) == 1
    assert events[0] == "test_event"

    assert telemetry.unsubscribe(sub_id) is True
    telemetry.publish_event(OperationalEvent(name="test_event_2"))
    assert len(events) == 1
