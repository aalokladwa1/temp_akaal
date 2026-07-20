"""
Transport-Agnostic Domain Event System for Enterprise Orchestration.
Defines immutable domain events, EventPublisher, EventSubscriber interfaces,
and in-process synchronous EventDispatcher implementation with failure isolation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Type, Callable, Optional
import uuid
import logging

from akaal.orchestration.domain.types import EngineState, Checksum

logger = logging.getLogger("nexusforge.orchestration.events")


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base immutable domain event."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    aggregate_id: str = ""
    event_type: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.__class__.__name__)


@dataclass(frozen=True)
class WorkflowStarted(DomainEvent):
    workflow_id: str = ""
    job_id: str = ""
    initial_step: str = ""


@dataclass(frozen=True)
class WorkflowCompleted(DomainEvent):
    workflow_id: str = ""
    job_id: str = ""
    final_step: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class WorkflowFailed(DomainEvent):
    workflow_id: str = ""
    job_id: str = ""
    failed_step: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class WorkflowRecovered(DomainEvent):
    workflow_id: str = ""
    session_id: str = ""
    recovered_step: str = ""
    checkpoint_checksum: str = ""


@dataclass(frozen=True)
class StateTransitioned(DomainEvent):
    workflow_id: str = ""
    job_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""


@dataclass(frozen=True)
class StepStarted(DomainEvent):
    workflow_id: str = ""
    step_name: str = ""
    step_index: int = 0


@dataclass(frozen=True)
class StepCompleted(DomainEvent):
    workflow_id: str = ""
    step_name: str = ""
    duration_seconds: float = 0.0
    output_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckpointCreated(DomainEvent):
    workflow_id: str = ""
    checkpoint_id: str = ""
    step_name: str = ""
    checksum: str = ""


@dataclass(frozen=True)
class ApprovalRequested(DomainEvent):
    workflow_id: str = ""
    approval_id: str = ""
    step_name: str = ""
    required_roles: List[str] = field(default_factory=list)


class EventPublisher(ABC):
    """Transport-agnostic EventPublisher interface."""
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all interested subscribers/brokers."""
        pass


class EventSubscriber(ABC):
    """Transport-agnostic EventSubscriber interface."""
    @abstractmethod
    def on_event(self, event: DomainEvent) -> None:
        """Receive and handle a published domain event."""
        pass


class InProcessEventDispatcher(EventPublisher):
    """
    In-process synchronous event dispatcher implementation with failure isolation.
    If any subscriber raises an exception during handling, the dispatcher logs the error
    and continues dispatching to remaining subscribers.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[Type[DomainEvent], List[EventSubscriber]] = {}
        self._global_subscribers: List[EventSubscriber] = []
        self._history: List[DomainEvent] = []

    def subscribe(self, subscriber: EventSubscriber, event_type: Optional[Type[DomainEvent]] = None) -> None:
        """Register a subscriber for a specific event type, or all events if event_type is None."""
        if event_type is None:
            if subscriber not in self._global_subscribers:
                self._global_subscribers.append(subscriber)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if subscriber not in self._subscribers[event_type]:
                self._subscribers[event_type].append(subscriber)

    def publish(self, event: DomainEvent) -> None:
        """Publish event synchronously to registered subscribers with failure isolation."""
        self._history.append(event)
        
        # Global subscribers
        for subscriber in list(self._global_subscribers):
            try:
                subscriber.on_event(event)
            except Exception as exc:
                logger.error(
                    f"Error in subscriber '{subscriber}' processing event '{event.event_type}': {str(exc)}",
                    exc_info=True
                )

        # Specific event type subscribers
        event_cls = type(event)
        if event_cls in self._subscribers:
            for subscriber in list(self._subscribers[event_cls]):
                try:
                    subscriber.on_event(event)
                except Exception as exc:
                    logger.error(
                        f"Error in subscriber '{subscriber}' processing event '{event.event_type}': {str(exc)}",
                        exc_info=True
                    )

    def get_history(self) -> List[DomainEvent]:
        """Return history of dispatched events."""
        return list(self._history)

    def clear(self) -> None:
        """Clear event history."""
        self._history.clear()
