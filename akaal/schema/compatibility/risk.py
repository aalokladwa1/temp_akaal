"""
AKAAL Platform 5 — RiskClassifier & Scoring Engine

Evaluates compatibility scores (0-100) and risk severity levels for schema modifications.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from akaal.schema.compatibility.comparator import SchemaDiff
from akaal.schema.domain.enums import RiskLevel


@dataclass
class RiskEvaluation:
    compatibility_score: float  # 0 to 100
    risk_level: RiskLevel
    breaking_changes: List[str] = field(default_factory=list)
    safe_changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RiskClassifier:
    """Classifies risk level and computes compatibility score for a SchemaDiff."""

    def classify(self, diff: SchemaDiff) -> RiskEvaluation:
        breaking = []
        safe = []
        warnings = []
        penalty = 0

        # Removed objects = breaking change
        for obj in diff.removed_objects:
            msg = f"Removed {obj['type']} '{obj['name']}'."
            breaking.append(msg)
            penalty += 30

        # Added objects = safe change
        for obj in diff.added_objects:
            msg = f"Added {obj['type']} '{obj['name']}'."
            safe.append(msg)

        # Modified objects check
        for obj in diff.modified_objects:
            mods = obj.get("modifications", {})
            for rem_col in mods.get("removed_columns", []):
                breaking.append(f"Dropped column '{rem_col['name']}' from table '{obj['name']}'.")
                penalty += 25

            for add_col in mods.get("added_columns", []):
                if not add_col.get("nullable", True) and add_col.get("default") is None:
                    breaking.append(f"Added NOT NULL column '{add_col['name']}' without default to table '{obj['name']}'.")
                    penalty += 20
                else:
                    safe.append(f"Added nullable/default column '{add_col['name']}' to table '{obj['name']}'.")

            for mod_col in mods.get("modified_columns", []):
                warnings.append(f"Modified column '{mod_col['column_name']}' in table '{obj['name']}'.")
                penalty += 10

        score = max(0.0, 100.0 - penalty)

        if penalty == 0:
            level = RiskLevel.NONE
        elif penalty <= 15:
            level = RiskLevel.LOW
        elif penalty <= 40:
            level = RiskLevel.MEDIUM
        elif penalty <= 70:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL

        return RiskEvaluation(
            compatibility_score=score,
            risk_level=level,
            breaking_changes=breaking,
            safe_changes=safe,
            warnings=warnings,
        )
