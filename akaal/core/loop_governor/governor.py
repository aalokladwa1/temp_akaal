"""
NexusForge — Loop Governor Engine
===================================
The Loop Governor is the execution safety control layer that ensures
NexusForge never enters infinite loops and always operates within
controlled, bounded execution cycles.

Source: loop_governor.md

Rules:
- Scout   → max 3 retries
- Validator → max 3 retries
- Live Intel → max 2 retries
- GB → max 2 retries

Infinite Loop Prevention:
- Same state_hash repeated 2x → WARNING
- Same state_hash repeated 3x → STOP LOOP
- Same state_hash repeated 4x+ → FORCE FREEZE SYSTEM

Backoff:
- Attempt 1 → no delay
- Attempt 2 → 5s delay
- Attempt 3 → 15s delay
- Attempt 4 → FORBIDDEN

The Loop Governor does NOT execute tasks. It only decides:
  whether to retry / stop / escalate / restore checkpoint.
"""

import asyncio
import hashlib
import inspect
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from akaal.core.models.enums import AgentType, FailureReason, FailureType, LoopDecision

logger = logging.getLogger("nexusforge.loop_governor")


# ---------------------------------------------------------------------------
# Retry limits per agent type (loop_governor.md Section 5)
# ---------------------------------------------------------------------------

AGENT_RETRY_LIMITS: Dict[AgentType, int] = {
    AgentType.SCOUT:             3,
    AgentType.VALIDATOR:         3,
    AgentType.LIVE_INTEL:        2,
    AgentType.GB:                2,
    AgentType.CHECKPOINT_ENGINE: 2,
    AgentType.CDC_ENGINE:        2,
    AgentType.MANAGER:           1,   # Manager failures are always critical
}

# Backoff delays in seconds (loop_governor.md Section 8)
BACKOFF_DELAYS: Dict[int, float] = {
    1: 0.0,    # Attempt 1 → no delay
    2: 5.0,    # Attempt 2 → 5s
    3: 15.0,   # Attempt 3 → 15s
}

# State hash repetition thresholds (loop_governor.md Section 7)
HASH_WARNING_THRESHOLD  = 2
HASH_STOP_THRESHOLD     = 3
HASH_FREEZE_THRESHOLD   = 4


# ---------------------------------------------------------------------------
# Loop Governor State — per workflow / per agent
# ---------------------------------------------------------------------------

@dataclass
class LoopState:
    """
    Tracks retry state for a single agent within a specific workflow context.
    loop_governor.md Section 4: Required tracking data.
    """
    agent_type: AgentType
    project_id: str
    migration_id: str

    attempt_count: int = 0
    failure_reason: Optional[str] = None
    state_hash: Optional[str] = None
    last_success_state: Optional[str] = None
    last_failure_state: Optional[str] = None
    timestamp_log: List[str] = field(default_factory=list)
    state_hash_history: List[str] = field(default_factory=list)
    is_frozen: bool = False

    def record_attempt(self, state_data: Dict[str, Any], reason: Optional[str] = None) -> None:
        """Record a new attempt with current state hash."""
        now = datetime.now(timezone.utc).isoformat()
        self.attempt_count += 1
        self.failure_reason = reason
        self.state_hash = _compute_state_hash(state_data)
        self.state_hash_history.append(self.state_hash)
        self.timestamp_log.append(now)
        logger.debug(
            "[LoopGovernor] agent=%s project=%s attempt=%d reason=%s",
            self.agent_type.value, self.project_id, self.attempt_count, reason
        )

    def record_success(self, state_label: str) -> None:
        """Record a successful resolution."""
        self.last_success_state = state_label
        self.attempt_count = 0
        self.state_hash_history.clear()

    def max_retries(self) -> int:
        return AGENT_RETRY_LIMITS.get(self.agent_type, 2)

    def retries_exceeded(self) -> bool:
        return self.attempt_count >= self.max_retries()

    def count_repeated_state_hash(self) -> int:
        """Count how many times the current state_hash has appeared."""
        if not self.state_hash:
            return 0
        return self.state_hash_history.count(self.state_hash)


