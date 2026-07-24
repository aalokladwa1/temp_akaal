"""
AKAAL Platform 6 — Governance Lifecycle States.
"""

from akaal.governance.domain.enums import LifecycleState

ALLOWED_STATE_TRANSITIONS = {
    LifecycleState.DRAFT: [LifecycleState.REVIEW],
    LifecycleState.REVIEW: [LifecycleState.APPROVED, LifecycleState.DRAFT],
    LifecycleState.APPROVED: [LifecycleState.ACTIVE],
    LifecycleState.ACTIVE: [LifecycleState.DEPRECATED],
    LifecycleState.DEPRECATED: [LifecycleState.RETIRED],
    LifecycleState.RETIRED: [LifecycleState.ARCHIVED],
    LifecycleState.ARCHIVED: [],
}
