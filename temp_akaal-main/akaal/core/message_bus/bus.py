"""
NexusForge — Async Message Bus
================================
In-process asynchronous message bus for inter-agent communication.

Every agent communicates ONLY through this bus.
Direct memory manipulation between agents is forbidden.
(manager_agent.md Section 9: No direct memory manipulation allowed)

Architecture:
  - Publisher/Subscriber pattern
  - Per-agent message queues
  - Message integrity verification before delivery
  - Full audit trail of all messages
  - Non-blocking delivery with configurable timeout

TRD Section 11: Every message shall be validated before processing.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from akaal.core.models.enums import AgentType
from akaal.core.models.message import Message, MessageType

logger = logging.getLogger("nexusforge.message_bus")


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Dead Letter Queue entry
# ---------------------------------------------------------------------------

class DeadLetterEntry:
    """Stores messages that could not be delivered."""
    def __init__(self, message: Message, reason: str) -> None:
        self.message = message
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Message Bus
# ---------------------------------------------------------------------------

class MessageBus:
    """
    Async publish/subscribe message bus.

    Usage:
        bus = MessageBus()
        await bus.subscribe(AgentType.MANAGER, handler_coroutine)
        await bus.publish(message)
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        # Per-agent queues: AgentType → asyncio.Queue
        self._queues: Dict[AgentType, asyncio.Queue] = {}
        # Per-agent registered handlers (for push-based delivery)
        self._handlers: Dict[AgentType, List[MessageHandler]] = defaultdict(list)
        # Message delivery tasks
        self._delivery_tasks: Dict[AgentType, asyncio.Task] = {}
        # Dead letter queue — messages that failed delivery
        self._dead_letters: List[DeadLetterEntry] = []
        # Audit log of all messages
        self._message_log: List[Dict[str, Any]] = []
        self._max_queue_size = max_queue_size
        self._running = False
        self._lock = asyncio.Lock()

        logger.info("[MessageBus] Initialized with max_queue_size=%d", max_queue_size)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start message delivery workers for all registered agents."""
        self._running = True
        async with self._lock:
            for agent_type in self._queues:
                if agent_type not in self._delivery_tasks or self._delivery_tasks[agent_type].done():
                    task = asyncio.create_task(
                        self._delivery_worker(agent_type),
                        name=f"bus_delivery_{agent_type.value}"
                    )
                    self._delivery_tasks[agent_type] = task
        logger.info("[MessageBus] Started.")

    async def stop(self) -> None:
        """Gracefully stop the message bus."""
        self._running = False
        # Cancel all delivery tasks
        for agent_type, task in self._delivery_tasks.items():
            task.cancel()
            logger.debug("[MessageBus] Cancelled delivery task for %s", agent_type.value)
        self._delivery_tasks.clear()
        logger.info("[MessageBus] Stopped.")

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    async def subscribe(self, agent_type: AgentType, handler: MessageHandler) -> None:
        """
        Register a message handler for an agent.
        Messages published to this agent will be delivered to the handler.
        """
        async with self._lock:
            if agent_type not in self._queues:
                self._queues[agent_type] = asyncio.Queue(maxsize=self._max_queue_size)
            self._handlers[agent_type].append(handler)

            # Start delivery worker if bus is running and task not already running
            if self._running:
                if agent_type not in self._delivery_tasks or self._delivery_tasks[agent_type].done():
                    task = asyncio.create_task(
                        self._delivery_worker(agent_type),
                        name=f"bus_delivery_{agent_type.value}"
                    )
                    self._delivery_tasks[agent_type] = task

        logger.info("[MessageBus] Agent %s subscribed.", agent_type.value)

    async def unsubscribe(self, agent_type: AgentType, handler: Optional[MessageHandler] = None) -> None:
        """Unregister an agent from the bus."""
        async with self._lock:
            if handler:
                if agent_type in self._handlers and handler in self._handlers[agent_type]:
                    self._handlers[agent_type].remove(handler)
                if not self._handlers.get(agent_type):
                    self._handlers.pop(agent_type, None)
                    if agent_type in self._delivery_tasks:
                        self._delivery_tasks[agent_type].cancel()
                        del self._delivery_tasks[agent_type]
            else:
                self._handlers.pop(agent_type, None)
                if agent_type in self._delivery_tasks:
                    self._delivery_tasks[agent_type].cancel()
                    del self._delivery_tasks[agent_type]
        logger.info("[MessageBus] Agent %s unsubscribed.", agent_type.value)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, message: Message) -> bool:
        """
        Publish a message to the receiver's queue.

        Steps:
        1. Verify message integrity (TRD Section 11)
        2. Log message to audit trail
        3. Enqueue to receiver's queue
        4. Return True on success, False on failure

        Returns: True if accepted, False if rejected
        """
        # Step 1: Integrity check
        if not message.verify_integrity():
            logger.error(
                "[MessageBus] REJECTED — checksum invalid. msg_id=%s type=%s",
                message.message_id, message.message_type
            )
            self._dead_letters.append(
                DeadLetterEntry(message, "Checksum validation failed")
            )
            return False

        # Step 2: Audit log
        self._log_message(message, "PUBLISHED")

        # Step 3: Enqueue
        receiver = message.receiver
        if receiver not in self._queues:
            async with self._lock:
                self._queues[receiver] = asyncio.Queue(maxsize=self._max_queue_size)

        try:
            self._queues[receiver].put_nowait(message)
            logger.debug(
                "[MessageBus] Enqueued: %s → %s type=%s",
                message.sender.value, receiver.value, message.message_type
            )
            return True
        except asyncio.QueueFull:
            logger.error(
                "[MessageBus] Queue full for agent=%s. msg_id=%s DROPPED.",
                receiver.value, message.message_id
            )
            self._dead_letters.append(
                DeadLetterEntry(message, f"Queue full for {receiver.value}")
            )
            return False

    async def publish_and_wait(
        self,
        message: Message,
        timeout: float = 30.0,
    ) -> Optional[Message]:
        """
        Publish a message and wait for a correlated response.
        Returns the response message or None on timeout.
        """
        response_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        correlation_id = message.correlation_id

        # Temporary handler to capture the response
        async def capture_response(msg: Message) -> None:
            if msg.correlation_id == correlation_id:
                await response_queue.put(msg)

        # Subscribe a temporary capture handler
        sender_agent = message.sender
        await self.subscribe(sender_agent, capture_response)

        # Publish the message
        await self.publish(message)

        try:
            response = await asyncio.wait_for(response_queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(
                "[MessageBus] Timed out waiting for response. correlation_id=%s timeout=%.1fs",
                correlation_id, timeout
            )
            return None
        finally:
            # Clean up temporary handler
            if capture_response in self._handlers.get(sender_agent, []):
                self._handlers[sender_agent].remove(capture_response)

    # ------------------------------------------------------------------
    # Direct receive (pull-based, for agents that manage their own loop)
    # ------------------------------------------------------------------

    async def receive(
        self,
        agent_type: AgentType,
        timeout: float = 5.0,
    ) -> Optional[Message]:
        """
        Pull the next message for the given agent.
        Returns None if queue is empty within timeout.
        """
        if agent_type not in self._queues:
            return None
        try:
            message = await asyncio.wait_for(
                self._queues[agent_type].get(),
                timeout=timeout
            )
            self._log_message(message, "RECEIVED")
            return message
        except asyncio.TimeoutError:
            return None

    # ------------------------------------------------------------------
    # Internal delivery worker (push-based)
    # ------------------------------------------------------------------

    async def _delivery_worker(self, agent_type: AgentType) -> None:
        """Background worker that delivers messages to registered handlers."""
        logger.debug("[MessageBus] Delivery worker started for %s", agent_type.value)
        while self._running:
            try:
                queue = self._queues.get(agent_type)
                if not queue:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                handlers = self._handlers.get(agent_type, [])
                if not handlers:
                    logger.warning(
                        "[MessageBus] No handler for agent=%s. Message type=%s dropped.",
                        agent_type.value, message.message_type
                    )
                    self._dead_letters.append(
                        DeadLetterEntry(message, f"No handler registered for {agent_type.value}")
                    )
                    continue

                # Deliver to all handlers
                for handler in handlers:
                    try:
                        await handler(message)
                        self._log_message(message, "DELIVERED")
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error(
                            "[MessageBus] Handler error for agent=%s type=%s: %s",
                            agent_type.value, message.message_type, exc
                        )

            except asyncio.CancelledError:
                logger.debug("[MessageBus] Delivery worker for %s cancelled.", agent_type.value)
                break
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[MessageBus] Delivery worker error for %s: %s", agent_type.value, exc)
                await asyncio.sleep(0.5)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _log_message(self, message: Message, event: str) -> None:
        """Append message event to the internal audit log."""
        self._message_log.append({
            "event": event,
            "message_id": message.message_id,
            "correlation_id": message.correlation_id,
            "project_id": message.project_id,
            "migration_id": message.migration_id,
            "sender": message.sender.value if hasattr(message.sender, "value") else message.sender,
            "receiver": message.receiver.value if hasattr(message.receiver, "value") else message.receiver,
            "message_type": message.message_type,
            "priority": message.priority.value if hasattr(message.priority, "value") else message.priority,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": message.payload,
        })

    def get_message_log(self) -> List[Dict[str, Any]]:
        """Return full message audit log."""
        return list(self._message_log)

    def get_dead_letters(self) -> List[DeadLetterEntry]:
        """Return all dead-letter entries."""
        return list(self._dead_letters)

    def queue_depth(self, agent_type: AgentType) -> int:
        """Return current queue depth for an agent."""
        q = self._queues.get(agent_type)
        return q.qsize() if q else 0

    def stats(self) -> Dict[str, Any]:
        """Return bus statistics for observability."""
        return {
            "total_messages_logged": len(self._message_log),
            "dead_letters": len(self._dead_letters),
            "active_agents": list(self._queues.keys()),
            "queue_depths": {
                agent.value: self._queues[agent].qsize()
                for agent in self._queues
            },
        }


# ---------------------------------------------------------------------------
# Singleton bus instance (shared across the application)
# ---------------------------------------------------------------------------

_bus_instance: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Return the global singleton MessageBus instance."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = MessageBus()
    return _bus_instance


def reset_message_bus() -> None:
    """Reset the singleton (used in tests only)."""
    global _bus_instance
    _bus_instance = None
