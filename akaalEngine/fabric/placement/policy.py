"""
akaalEngine.fabric.placement.policy
======================================
P7B.14 -- Policy-Aware Scheduling.

Answers "is this capability-satisfied candidate PERMITTED" -- and answers it by asking
the existing canonical authorization authority
(akaalPipeline.security.central_authorization.CentralAuthorizationEngine in production),
never by deciding permission itself.

ABSOLUTE LAW:

    CAPABLE != AUTHORIZED. SCHEDULABLE != AUTHORIZED. PLACED != AUTHORIZED.
    POLICY MATCH != AUTHENTICATED.

Mirrors the exact discipline already established by
akaalEngine.fabric.execution_site.registry.SiteRegistry.assign_execution: the
authorization callback parameter is typed Optional only so a caller who omits it gets an
explicit, loud failure -- there is no default-allow path, and no caller-supplied
role/scope/site flag ever becomes authoritative merely by reaching this module. This
module never constructs its own callback, never caches a prior decision as durable
truth, and never invents identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Tuple

from akaalEngine.fabric.execution_site.models import ExecutionSite

# The caller supplies the real decision function -- in production, a thin closure over
# akaalPipeline.security.central_authorization.CentralAuthorizationEngine.authorize(...).
# Signature: (site, actor_context, action, context) -> bool. Must return an explicit
# bool; any other return value is treated as a caller bug, not a permissive default.
PlacementAuthorizationCallback = Callable[[ExecutionSite, Any, str, Mapping[str, Any]], bool]


class PlacementPolicyError(ValueError):
    pass


class NoAuthorizationCallbackSuppliedError(PlacementPolicyError):
    """A site (or this module) can never self-authorize placement."""


class MalformedAuthorizationDecisionError(PlacementPolicyError):
    """Raised when a supplied callback returns something other than an explicit bool --
    fails loudly rather than coercing a truthy/falsy value, which could silently accept
    an exception object, a Mock, or a non-empty string as "authorized"."""


@dataclass(frozen=True)
class PolicyEvaluation:
    site_id: str
    permitted: bool
    reasons: Tuple[str, ...] = field(default_factory=tuple)


def evaluate_policy(
    site: ExecutionSite,
    actor_context: Any,
    *,
    action: str,
    authorization_callback: Optional[PlacementAuthorizationCallback],
    context: Optional[Mapping[str, Any]] = None,
) -> PolicyEvaluation:
    """
    Delegates the actual authorization decision to `authorization_callback`. This
    function itself never grants, infers, or caches authorization -- it only shapes the
    call and the explainable result. `authorization_callback=None` is a hard error
    (never treated as "no policy configured, allow"), matching
    SiteRegistry.assign_execution's discipline exactly.
    """
    if authorization_callback is None:
        raise NoAuthorizationCallbackSuppliedError(
            "No PlacementAuthorizationCallback supplied; a placement decision can never "
            "self-authorize a candidate site."
        )
    if not action or not action.strip():
        raise PlacementPolicyError("evaluate_policy requires a non-empty action.")

    decision = authorization_callback(site, actor_context, action, context or {})
    if not isinstance(decision, bool):
        raise MalformedAuthorizationDecisionError(
            f"PlacementAuthorizationCallback must return an explicit bool; got {type(decision).__name__!r}."
        )

    if decision:
        return PolicyEvaluation(site_id=site.site_id, permitted=True, reasons=(f"authorization granted for action {action!r}",))
    return PolicyEvaluation(site_id=site.site_id, permitted=False, reasons=(f"authorization denied for action {action!r}",))
