"""akaalEngine.intelligence.mediation.errors
=============================================
Typed error hierarchy for the P7C.6 Action Mediation Gateway.
"""

from __future__ import annotations

from akaalEngine.intelligence.models.errors import IntelligenceError


class ActionMediationError(IntelligenceError):
    code = "ACTION_MEDIATION_ERROR"


class NonDelegableActionError(ActionMediationError):
    """Raised unconditionally for any action_type in NON_DELEGABLE_ACTION_TYPES.
    Cannot be bypassed by any caller-supplied flag or autonomy override."""

    code = "ACTION_MEDIATION_NON_DELEGABLE"


class UnregisteredActionTypeError(ActionMediationError):
    """Raised when an action_type has no explicit autonomy classification. An
    unclassified action is refused, never defaulted to a permissive level."""

    code = "ACTION_MEDIATION_UNREGISTERED_ACTION_TYPE"


class StaleProposalError(ActionMediationError):
    """Raised when a proposal's bound context fingerprint no longer matches
    current canonical state -- mirrors IntelligenceStaleArtifactError but at the
    mediation boundary (a proposal can go stale even if its source artifact was
    still fresh at generation time, if time has passed since)."""

    code = "ACTION_MEDIATION_STALE_PROPOSAL"


class SelfApprovalError(ActionMediationError):
    """Raised when the proposal's requester and its approver would be the same
    principal (P7C brief 'AI cannot count as both maker and checker')."""

    code = "ACTION_MEDIATION_SELF_APPROVAL"


class AuthorizationAuthorityUnavailableError(ActionMediationError):
    """Raised when no canonical authorizer was injected. Missing authorization
    authority must never be treated as allow -- mirrors akaalPipeline.application.
    unified_caller.PipelineUnifiedCaller's AUTHORIZATION_AUTHORITY_UNAVAILABLE
    fail-closed discipline."""

    code = "ACTION_MEDIATION_AUTHORIZATION_AUTHORITY_UNAVAILABLE"


class ApprovalRequiredError(ActionMediationError):
    """Raised when an L3 action lacks a verified governance approval reference."""

    code = "ACTION_MEDIATION_APPROVAL_REQUIRED"


class PreauthorizationPolicyDeniedError(ActionMediationError):
    """Raised when an L4 action does not match any pre-authorized, bounded,
    low-risk policy rule."""

    code = "ACTION_MEDIATION_PREAUTHORIZATION_DENIED"


class MalformedProposalError(ActionMediationError):
    """Raised when a proposal fails structural/semantic validation -- e.g.
    references a resource type/action combination that is structurally impossible."""

    code = "ACTION_MEDIATION_MALFORMED_PROPOSAL"


class AuthorizationDeniedError(ActionMediationError):
    """Raised when the injected canonical authorizer denies the proposal."""

    code = "ACTION_MEDIATION_AUTHORIZATION_DENIED"
