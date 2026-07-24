"""ReplayService: Deterministic validation replay and checkpoint engine."""

import time
import json
from typing import Any, Dict, List, Optional
from akaal.validation.core.interfaces import IService
from akaal.validation.core.models import ValidationResult, ValidationStatus


class ReplayService(IService):
    """Infrastructure service enabling deterministic replay of historical validation sessions."""

    @property
    def service_name(self) -> str:
        return "ReplayService"

    def __init__(self):
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

    def save_checkpoint(self, session_id: str, step_name: str, payload: Dict[str, Any]) -> str:
        """Record a validation checkpoint for replay."""
        checkpoint_id = f"chk_{session_id}_{step_name}_{int(time.time()*1000)}"
        self._checkpoints[checkpoint_id] = {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "step_name": step_name,
            "timestamp": time.time(),
            "payload": payload,
        }
        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve checkpoint state."""
        return self._checkpoints.get(checkpoint_id)

    def replay_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Replay all recorded steps for a given session ID in chronological order."""
        session_chks = [c for c in self._checkpoints.values() if c["session_id"] == session_id]
        return sorted(session_chks, key=lambda x: x["timestamp"])
