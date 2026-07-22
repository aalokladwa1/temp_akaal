"""
Optimization Session Manager (Root Coordinator).
Tracks all active/historical optimization sessions.
"""

from typing import Dict, List, Optional
from threading import RLock

from akaal.performance.orchestration.optimization_session import OptimizationSession


class OptimizationSessionManager:
    """Orchestrates optimization runs, storing trace records of execution metrics."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: Dict[str, OptimizationSession] = {}

    def start_session(self, run_mode: str = "Auto") -> OptimizationSession:
        with self._lock:
            session = OptimizationSession(run_mode=run_mode)
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[OptimizationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def get_all_sessions(self) -> List[OptimizationSession]:
        with self._lock:
            return list(self._sessions.values())

    def get_completed_sessions(self) -> List[OptimizationSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.end_time is not None]
