"""akaalEngine.intelligence.mediation.non_delegable
====================================================
Hard non-delegable operations (P7C brief §P7C.6). These action categories must
remain permanently non-autonomous -- no autonomy level, no approval, and no policy
configuration can ever route them through AI-mediated action approval. The
mediator checks this list unconditionally, before any authorization/approval
logic runs, and the check cannot be disabled by a caller-supplied flag.
"""

from __future__ import annotations

from typing import FrozenSet

NON_DELEGABLE_ACTION_TYPES: FrozenSet[str] = frozenset(
    {
        "override_data_residency",
        "weaken_tenant_isolation",
        "weaken_tls_or_transport_security",
        "edit_evidence_record",
        "mark_validation_passed",
        "self_approve_own_proposal",
        "bypass_approval_quorum",
        "edit_checkpoint_truth",
        "manufacture_provider_success",
        "bypass_fencing_token",
        "bypass_ownership_lease",
        "weaken_authorization",
        "elevate_caller_role",
        "edit_migration_history",
    }
)


def is_non_delegable(action_type: str) -> bool:
    return action_type in NON_DELEGABLE_ACTION_TYPES
