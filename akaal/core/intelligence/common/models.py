"""
Akaal — Intelligence Shared Immutable Domain Models
===================================================
Defines the shared dataclasses, enums, report models, diagnostic definitions,
and score calculators for the Migration Intelligence platform.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.models import DbVersion


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DiagnosticCategory(str, Enum):
    COMPATIBILITY = "COMPATIBILITY"
    STORAGE = "STORAGE"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    MIGRATION = "MIGRATION"


@dataclass(frozen=True)
class Diagnostic:
    """Immutable representation of a linter diagnostic or compatibility alert."""
    diagnostic_code: str
    severity: Severity
    category: DiagnosticCategory
    message: str
    path: str
    remediation_guidance: Optional[str] = None
    explanation: Optional[str] = None
    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    affected_event: Optional[str] = None
    affected_session: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass(frozen=True)
class DiagnosticsSummary:
    """Consolidated metrics of diagnostic runs."""
    warnings: int
    errors: int
    infos: int


@dataclass(frozen=True)
class RecommendationScore:
    """Structured rating metric for migration suggestions."""
    confidence: float              # 0.0 to 1.0
    priority: int                  # 1 to 10
    estimated_benefit: float       # 0.0 to 1.0
    implementation_complexity: int # 1 to 5
    migration_risk: int            # 1 to 5
    rationale: str
    supporting_diagnostics: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def composite_rank(self) -> float:
        """
        Calculates composite rank value:
        High Priority and Benefit, with low Risk and Complexity, yields highest rank.
        """
        impact = (self.priority * 1.5) + (self.estimated_benefit * 10.0)
        friction = (self.implementation_complexity * 0.5) + (self.migration_risk * 1.2)
        return round((impact / max(friction, 0.5)) * self.confidence, 2)


@dataclass(frozen=True)
class Recommendation:
    """Immutable model representing an advisory suggestion."""
    recommendation_id: str
    title: str
    description: str
    target_object_path: str
    score: RecommendationScore


@dataclass(frozen=True)
class PluginMetadata:
    """Immutable metadata tracking plugin dependencies and configurations."""
    plugin_id: str
    version: str
    min_platform_version: str
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    priority: int = 100


@dataclass(frozen=True)
class ConfigMetadata:
    """Immutable metadata for verified external configuration files."""
    file_name: str
    file_path: str
    checksum: str
    schema_version: str
    loaded_at: datetime


@dataclass(frozen=True)
class ReportMetadata:
    """Common metadata schema for execution profiling and traceability."""
    report_id: str
    correlation_id: str
    trace_id: str
    request_id: str
    migration_id: str
    generated_timestamp: datetime
    execution_duration_ms: float
    subsystem_version: str
    diagnostics_summary: Dict[str, int]
    warning_count: int
    error_count: int
    recommendation_count: int
    confidence_summary: Dict[str, float]
    replay_id: Optional[str] = None


# =============================================================================
# Subsystem Specific Reports
# =============================================================================

@dataclass(frozen=True)
class ReplayReport:
    """Immutable modeling report of CDC event timeline consistency scans."""
    metadata: ReportMetadata
    session_id: str
    validation_passed: bool
    detected_gaps: Tuple[int, ...] = field(default_factory=tuple)
    out_of_order_count: int = 0
    timeline_summary: Dict[str, Any] = field(default_factory=dict)
    replay_summary: Dict[str, Any] = field(default_factory=dict)
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    timeline_statistics: Dict[str, Any] = field(default_factory=dict)
    session_statistics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageReport:
    """Immutable report of database tablespaces and partition allocations."""
    metadata: ReportMetadata
    total_tables: int
    projected_total_size_kb: int
    allocations: Dict[str, Any] = field(default_factory=dict)
    warnings: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CompressionReport:
    """Immutable report summarizing source-target compression mappings."""
    metadata: ReportMetadata
    compressed_tables_count: int
    mappings: Dict[str, Any] = field(default_factory=dict)
    incompatibilities: Tuple[Diagnostic, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EncryptionReport:
    """Immutable report summarizing column/table encryption strategies."""
    metadata: ReportMetadata
    encrypted_columns_count: int
    specifications: Dict[str, Any] = field(default_factory=dict)
    handshake_errors: Tuple[Diagnostic, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CompatibilityReport:
    """Immutable report summarizing dialect and cross-version capability diagnostics."""
    metadata: ReportMetadata
    target_dialect: SystemType
    target_version: DbVersion
    is_compatible: bool
    unsupported_features: Tuple[Any, ...] = field(default_factory=tuple)
    diagnostics: Tuple[Diagnostic, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecommendationReport:
    """Immutable report containing ranked advisory recommendations."""
    metadata: ReportMetadata
    recommendations: Tuple[Recommendation, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IntelligenceReport:
    """The master migration intelligence audit statement aggregating all sub-reports."""
    metadata: ReportMetadata
    compatibility: CompatibilityReport
    storage: StorageReport
    compression: CompressionReport
    encryption: EncryptionReport
    recommendations: RecommendationReport
    replay: Optional[ReplayReport] = None
