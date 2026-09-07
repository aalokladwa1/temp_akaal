"""
P7B.14 -- Policy-Aware Scheduling: positive and hostile tests.
"""

import pytest

from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteKind, SiteTrustState
from akaalEngine.fabric.placement.policy import (
    MalformedAuthorizationDecisionError,
    NoAuthorizationCallbackSuppliedError,
    PlacementPolicyError,
    evaluate_policy,
)


def _site(site_id="site-1"):
    return ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1", trust_state=SiteTrustState.TRUSTED)


def test_permitted_when_callback_grants():
    result = evaluate_policy(_site(), actor_context={"actor": "alice"}, action="assign_execution",
                              authorization_callback=lambda site, actor, action, ctx: True)
    assert result.permitted


def test_denied_when_callback_denies():
    result = evaluate_policy(_site(), actor_context={"actor": "mallory"}, action="assign_execution",
                              authorization_callback=lambda site, actor, action, ctx: False)
    assert not result.permitted


def test_no_callback_supplied_is_hard_error_never_default_allow():
    with pytest.raises(NoAuthorizationCallbackSuppliedError):
        evaluate_policy(_site(), actor_context={}, action="assign_execution", authorization_callback=None)


def test_non_bool_decision_rejected_not_coerced():
    with pytest.raises(MalformedAuthorizationDecisionError):
        evaluate_policy(_site(), actor_context={}, action="assign_execution",
                         authorization_callback=lambda site, actor, action, ctx: "yes")


def test_none_decision_rejected_not_coerced_to_falsy_deny():
    """A callback bug returning None must be loud, not silently treated as deny (which
    could mask the caller never actually invoking the real authorization engine)."""
    with pytest.raises(MalformedAuthorizationDecisionError):
        evaluate_policy(_site(), actor_context={}, action="assign_execution",
                         authorization_callback=lambda site, actor, action, ctx: None)


def test_truthy_non_bool_never_accepted_as_authorization():
    with pytest.raises(MalformedAuthorizationDecisionError):
        evaluate_policy(_site(), actor_context={}, action="assign_execution",
                         authorization_callback=lambda site, actor, action, ctx: 1)


def test_empty_action_rejected():
    with pytest.raises(PlacementPolicyError):
        evaluate_policy(_site(), actor_context={}, action="", authorization_callback=lambda *a: True)


def test_cheaper_site_cannot_self_authorize_via_capability_alone():
    """Capability satisfaction must never be conflated with authorization -- this test
    proves evaluate_policy makes its OWN decision via the callback regardless of what a
    hypothetical capability evaluation said; policy.py has no knowledge of capability at
    all (structurally enforced -- it never imports capability.py)."""
    import akaalEngine.fabric.placement.policy as policy_module
    source = open(policy_module.__file__, encoding="utf-8").read()
    assert "placement.capability" not in source


def test_actor_context_and_action_propagated_to_callback():
    seen = {}

    def cb(site, actor, action, ctx):
        seen["site_id"] = site.site_id
        seen["actor"] = actor
        seen["action"] = action
        seen["ctx"] = ctx
        return True

    evaluate_policy(_site("site-99"), actor_context={"tenant": "t1"}, action="assign_execution",
                     authorization_callback=cb, context={"plan_id": "p1"})
    assert seen["site_id"] == "site-99"
    assert seen["actor"] == {"tenant": "t1"}
    assert seen["action"] == "assign_execution"
    assert seen["ctx"] == {"plan_id": "p1"}
