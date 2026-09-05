"""
tests.unit.engine_extensions.test_certification_aggregation_e2e
====================================================================
Hostile-review Blocker #4: end-to-end proof (real ConnectorCertificationRunner, real
ExtensionsAuthority, real capability truth resolution) for all four aggregation edge
cases -- not just unit tests of CertificationReport's aggregation math against
hand-built ObligationResult objects (those already exist in test_certification_framework.py
and pass), but proof that the REAL pipeline actually produces the right result.
"""

from __future__ import annotations

import pytest

from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.certification.obligations import ObligationCategory, ObligationResult, ObligationStatus
from akaalEngine.extensions.certification.profiles import CertificationObligation, CertificationProfile
from akaalEngine.extensions.certification.runner import ConnectorCertificationRunner
from akaalEngine.extensions.lifecycle.manager import LifecycleManager
from akaalEngine.extensions.models import (
    AuthorityId,
    CapabilityDeclaration,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.models.dependency import DependencyRequirement, PythonDependency
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.resolution.resolver import StrategyResolver
from akaalEngine.extensions.spi.authority_contract import AuthorityContractDefinition


class _ConformingStrategy:
    def do_thing(self):
        return "ok"


def _fresh_authority():
    fresh_registry = ExtensionRegistry()
    fresh_lifecycle_mgr = LifecycleManager()
    fresh_resolver = StrategyResolver(registry=fresh_registry, lifecycle_manager=fresh_lifecycle_mgr)
    ext_auth = ExtensionsAuthority(
        registry=fresh_registry,
        lifecycle_manager=fresh_lifecycle_mgr,
        strategy_resolver=fresh_resolver,
        auto_bootstrap=False,
    )
    ext_auth.register_authority_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("test-authority"),
            contract_version="1.0.0",
            description="Test authority contract",
        )
    )
    return ext_auth


def _register(ext_auth, ext_id, provider_id, capabilities, dependencies=()):
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{provider_id}-strat"),
        authority_id=AuthorityId("test-authority"),
        provider_id=ProviderId(provider_id),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_ConformingStrategy,
        capabilities=capabilities,
        dependencies=dependencies,
    )
    prov = ProviderContribution(
        provider_id=ProviderId(provider_id), vendor_name="V", display_name="P",
        family="relational", strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId(ext_id), version="1.0.0", display_name=f"Ext {ext_id}",
        engine_version_range=CompatibilityRange(">=1.0.0"), provider_contributions=(prov,),
    )
    ext_auth.register_extension(manifest)
    ext_auth.activate_extension(ext_id)


# ---------------------------------------------------------------------------
# Case A: declared YES + mandatory obligation resolves UNSUPPORTED -> FAIL
# ---------------------------------------------------------------------------

def test_case_a_declared_yes_but_dependency_missing_blocks_resolution_entirely():
    """
    A connector declares BULK_READ=True but has an unmet MANDATORY dependency. Traced
    end-to-end: resolve_strategy() itself fails closed (DependencyResolutionError) before
    capability truth or certification is even reached -- there is no path where a strategy
    with an unsatisfied mandatory dependency reaches a runnable, certifiable state at all.
    This is a stronger outcome than a mere obligation FAIL: the connector cannot be
    resolved/certified/executed at all until the dependency is satisfied.
    """
    from akaalEngine.extensions.errors.taxonomy import DependencyResolutionError

    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.case_a_dep", "case-a-dep-provider",
        capabilities=(CapabilityDeclaration(capability_name="BULK_READ", is_supported=True),),
        dependencies=(
            PythonDependency(name="this_module_definitely_does_not_exist_xyz123", is_optional=False),
        ),
    )
    with pytest.raises(DependencyResolutionError):
        ConnectorCertificationRunner.certify(ext_auth, "case-a-dep-provider", "test-authority")


