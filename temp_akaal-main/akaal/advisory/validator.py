from __future__ import annotations
from typing import Any, Dict, List
from akaal.advisory.rulebook.concepts import CONCEPTS
from akaal.advisory.rulebook.exceptions import RulebookError
class ValidationError(RulebookError):
    def __init__(self, errors: List[str]) -> None:
        self.errors: List[str] = list(errors)
        super().__init__(self.errors)
_REQUIRED_FIELDS = ("concept", "family", "status")
_ALLOWED_STATUSES = ("mapped", "unsupported")
_ALLOWED_KEYS = (
    "concept",
    "family",
    "status",
    "precision",
    "scale",
    "length",
    "timezone",
)
_NUMERIC_ONLY_KEYS = ("precision", "scale")
_STRING_ONLY_KEYS = ("length",)
_TEMPORAL_ONLY_KEYS = ("timezone",)
def validate(udm: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    # -----------------------------
    # 1. REQUIRED FIELD CHECK
    # -----------------------------
    for field in _REQUIRED_FIELDS:
        if field not in udm:
            errors.append(f"missing_required_field:{field}")
    if errors:
        raise ValidationError(errors)
    # -----------------------------
    # 2. KEY VALIDATION
    # -----------------------------
    for key in udm.keys():
        if key not in _ALLOWED_KEYS:
            errors.append(f"unknown_key:{key}")
    if errors:
        raise ValidationError(errors)
    # -----------------------------
    # 3. STATUS VALIDATION
    # -----------------------------
    if udm["status"] not in _ALLOWED_STATUSES:
        errors.append(f"invalid_status:{udm['status']}")
    # -----------------------------
    # 4. CONCEPT VALIDATION
    # -----------------------------
    concept = udm["concept"]
    if concept not in CONCEPTS:
        errors.append(f"unknown_concept:{concept}")
    else:
        expected_family = CONCEPTS[concept]
        family = udm["family"]
        # -----------------------------
        # 5. FAMILY VALIDATION
        # -----------------------------
        if family != expected_family:
            errors.append(
                f"family_mismatch:concept={concept}:expected={expected_family}:got={family}"
            )
        # -----------------------------
        # 6. FAMILY-BASED KEY RULES
        # -----------------------------
        for key in _NUMERIC_ONLY_KEYS:
            if key in udm and expected_family != "numeric":
                errors.append(f"invalid_key_for_family:{key}:family={family}")
        for key in _STRING_ONLY_KEYS:
            if key in udm and expected_family != "string":
                errors.append(f"invalid_key_for_family:{key}:family={family}")
        for key in _TEMPORAL_ONLY_KEYS:
            if key in udm and expected_family != "temporal":
                errors.append(f"invalid_key_for_family:{key}:family={family}")
    # -----------------------------
    # FINAL DECISION
    # -----------------------------
    if errors:
        raise ValidationError(errors)
    return {
        "valid": True,
        "udm": dict(udm),
        "errors": [],
    }