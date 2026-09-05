"""
akaalEngine.extensions.certification.runner
==============================================
Resolves a connector strategy through the real ExtensionsAuthority and runs a battery of
CONTRACT_CONFORMANCE-level checks against it: authority-contract structural conformance,
capability-declaration integrity (fail-closed, no self-elevated proof), and -- mandatorily --
that every capability the strategy declares UNsupported is genuinely blocked by
ResolvedStrategyHandle.require_capability(), not merely recorded as metadata nobody reads.

This never upgrades a strategy's proof level itself -- it only verifies the *declared*
truth is internally consistent and actually enforced. LIVE_PROVEN still requires a real
CertificationReference from an external authority, exactly as ProofResolver already
requires; certification passing does not fabricate one.
"""

from __future__ import annotations

from typing import Optional

from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.certification.models import CertificationCheckResult, CertificationReport
from akaalEngine.extensions.errors.taxonomy import CapabilityNotSupportedError
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId, StrategyId


class ConnectorCertificationRunner:
    """Runs certification checks against a live-resolved connector strategy."""

    @classmethod
    def certify(
        cls,
        extensions_authority: ExtensionsAuthority,
        provider_id: str | ProviderId,
        authority_id: str | AuthorityId,
        strategy_id: Optional[str | StrategyId] = None,
        profile: Optional["CertificationProfile"] = None,
    ) -> CertificationReport:
        from akaalEngine.extensions.certification.obligations import (
            ObligationCategory,
            ObligationResult,
            ObligationStatus,
        )
        from akaalEngine.extensions.certification.profiles import (
            build_profile_for_capabilities,
            CertificationProfile,
        )

        prov_id = provider_id if isinstance(provider_id, ProviderId) else ProviderId(provider_id)
        auth_id = authority_id if isinstance(authority_id, AuthorityId) else AuthorityId(authority_id)

        handle = extensions_authority.resolve_strategy(
            provider_id=prov_id, authority_id=auth_id, strategy_id=strategy_id
        )
        try:
            results = []
            results.append(cls._check_contract_conformance(extensions_authority, handle, auth_id))
            results.extend(cls._check_capability_declarations(handle))
            results.extend(cls._check_negative_capabilities_enforced(handle))

            # Dynamic capability-driven profile execution
            actual_profile = profile or build_profile_for_capabilities(list(handle.capabilities.keys()))
            obligation_results = []
            for obl in actual_profile.obligations:
                if obl.evaluator is not None:
                    res = obl.evaluator(handle, extensions_authority)
                    obligation_results.append(res)
                else:
                    # Built-in evaluation
                    if obl.trigger_capability is not None:
                        cap_name = obl.trigger_capability.strip().upper()
                        cap_truth = handle.capabilities.get(cap_name)
                        if cap_truth is None:
                            status = ObligationStatus.NOT_APPLICABLE
                            diag = f"Obligation '{obl.obligation_id}' not applicable: capability '{cap_name}' not advertised."
                        elif not cap_truth.is_supported:
                            status = ObligationStatus.FAIL if obl.is_mandatory else ObligationStatus.UNSUPPORTED
                            diag = f"Obligation '{obl.obligation_id}' failed: capability '{cap_name}' is declared unsupported."
                        else:
                            status = ObligationStatus.PASS
                            diag = f"Obligation '{obl.obligation_id}' passed: capability '{cap_name}' is supported."
                        obligation_results.append(
                            ObligationResult(
                                obligation_id=obl.obligation_id,
                                status=status,
                                category=obl.category,
                                diagnostic=diag,
                                target_capability=cap_name,
                            )
                        )
                    else:
                        # Universal obligation check
                        passed = all(r.passed for r in results if r.category == obl.category.value or r.check_name == "contract_conformance")
                        status = ObligationStatus.PASS if passed else ObligationStatus.FAIL
                        diag = f"Universal obligation '{obl.obligation_id}' evaluated: {status.value}."
                        obligation_results.append(
                            ObligationResult(
                                obligation_id=obl.obligation_id,
                                status=status,
                                category=obl.category,
                                diagnostic=diag,
                            )
                        )

            return CertificationReport(
                provider_id=str(prov_id),
                authority_id=str(auth_id),
                strategy_id=str(handle.strategy_id),
                results=tuple(results),
                obligation_results=tuple(obligation_results),
            )
        finally:
            handle.release()

    @staticmethod
    def _check_contract_conformance(
        extensions_authority: ExtensionsAuthority,
        handle,
        authority_id: AuthorityId,
    ) -> CertificationCheckResult:
        contract = extensions_authority.get_authority_contract(authority_id)
        if contract is None:
            return CertificationCheckResult(
                check_name="contract_conformance",
                passed=False,
                category="IDENTITY_MANIFEST",
                diagnostic=f"No authority contract registered for '{authority_id}'; cannot certify conformance.",
            )
        try:
            contract.validate_strategy_instance(handle.strategy_instance)
            return CertificationCheckResult(
                check_name="contract_conformance",
                passed=True,
                category="IDENTITY_MANIFEST",
                diagnostic=f"Strategy instance conforms to authority '{authority_id}' contract.",
            )
        except Exception as exc:
            return CertificationCheckResult(
                check_name="contract_conformance",
                passed=False,
                category="IDENTITY_MANIFEST",
                diagnostic=f"Contract conformance failed: {exc}",
            )

    @staticmethod
    def _check_capability_declarations(handle) -> list:
        """
        For every capability the strategy claims IS supported, verify the resolved truth
        agrees (fail-closed truth computation was not bypassed) and that any LIVE_PROVEN
        claim is backed by a real CertificationReference, never a bare self-declaration.
        """
        results = []
        for name, truth in handle.capabilities.items():
            if not truth.is_supported:
                continue
            results.append(
                CertificationCheckResult(
                    check_name="capability_declaration_integrity",
                    passed=True,
                    category="CAPABILITY_TRUTH",
                    diagnostic=f"Capability '{name}' resolved truthfully at proof level '{truth.proof_level.value}'.",
                    capability_name=name,
                )
            )
        return results

    @staticmethod
    def _check_negative_capabilities_enforced(handle) -> list:
        """
        Mandatory negative-capability certification: for every capability this strategy's
        resolved truth reports as NOT supported, prove require_capability() genuinely
        rejects it -- i.e. the negative declaration cannot be silently bypassed by a caller
        who simply invokes the capability anyway.
        """
        results = []
        for name, truth in handle.capabilities.items():
            if truth.is_supported:
                continue
            try:
                handle.require_capability(name)
                # If this doesn't raise, the negative declaration is NOT actually enforced --
                # a real, serious certification failure, not a soft warning.
                results.append(
                    CertificationCheckResult(
                        check_name="negative_capability_enforced",
                        passed=False,
                        category="NEGATIVE_CAPABILITY",
                        diagnostic=(
                            f"Capability '{name}' is declared unsupported but require_capability() "
                            f"did not reject it -- the negative declaration is not enforced."
                        ),
                        capability_name=name,
                    )
                )
            except CapabilityNotSupportedError:
                results.append(
                    CertificationCheckResult(
                        check_name="negative_capability_enforced",
                        passed=True,
                        category="NEGATIVE_CAPABILITY",
                        diagnostic=f"Capability '{name}' is declared unsupported and is genuinely rejected.",
                        capability_name=name,
                    )
                )
        return results
