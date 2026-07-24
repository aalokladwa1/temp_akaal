"""Data models for AKAAL Enterprise Validation Platform."""

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class SeverityLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


@dataclass
class ValidationIssue:
    """Represents a specific issue discovered during validation."""

    issue_id: str
    capability_id: str
    severity: SeverityLevel
    table_name: Optional[str]
    column_name: Optional[str]
    row_identifier: Optional[Any]
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    remediation_suggestion: Optional[str] = None


@dataclass
class ExplainabilityContext:
    """Diagnostic context explaining root cause and resolution steps."""

    issue_id: str
    root_cause_category: str
    technical_description: str
    diff_summary: Dict[str, Any]
    repair_command_recommendation: Optional[str] = None
    confidence: float = 1.0


@dataclass
class EvidencePackage:
    """Signed audit proof package for enterprise compliance."""

    package_id: str
    timestamp: float
    session_id: str
    merkle_root: str
    checksum_digest: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    issues: List[ValidationIssue]
    signature: str
    policy_profile: str


@dataclass
class ValidationResult:
    """Comprehensive result returned by validators and domain engines."""

    domain_name: str
    capabilities_tested: List[str]
    status: ValidationStatus
    total_records_checked: int = 0
    passed_count: int = 0
    failed_count: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence_score: float = 100.0
    execution_time_ms: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    explainability: List[ExplainabilityContext] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        self.capabilities_tested = list(set(self.capabilities_tested + other.capabilities_tested))
        self.total_records_checked += other.total_records_checked
        self.passed_count += other.passed_count
        self.failed_count += other.failed_count
        self.issues.extend(other.issues)
        self.explainability.extend(other.explainability)
        self.execution_time_ms += other.execution_time_ms
        self.metrics.update(other.metrics)

        if other.status == ValidationStatus.FAILED or self.status == ValidationStatus.FAILED:
            self.status = ValidationStatus.FAILED
        elif other.status == ValidationStatus.WARNING and self.status != ValidationStatus.FAILED:
            self.status = ValidationStatus.WARNING

        self.confidence_score = min(self.confidence_score, other.confidence_score)
        return self
