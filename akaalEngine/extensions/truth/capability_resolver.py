"""
akaalEngine.extensions.truth.capability_resolver
================================================
Derives effective capability truth from declaration, dependencies, lifecycle state, and proof governance.
Guarantees fail-closed evaluation: UNKNOWN != SUPPORTED.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from akaalEngine.extensions.truth.authority_store import CertificationAuthorityStore
from akaalEngine.extensions.dependencies.diagnostics import DependencyDiagnosticReport
from akaalEngine.extensions.models.capability import CapabilityDeclaration, CapabilityTruth
from akaalEngine.extensions.models.enums import ExtensionLifecycleState, ProofLevel
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference
from akaalEngine.extensions.truth.proof_resolver import ProofResolver


class CapabilityTruthResolver:
    """
    Derives authoritative CapabilityTruth instances.
    """

    @classmethod
    def resolve_capability_truth(
        cls,
        declaration: Optional[CapabilityDeclaration],
        capability_name: str,
        lifecycle_state: ExtensionLifecycleState,
        dep_report: Optional[DependencyDiagnosticReport] = None,
        proof_references: Sequence[ProofReference] = (),
        certifications: Sequence[CertificationReference] = (),
        authority_store: Optional[CertificationAuthorityStore] = None,
        extension_id: Optional[str] = None,
        extension_version: Optional[str] = None,
        provider_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> CapabilityTruth:
        cap_name_norm = capability_name.strip().upper()

        if declaration is None or not declaration.is_supported:
            return CapabilityTruth(
                capability_name=cap_name_norm,
                is_supported=False,
                proof_level=ProofLevel.DECLARED,
                is_dependency_satisfied=False,
                diagnostic=getattr(declaration, "notes", None) or f"Capability '{cap_name_norm}' is not declared or explicitly unsupported.",
            )

        # Check lifecycle state: if UNAVAILABLE or FAULTED, it cannot be supported
        if lifecycle_state in (ExtensionLifecycleState.UNAVAILABLE, ExtensionLifecycleState.FAULTED, ExtensionLifecycleState.REMOVED):
            return CapabilityTruth(
                capability_name=cap_name_norm,
                is_supported=False,
                proof_level=ProofLevel.DECLARED,
                is_dependency_satisfied=False,
                diagnostic=f"Extension lifecycle state '{lifecycle_state.value}' disables capability support.",
            )

        # Check dependencies
        dep_satisfied = True
        missing_deps: list[str] = []
        if dep_report is not None:
            if not dep_report.is_all_mandatory_satisfied:
                dep_satisfied = False
                missing_deps = [d.dependency_name for d in dep_report.missing_mandatory]

        if not dep_satisfied:
            return CapabilityTruth(
                capability_name=cap_name_norm,
                is_supported=False,
                proof_level=ProofLevel.DECLARED,
                is_dependency_satisfied=False,
                missing_dependencies=tuple(missing_deps),
                diagnostic=f"Capability '{cap_name_norm}' requires unsatisfied dependencies: {missing_deps}.",
            )

        # Resolve proof level
        effective_proof = ProofResolver.resolve_effective_proof_level(
            declaration=declaration,
            proof_references=proof_references,
            certifications=certifications,
            authority_store=authority_store,
            extension_id=extension_id,
            extension_version=extension_version,
            provider_id=provider_id,
            strategy_id=strategy_id,
        )

        return CapabilityTruth(
            capability_name=cap_name_norm,
            is_supported=True,
            proof_level=effective_proof,
            is_dependency_satisfied=True,
            restrictions=declaration.restrictions,
        )


default_capability_truth_resolver = CapabilityTruthResolver()
