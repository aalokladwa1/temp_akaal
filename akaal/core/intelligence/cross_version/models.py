"""
Akaal — Cross-Version Compatibility Domain Models
==================================================
Immutable dataclasses and enums modeling database dialect version features,
feature capability matrices, compatibility rules, scores, and diagnostics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.models import DbVersion
from akaal.core.intelligence.common.models import ReportMetadata, Diagnostic


# =============================================================================
# Enums
# =============================================================================

class CompatibilityTier(str, Enum):
    """Categorizes source-to-target dialect feature compatibility."""
    NATIVE          = "NATIVE"           # Feature is natively equivalent on target
    EMULATED        = "EMULATED"         # Feature can be emulated with configuration
    PARTIAL         = "PARTIAL"          # Feature partially supported; behavior may differ
    PLUGIN_PROVIDED = "PLUGIN_PROVIDED"  # Support requires a third-party extension
    UNSUPPORTED     = "UNSUPPORTED"      # Feature is not available on target


class FeatureCategory(str, Enum):
    """Taxonomic grouping for database feature capabilities."""
    DDL           = "DDL"           # Schema structure, types, constraints
    DML           = "DML"           # Data manipulation capabilities
    INDEXING      = "INDEXING"      # Index types and strategies
    PARTITIONING  = "PARTITIONING"  # Table partitioning schemes
    SECURITY      = "SECURITY"      # Encryption, masking, RLS, auditing
    PROCEDURAL    = "PROCEDURAL"    # Stored procedures, functions, triggers
    REPLICATION   = "REPLICATION"   # CDC, logical replication, slots
    PERFORMANCE   = "PERFORMANCE"   # Query plans, hints, statistics
    NETWORKING    = "NETWORKING"    # Protocols, TLS, connection pooling
    ANALYTICS     = "ANALYTICS"     # Window functions, CTEs, OLAP


class CompatibilityRuleAction(str, Enum):
    """Action taken when a compatibility rule fires."""
    ALLOW           = "ALLOW"           # Feature passes without issues
    WARN            = "WARN"            # Issue advisory, allow migration
    BLOCK           = "BLOCK"           # Block migration until resolved
    REQUIRE_MANUAL  = "REQUIRE_MANUAL"  # Requires manual operator intervention


# =============================================================================
# Core Models
# =============================================================================

@dataclass(frozen=True)
class FeatureCapability:
    """
    Describes a specific database feature and its support level on a given dialect/version.
    """
    feature_id: str
    feature_name: str
    category: FeatureCategory
    dialect: SystemType
    min_version: str
    is_supported: bool
    compatibility_tier: CompatibilityTier
    requires_enterprise: bool = False
    requires_plugin: bool = False
    notes: Optional[str] = None


@dataclass(frozen=True)
class CompatibilityRule:
    """
    A deterministic rule mapping a source feature to target dialect acceptance criteria.
    Higher priority wins when multiple rules match.
    """
    rule_id: str
    rule_name: str
    feature_id: str
    source_dialect: SystemType
    target_dialect: SystemType
    priority: int
    action: CompatibilityRuleAction
    compatibility_tier: CompatibilityTier
    min_source_version: Optional[str] = None
    max_source_version: Optional[str] = None
    min_target_version: Optional[str] = None
    max_target_version: Optional[str] = None
    remediation_guidance: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompatibilityScore:
    """
    Weighted compatibility assessment for a specific feature migration path.
    """
    confidence: float           # 0.0 to 1.0
    priority: int               # 1 to 10
    risk_level: int             # 1 to 5 (1=lowest risk)
    migration_effort: int       # 1 to 5 (1=minimal effort)
    remediation_count: int      # Number of required remediations
    blocking_issues: int        # Count of BLOCK-action diagnostics
    rationale: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def composite_rank(self) -> float:
        """
        Computes composite compatibility rank:
        High confidence and low risk/effort yields highest rank.
        """
        benefit = self.confidence * 10.0
        friction = (self.risk_level * 1.5) + (self.migration_effort * 1.0) + (self.blocking_issues * 3.0)
        friction = max(1.0, friction)
        return round((benefit / friction) * self.confidence, 2)


@dataclass(frozen=True)
class CompatibilityFinding:
    """
    Immutable record of a single compatibility evaluation outcome for one feature.
    """
    feature_id: str
    feature_name: str
    category: FeatureCategory
    source_dialect: SystemType
    target_dialect: SystemType
    compatibility_tier: CompatibilityTier
    action: CompatibilityRuleAction
    score: CompatibilityScore
    applied_rule_id: Optional[str] = None
    remediation_guidance: Optional[str] = None


@dataclass(frozen=True)
class CompatibilityStatistics:
    """
    High-level aggregated metrics from a compatibility analysis run.
    """
    total_features_analyzed: int
    native_features_count: int
    emulated_features_count: int
    partial_features_count: int
    plugin_required_count: int
    unsupported_features_count: int
    blocking_issues_count: int
    warning_issues_count: int
    average_confidence: float


@dataclass(frozen=True)
class CompatibilitySummary:
    """
    Executive summary of a cross-version compatibility assessment.
    """
    is_fully_compatible: bool
    has_blocking_issues: bool
    requires_manual_intervention: bool
    requires_plugin_installation: bool
    unsupported_feature_ids: Tuple[str, ...]
    blocking_feature_ids: Tuple[str, ...]


@dataclass(frozen=True)
class CompatibilityReport:
    """
    Unified immutable outcome report generated by the cross-version compatibility subsystem.
    """
    metadata: ReportMetadata
    source_dialect: SystemType
    target_dialect: SystemType
    target_version: DbVersion
    statistics: CompatibilityStatistics
    summary: CompatibilitySummary
    findings: Tuple[CompatibilityFinding, ...]
    diagnostics: Tuple[Diagnostic, ...]
    warnings: Tuple[str, ...]
