"""
AKAAL Platform 5 — Multi-Stage Validation Diagnostic Report

Provides structured diagnostic entry logging across the 5 validation pipeline stages.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List

from akaal.schema.domain.enums import ValidationStage


@dataclass
class DiagnosticEntry:
    stage: ValidationStage
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DiagnosticReport:
    is_valid: bool
    entries: List[DiagnosticEntry] = field(default_factory=list)

    def add_entry(self, stage: ValidationStage, passed: bool, message: str, details: Dict[str, Any] = None) -> None:
        entry = DiagnosticEntry(stage=stage, passed=passed, message=message, details=details or {})
        self.entries.append(entry)
        if not passed:
            self.is_valid = False
