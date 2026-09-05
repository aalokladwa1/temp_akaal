"""
tests.unit.engine_extensions.test_p7a_campaign_b_first10_certification
======================================================================
P7A Campaign B — First-10-Provider certification / negative-capability acceptance
closure.

Uses the REAL, pre-existing, generic ConnectorCertificationRunner.certify()
(akaalEngine/extensions/certification/runner.py, unmodified) against the real,
bootstrapped "connection" authority strategy for each of the 10 first-Campaign-B
providers, proving:

  1. Certification obligations/results correspond to the ACTUAL resolved capability
     truth of each provider's live strategy instance (via ExtensionsAuthority.
     resolve_strategy()), never a bare manifest declaration -- the runner independently
     re-derives capability truth and checks contract conformance rather than trusting
     the strategy's self-report.
  2. Every capability a provider declares UNsupported is genuinely rejected by
     ResolvedStrategyHandle.require_capability() -- the real, executable negative-
     capability enforcement mechanism -- for all 10 providers, closing the "negative
     capability matrix... each NO enforced in executable code" acceptance cell without
     needing a bespoke per-provider test for every declared-unsupported capability.
  3. Certification cannot self-certify: a provider cannot elevate its own capability
     claims merely by declaring them -- reusing the same runner already proven (in
     tests/unit/engine_extensions/test_certification_runner.py) to refuse fabricating
     LIVE_PROVEN without a real CertificationReference, now exercised against real
     first-10 provider strategies rather than synthetic test doubles.
"""

from __future__ import annotations

import pytest

from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.certification.runner import ConnectorCertificationRunner

NEW_PROVIDERS = [
    "cockroachdb", "rabbitmq", "pulsar", "dynamodb", "couchbase",
    "clickhouse", "influxdb", "yugabytedb", "tidb", "singlestore",
]


def _fresh_extensions_authority():
    ext_auth = ExtensionsAuthority.get_instance()
    ext_auth.bootstrap_builtin_providers()
    return ext_auth


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_real_certification_run_passes_contract_conformance(provider_id):
    """The real ConnectorCertificationRunner must successfully resolve and certify
    every one of the 10 providers' live "connection" strategy instance -- contract
    conformance passing proves the runner is independently re-validating the strategy
    instance against the real authority contract, not merely trusting a manifest."""
    ext_auth = _fresh_extensions_authority()
    report = ConnectorCertificationRunner.certify(ext_auth, provider_id, "connection")

    assert report.provider_id == provider_id
    contract_check = next(r for r in report.results if r.check_name == "contract_conformance")
    assert contract_check.passed, f"'{provider_id}' failed real contract conformance: {contract_check.diagnostic}"


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_every_declared_unsupported_capability_is_genuinely_enforced(provider_id):
    """For every one of the 10 providers, every capability its real resolved strategy
    handle declares UNsupported must be genuinely rejected by require_capability() --
    proving the negative-capability matrix is enforced in executable code for all 10,
    not merely documented in a static manifest."""
    ext_auth = _fresh_extensions_authority()
    report = ConnectorCertificationRunner.certify(ext_auth, provider_id, "connection")

    negative_checks = [r for r in report.results if r.check_name == "negative_capability_enforced"]
    assert negative_checks, (
        f"'{provider_id}' declared zero unsupported capabilities -- suspicious for any "
        f"real connector; expected at least one genuine negative capability"
    )
    unenforced = [c for c in negative_checks if not c.passed]
    assert not unenforced, (
        f"'{provider_id}' has {len(unenforced)} declared-unsupported capabilities that "
        f"require_capability() did NOT reject: {[c.capability_name for c in unenforced]}"
    )


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_every_declared_supported_capability_resolves_truthfully(provider_id):
    """Every capability a provider's real strategy declares SUPPORTED must resolve to a
    truthful, non-fabricated proof level via the runner's independent capability-
    declaration-integrity check, for all 10 providers."""
    ext_auth = _fresh_extensions_authority()
    report = ConnectorCertificationRunner.certify(ext_auth, provider_id, "connection")

    positive_checks = [r for r in report.results if r.check_name == "capability_declaration_integrity"]
    assert positive_checks, f"'{provider_id}' declared zero supported capabilities"
    assert all(c.passed for c in positive_checks)


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_certification_obligations_reflect_only_actually_declared_capabilities(provider_id):
    """The obligation set attached to the report must be entirely derived from this
    provider's own real resolved capabilities (never a fixed universal set) -- every
    non-NOT_APPLICABLE, capability-triggered obligation must target a capability this
    provider's live strategy actually advertises (supported or not), for all 10
    providers."""
    from akaalEngine.extensions.certification.obligations import ObligationStatus

    ext_auth = _fresh_extensions_authority()
    report = ConnectorCertificationRunner.certify(ext_auth, provider_id, "connection")

    assert len(report.obligation_results) > 0
    for obl_result in report.obligation_results:
        if obl_result.status == ObligationStatus.NOT_APPLICABLE:
            continue
        if obl_result.target_capability is not None:
            handle = ext_auth.resolve_strategy(provider_id=provider_id, authority_id="connection")
            try:
                assert obl_result.target_capability in handle.capabilities, (
                    f"'{provider_id}' obligation '{obl_result.obligation_id}' targets capability "
                    f"'{obl_result.target_capability}' which this provider's real strategy never "
                    f"advertises at all -- obligations must be capability-derived, not fabricated"
                )
            finally:
                handle.release()
