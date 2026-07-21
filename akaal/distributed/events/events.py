"""
Transport-Independent Domain Event System for Distributed Runtime (Platform 2).
Provides standardized EventMetadata and domain events with failure-isolated event dispatching.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Type, Optional
import uuid
import logging

logger = logging.getLogger("nexusforge.distributed.events")


@dataclass(frozen=True)
class EventMetadata:
    """Standardized metadata for all distributed domain events."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_version: str = "1.0.0"
    event_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = ""
    causation_id: str = ""
    producer_id: str = "platform_2_runtime"


@dataclass(frozen=True)
class DistributedDomainEvent(ABC):
    """Base immutable distributed domain event with standardized EventMetadata."""
    metadata: EventMetadata = field(default_factory=EventMetadata)

    def __post_init__(self) -> None:
        if not self.metadata.event_type:
            meta = EventMetadata(
                event_id=self.metadata.event_id,
                event_version=self.metadata.event_version,
                event_type=self.__class__.__name__,
                timestamp=self.metadata.timestamp,
                correlation_id=self.metadata.correlation_id,
                causation_id=self.metadata.causation_id,
                producer_id=self.metadata.producer_id,
            )
            object.__setattr__(self, "metadata", meta)


@dataclass(frozen=True)
class WorkerRegistered(DistributedDomainEvent):
    worker_id: str = ""
    node_id: str = ""
    capabilities: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkerRemoved(DistributedDomainEvent):
    worker_id: str = ""
    reason: str = ""


@dataclass(frozen=True)
class WorkerHeartbeatEvent(DistributedDomainEvent):
    worker_id: str = ""
    status: str = ""
    health: str = ""


@dataclass(frozen=True)
class WorkerUnavailable(DistributedDomainEvent):
    worker_id: str = ""
    reason: str = ""


@dataclass(frozen=True)
class LeaderChanged(DistributedDomainEvent):
    cluster_id: str = ""
    old_leader_node_id: str = ""
    new_leader_node_id: str = ""


@dataclass(frozen=True)
class TaskQueued(DistributedDomainEvent):
    task_id: str = ""
    execution_id: str = ""
    priority: int = 10


@dataclass(frozen=True)
class TaskAssigned(DistributedDomainEvent):
    task_id: str = ""
    worker_id: str = ""


@dataclass(frozen=True)
class TaskLeased(DistributedDomainEvent):
    task_id: str = ""
    worker_id: str = ""
    lease_id: str = ""
    expires_at: float = 0.0


@dataclass(frozen=True)
class TaskStarted(DistributedDomainEvent):
    task_id: str = ""
    execution_id: str = ""
    worker_id: str = ""


@dataclass(frozen=True)
class TaskCompleted(DistributedDomainEvent):
    task_id: str = ""
    execution_id: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class TaskFailed(DistributedDomainEvent):
    task_id: str = ""
    execution_id: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class TaskRetried(DistributedDomainEvent):
    task_id: str = ""
    execution_id: str = ""
    attempt_count: int = 1


@dataclass(frozen=True)
class LeaseExpired(DistributedDomainEvent):
    lease_id: str = ""
    task_id: str = ""
    worker_id: str = ""


@dataclass(frozen=True)
class WorkerScaled(DistributedDomainEvent):
    direction: str = ""  # SCALE_UP or SCALE_DOWN
    worker_count: int = 0


@dataclass(frozen=True)
class ClusterRecovered(DistributedDomainEvent):
    cluster_id: str = ""
    recovered_at: str = ""


@dataclass(frozen=True)
class ClusterDegraded(DistributedDomainEvent):
    cluster_id: str = ""
    reason: str = ""


@dataclass(frozen=True)
class ConfigReloaded(DistributedDomainEvent):
    config_version: int = 1
    reloaded_at: str = ""


class EventPublisher(ABC):
    """Transport-agnostic EventPublisher interface."""
    @abstractmethod
    def publish(self, event: DistributedDomainEvent) -> None:
        pass


class EventSubscriber(ABC):
    """Transport-agnostic EventSubscriber interface."""
    @abstractmethod
    def on_event(self, event: DistributedDomainEvent) -> None:
        pass


class InProcessEventDispatcher(EventPublisher):
    """
    In-process synchronous event dispatcher with subscriber failure isolation.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[Type[DistributedDomainEvent], List[EventSubscriber]] = {}
        self._global_subscribers: List[EventSubscriber] = []
        self._history: List[DistributedDomainEvent] = []

    def subscribe(self, subscriber: EventSubscriber, event_type: Optional[Type[DistributedDomainEvent]] = None) -> None:
        if event_type is None:
            if subscriber not in self._global_subscribers:
                self._global_subscribers.append(subscriber)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if subscriber not in self._subscribers[event_type]:
                self._subscribers[event_type].append(subscriber)

    def publish(self, event: DistributedDomainEvent) -> None:
        self._history.append(event)
        
        # Dispatch to global subscribers
        for subscriber in list(self._global_subscribers):
            try:
                subscriber.on_event(event)
            except Exception as exc:
                logger.error(
                    f"Error in subscriber '{subscriber}' handling event '{event.metadata.event_type}': {str(exc)}",
                    exc_info=True
                )

        # Dispatch to event-specific subscribers
        event_cls = type(event)
        if event_cls in self._subscribers:
            for subscriber in list(self._subscribers[event_cls]):
                try:
                    subscriber.on_event(event)
                except Exception as exc:
                    logger.error(
                        f"Error in subscriber '{subscriber}' handling event '{event.metadata.event_type}': {str(exc)}",
                        exc_info=True
                    )

    def get_history(self) -> List[DistributedDomainEvent]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()