def test_case_a_declared_yes_but_behavioral_evaluator_finds_unsupported_e2e():
    """
    The realistic shape of Case A: a connector declares CAPABILITY_X=True, but a mandatory
    certification obligation with a REAL behavioral evaluator (the framework's actual
    mechanism for this, proven end-to-end here, not a hand-built ObligationResult) inspects
    the resolved strategy and determines the capability is not genuinely usable. This must
    surface as a real obligation FAIL and the report must not pass -- a connector cannot
    advertise YES while a mandatory verification concludes UNSUPPORTED.
    """
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.case_a_behavior", "case-a-behavior-provider",
        capabilities=(CapabilityDeclaration(capability_name="BULK_READ", is_supported=True),),
    )

    def _behavioral_bulk_read_evaluator(handle, ext_authority):
        # Real inspection of the resolved strategy instance -- here, a stand-in for e.g.
        # checking the instance actually exposes a working bulk-read method.
        has_real_impl = hasattr(handle.strategy_instance, "stream_bulk_read")
        if not has_real_impl:
            return ObligationResult(
                obligation_id="OBL-BULK-READ-BEHAVIOR",
                status=ObligationStatus.UNSUPPORTED,
                category=ObligationCategory.DATA_MOVEMENT,
                diagnostic="Declared BULK_READ=True but strategy instance has no working bulk-read implementation.",
                target_capability="BULK_READ",
            )
        return ObligationResult(
            obligation_id="OBL-BULK-READ-BEHAVIOR",
            status=ObligationStatus.PASS,
            category=ObligationCategory.DATA_MOVEMENT,
            diagnostic="Bulk read implementation verified.",
            target_capability="BULK_READ",
        )

    custom_profile = CertificationProfile(
        name="case-a-behavior-profile",
        target_capabilities=frozenset({"BULK_READ"}),
        obligations=(
            CertificationObligation(
                obligation_id="OBL-BULK-READ-BEHAVIOR",
                name="Bulk Read Behavioral Verification",
                category=ObligationCategory.DATA_MOVEMENT,
                description="Verifies bulk read is genuinely implemented.",
                is_mandatory=True,
                evaluator=_behavioral_bulk_read_evaluator,
            ),
        ),
    )
    report = ConnectorCertificationRunner.certify(
        ext_auth, "case-a-behavior-provider", "test-authority", profile=custom_profile
    )
    bulk_read_obligations = [o for o in report.obligation_results if o.target_capability == "BULK_READ"]
    assert len(bulk_read_obligations) == 1
    assert bulk_read_obligations[0].status == ObligationStatus.UNSUPPORTED
    assert report.passed is False, (
        "Certification passed despite a mandatory obligation resolving UNSUPPORTED for a "
        "capability the connector declared YES -- this is the exact contradiction Case A forbids."
    )


# ---------------------------------------------------------------------------
# Case B: mandatory live-provider obligation EXTERNAL_DEFERRED -> ceiling INTEGRATION_PROVEN,
# never LIVE_PROVEN, while still truthfully PASSing locally.
# ---------------------------------------------------------------------------

def test_case_b_external_deferred_custom_evaluator_caps_proof_level_e2e():
    """A real custom evaluator (as the runner actually supports) returning EXTERNAL_DEFERRED
    must flow through the real certify() call and cap allowable_proof_level below LIVE_PROVEN."""
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.case_b", "case-b-provider",
        capabilities=(CapabilityDeclaration(capability_name="SCHEMA_DISCOVERY", is_supported=True),),
    )

    def _live_cluster_evaluator(handle, ext_authority):
        return ObligationResult(
            obligation_id="OBL-LIVE-CLUSTER-B",
            status=ObligationStatus.EXTERNAL_DEFERRED,
            category=ObligationCategory.CONNECTION_SECURITY,
            diagnostic="No live cluster available locally -- deferred, not faked as LIVE_PROVEN.",
        )

    custom_profile = CertificationProfile(
        name="case-b-profile",
        target_capabilities=frozenset({"SCHEMA_DISCOVERY"}),
        obligations=(
            CertificationObligation(
                obligation_id="OBL-LIVE-CLUSTER-B",
                name="Live Cluster Connectivity",
                category=ObligationCategory.CONNECTION_SECURITY,
                description="Requires a real external cluster.",
                is_mandatory=True,
                evaluator=_live_cluster_evaluator,
            ),
        ),
    )
    report = ConnectorCertificationRunner.certify(
        ext_auth, "case-b-provider", "test-authority", profile=custom_profile
    )
    assert report.passed is True, "Locally-passable obligations with only EXTERNAL_DEFERRED must still PASS locally."
    assert report.has_external_deferred is True
    assert report.allowable_proof_level == ProofLevel.INTEGRATION_PROVEN
    assert report.allowable_proof_level != ProofLevel.LIVE_PROVEN


