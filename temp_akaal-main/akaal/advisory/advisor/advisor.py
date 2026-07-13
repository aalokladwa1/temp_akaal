from __future__ import annotations
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------
# RISK LEVEL INTERPRETATIONS (DETERMINISTIC)
# ---------------------------------------------------------
_RISK_LEVEL_INTERPRETATIONS = {
    "LOW": "Risk is low. The migration carries minimal complexity and is unlikely to cause data issues.",
    "MEDIUM": "Risk is moderate. The migration involves type or schema adjustments that require careful validation.",
    "HIGH": "Risk is high. The migration involves significant structural changes with potential for data loss or incompatibility.",
    "CRITICAL": "Risk is critical. The migration poses severe threats to data integrity and must not proceed without redesign.",
}

# ---------------------------------------------------------
# DECISION EXPLANATIONS (DETERMINISTIC)
# ---------------------------------------------------------
_DECISION_EXPLANATIONS = {
    "CAST": "The planner determined this migration is safe for direct casting. No transformation or restructuring is required.",
    "TRANSFORM": "The planner determined that a type or structural conversion is required before migration can proceed safely.",
    "BLOCK": "The planner has blocked this migration due to unacceptable risk of data loss or system incompatibility.",
}

# ---------------------------------------------------------
# DECISION SUMMARIES (DETERMINISTIC)
# ---------------------------------------------------------
_DECISION_SUMMARIES = {
    "CAST": "Direct migration is safe. Proceed with casting to target type.",
    "TRANSFORM": "Migration requires conversion. Apply the recommended transformation strategy before proceeding.",
    "BLOCK": "Migration is blocked. The operation carries unacceptable risk and must be rejected or redesigned.",
}

# ---------------------------------------------------------
# RECOMMENDED ACTIONS (DETERMINISTIC)
# ---------------------------------------------------------
_RECOMMENDED_ACTIONS = {
    "direct": "Proceed with direct cast migration to the target system.",
    "convert": "Apply type conversion transformation before migrating to the target system.",
    "restructure": "Restructure the schema or data model before attempting migration.",
    "reject": "Reject the migration. Review the source type and target compatibility before reattempting.",
}

# ---------------------------------------------------------
# SAFE ALTERNATIVES (DETERMINISTIC)
# ---------------------------------------------------------
_SAFE_ALTERNATIVES = {
    "direct": None,
    "convert": "If conversion is not feasible, consider mapping to a wider compatible type in the target system.",
    "restructure": "If restructuring is not feasible, consider decomposing the migration into smaller compatible operations.",
    "reject": "Redesign the target schema to accommodate the source type, or exclude this column from migration scope.",
}

# ---------------------------------------------------------
# CONFIDENCE TIERS (DETERMINISTIC)
# ---------------------------------------------------------
_CONFIDENCE_TIERS = [
    (0.8, "Decision confidence is high. The planner has strong certainty that this migration path is stable and reliable."),
    (0.5, "Decision confidence is moderate. The migration path is viable but requires validation of transformation results."),
    (0.0, "Decision confidence is low. The migration path carries significant uncertainty and should be reviewed before execution."),
]


def generate_advisory(
    udm: Dict[str, Any],
    risk_output: Dict[str, Any],
    planner_output: Dict[str, Any],
) -> Dict[str, Any]:
    """
    V1 COMPLIANT ADVISOR — DETERMINISTIC EXPLANATION ENGINE

    Final layer: Planner V1 -> Advisor V1
    Consumes validated UDM, Risk Scorer output, and Planner output (MPO)
    to produce a Migration Advisory Object (MAO).

    This function ONLY interprets inputs. It does NOT:
    - modify UDM
    - recompute risk
    - re-evaluate planner decisions
    - introduce new logic
    """
    # -------------------------------------------------
    # 1. EXTRACT INPUTS (READ-ONLY)
    # -------------------------------------------------
    decision = str(planner_output.get("decision", "")).upper()
    strategy = str(planner_output.get("strategy", ""))
    confidence = float(planner_output.get("confidence", 0.0))

    risk_data = risk_output.get("risk", {})
    risk_score = risk_data.get("score", 0)
    risk_level = str(risk_data.get("level", "LOW")).upper()
    risk_flags = list(risk_data.get("flags", []))

    concept = str(udm.get("concept", ""))
    family = str(udm.get("family", ""))

    # -------------------------------------------------
    # 2. SUMMARY
    # -------------------------------------------------
    summary = _DECISION_SUMMARIES.get(
        decision,
        "Migration status could not be determined from planner output.",
    )

    # -------------------------------------------------
    # 3. DECISION EXPLANATION
    # -------------------------------------------------
    decision_explanation = _DECISION_EXPLANATIONS.get(
        decision,
        "The planner returned an unrecognized decision type.",
    )

    # -------------------------------------------------
    # 4. RISK INTERPRETATION
    # -------------------------------------------------
    level_text = _RISK_LEVEL_INTERPRETATIONS.get(
        risk_level,
        "Risk level is unrecognized.",
    )
    risk_interpretation = (
        f"{level_text} "
        f"Risk score: {risk_score}. "
        f"Risk level: {risk_level}."
    )

    # -------------------------------------------------
    # 5. MIGRATION GUIDANCE
    # -------------------------------------------------
    recommended_action = _RECOMMENDED_ACTIONS.get(
        strategy,
        "Review the migration plan manually before proceeding.",
    )

    safe_alternative: Optional[str] = _SAFE_ALTERNATIVES.get(strategy)

    warnings = _derive_warnings(risk_flags)

    migration_guidance = {
        "recommended_action": recommended_action,
        "safe_alternative": safe_alternative,
        "warnings": warnings,
    }

    # -------------------------------------------------
    # 6. EXECUTION NOTES
    # -------------------------------------------------
    execution_notes = _build_execution_notes(decision, strategy, concept, family)

    # -------------------------------------------------
    # 7. CONFIDENCE COMMENTARY
    # -------------------------------------------------
    confidence_commentary = _build_confidence_commentary(confidence, risk_level)

    # -------------------------------------------------
    # 8. ASSEMBLE MAO
    # -------------------------------------------------
    return {
        "summary": summary,
        "decision_explanation": decision_explanation,
        "risk_interpretation": risk_interpretation,
        "migration_guidance": migration_guidance,
        "execution_notes": execution_notes,
        "confidence_commentary": confidence_commentary,
    }


