"""
Akaal — Compatibility Validator
===============================
Validates cross-engine compatibility parameters for Rulebook platform.
"""

from typing import List
from akaal.scout.models.discovery_report import DiscoveryReport


class CompatibilityValidator:
    """Validates compatibility between source engine, target engine, and rule constraints."""

    @staticmethod
    def validate_engine_compatibility(source_engine: str, target_engine: str) -> List[str]:
        warnings: List[str] = []
        s_eng = source_engine.upper()
        t_eng = target_engine.upper()
        if s_eng == t_eng:
            warnings.append(f"Source and Target database engines are identical ({s_eng}). Same-engine migration rules applied.")
        return warnings
