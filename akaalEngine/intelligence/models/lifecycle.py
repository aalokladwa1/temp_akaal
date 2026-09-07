"""akaalEngine.intelligence.models.lifecycle
=============================================
Recommendation/artifact lifecycle state machine (P7C.1). This lifecycle governs
*intelligence artifacts only* -- it is a distinct, deliberately narrower state
machine from the canonical migration lifecycle (akaalPipeline.contracts.enums.
MigrationLifecycleState) and never replaces it. Consequential accepted proposals
still require downstream canonical policy/approval/planning/execution -- ACCEPTED
here means "the recommendation was accepted for further canonical processing," not
"executed."
"""

from __future__ import annotations

import enum
from typing import Dict, FrozenSet


class ArtifactLifecycleState(str, enum.Enum):
    GENERATED = "GENERATED"
    GROUNDED = "GROUNDED"
    VALIDATED = "VALIDATED"
    PRESENTED = "PRESENTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


# Terminal states: no further transition is ever legal from these.
TERMINAL_STATES: FrozenSet[ArtifactLifecycleState] = frozenset(
    {
        ArtifactLifecycleState.REJECTED,
        ArtifactLifecycleState.EXPIRED,
        ArtifactLifecycleState.SUPERSEDED,
    }
)

# Explicit allow-list of legal transitions. Anything not listed here is illegal --
# the state machine fails closed on an unrecognized transition rather than allowing
# it by omission.
_ALLOWED_TRANSITIONS: Dict[ArtifactLifecycleState, FrozenSet[ArtifactLifecycleState]] = {
    ArtifactLifecycleState.GENERATED: frozenset(
        {
            ArtifactLifecycleState.GROUNDED,
            ArtifactLifecycleState.VALIDATED,
            ArtifactLifecycleState.PRESENTED,
            ArtifactLifecycleState.STALE,
            ArtifactLifecycleState.EXPIRED,
            ArtifactLifecycleState.SUPERSEDED,
            ArtifactLifecycleState.REJECTED,
        }
    ),
    ArtifactLifecycleState.GROUNDED: frozenset(
        {
            ArtifactLifecycleState.VALIDATED,
            ArtifactLifecycleState.PRESENTED,
            ArtifactLifecycleState.STALE,
            ArtifactLifecycleState.EXPIRED,
            ArtifactLifecycleState.SUPERSEDED,
            ArtifactLifecycleState.REJECTED,
        }
    ),
    ArtifactLifecycleState.VALIDATED: frozenset(
        {
            ArtifactLifecycleState.PRESENTED,
            ArtifactLifecycleState.STALE,
            ArtifactLifecycleState.EXPIRED,
            ArtifactLifecycleState.SUPERSEDED,
            ArtifactLifecycleState.REJECTED,
        }
    ),
    ArtifactLifecycleState.PRESENTED: frozenset(
        {
            ArtifactLifecycleState.ACCEPTED,
            ArtifactLifecycleState.REJECTED,
            ArtifactLifecycleState.MODIFIED,
            ArtifactLifecycleState.STALE,
            ArtifactLifecycleState.EXPIRED,
            ArtifactLifecycleState.SUPERSEDED,
        }
    ),
    ArtifactLifecycleState.MODIFIED: frozenset(
        {
            ArtifactLifecycleState.PRESENTED,
            ArtifactLifecycleState.ACCEPTED,
            ArtifactLifecycleState.REJECTED,
            ArtifactLifecycleState.STALE,
            ArtifactLifecycleState.EXPIRED,
            ArtifactLifecycleState.SUPERSEDED,
        }
    ),
    ArtifactLifecycleState.ACCEPTED: frozenset(
        {
            # An accepted recommendation can still be superseded by a fresher one, or
            # discovered stale before any canonical downstream action consumes it.
            ArtifactLifecycleState.STALE,
            ArtifactLifecycleState.SUPERSEDED,
        }
    ),
    ArtifactLifecycleState.STALE: frozenset(
        {
            # A stale artifact may only be superseded (by a freshly regenerated one)
            # or expire; it can never silently become actionable again.
            ArtifactLifecycleState.SUPERSEDED,
            ArtifactLifecycleState.EXPIRED,
        }
    ),
    ArtifactLifecycleState.REJECTED: frozenset(),
    ArtifactLifecycleState.EXPIRED: frozenset(),
    ArtifactLifecycleState.SUPERSEDED: frozenset(),
}


def is_terminal(state: ArtifactLifecycleState) -> bool:
    return state in TERMINAL_STATES


def is_transition_allowed(from_state: ArtifactLifecycleState, to_state: ArtifactLifecycleState) -> bool:
    if from_state == to_state:
        return False
    return to_state in _ALLOWED_TRANSITIONS.get(from_state, frozenset())


def validate_transition(from_state: ArtifactLifecycleState, to_state: ArtifactLifecycleState) -> None:
    """Fail-closed transition guard. Raises IntelligenceInvalidTransitionError for
    any transition not explicitly allow-listed above, including from a terminal state."""
    from akaalEngine.intelligence.models.errors import IntelligenceInvalidTransitionError

    if not is_transition_allowed(from_state, to_state):
        raise IntelligenceInvalidTransitionError(
            f"Illegal intelligence artifact lifecycle transition: "
            f"{from_state.value!r} -> {to_state.value!r}."
        )
