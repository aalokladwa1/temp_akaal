from __future__ import annotations
from typing import Any, Dict, List

def plan_migration(udm: Dict[str, Any], risk_scorer_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    V1 COMPLIANT PLANNER DECISION ENGINE

    Sits between: Validator V1 -> Planner V1 -> Advisor V1
    Consumes a validated UDM object and Risk Scorer output to produce a Migration Plan Object (MPO).
    """
    # Extract risk information safely without modifications
    risk_data = risk_scorer_output.get("risk", {})
    risk_score = risk_data.get("score", 0)
    risk_level = str(risk_data.get("level", "LOW")).upper()
    flags = [str(f).strip() for f in risk_data.get("flags", [])]

    # Flags classifications
    loss_indicators = {
        "irreversible_loss",
        "lossy_conversion",
        "precision_loss",
        "scale_loss",
        "data_truncation",
        "truncation",
        "lossy",
        "irreversible",
    }
    
    has_irreversible_loss = False
    for flag in flags:
        flag_lower = flag.lower()
        if flag_lower in loss_indicators or "loss" in flag_lower or "irreversible" in flag_lower:
            has_irreversible_loss = True
            break

    spatial_network_mismatch_indicators = {
        "spatial_mismatch",
        "network_mismatch",
        "spatial_network_mismatch",
        "incompatible_spatial",
        "incompatible_network",
        "incompatible_system",
        "system_mismatch",
    }
    
    has_spatial_network_mismatch = False
    for flag in flags:
        flag_lower = flag.lower()
        if flag_lower in spatial_network_mismatch_indicators or "spatial" in flag_lower or "network" in flag_lower:
            has_spatial_network_mismatch = True
            break

    family_mismatch_indicators = {
        "family_mismatch",
        "cross_family",
        "family_conversion",
        "type_conversion",
        "family_mismatch_detected",
    }
    
    has_family_mismatch = False
    for flag in flags:
        flag_lower = flag.lower()
        if flag_lower in family_mismatch_indicators or "cross_family" in flag_lower:
            has_family_mismatch = True
            break

    precision_scale_indicators = {
        "precision_adjustment",
        "scale_adjustment",
        "precision_scale_adjustment",
        "precision_scale_adjustments",
    }
    
    has_precision_scale_adjustments = False
    for flag in flags:
        flag_lower = flag.lower()
        if flag_lower in precision_scale_indicators or "adjust" in flag_lower:
            has_precision_scale_adjustments = True
            break

    structural_indicators = {
        "structural_incompatibility",
        "structural_mismatch",
        "structural_incompatibility_exists",
        "restructure",
    }
    
    has_structural_incompatibility = False
    for flag in flags:
        flag_lower = flag.lower()
        if flag_lower in structural_indicators or "structural" in flag_lower or "restructure" in flag_lower:
            has_structural_incompatibility = True
            break

    # Determine Decision and Strategy
    decision = "CAST"
    strategy = "direct"

    # BLOCK Conditions
    is_blocked = (
        risk_level == "CRITICAL"
        or has_irreversible_loss
        or has_spatial_network_mismatch
    )

    if is_blocked:
        decision = "BLOCK"
        strategy = "reject"
    else:
        # TRANSFORM Conditions
        is_transform = (
            risk_level in ("MEDIUM", "HIGH")
            or has_family_mismatch
            or has_precision_scale_adjustments
            or has_structural_incompatibility
        )

        # LOW: CAST preferred. TRANSFORM only if structural mismatch.
        if risk_level == "LOW" and not has_structural_incompatibility:
            is_transform = False

        if is_transform:
            decision = "TRANSFORM"
            if has_structural_incompatibility:
                strategy = "restructure"
            else:
                strategy = "convert"

    # Compute confidence
    if decision == "CAST":
        confidence = max(0.8, min(1.0, 1.0 - (risk_score / 500.0)))
    elif decision == "TRANSFORM":
        confidence = max(0.5, min(0.8, 0.8 - (risk_score / 500.0)))
    else:
        # BLOCK
        confidence = max(0.0, min(0.4, 0.4 - (risk_score / 500.0)))

    # Compile deterministic reasoning reasons
    reasons = [f"risk_level:{risk_level}"]

    if has_family_mismatch:
        reasons.append("family_mismatch_detected")
    if has_precision_scale_adjustments:
        reasons.append("precision_scale_adjustments")
    if has_structural_incompatibility:
        reasons.append("structural_incompatibility_detected")
    if has_irreversible_loss:
        reasons.append("irreversible_loss_detected")
    if has_spatial_network_mismatch:
        reasons.append("spatial_network_mismatch")

    if decision == "CAST":
        reasons.append("direct_migration_safe")
    elif decision == "TRANSFORM":
        reasons.append("conversion_required")
    elif decision == "BLOCK":
        reasons.append("migration_blocked")

    # Compile execution notes
    execution_notes = []
    if decision == "BLOCK":
        execution_notes.append("Migration is blocked due to critical risk factors or potential data loss.")
    elif decision == "TRANSFORM":
        execution_notes.append(f"Type transformation required with strategy: {strategy}.")
    else:
        execution_notes.append("Direct cast migration is safe to proceed.")

    return {
        "decision": decision,
        "strategy": strategy,
        "confidence": confidence,
        "reason": reasons,
        "risk_snapshot": dict(risk_scorer_output),
        "execution_notes": execution_notes,
    }
