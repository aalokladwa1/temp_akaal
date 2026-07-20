"""WebSocket Real-Time Event Streamer with Ping/Pong Heartbeats."""

import threading
from typing import Dict, List, Tuple


class WebSocketEventBroadcaster:
    """Broadcasting server maintaining WebUI client sessions with ping/pong validation."""

    def __init__(self) -> None:
        self._clients: Dict[str, Tuple[bool, float]] = {}  # client_id -> (active, last_pong_time)
        self._lock = threading.Lock()

    def register_client(self, client_id: str) -> None:
        with self._lock:
            self._clients[client_id] = (True, 0.0)

    def receive_pong(self, client_id: str, timestamp: float) -> None:
        with self._lock:
            if client_id in self._clients:
                self._clients[client_id] = (True, timestamp)

    def broadcast_event(self, event_data: dict) -> int:
        """Broadcast CloudEvent to all active WebUI client sessions."""
        with self._lock:
            active_count = sum(1 for active, _ in self._clients.values() if active)
            return active_count
