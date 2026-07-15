"""
Akaal — Replay Session Manager
==============================
Implements the ReplaySessionManager, state transition verifications,
checkpoint persistences, and session timeout handlers.
"""

import threading
from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from akaal.core.intelligence.common.exceptions import ReplaySequenceError
from akaal.core.intelligence.replay.models import (
    ReplayCheckpoint,
    ReplaySession,
    ReplayState,
    SessionStatistics,
    VALID_TRANSITIONS,
)


class ReplaySessionManager:
    """Manages ReplaySession states, transitions, recoveries, and expirations."""
    def __init__(self) -> None:
        self._sessions: Dict[str, ReplaySession] = {}
        self._lock = threading.RLock()

    def create_session(self, session_id: str, session: ReplaySession) -> None:
        """Saves a newly initialized session record."""
        with self._lock:
            if session_id in self._sessions:
                raise ReplaySequenceError(
                    f"Session '{session_id}' already exists.",
                    error_code="REPLAY_SESSION_EXISTS"
                )
            self._sessions[session_id] = session

    def get_session(self, session_id: str) -> Optional[ReplaySession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> List[ReplaySession]:
        with self._lock:
            return list(self._sessions.values())

    def transition_state(self, session_id: str, target_state: ReplayState) -> ReplaySession:
        """Transitions a session state dynamically following the transition validation matrix."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ReplaySequenceError(
                    f"Session '{session_id}' not found.",
                    error_code="REPLAY_SESSION_NOT_FOUND"
                )

            current_state = session.state
            allowed = VALID_TRANSITIONS.get(current_state, set())
            if target_state not in allowed:
                raise ReplaySequenceError(
                    f"Invalid state transition from '{current_state.value}' to '{target_state.value}'.",
                    error_code="INVALID_STATE_TRANSITION"
                )

            # Update session statistics
            stats = session.statistics
            new_stats = replace(
                stats,
                total_transitions=stats.total_transitions + 1,
                active_duration_seconds=stats.active_duration_seconds + (datetime.now(timezone.utc) - session.updated_at).total_seconds()
            )

            # Transition state
            now = datetime.now(timezone.utc)
            updated_session = replace(
                session,
                state=target_state,
                statistics=new_stats,
                updated_at=now
            )
            self._sessions[session_id] = updated_session
            return updated_session

    def add_checkpoint(self, session_id: str, checkpoint: ReplayCheckpoint) -> ReplaySession:
        """Adds a verified checkpoint to the session state."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ReplaySequenceError(
                    f"Session '{session_id}' not found.",
                    error_code="REPLAY_SESSION_NOT_FOUND"
                )

            # Verify no duplicate checkpoints
            for cp in session.checkpoints:
                if cp.checkpoint_id == checkpoint.checkpoint_id:
                    raise ReplaySequenceError(
                        f"Duplicate checkpoint '{checkpoint.checkpoint_id}' detected.",
                        error_code="REPLAY_DUPLICATE_CHECKPOINT"
                    )

            stats = session.statistics
            new_stats = replace(
                stats,
                checkpoint_count=stats.checkpoint_count + 1,
                last_checkpoint_sequence=max(stats.last_checkpoint_sequence, checkpoint.commit_sequence)
            )

            updated_session = replace(
                session,
                checkpoints=session.checkpoints + (checkpoint,),
                statistics=new_stats,
                updated_at=datetime.now(timezone.utc)
            )
            self._sessions[session_id] = updated_session
            return updated_session

    def recover_session(self, session_id: str) -> ReplaySession:
        """Triggers recovery behavior on a failed session by restoring to the last valid checkpoint."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ReplaySequenceError(
                    f"Session '{session_id}' not found.",
                    error_code="REPLAY_SESSION_NOT_FOUND"
                )

            if not session.checkpoints:
                raise ReplaySequenceError(
                    f"Session '{session_id}' cannot recover: no checkpoints exist.",
                    error_code="REPLAY_RECOVERY_NO_CHECKPOINTS"
                )

            # Retrieve the last valid checkpoint
            last_checkpoint = sorted(session.checkpoints, key=lambda c: c.commit_sequence)[-1]

            # Re-transition to RESUMED state via intermediate state jumps if needed, or directly
            # For modeling, we transition from FAILED or ACTIVE to SUSPENDED, and then to RESUMED
            self.transition_state(session_id, ReplayState.CANCELLED if session.state == ReplayState.CANCELLED else ReplayState.FAILED)
            # Rollback active stats and reset sequence watermark
            stats = session.statistics
            new_stats = replace(
                stats,
                last_checkpoint_sequence=last_checkpoint.commit_sequence
            )
            now = datetime.now(timezone.utc)
            updated_session = replace(
                session,
                state=ReplayState.RESUMED,
                statistics=new_stats,
                updated_at=now
            )
            self._sessions[session_id] = updated_session
            return updated_session
