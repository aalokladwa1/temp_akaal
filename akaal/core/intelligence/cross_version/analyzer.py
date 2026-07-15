"""
Akaal — Cross-Version Compatibility Capability Analyzer
========================================================
Evaluates source schema features against target dialect capability matrices,
resolves compatibility tiers, generates structured findings, and produces
CompatibilityStatistics and CompatibilitySummary for report assembly.

No SQL generation. No DDL output. No database writes.
Pure metadata analysis and planning only.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.comparison.models import Schema
from akaal.core.conversion.api.models import DbVersion

from akaal.core.intelligence.cross_version.models import (
    CompatibilityTier,
    CompatibilityRuleAction,
    FeatureCategory,
    FeatureCapability,
    CompatibilityRule,
    CompatibilityScore,
    CompatibilityFinding,
    CompatibilityStatistics,
    CompatibilitySummary,
    CompatibilityReport,
)
from akaal.core.intelligence.cross_version.registry import CompatibilityStrategyRegistry
from akaal.core.intelligence.cross_version.report import CompatibilityReportBuilder
from akaal.core.intelligence.common.models import Diagnostic, Severity, DiagnosticCategory


# =============================================================================
# Built-in Feature Capability Matrix
# =============================================================================

# Each entry describes a feature and its native support per dialect/version.
# The analyzer uses this as the ground-truth catalog.
_BUILT_IN_CAPABILITIES: List[FeatureCapability] = [
    # ---- Oracle ----
    FeatureCapability("oracle.partitioning", "Table Partitioning", FeatureCategory.PARTITIONING,
                      SystemType.ORACLE, "8i", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("oracle.tde", "Transparent Data Encryption", FeatureCategory.SECURITY,
                      SystemType.ORACLE, "11g", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("oracle.hcc", "Hybrid Columnar Compression", FeatureCategory.PERFORMANCE,
                      SystemType.ORACLE, "11.2", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("oracle.stored_procs", "PL/SQL Stored Procedures", FeatureCategory.PROCEDURAL,
                      SystemType.ORACLE, "7", True, CompatibilityTier.NATIVE),
    FeatureCapability("oracle.materialized_views", "Materialized Views", FeatureCategory.DDL,
                      SystemType.ORACLE, "8", True, CompatibilityTier.NATIVE),
    FeatureCapability("oracle.dblinks", "Database Links", FeatureCategory.NETWORKING,
                      SystemType.ORACLE, "7", True, CompatibilityTier.NATIVE),
    FeatureCapability("oracle.bitmap_indexes", "Bitmap Indexes", FeatureCategory.INDEXING,
                      SystemType.ORACLE, "8i", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("oracle.cdc_logminer", "LogMiner CDC", FeatureCategory.REPLICATION,
                      SystemType.ORACLE, "9i", True, CompatibilityTier.NATIVE),

    # ---- PostgreSQL ----
    FeatureCapability("pg.partitioning", "Declarative Partitioning", FeatureCategory.PARTITIONING,
                      SystemType.POSTGRESQL, "10", True, CompatibilityTier.NATIVE),
    FeatureCapability("pg.tde", "pgcrypto Column Encryption", FeatureCategory.SECURITY,
                      SystemType.POSTGRESQL, "8.3", True, CompatibilityTier.PLUGIN_PROVIDED,
                      requires_plugin=True, notes="Requires pgcrypto extension"),
    FeatureCapability("pg.stored_procs", "PL/pgSQL Stored Procedures", FeatureCategory.PROCEDURAL,
                      SystemType.POSTGRESQL, "8.0", True, CompatibilityTier.NATIVE),
    FeatureCapability("pg.cte", "Common Table Expressions", FeatureCategory.ANALYTICS,
                      SystemType.POSTGRESQL, "8.4", True, CompatibilityTier.NATIVE),
    FeatureCapability("pg.window_functions", "Window Functions", FeatureCategory.ANALYTICS,
                      SystemType.POSTGRESQL, "8.4", True, CompatibilityTier.NATIVE),
    FeatureCapability("pg.logical_replication", "Logical Replication", FeatureCategory.REPLICATION,
                      SystemType.POSTGRESQL, "10", True, CompatibilityTier.NATIVE),
    FeatureCapability("pg.materialized_views", "Materialized Views", FeatureCategory.DDL,
                      SystemType.POSTGRESQL, "9.3", True, CompatibilityTier.NATIVE),

    # ---- MySQL ----
    FeatureCapability("mysql.partitioning", "Table Partitioning", FeatureCategory.PARTITIONING,
                      SystemType.MYSQL, "5.1", True, CompatibilityTier.NATIVE),
    FeatureCapability("mysql.tde", "InnoDB Tablespace Encryption", FeatureCategory.SECURITY,
                      SystemType.MYSQL, "5.7.11", True, CompatibilityTier.NATIVE,
                      requires_plugin=True, notes="Requires keyring plugin"),
    FeatureCapability("mysql.stored_procs", "Stored Procedures", FeatureCategory.PROCEDURAL,
                      SystemType.MYSQL, "5.0", True, CompatibilityTier.NATIVE),
    FeatureCapability("mysql.window_functions", "Window Functions", FeatureCategory.ANALYTICS,
                      SystemType.MYSQL, "8.0", True, CompatibilityTier.NATIVE),
    FeatureCapability("mysql.cte", "CTEs", FeatureCategory.ANALYTICS,
                      SystemType.MYSQL, "8.0", True, CompatibilityTier.NATIVE),

    # ---- SQL Server ----
    FeatureCapability("mssql.partitioning", "Table Partitioning", FeatureCategory.PARTITIONING,
                      SystemType.MSSQL, "2005", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("mssql.tde", "Transparent Data Encryption", FeatureCategory.SECURITY,
                      SystemType.MSSQL, "2008", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("mssql.columnstore", "Columnstore Indexes", FeatureCategory.INDEXING,
                      SystemType.MSSQL, "2012", True, CompatibilityTier.NATIVE, requires_enterprise=True),
    FeatureCapability("mssql.stored_procs", "T-SQL Stored Procedures", FeatureCategory.PROCEDURAL,
                      SystemType.MSSQL, "2000", True, CompatibilityTier.NATIVE),
    FeatureCapability("mssql.window_functions", "Window Functions", FeatureCategory.ANALYTICS,
                      SystemType.MSSQL, "2005", True, CompatibilityTier.NATIVE),
    FeatureCapability("mssql.cte", "CTEs", FeatureCategory.ANALYTICS,
                      SystemType.MSSQL, "2005", True, CompatibilityTier.NATIVE),
]


def _build_capability_index() -> Dict[str, FeatureCapability]:
    """Indexes capabilities by feature_id for O(1) lookup."""
    return {cap.feature_id: cap for cap in _BUILT_IN_CAPABILITIES}


_CAPABILITY_INDEX: Dict[str, FeatureCapability] = _build_capability_index()


# =============================================================================
# Cross-Dialect Compatibility Graph
# =============================================================================

# Maps (source_feature_prefix, target_dialect) -> (tier, confidence, notes)
# e.g. oracle features migrating to PostgreSQL
_CROSS_DIALECT_TIERS: Dict[Tuple[str, SystemType], Tuple[CompatibilityTier, float, str]] = {
    # Oracle -> PostgreSQL
    ("oracle.partitioning", SystemType.POSTGRESQL): (CompatibilityTier.NATIVE, 0.90, "Declarative partitioning supported"),
    ("oracle.tde", SystemType.POSTGRESQL): (CompatibilityTier.PLUGIN_PROVIDED, 0.70, "pgcrypto extension required"),
    ("oracle.hcc", SystemType.POSTGRESQL): (CompatibilityTier.PARTIAL, 0.50, "TOAST compression available; HCC semantics differ"),
    ("oracle.stored_procs", SystemType.POSTGRESQL): (CompatibilityTier.EMULATED, 0.80, "PL/pgSQL is functionally similar"),
    ("oracle.materialized_views", SystemType.POSTGRESQL): (CompatibilityTier.NATIVE, 0.92, "Native materialized views in 9.3+"),
    ("oracle.dblinks", SystemType.POSTGRESQL): (CompatibilityTier.PLUGIN_PROVIDED, 0.60, "postgres_fdw provides remote access"),
    ("oracle.bitmap_indexes", SystemType.POSTGRESQL): (CompatibilityTier.PARTIAL, 0.55, "BRIN indexes partially equivalent"),
    ("oracle.cdc_logminer", SystemType.POSTGRESQL): (CompatibilityTier.EMULATED, 0.75, "Logical replication slots available"),

    # Oracle -> MySQL
    ("oracle.partitioning", SystemType.MYSQL): (CompatibilityTier.NATIVE, 0.85, "MySQL range/list partitioning available"),
    ("oracle.tde", SystemType.MYSQL): (CompatibilityTier.NATIVE, 0.80, "InnoDB tablespace encryption available"),
    ("oracle.hcc", SystemType.MYSQL): (CompatibilityTier.UNSUPPORTED, 0.10, "No columnar compression in MySQL"),
    ("oracle.stored_procs", SystemType.MYSQL): (CompatibilityTier.EMULATED, 0.70, "MySQL stored procedures are limited"),
    ("oracle.materialized_views", SystemType.MYSQL): (CompatibilityTier.UNSUPPORTED, 0.10, "No native materialized views"),
    ("oracle.dblinks", SystemType.MYSQL): (CompatibilityTier.PLUGIN_PROVIDED, 0.50, "FEDERATED engine available"),
    ("oracle.bitmap_indexes", SystemType.MYSQL): (CompatibilityTier.UNSUPPORTED, 0.05, "No bitmap indexes in MySQL"),
    ("oracle.cdc_logminer", SystemType.MYSQL): (CompatibilityTier.EMULATED, 0.65, "Binary log CDC available"),

    # Oracle -> MSSQL
    ("oracle.partitioning", SystemType.MSSQL): (CompatibilityTier.NATIVE, 0.88, "Partition functions and schemes available"),
    ("oracle.tde", SystemType.MSSQL): (CompatibilityTier.NATIVE, 0.92, "MSSQL TDE natively supported"),
    ("oracle.hcc", SystemType.MSSQL): (CompatibilityTier.PARTIAL, 0.65, "Columnstore indexes partially equivalent"),
    ("oracle.stored_procs", SystemType.MSSQL): (CompatibilityTier.EMULATED, 0.75, "T-SQL has different semantics"),
    ("oracle.materialized_views", SystemType.MSSQL): (CompatibilityTier.EMULATED, 0.80, "Indexed views approximate MV behavior"),
    ("oracle.bitmap_indexes", SystemType.MSSQL): (CompatibilityTier.PARTIAL, 0.55, "Columnstore indexes partially substitute"),
    ("oracle.cdc_logminer", SystemType.MSSQL): (CompatibilityTier.NATIVE, 0.85, "MSSQL CDC natively supported"),

    # PostgreSQL -> MySQL
    ("pg.partitioning", SystemType.MYSQL): (CompatibilityTier.NATIVE, 0.85, "MySQL partitioning supported"),
    ("pg.tde", SystemType.MYSQL): (CompatibilityTier.NATIVE, 0.78, "InnoDB encryption available"),
    ("pg.stored_procs", SystemType.MYSQL): (CompatibilityTier.EMULATED, 0.70, "MySQL SPs have different dialect"),
    ("pg.cte", SystemType.MYSQL): (CompatibilityTier.NATIVE, 0.90, "CTEs supported since MySQL 8.0"),
    ("pg.window_functions", SystemType.MYSQL): (CompatibilityTier.NATIVE, 0.90, "Supported since MySQL 8.0"),
    ("pg.logical_replication", SystemType.MYSQL): (CompatibilityTier.EMULATED, 0.65, "Binary log replication is similar"),
    ("pg.materialized_views", SystemType.MYSQL): (CompatibilityTier.UNSUPPORTED, 0.10, "No native MVs in MySQL"),

    # MySQL -> PostgreSQL
    ("mysql.partitioning", SystemType.POSTGRESQL): (CompatibilityTier.NATIVE, 0.88, "Declarative partitioning available"),
    ("mysql.tde", SystemType.POSTGRESQL): (CompatibilityTier.PLUGIN_PROVIDED, 0.70, "pgcrypto required"),
    ("mysql.stored_procs", SystemType.POSTGRESQL): (CompatibilityTier.EMULATED, 0.75, "PL/pgSQL dialect differs"),
    ("mysql.window_functions", SystemType.POSTGRESQL): (CompatibilityTier.NATIVE, 0.95, "Full window function support"),
    ("mysql.cte", SystemType.POSTGRESQL): (CompatibilityTier.NATIVE, 0.95, "Full CTE support"),
}


# =============================================================================
# Compatibility Analyzer
# =============================================================================

class CompatibilityCapabilityAnalyzer:
    """
    Evaluates a source schema against a target dialect/version, producing
    structured findings for each known feature.

    Analysis steps:
    1. Enumerate all known source-dialect features.
    2. For each feature, look up the cross-dialect compatibility tier.
    3. Resolve the best matching rule from the registry (if any).
    4. Score the finding.
    5. Emit diagnostics for BLOCK/WARN actions.
    6. Aggregate statistics and summary.
    """

    def __init__(self, registry: CompatibilityStrategyRegistry) -> None:
        self._registry = registry

    def analyze(
        self,
        schema: Schema,
        source_dialect: SystemType,
        target_dialect: SystemType,
        source_version: str,
        target_version: str,
        correlation_id: str = "",
        trace_id: str = "",
        session_id: Optional[str] = None,
    ) -> Tuple[
        List[CompatibilityFinding],
        List[Diagnostic],
        CompatibilityStatistics,
        CompatibilitySummary,
    ]:
        """
        Runs the full compatibility analysis pass.

        Returns:
            findings: One CompatibilityFinding per evaluated feature.
            diagnostics: WARN/BLOCK diagnostics for operator review.
            statistics: Aggregate numeric metrics.
            summary: Executive boolean summary.
        """
        findings: List[CompatibilityFinding] = []
        diagnostics: List[Diagnostic] = []

        # Enumerate source-dialect capabilities to analyze
        source_capabilities = [
            cap for cap in _BUILT_IN_CAPABILITIES
            if cap.dialect == source_dialect
        ]

        for capability in source_capabilities:
            finding, diags = self._evaluate_capability(
                capability=capability,
                source_dialect=source_dialect,
                target_dialect=target_dialect,
                source_version=source_version,
                target_version=target_version,
                correlation_id=correlation_id,
                trace_id=trace_id,
                session_id=session_id,
            )
            findings.append(finding)
            diagnostics.extend(diags)

        statistics = self._compute_statistics(findings)
        summary = self._compute_summary(findings)

        return findings, diagnostics, statistics, summary

    def _evaluate_capability(
        self,
        capability: FeatureCapability,
        source_dialect: SystemType,
        target_dialect: SystemType,
        source_version: str,
        target_version: str,
        correlation_id: str,
        trace_id: str,
        session_id: Optional[str],
    ) -> Tuple[CompatibilityFinding, List[Diagnostic]]:
        """Evaluates a single source capability against the target dialect."""
        diagnostics: List[Diagnostic] = []

        # 1. Look up the cross-dialect tier from the built-in graph
        key = (capability.feature_id, target_dialect)
        tier_info = _CROSS_DIALECT_TIERS.get(key)

        if tier_info is not None:
            tier, base_confidence, notes = tier_info
        else:
            # Default: features not in the cross-dialect map are UNSUPPORTED
            tier = CompatibilityTier.UNSUPPORTED
            base_confidence = 0.10
            notes = f"No known mapping for {capability.feature_id} to {target_dialect.value}"

        # 2. Check registry for an overriding rule
        registry_rules = self._registry.get_matching_rules(
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            source_version=source_version,
            target_version=target_version,
        )
        # Take only rules that apply to this feature
        feature_rules = [r for r in registry_rules if r.feature_id == capability.feature_id]

        applied_rule: Optional[CompatibilityRule] = None
        action = CompatibilityRuleAction.ALLOW
        remediation: Optional[str] = None

        if feature_rules:
            applied_rule = feature_rules[0]  # Highest specificity/priority
            action = applied_rule.action
            tier = applied_rule.compatibility_tier
            remediation = applied_rule.remediation_guidance

        else:
            # Derive action from tier
            action = self._tier_to_default_action(tier)

        # 3. Build the compatibility score
        score = self._compute_score(tier, base_confidence, action)

        # 4. Emit diagnostics for WARN/BLOCK findings
        if action == CompatibilityRuleAction.BLOCK:
            diagnostics.append(Diagnostic(
                diagnostic_code=f"COMPAT_BLOCK_{capability.feature_id.upper().replace('.', '_')}",
                severity=Severity.CRITICAL,
                category=DiagnosticCategory.COMPATIBILITY,
                message=(
                    f"Feature '{capability.feature_name}' from {source_dialect.value} "
                    f"is BLOCKED on target {target_dialect.value}: {notes}"
                ),
                path=f"features.{capability.feature_id}",
                remediation_guidance=remediation or "Manual schema redesign required.",
                explanation=notes,
                root_cause=f"Incompatible dialect feature: {capability.feature_id}",
                affected_session=session_id,
                correlation_id=correlation_id or None,
                trace_id=trace_id or None,
            ))
        elif action in (CompatibilityRuleAction.WARN, CompatibilityRuleAction.REQUIRE_MANUAL):
            diagnostics.append(Diagnostic(
                diagnostic_code=f"COMPAT_WARN_{capability.feature_id.upper().replace('.', '_')}",
                severity=Severity.WARNING,
                category=DiagnosticCategory.COMPATIBILITY,
                message=(
                    f"Feature '{capability.feature_name}' from {source_dialect.value} "
                    f"has limited support on {target_dialect.value}: {notes}"
                ),
                path=f"features.{capability.feature_id}",
                remediation_guidance=remediation or "Review target documentation.",
                explanation=notes,
                root_cause=f"Partial or emulated feature: {capability.feature_id}",
                affected_session=session_id,
                correlation_id=correlation_id or None,
                trace_id=trace_id or None,
            ))

        finding = CompatibilityFinding(
            feature_id=capability.feature_id,
            feature_name=capability.feature_name,
            category=capability.category,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            compatibility_tier=tier,
            action=action,
            score=score,
            applied_rule_id=applied_rule.rule_id if applied_rule else None,
            remediation_guidance=remediation,
        )

        return finding, diagnostics

    def _tier_to_default_action(
        self, tier: CompatibilityTier
    ) -> CompatibilityRuleAction:
        """Maps a compatibility tier to a default action when no registry rule overrides."""
        return {
            CompatibilityTier.NATIVE: CompatibilityRuleAction.ALLOW,
            CompatibilityTier.EMULATED: CompatibilityRuleAction.WARN,
            CompatibilityTier.PARTIAL: CompatibilityRuleAction.WARN,
            CompatibilityTier.PLUGIN_PROVIDED: CompatibilityRuleAction.WARN,
            CompatibilityTier.UNSUPPORTED: CompatibilityRuleAction.BLOCK,
        }.get(tier, CompatibilityRuleAction.WARN)

    def _compute_score(
        self,
        tier: CompatibilityTier,
        base_confidence: float,
        action: CompatibilityRuleAction,
    ) -> CompatibilityScore:
        """Computes a structured CompatibilityScore from tier and action."""
        tier_scores: Dict[CompatibilityTier, Tuple[int, int, int]] = {
            # risk, effort, priority
            CompatibilityTier.NATIVE:          (1, 1, 9),
            CompatibilityTier.EMULATED:        (2, 2, 7),
            CompatibilityTier.PARTIAL:         (3, 3, 6),
            CompatibilityTier.PLUGIN_PROVIDED: (2, 2, 6),
            CompatibilityTier.UNSUPPORTED:     (5, 5, 2),
        }
        risk, effort, priority = tier_scores.get(tier, (3, 3, 5))
        blocking = 1 if action == CompatibilityRuleAction.BLOCK else 0
        remediation_count = 0 if action == CompatibilityRuleAction.ALLOW else 1

        return CompatibilityScore(
            confidence=base_confidence,
            priority=priority,
            risk_level=risk,
            migration_effort=effort,
            remediation_count=remediation_count,
            blocking_issues=blocking,
            rationale=f"Tier: {tier.value}, Action: {action.value}",
            evidence={"tier": tier.value, "action": action.value},
        )

    def _compute_statistics(
        self, findings: List[CompatibilityFinding]
    ) -> CompatibilityStatistics:
        """Aggregates finding counts into CompatibilityStatistics."""
        native = sum(1 for f in findings if f.compatibility_tier == CompatibilityTier.NATIVE)
        emulated = sum(1 for f in findings if f.compatibility_tier == CompatibilityTier.EMULATED)
        partial = sum(1 for f in findings if f.compatibility_tier == CompatibilityTier.PARTIAL)
        plugin = sum(1 for f in findings if f.compatibility_tier == CompatibilityTier.PLUGIN_PROVIDED)
        unsupported = sum(1 for f in findings if f.compatibility_tier == CompatibilityTier.UNSUPPORTED)
        blocking = sum(1 for f in findings if f.action == CompatibilityRuleAction.BLOCK)
        warning = sum(
            1 for f in findings
            if f.action in (CompatibilityRuleAction.WARN, CompatibilityRuleAction.REQUIRE_MANUAL)
        )
        avg_conf = (
            round(sum(f.score.confidence for f in findings) / len(findings), 4)
            if findings else 0.0
        )
        return CompatibilityStatistics(
            total_features_analyzed=len(findings),
            native_features_count=native,
            emulated_features_count=emulated,
            partial_features_count=partial,
            plugin_required_count=plugin,
            unsupported_features_count=unsupported,
            blocking_issues_count=blocking,
            warning_issues_count=warning,
            average_confidence=avg_conf,
        )

    def _compute_summary(
        self, findings: List[CompatibilityFinding]
    ) -> CompatibilitySummary:
        """Derives boolean executive summary from findings."""
        blocking_ids = tuple(
            f.feature_id for f in findings
            if f.action == CompatibilityRuleAction.BLOCK
        )
        unsupported_ids = tuple(
            f.feature_id for f in findings
            if f.compatibility_tier == CompatibilityTier.UNSUPPORTED
        )
        requires_manual = any(
            f.action == CompatibilityRuleAction.REQUIRE_MANUAL for f in findings
        )
        requires_plugin = any(
            f.compatibility_tier == CompatibilityTier.PLUGIN_PROVIDED for f in findings
        )
        has_blocking = len(blocking_ids) > 0

        return CompatibilitySummary(
            is_fully_compatible=not has_blocking and not unsupported_ids,
            has_blocking_issues=has_blocking,
            requires_manual_intervention=requires_manual,
            requires_plugin_installation=requires_plugin,
            unsupported_feature_ids=unsupported_ids,
            blocking_feature_ids=blocking_ids,
        )


# =============================================================================
# Public Facade Analyzer
# =============================================================================

class CrossVersionCompatibilityAnalyzer:
    """
    Production-grade compatibility engine implementing ICompatibilityEngine.

    Orchestrates registry lookups, capability matrix evaluation,
    scoring, diagnostics, and report assembly.

    Performance budget:
    - Registry bootstrap:  < 20ms
    - Single analysis run: < 25ms
    """

    def __init__(
        self,
        registry: Optional[CompatibilityStrategyRegistry] = None,
    ) -> None:
        self._registry = registry or CompatibilityStrategyRegistry()
        self._capability_analyzer = CompatibilityCapabilityAnalyzer(self._registry)

    def check_compatibility(
        self,
        schema: Schema,
        source_dialect: SystemType,
        target_dialect: SystemType,
        target_version: DbVersion,
        source_version: str = "1.0",
        correlation_id: str = "",
        trace_id: str = "",
        request_id: str = "",
        migration_id: str = "",
        replay_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> CompatibilityReport:
        """
        Runs the full cross-version compatibility check.

        Args:
            schema: The source database schema to analyze.
            source_dialect: Source database system type.
            target_dialect: Target database system type.
            target_version: Target DbVersion (major.minor.patch).
            source_version: Source version string (default "1.0").
            correlation_id: Distributed tracing correlation ID.
            trace_id: Distributed tracing trace ID.
            request_id: Unique request identifier.
            migration_id: Migration project ID.
            replay_id: Optional CDC replay session ID.
            session_id: Optional analysis session ID.

        Returns:
            Immutable CompatibilityReport.
        """
        start_ms = time.perf_counter()

        target_version_str = f"{target_version.major}.{target_version.minor}"

        findings, diagnostics, statistics, summary = self._capability_analyzer.analyze(
            schema=schema,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            source_version=source_version,
            target_version=target_version_str,
            correlation_id=correlation_id,
            trace_id=trace_id,
            session_id=session_id,
        )

        duration_ms = (time.perf_counter() - start_ms) * 1000.0

        # Build warnings list
        warnings = tuple(
            f"[{f.feature_id}] {f.compatibility_tier.value}: "
            f"{f.remediation_guidance or 'Review compatibility.'}"
            for f in findings
            if f.action in (
                CompatibilityRuleAction.WARN,
                CompatibilityRuleAction.REQUIRE_MANUAL,
                CompatibilityRuleAction.BLOCK,
            )
        )

        builder = CompatibilityReportBuilder(
            correlation_id=correlation_id,
            trace_id=trace_id,
            request_id=request_id,
            migration_id=migration_id,
            replay_id=replay_id,
        )

        return builder.build_report(
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            target_version=target_version,
            findings=tuple(findings),
            diagnostics=tuple(diagnostics),
            statistics=statistics,
            summary=summary,
            duration_ms=duration_ms,
            warnings=warnings,
        )
