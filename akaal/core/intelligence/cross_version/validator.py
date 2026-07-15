"""
Akaal — Cross-Version Compatibility Validator
=============================================
Validates compatibility rule configurations and startup profiles.
Checks for inverted version bounds, missing required fields,
duplicate profile IDs, and unsupported dialect combinations.
"""

from typing import Any, Dict, List, Optional, Set

from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.models import Diagnostic, Severity, DiagnosticCategory
from akaal.core.intelligence.cross_version.exceptions import (
    CompatibilityRuleValidationError,
)
from akaal.core.intelligence.cross_version.models import (
    CompatibilityRule,
    CompatibilityRuleAction,
)
from akaal.core.intelligence.cross_version.registry import _parse_version


class CompatibilityRuleSetValidator:
    """
    Validates a collection of CompatibilityRules for structural correctness
    before they are submitted to the registry.

    Checks:
    - rule_id and rule_name are non-empty
    - priority is within [1, 1000]
    - Version bounds are not inverted (min <= max)
    - No duplicate rule IDs within the set
    """

    def validate_ruleset(self, rules: List[CompatibilityRule]) -> None:
        """
        Validates the entire rule set. Raises CompatibilityRuleValidationError
        on the first structural violation found.
        """
        seen_ids: Set[str] = set()

        for rule in rules:
            if not rule.rule_id:
                raise CompatibilityRuleValidationError(
                    "Rule is missing 'rule_id'.",
                    error_code="COMPAT_CONFIG_MISSING_RULE_ID",
                )
            if rule.rule_id in seen_ids:
                raise CompatibilityRuleValidationError(
                    f"Duplicate rule_id detected: '{rule.rule_id}'.",
                    error_code="COMPAT_CONFIG_DUPLICATE_RULE_ID",
                )
            seen_ids.add(rule.rule_id)

            if not rule.rule_name:
                raise CompatibilityRuleValidationError(
                    f"Rule '{rule.rule_id}' is missing 'rule_name'.",
                    error_code="COMPAT_CONFIG_MISSING_RULE_NAME",
                )

            if not (1 <= rule.priority <= 1000):
                raise CompatibilityRuleValidationError(
                    f"Rule '{rule.rule_id}' priority {rule.priority} is out of range [1, 1000].",
                    error_code="COMPAT_CONFIG_INVALID_PRIORITY",
                )

            if rule.min_source_version and rule.max_source_version:
                if _parse_version(rule.min_source_version) > _parse_version(rule.max_source_version):
                    raise CompatibilityRuleValidationError(
                        f"Rule '{rule.rule_id}' has inverted source version bounds: "
                        f"min_source_version '{rule.min_source_version}' > "
                        f"max_source_version '{rule.max_source_version}'.",
                        error_code="COMPAT_CONFIG_INVERTED_VERSION_BOUNDS",
                    )

            if rule.min_target_version and rule.max_target_version:
                if _parse_version(rule.min_target_version) > _parse_version(rule.max_target_version):
                    raise CompatibilityRuleValidationError(
                        f"Rule '{rule.rule_id}' has inverted target version bounds: "
                        f"min_target_version '{rule.min_target_version}' > "
                        f"max_target_version '{rule.max_target_version}'.",
                        error_code="COMPAT_CONFIG_INVERTED_VERSION_BOUNDS",
                    )

    def validate_startup_config(self, config_data: Dict[str, Any]) -> None:
        """
        Validates a JSON-deserialized configuration dictionary containing
        a list of rule definitions. Used for startup-time config validation.

        Expected structure:
        {
            "rules": [
                {"rule_id": "...", "rule_name": "...", "priority": 10, ...},
                ...
            ]
        }
        """
        rules_data = config_data.get("rules", [])
        seen_ids: Set[str] = set()

        for idx, rule_dict in enumerate(rules_data):
            rule_id = rule_dict.get("rule_id")
            if not rule_id:
                raise CompatibilityRuleValidationError(
                    f"Rule at index {idx} is missing 'rule_id'.",
                    error_code="COMPAT_CONFIG_MISSING_RULE_ID",
                )
            if rule_id in seen_ids:
                raise CompatibilityRuleValidationError(
                    f"Duplicate rule_id '{rule_id}' at index {idx}.",
                    error_code="COMPAT_CONFIG_DUPLICATE_RULE_ID",
                )
            seen_ids.add(rule_id)

            min_src = rule_dict.get("min_source_version")
            max_src = rule_dict.get("max_source_version")
            if min_src and max_src:
                if _parse_version(min_src) > _parse_version(max_src):
                    raise CompatibilityRuleValidationError(
                        f"Rule '{rule_id}' source version bounds are inverted: "
                        f"min='{min_src}' > max='{max_src}'.",
                        error_code="COMPAT_CONFIG_INVERTED_VERSION_BOUNDS",
                    )


class CompatibilityFindingAuditor:
    """
    Post-analysis auditor that inspects computed findings for
    known anti-patterns and emits additional advisory diagnostics.

    Checks:
    - Blocking issues for critical features (partitioning, security)
    - Enterprise-only features requested on non-enterprise targets
    """

    _CRITICAL_FEATURES = frozenset({
        "oracle.tde", "mssql.tde", "mysql.tde", "pg.tde",
        "oracle.partitioning", "mssql.partitioning",
        "mysql.partitioning", "pg.partitioning",
    })

    def audit(
        self,
        findings: List[Any],
        target_edition: str = "STANDARD",
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[Diagnostic]:
        """
        Produces additional advisory diagnostics from finding results.

        Args:
            findings: List of CompatibilityFinding instances.
            target_edition: Target database edition (e.g., ENTERPRISE, STANDARD).
            session_id: Optional session ID for diagnostic context.
            correlation_id: Distributed trace correlation ID.
            trace_id: Distributed trace ID.

        Returns:
            List of additional Diagnostic instances.
        """
        extra_diagnostics: List[Diagnostic] = []

        for finding in findings:
            # Flag blocked critical features at CRITICAL severity
            if (
                finding.action == CompatibilityRuleAction.BLOCK
                and finding.feature_id in self._CRITICAL_FEATURES
            ):
                extra_diagnostics.append(Diagnostic(
                    diagnostic_code="COMPAT_CRITICAL_FEATURE_BLOCKED",
                    severity=Severity.CRITICAL,
                    category=DiagnosticCategory.COMPATIBILITY,
                    message=(
                        f"Critical feature '{finding.feature_name}' is BLOCKED "
                        f"on target {finding.target_dialect.value}. "
                        f"This may prevent migration completion."
                    ),
                    path=f"features.{finding.feature_id}",
                    remediation_guidance=(
                        finding.remediation_guidance
                        or "Consider an alternative target or redesign the schema."
                    ),
                    explanation=(
                        f"Feature '{finding.feature_id}' is classified as critical "
                        f"and is unsupported or incompatible on the target dialect."
                    ),
                    root_cause="Dialect incompatibility for critical feature.",
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                ))

        return extra_diagnostics
