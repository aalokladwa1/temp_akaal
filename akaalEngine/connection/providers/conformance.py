"""
akaalEngine.connection.providers.conformance
===========================================
Reusable Provider Conformance Test Suite & Runner.
Enforces zero-fake manifest invariants, truthful dependency diagnostics, and error normalization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import ConnectionFailure, FailureCategory
from akaalEngine.connection.providers.base import BaseProviderStrategy

logger = logging.getLogger("akaalEngine.connection.providers.conformance")


@dataclass
class ConformanceCheckResult:
    check_name: str
    passed: bool
    details: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConformanceReport:
    provider_id: str
    is_conformant: bool
    results: List[ConformanceCheckResult] = field(default_factory=list)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "is_conformant": self.is_conformant,
            "checks_total": len(self.results),
            "checks_passed": sum(1 for r in self.results if r.passed),
            "checks_failed": sum(1 for r in self.results if not r.passed),
            "results": [
                {"name": r.check_name, "passed": r.passed, "details": r.details}
                for r in self.results
            ],
        }


class ProviderConformanceSuite:
    """
    Executes automated contract and behavior conformance verification against any BaseProviderStrategy.
    """

    @classmethod
    def run_suite(cls, strategy: BaseProviderStrategy) -> ConformanceReport:
        results: list[ConformanceCheckResult] = []
        provider_id = strategy.PROVIDER_ID

        # 1. Manifest Invariant Checks
        try:
            manifest = strategy.get_static_manifest()
            if not manifest.provider_id or manifest.provider_id.lower() != provider_id.lower():
                results.append(
                    ConformanceCheckResult("manifest_identity", False, "Manifest provider_id mismatch.")
                )
            else:
                results.append(
                    ConformanceCheckResult("manifest_identity", True, "Manifest provider_id matches strategy.")
                )

            # Check fail-closed behavior on unknown capability
            is_fake_cap_supported = manifest.is_capability_supported("NON_EXISTENT_FAKE_CAPABILITY")
            if is_fake_cap_supported:
                results.append(
                    ConformanceCheckResult("fail_closed_unknown_capability", False, "Unknown capability returned True.")
                )
            else:
                results.append(
                    ConformanceCheckResult("fail_closed_unknown_capability", True, "Unknown capability correctly returned False.")
                )

        except Exception as exc:
            results.append(
                ConformanceCheckResult("manifest_retrieval", False, f"Manifest check failed: {exc}")
            )

        # 2. Dependency Reporting Invariant (Must never raise ImportError)
        try:
            is_avail, msg = strategy.is_dependency_available()
            if not isinstance(is_avail, bool) or not isinstance(msg, str):
                results.append(
                    ConformanceCheckResult("dependency_reporting", False, "Invalid dependency report return type.")
                )
            else:
                results.append(
                    ConformanceCheckResult("dependency_reporting", True, f"Dependency reported: available={is_avail}")
                )
        except Exception as exc:
            results.append(
                ConformanceCheckResult("dependency_reporting", False, f"Dependency check threw exception: {exc}")
            )

        # 3. Error Normalization & Redaction Check
        try:
            fake_exc = Exception("Connection to host:5432 failed password=SUPER_SECRET_VALUE token=BEARER_XYZ")
            failure = strategy.normalize_error(fake_exc, stage="TEST")
            if not isinstance(failure, ConnectionFailure):
                results.append(
                    ConformanceCheckResult("error_normalization_type", False, "normalize_error did not return ConnectionFailure.")
                )
            else:
                if "SUPER_SECRET_VALUE" in failure.message or "BEARER_XYZ" in failure.message:
                    results.append(
                        ConformanceCheckResult("error_redaction", False, "Normalized failure leaked secret values.")
                    )
                else:
                    results.append(
                        ConformanceCheckResult("error_redaction", True, "Normalized failure successfully redacted secrets.")
                    )
        except Exception as exc:
            results.append(
                ConformanceCheckResult("error_normalization", False, f"normalize_error threw exception: {exc}")
            )

        # 4. Configuration Validation Check
        try:
            valid_spec = EndpointSpec(
                provider_id=provider_id,
                host="localhost",
                port=5432,
                database_name="default_db",
            )
            strategy.validate_configuration(valid_spec)
            results.append(
                ConformanceCheckResult("configuration_validation", True, "Valid configuration passed validation.")
            )
        except Exception as exc:
            results.append(
                ConformanceCheckResult("configuration_validation", False, f"validate_configuration failed: {exc}")
            )

        all_passed = all(r.passed for r in results)
        return ConformanceReport(provider_id=provider_id, is_conformant=all_passed, results=results)
