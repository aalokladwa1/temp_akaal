"""
tests.unit.engine_extensions.test_notifications
===============================================
Tests for internal typed notification events and listener error isolation.
"""

from akaalEngine.extensions.lifecycle.notifications import NotificationDispatcher
from akaalEngine.extensions.models.events import ExtensionEvent, ExtensionEventType
from akaalEngine.extensions.models.identity import ExtensionId, RegistryGeneration


def test_notification_dispatcher_listener_isolation():
    dispatcher = NotificationDispatcher()
    received_events = []

    def failing_listener(evt: ExtensionEvent):
        raise RuntimeError("Simulated listener exception!")

    def working_listener(evt: ExtensionEvent):
        received_events.append(evt)

    dispatcher.subscribe(failing_listener)
    dispatcher.subscribe(working_listener)

    event = ExtensionEvent(
        event_type=ExtensionEventType.EXTENSION_ACTIVATED,
        extension_id=ExtensionId("ext-test"),
        generation=RegistryGeneration(1),
    )

    # Emitting event should not crash despite failing_listener exception
    dispatcher.emit(event)

    assert len(received_events) == 1
    assert received_events[0] == event

    # Unsubscribe
    dispatcher.unsubscribe(working_listener)
    dispatcher.emit(event)
    assert len(received_events) == 1  # No new event received
