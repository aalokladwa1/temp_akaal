"""akaalEngine.intelligence.mediation.autonomy
===============================================
Per-action autonomy classification (P7C brief §P7C.6 "Per-action autonomy").
Autonomy belongs to the action TYPE and policy, never to a global "AI is L4"
label. There is deliberately no L5 -- unrestricted autonomy is never implemented.
"""

from __future__ import annotations

import enum


class AutonomyLevel(str, enum.Enum):
    L0_EXPLAIN = "L0_EXPLAIN"
    L1_RECOMMEND = "L1_RECOMMEND"
    L2_STRUCTURED_PROPOSAL = "L2_STRUCTURED_PROPOSAL"
    L3_GOVERNED_ACTION_AFTER_APPROVAL = "L3_GOVERNED_ACTION_AFTER_APPROVAL"
    L4_BOUNDED_PREAUTHORIZED_LOW_RISK = "L4_BOUNDED_PREAUTHORIZED_LOW_RISK"


# Every action_type this gateway can mediate must appear here exactly once. This
# is a closed, explicit allow-list -- an unregistered action_type is refused
# rather than defaulting to some permissive level.
ACTION_AUTONOMY_REGISTRY = {
    "explain_migration_risk": AutonomyLevel.L0_EXPLAIN,
    "recommend_strategy": AutonomyLevel.L1_RECOMMEND,
    "propose_wave_plan": AutonomyLevel.L2_STRUCTURED_PROPOSAL,
    "propose_schema_optimization": AutonomyLevel.L2_STRUCTURED_PROPOSAL,
    "propose_cutover_schedule": AutonomyLevel.L3_GOVERNED_ACTION_AFTER_APPROVAL,
    "propose_migration_start": AutonomyLevel.L3_GOVERNED_ACTION_AFTER_APPROVAL,
    "acknowledge_low_risk_alert": AutonomyLevel.L4_BOUNDED_PREAUTHORIZED_LOW_RISK,
    # P7C.18 -- Governed Recovery & Remediation Intelligence. Pausing a live
    # migration is a state-changing, human-reversible action against an
    # already-existing canonical command (akaalPipeline.application.
    # command_handlers.CommandHandlerRegistry.handle_pause_migration) --
    # requires governance approval (maker-checker), never AI self-approval.
    "propose_remediation_pause_migration": AutonomyLevel.L3_GOVERNED_ACTION_AFTER_APPROVAL,
}


def autonomy_for(action_type: str) -> AutonomyLevel:
    from akaalEngine.intelligence.mediation.errors import UnregisteredActionTypeError

    level = ACTION_AUTONOMY_REGISTRY.get(action_type)
    if level is None:
        raise UnregisteredActionTypeError(
            f"Action type {action_type!r} has no registered autonomy classification; "
            f"refusing to mediate an unclassified action."
        )
    return level
