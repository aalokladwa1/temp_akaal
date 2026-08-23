"""
akaalEngine.data_processing.models.result
==========================================
Processing diagnostic and result models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class TransformationDiagnostic:
    """Sanitized diagnostic entry for processing events."""
    level: str  # INFO, WARNING, BLOCKER
    code: str
    message: str
    column_name: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass(frozen=True)
class ProcessingResult:
    """Result status for row transformation."""
    status: str  # SUCCESS, FILTERED, REJECTED, QUARANTINED, FAILED
    transformed_row: Optional[Dict[str, Any]] = None
    diagnostics: Sequence[TransformationDiagnostic] = field(default_factory=tuple)
    quarantine_metadata: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class ChangeImageResult:
    """Result for CDC change-image transformation."""
    status: str
    transformed_image: Optional[Dict[str, Any]] = None
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None