# =============================================================
# INTERNAL HELPERS (DETERMINISTIC, STATELESS)
# =============================================================


def _derive_warnings(risk_flags: List[Any]) -> List[str]:
    """
    Translate risk flags into human-readable, actionable warnings.
    Each flag maps deterministically to a warning string.
    NO new risk logic is introduced.
    """
    flag_warning_map = {
        "irreversible_loss": "Irreversible data loss has been detected. This migration cannot be safely reversed.",
        "lossy_conversion": "The conversion may cause data loss due to type narrowing or truncation.",
        "precision_loss": "Numeric precision may be lost during migration. Validate target precision constraints.",
        "scale_loss": "Numeric scale may be reduced. Verify decimal precision requirements in the target system.",
        "data_truncation": "Data truncation is expected. Source values may exceed target column capacity.",
        "truncation": "Data truncation risk exists. Verify target type length is sufficient.",
        "spatial_mismatch": "Spatial type mismatch detected. Source and target spatial systems are incompatible.",
        "network_mismatch": "Network type mismatch detected. Source and target network type representations differ.",
        "spatial_network_mismatch": "Spatial or network type mismatch detected between source and target systems.",
        "incompatible_spatial": "The target system does not support the source spatial type natively.",
        "incompatible_network": "The target system does not support the source network type natively.",
        "incompatible_system": "Source and target systems have fundamental type incompatibilities.",
        "family_mismatch": "The source and target types belong to different type families. Cross-family conversion is required.",
        "family_mismatch_detected": "A type family mismatch was detected between source and target types.",
        "cross_family": "Cross-family type conversion is required. Validate semantic equivalence after migration.",
        "family_conversion": "Type family conversion is needed. Ensure the target type preserves source semantics.",
        "type_conversion": "A type conversion is required between source and target representations.",
        "precision_adjustment": "Precision adjustment is required. Verify numeric bounds in the target system.",
        "scale_adjustment": "Scale adjustment is required. Validate decimal places in the target representation.",
        "precision_scale_adjustment": "Both precision and scale require adjustment for the target type.",
        "precision_scale_adjustments": "Precision and scale adjustments are needed for target type compatibility.",
        "structural_incompatibility": "Structural incompatibility exists between source and target schemas.",
        "structural_mismatch": "The source and target structures differ. Schema restructuring may be required.",
        "structural_incompatibility_exists": "A structural incompatibility has been confirmed between systems.",
        "system_mismatch": "A system-level mismatch exists between source and target platforms.",
    }

    warnings: List[str] = []
    for flag in risk_flags:
        flag_str = str(flag).strip().lower()
        warning = flag_warning_map.get(flag_str)
        if warning is not None:
            warnings.append(warning)
        else:
            # Deterministic fallback for unknown flags: surface the flag as-is
            warnings.append(f"Risk flag detected: {flag}. Review before proceeding.")

    return warnings


def _build_execution_notes(
    decision: str,
    strategy: str,
    concept: str,
    family: str,
) -> List[str]:
    """
    Generate step-based, deterministic, actionable execution notes.
    """
    notes: List[str] = []

    if decision == "CAST":
        notes.append(f"Verify that the target system supports the {concept} concept in the {family} family.")
        notes.append("Execute direct cast migration.")
        notes.append("Validate migrated data against source checksums.")

    elif decision == "TRANSFORM":
        notes.append(f"Identify the target type mapping for {concept} ({family} family).")
        if strategy == "restructure":
            notes.append("Restructure the source schema to align with target system constraints.")
            notes.append("Apply structural transformation before data migration.")
        else:
            notes.append("Apply type conversion transformation to source data.")
        notes.append("Execute migration with transformation applied.")
        notes.append("Validate transformed data for semantic equivalence with source.")

    elif decision == "BLOCK":
        notes.append("Do not proceed with migration.")
        notes.append(f"Review the {concept} type ({family} family) for target system compatibility.")
        notes.append("Consult migration documentation or redesign the target schema.")
        notes.append("Re-run the migration pipeline after changes have been applied.")

    return notes


def _build_confidence_commentary(confidence: float, risk_level: str) -> str:
    """
    Deterministic confidence commentary based on planner confidence value
    and risk level alignment.
    """
    # Select tier based on confidence threshold
    commentary = _CONFIDENCE_TIERS[-1][1]  # default to lowest tier
    for threshold, text in _CONFIDENCE_TIERS:
        if confidence >= threshold:
            commentary = text
            break

    # Append risk alignment context
    if risk_level in ("LOW",) and confidence >= 0.8:
        commentary += " Risk level and confidence are aligned."
    elif risk_level in ("MEDIUM",) and 0.5 <= confidence < 0.8:
        commentary += " Risk level and confidence are aligned."
    elif risk_level in ("HIGH", "CRITICAL") and confidence < 0.5:
        commentary += " Risk level and confidence are aligned."
    else:
        commentary += " Review risk level against confidence for additional context."

    return commentary