def _compute_state_hash(state_data: Dict[str, Any]) -> str:
    """Compute deterministic hash of the current system state snapshot."""
    canonical = json.dumps(state_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Loop Governor Engine
# ---------------------------------------------------------------------------

class LoopGovernor:
    """
    The central execution safety control layer for NexusForge.

    Usage:
        governor = LoopGovernor()
        state = governor.get_or_create_state(agent_type, project_id, migration_id)
        decision = await governor.evaluate(state, current_state_data, failure_type, reason)
    """

    def __init__(self) -> None:
        # Keyed by (agent_type, project_id, migration_id)
        self._states: Dict[str, LoopState] = {}
        self._freeze_callbacks: List[Callable] = []
        self._escalation_callbacks: List[Callable] = []

    def _state_key(self, agent_type: AgentType, project_id: str, migration_id: str) -> str:
        return f"{agent_type.value}::{project_id}::{migration_id}"

    def get_or_create_state(
        self,
        agent_type: AgentType,
        project_id: str,
        migration_id: str,
    ) -> LoopState:
        """Get existing loop state or create fresh one."""
        key = self._state_key(agent_type, project_id, migration_id)
        if key not in self._states:
            self._states[key] = LoopState(
                agent_type=agent_type,
                project_id=project_id,
                migration_id=migration_id,
            )
        return self._states[key]

    def reset_state(self, agent_type: AgentType, project_id: str, migration_id: str) -> None:
        """Reset loop state after successful completion."""
        key = self._state_key(agent_type, project_id, migration_id)
        if key in self._states:
            del self._states[key]

    def register_freeze_callback(self, callback: Callable) -> None:
        """Register a callback to be invoked when system freeze is triggered."""
        self._freeze_callbacks.append(callback)

    def register_escalation_callback(self, callback: Callable) -> None:
        """Register a callback invoked when escalation is triggered."""
        self._escalation_callbacks.append(callback)

    async def evaluate(
        self,
        loop_state: LoopState,
        current_state_data: Dict[str, Any],
        failure_type: FailureType,
        failure_reason: FailureReason,
    ) -> LoopDecision:
        """
        Evaluate a failure and decide what to do next.

        loop_governor.md Section 6: Decision Rules
          CASE 1: Recoverable → retry with backoff
          CASE 2: Non-recoverable → STOP, escalate
          CASE 3: Unknown → send to Live Intel

        Returns a LoopDecision enum value.
        """
        # Record the failure attempt
        loop_state.record_attempt(current_state_data, failure_reason.value)

        repeat_count = loop_state.count_repeated_state_hash()

        # -------------------------------------------------------------------
        # Infinite loop detection (loop_governor.md Section 7)
        # -------------------------------------------------------------------
        if repeat_count >= HASH_FREEZE_THRESHOLD:
            logger.critical(
                "[LoopGovernor] FREEZE — state_hash repeated %d times. "
                "agent=%s project=%s",
                repeat_count, loop_state.agent_type.value, loop_state.project_id
            )
            loop_state.is_frozen = True
            await self._trigger_freeze(loop_state)
            return LoopDecision.FREEZE

        if repeat_count >= HASH_STOP_THRESHOLD:
            logger.error(
                "[LoopGovernor] STOP — state_hash repeated %d times. "
                "agent=%s project=%s",
                repeat_count, loop_state.agent_type.value, loop_state.project_id
            )
            await self._trigger_escalation(loop_state, "State hash repeated 3 times — stopping loop")
            return LoopDecision.STOP

        if repeat_count >= HASH_WARNING_THRESHOLD:
            logger.warning(
                "[LoopGovernor] WARNING — state_hash repeated %d times. "
                "agent=%s project=%s",
                repeat_count, loop_state.agent_type.value, loop_state.project_id
            )

        # -------------------------------------------------------------------
        # Retry limit check (loop_governor.md Section 5)
        # -------------------------------------------------------------------
        if loop_state.retries_exceeded():
            logger.error(
                "[LoopGovernor] Retry limit exceeded for agent=%s (limit=%d). "
                "project=%s Escalating.",
                loop_state.agent_type.value,
                loop_state.max_retries(),
                loop_state.project_id,
            )
            await self._trigger_escalation(loop_state, "Retry limit exceeded")
            return LoopDecision.ESCALATE

        # -------------------------------------------------------------------
        # Failure type classification (loop_governor.md Section 6)
        # -------------------------------------------------------------------
        if failure_type == FailureType.SYSTEM:
            # System failures are always non-recoverable → escalate
            logger.critical(
                "[LoopGovernor] SYSTEM failure — escalating. agent=%s project=%s",
                loop_state.agent_type.value, loop_state.project_id
            )
            await self._trigger_escalation(loop_state, f"System failure: {failure_reason.value}")
            return LoopDecision.ESCALATE

        if failure_type == FailureType.CRITICAL:
            # Critical → restore checkpoint, then retry
            delay = self._backoff_delay(loop_state.attempt_count)
            logger.warning(
                "[LoopGovernor] CRITICAL failure → restore checkpoint. "
                "agent=%s attempt=%d backoff=%.1fs",
                loop_state.agent_type.value, loop_state.attempt_count, delay
            )
            if delay > 0:
                await asyncio.sleep(delay)
            return LoopDecision.RESTORE

        if failure_type == FailureType.UNKNOWN:
            # Unknown → send to Live Intel
            logger.warning(
                "[LoopGovernor] UNKNOWN failure → escalating to Live Intel. "
                "agent=%s project=%s",
                loop_state.agent_type.value, loop_state.project_id
            )
            await self._trigger_escalation(loop_state, f"Unknown failure: {failure_reason.value}")
            return LoopDecision.ESCALATE

        # MINOR or MODERATE → retry with backoff
        delay = self._backoff_delay(loop_state.attempt_count)
        logger.info(
            "[LoopGovernor] Recoverable failure → retry. "
            "agent=%s attempt=%d/%d backoff=%.1fs reason=%s",
            loop_state.agent_type.value,
            loop_state.attempt_count,
            loop_state.max_retries(),
            delay,
            failure_reason.value,
        )
        if delay > 0:
            await asyncio.sleep(delay)
        return LoopDecision.RETRY

    def _backoff_delay(self, attempt: int) -> float:
        """Return backoff delay in seconds for given attempt number."""
        return BACKOFF_DELAYS.get(attempt, 15.0)  # Default to 15s for any attempt > 3

    async def _trigger_freeze(self, loop_state: LoopState) -> None:
        """Invoke all registered freeze callbacks."""
        for cb in self._freeze_callbacks:
            try:
                if inspect.iscoroutinefunction(cb):
                    await cb(loop_state)
                else:
                    cb(loop_state)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[LoopGovernor] Freeze callback error: %s", exc)

    async def _trigger_escalation(self, loop_state: LoopState, reason: str) -> None:
        """Invoke all registered escalation callbacks."""
        for cb in self._escalation_callbacks:
            try:
                if inspect.iscoroutinefunction(cb):
                    await cb(loop_state, reason)
                else:
                    cb(loop_state, reason)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[LoopGovernor] Escalation callback error: %s", exc)

    def get_all_states(self) -> Dict[str, LoopState]:
        """Return all active loop states (for observability)."""
        return dict(self._states)

    def summary(self) -> Dict[str, Any]:
        """Return a diagnostic summary of all loop states."""
        return {
            key: {
                "agent": state.agent_type.value,
                "attempt_count": state.attempt_count,
                "retries_exceeded": state.retries_exceeded(),
                "is_frozen": state.is_frozen,
                "state_hash": state.state_hash,
                "repeated_count": state.count_repeated_state_hash(),
                "last_failure": state.failure_reason,
            }
            for key, state in self._states.items()
        }