# ---------------------------------------------------------------------------
# Case C: a mandatory, profile-included obligation that is never executed must not PASS.
# ---------------------------------------------------------------------------

def test_case_c_unexecuted_mandatory_obligation_cannot_silently_pass():
    """
    If a profile includes a mandatory obligation whose evaluator raises (a real execution
    failure -- e.g. a broken/incompatible evaluator), that must NOT be silently absorbed
    into a PASSing report. The exception must propagate (fail closed) rather than being
    swallowed into an implicit PASS.
    """
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.case_c", "case-c-provider",
        capabilities=(CapabilityDeclaration(capability_name="SCHEMA_DISCOVERY", is_supported=True),),
    )

    def _broken_evaluator(handle, ext_authority):
        raise RuntimeError("evaluator crashed before producing any ObligationResult")

    custom_profile = CertificationProfile(
        name="case-c-profile",
        target_capabilities=frozenset({"SCHEMA_DISCOVERY"}),
        obligations=(
            CertificationObligation(
                obligation_id="OBL-BROKEN-C",
                name="Broken Obligation",
                category=ObligationCategory.SEMANTICS,
                description="Deliberately broken evaluator.",
                is_mandatory=True,
                evaluator=_broken_evaluator,
            ),
        ),
    )
    with pytest.raises(RuntimeError):
        ConnectorCertificationRunner.certify(ext_auth, "case-c-provider", "test-authority", profile=custom_profile)


def test_case_c_empty_obligation_set_never_passes():
    """A report with zero obligation results (nothing evaluated at all) must not report PASS."""
    from akaalEngine.extensions.certification.models import CertificationReport
    report = CertificationReport(provider_id="p", authority_id="a", strategy_id="s", obligation_results=())
    assert report.passed is False


# ---------------------------------------------------------------------------
# Case D: NOT_APPLICABLE must be trust-derived, not extension-self-declared.
# Documents the real, honest scope boundary of the current purely-capability-driven design.
# ---------------------------------------------------------------------------

def test_case_d_capability_never_declared_excludes_obligation_honestly():
    """
    An extension that never declares TRANSACTION_ACID at all (e.g. a genuine message-queue
    connector) correctly never sees OBL-TX-01 at all -- applicability is derived from the
    resolved capability truth dict, not an extension-supplied "N/A" flag. This is the
    legitimate, honest case (already covered by test_messaging_profile_does_not_force_
    relational_transactions at the profile-construction level); this test proves it holds
    through the real end-to-end runner too.
    """
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.case_d_honest", "case-d-honest-provider",
        capabilities=(CapabilityDeclaration(capability_name="MESSAGING", is_supported=True),),
    )
    report = ConnectorCertificationRunner.certify(ext_auth, "case-d-honest-provider", "test-authority")
    assert not any(o.obligation_id == "OBL-TX-01" for o in report.obligation_results)


def test_case_d_explicit_negative_declaration_is_not_a_free_pass():
    """
    A connector that explicitly declares TRANSACTION_ACID=False (an honest "I checked, I
    don't support this" signal) must be held to the SAME mandatory-obligation outcome as
    one whose dependency silently fails -- FAIL, not a quiet NOT_APPLICABLE escape. Proves
    the applicability gate cannot be used by a connector to dodge accountability for a
    capability it explicitly considered and declared unsupported.
    """
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.case_d_explicit", "case-d-explicit-provider",
        capabilities=(
            CapabilityDeclaration(capability_name="TRANSACTION_ACID", is_supported=False),
        ),
    )
    report = ConnectorCertificationRunner.certify(ext_auth, "case-d-explicit-provider", "test-authority")
    tx_obligations = [o for o in report.obligation_results if o.obligation_id == "OBL-TX-01"]
    assert len(tx_obligations) == 1, "An explicitly-declared-unsupported capability must still surface its obligation."
    assert tx_obligations[0].status == ObligationStatus.FAIL
    assert report.passed is False
