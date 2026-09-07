"""tests/unit/engine_intelligence/test_p7c4_model_gateway.py
================================================================
P7C.4 Model Gateway, Supply Chain & Model Governance: registration, capability
routing, residency/sensitivity enforcement BEFORE cost, failover, and fail-closed
behavior when nothing is compatible.
"""

from __future__ import annotations

import pytest

from akaalEngine.intelligence.gateway.adapter import DeterministicAlgorithmicAdapter
from akaalEngine.intelligence.gateway.errors import (
    ModelResidencyProhibitedError,
    ModelSensitivityProhibitedError,
    ModelUnavailableError,
    NoCompatibleModelError,
)
from akaalEngine.intelligence.gateway.registry import (
    ApprovalStatus,
    DataClassification,
    ModelDescriptor,
    ModelRegistry,
)
from akaalEngine.intelligence.gateway.routing import ModelRouter, RoutingRequest


def _model(model_id, **overrides) -> ModelDescriptor:
    base = dict(
        model_id=model_id,
        provider="acme",
        model_family="deterministic",
        model_version="1.0",
        capabilities=frozenset({"structured_diagnostic"}),
        allowed_regions=frozenset({"us"}),
        allowed_data_classifications=frozenset({DataClassification.INTERNAL}),
        approval_status=ApprovalStatus.APPROVED,
        healthy=True,
    )
    base.update(overrides)
    return ModelDescriptor(**base)


class TestRegistrationAndLookup:
    def test_register_and_get(self):
        reg = ModelRegistry()
        reg.register(_model("m1"))
        assert reg.get("m1").model_id == "m1"

    def test_unknown_model_returns_none(self):
        reg = ModelRegistry()
        assert reg.get("does-not-exist") is None

    def test_health_transition(self):
        reg = ModelRegistry()
        reg.register(_model("m1"))
        reg.set_health("m1", False)
        assert reg.get("m1").healthy is False

    def test_approval_status_transition(self):
        reg = ModelRegistry()
        reg.register(_model("m1", approval_status=ApprovalStatus.PENDING))
        reg.set_approval_status("m1", ApprovalStatus.APPROVED)
        assert reg.get("m1").approval_status == ApprovalStatus.APPROVED


class TestRoutingHappyPath:
    def test_selects_only_compatible_model(self):
        reg = ModelRegistry()
        reg.register(_model("m1"))
        reg.register(_model("m2", capabilities=frozenset({"unrelated_capability"})))
        chosen = ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))
        assert chosen.model_id == "m1"

    def test_prefers_lowest_cost_among_compatible(self):
        reg = ModelRegistry()
        reg.register(_model("expensive", relative_cost_score=10.0))
        reg.register(_model("cheap", relative_cost_score=1.0))
        chosen = ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))
        assert chosen.model_id == "cheap"


class TestFailClosedRouting:
    def test_no_capability_match_raises_typed_error(self):
        reg = ModelRegistry()
        reg.register(_model("m1", capabilities=frozenset({"other"})))
        with pytest.raises(NoCompatibleModelError):
            ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))

    def test_tenant_not_allowlisted_raises(self):
        reg = ModelRegistry()
        reg.register(_model("m1", allowed_tenants=frozenset({"tenant-other"})))
        with pytest.raises(NoCompatibleModelError):
            ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))

    def test_unhealthy_model_excluded(self):
        reg = ModelRegistry()
        reg.register(_model("m1", healthy=False))
        with pytest.raises(ModelUnavailableError):
            ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))

    def test_unapproved_model_excluded(self):
        reg = ModelRegistry()
        reg.register(_model("m1", approval_status=ApprovalStatus.PENDING))
        with pytest.raises(ModelUnavailableError):
            ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))

    def test_deprecated_model_excluded(self):
        reg = ModelRegistry()
        reg.register(_model("m1", approval_status=ApprovalStatus.DEPRECATED))
        with pytest.raises(ModelUnavailableError):
            ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))


class TestResidencyAndSensitivityHostile:
    def test_hostile_residency_never_relaxed_even_when_cheaper(self):
        """A model in a prohibited region must be excluded even though it is the
        only otherwise-compatible, cheapest option -- security constraints beat
        cost preference, never the reverse."""
        reg = ModelRegistry()
        reg.register(_model("cheap-wrong-region", allowed_regions=frozenset({"singapore"}), relative_cost_score=0.1))
        with pytest.raises(ModelResidencyProhibitedError):
            ModelRouter.select(
                reg,
                RoutingRequest(
                    required_capability="structured_diagnostic",
                    tenant_id="tenant-a",
                    allowed_regions=frozenset({"india"}),
                ),
            )

    def test_hostile_sensitivity_never_relaxed(self):
        reg = ModelRegistry()
        reg.register(_model("public-only", allowed_data_classifications=frozenset({DataClassification.PUBLIC})))
        with pytest.raises(ModelSensitivityProhibitedError):
            ModelRouter.select(
                reg,
                RoutingRequest(
                    required_capability="structured_diagnostic",
                    tenant_id="tenant-a",
                    data_classification=DataClassification.RESTRICTED,
                ),
            )

    def test_compliant_region_selected_over_cheaper_noncompliant_one(self):
        reg = ModelRegistry()
        reg.register(_model("cheap-noncompliant", allowed_regions=frozenset({"singapore"}), relative_cost_score=0.1))
        reg.register(_model("compliant", allowed_regions=frozenset({"india"}), relative_cost_score=5.0))
        chosen = ModelRouter.select(
            reg,
            RoutingRequest(
                required_capability="structured_diagnostic",
                tenant_id="tenant-a",
                allowed_regions=frozenset({"india"}),
            ),
        )
        assert chosen.model_id == "compliant"


class TestFailover:
    def test_failover_to_next_healthy_compatible_model(self):
        reg = ModelRegistry()
        reg.register(_model("primary", healthy=False, relative_cost_score=1.0))
        reg.register(_model("secondary", healthy=True, relative_cost_score=2.0))
        chosen = ModelRouter.select(reg, RoutingRequest(required_capability="structured_diagnostic", tenant_id="tenant-a"))
        assert chosen.model_id == "secondary"

    def test_failover_never_crosses_into_prohibited_region(self):
        """Hostile: primary (compliant) goes unhealthy; the only failover candidate
        is in a prohibited region. Routing must fail closed -- raising
        ModelUnavailableError (the compliant model is merely unhealthy) rather than
        ever selecting the non-compliant one, proves the region filter is applied
        strictly before failover ever gets a chance to consider it."""
        reg = ModelRegistry()
        reg.register(_model("primary-compliant", allowed_regions=frozenset({"india"}), healthy=False))
        reg.register(_model("secondary-noncompliant", allowed_regions=frozenset({"singapore"}), healthy=True))
        with pytest.raises(ModelUnavailableError):
            ModelRouter.select(
                reg,
                RoutingRequest(
                    required_capability="structured_diagnostic",
                    tenant_id="tenant-a",
                    allowed_regions=frozenset({"india"}),
                ),
            )


class TestDeterministicAdapterInvocation:
    def test_adapter_genuinely_computes_from_request(self):
        adapter = DeterministicAlgorithmicAdapter(lambda req: {"echo": req["value"] * 2})
        result = adapter.invoke({"value": 21})
        assert result["echo"] == 42
