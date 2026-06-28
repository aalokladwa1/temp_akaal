from __future__ import annotations
import copy
from typing import Any, Dict, List, Optional


# =============================================================
# DETERMINISTIC CONCEPT → TARGET TYPE MAP (PostgreSQL MVP)
# =============================================================
# This is the ONLY source of truth for target type resolution.
# Executor MUST NOT invent mappings outside this table.

_CONCEPT_TARGET_MAP: Dict[str, str] = {
    # numeric
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "FLOAT": "DOUBLE PRECISION",
    "DECIMAL": "NUMERIC",
    # string
    "STRING": "VARCHAR",
    "TEXT": "TEXT",
    # boolean
    "BOOLEAN": "BOOLEAN",
    # temporal
    "DATE": "DATE",
    "TIME": "TIME",
    "TIMESTAMP": "TIMESTAMP",
    "INTERVAL": "INTERVAL",
    # structured
    "JSON": "JSONB",
    "ARRAY": "ARRAY",
    # binary
    "BINARY": "BYTEA",
    # spatial
    "GEOMETRY": "GEOMETRY",
    # network
    "NETWORK": "INET",
    # identifier
    "IDENTIFIER": "TEXT",
}


# =============================================================
# ADAPTER REGISTRY
# =============================================================
# Adapters available for parsing / transformation dispatch.
# Keys match engine names used throughout the pipeline.

_ADAPTER_REGISTRY: Dict[str, str] = {
    "oracle": "akaal.advisory.parsers.oracle_parser",
    "mysql": "akaal.advisory.parsers.mysql_parser",
    "postgresql": "akaal.advisory.parsers.postgresql_parser",
}


def execute(
    udm: Dict[str, Any],
    planner_output: Dict[str, Any],
    *,
    source_engine: str = "oracle",
) -> Dict[str, Any]:
    """
    V1 COMPLIANT EXECUTOR — DETERMINISTIC MIGRATION EXECUTION ENGINE

    Final active layer: Planner V1 → Advisor V1 → Executor V1.

    Applies planner decisions using adapter-driven transformations ONLY.
    This function MUST NOT modify UDM or planner output.
    """
    # -------------------------------------------------
    # 0. PRE-EXECUTION SNAPSHOT (rollback support)
    # -------------------------------------------------
    pre_execution_snapshot = copy.deepcopy(udm)

    # -------------------------------------------------
    # 1. READ PLANNER DECISION (read-only)
    # -------------------------------------------------
    decision = str(planner_output.get("decision", "")).upper()
    strategy = str(planner_output.get("strategy", ""))
    reasons = list(planner_output.get("reason", []))

    concept = str(udm.get("concept", ""))
    family = str(udm.get("family", ""))
    source_type = concept  # UDM concept is the canonical source type

    execution_log: List[str] = []
    execution_log.append(f"decision:{decision}")
    execution_log.append(f"strategy:{strategy}")
    execution_log.append(f"source_engine:{source_engine}")
    execution_log.append(f"source_concept:{concept}")
    execution_log.append(f"source_family:{family}")

    # -------------------------------------------------
    # 2. BLOCK → IMMEDIATE REJECTION
    # -------------------------------------------------
    if decision == "BLOCK":
        execution_log.append("action:BLOCKED")
        execution_log.append("reason:" + ";".join(reasons))
        return {
            "status": "BLOCKED",
            "applied_strategy": strategy,
            "source_type": source_type,
            "target_type": "",
            "transformed_value": None,
            "execution_log": execution_log,
            "rollback_info": {
                "pre_execution_snapshot": pre_execution_snapshot,
            },
        }

    # -------------------------------------------------
    # 3. RESOLVE TARGET TYPE (deterministic lookup)
    # -------------------------------------------------
    target_type = _resolve_target_type(concept, udm)
    execution_log.append(f"target_type:{target_type}")

    # -------------------------------------------------
    # 4. CAST → DIRECT PASS-THROUGH
    # -------------------------------------------------
    if decision == "CAST":
        execution_log.append("action:CAST_PASSTHROUGH")
        execution_log.append(f"adapter:{_ADAPTER_REGISTRY.get(source_engine, 'none')}")
        execution_log.append("transformation:none")
        execution_log.append(f"output_type:{target_type}")
        return {
            "status": "SUCCESS",
            "applied_strategy": strategy,
            "source_type": source_type,
            "target_type": target_type,
            "transformed_value": copy.deepcopy(udm),
            "execution_log": execution_log,
            "rollback_info": {
                "pre_execution_snapshot": pre_execution_snapshot,
            },
        }

    # -------------------------------------------------
    # 5. TRANSFORM → ADAPTER-BASED CONVERSION
    # -------------------------------------------------
    if decision == "TRANSFORM":
        adapter_module = _ADAPTER_REGISTRY.get(source_engine)
        execution_log.append(f"adapter:{adapter_module or 'none'}")

        if adapter_module is None:
            execution_log.append(f"error:no_adapter_for_engine:{source_engine}")
            execution_log.append("action:TRANSFORM_FAILED")
            return {
                "status": "FAILED",
                "applied_strategy": strategy,
                "source_type": source_type,
                "target_type": target_type,
                "transformed_value": None,
                "execution_log": execution_log,
                "rollback_info": {
                    "pre_execution_snapshot": pre_execution_snapshot,
                },
            }

        # Apply deterministic transformation
        transformed, transform_log = _apply_transform(
            udm, concept, family, target_type, strategy,
        )

        execution_log.extend(transform_log)

        if transformed is None:
            execution_log.append("action:TRANSFORM_FAILED")
            return {
                "status": "FAILED",
                "applied_strategy": strategy,
                "source_type": source_type,
                "target_type": target_type,
                "transformed_value": None,
                "execution_log": execution_log,
                "rollback_info": {
                    "pre_execution_snapshot": pre_execution_snapshot,
                },
            }

        execution_log.append("action:TRANSFORM_SUCCESS")
        execution_log.append(f"output_type:{target_type}")
        return {
            "status": "SUCCESS",
            "applied_strategy": strategy,
            "source_type": source_type,
            "target_type": target_type,
            "transformed_value": transformed,
            "execution_log": execution_log,
            "rollback_info": {
                "pre_execution_snapshot": pre_execution_snapshot,
            },
        }

    # -------------------------------------------------
    # 6. UNKNOWN DECISION → FAIL SAFE
    # -------------------------------------------------
    execution_log.append(f"error:unknown_decision:{decision}")
    execution_log.append("action:FAILED")
    return {
        "status": "FAILED",
        "applied_strategy": strategy,
        "source_type": source_type,
        "target_type": "",
        "transformed_value": None,
        "execution_log": execution_log,
        "rollback_info": {
            "pre_execution_snapshot": pre_execution_snapshot,
        },
    }


# =============================================================
# TARGET TYPE RESOLUTION (DETERMINISTIC)
# =============================================================

def _resolve_target_type(concept: str, udm: Dict[str, Any]) -> str:
    """
    Resolve the target database type from the UDM concept.
    Uses the deterministic concept-to-target map ONLY.
    Appends precision/scale/length qualifiers when present.
    """
    base_target = _CONCEPT_TARGET_MAP.get(concept, "")

    if not base_target:
        return ""

    # Enrich with precision/scale/length metadata from UDM
    precision = udm.get("precision")
    scale = udm.get("scale")
    length = udm.get("length")
    timezone = udm.get("timezone")

    if base_target == "NUMERIC" and precision is not None:
        if scale is not None:
            return f"NUMERIC({precision},{scale})"
        return f"NUMERIC({precision})"

    if base_target == "VARCHAR" and length is not None:
        return f"VARCHAR({length})"

    if base_target == "TIMESTAMP" and timezone is True:
        return "TIMESTAMP WITH TIME ZONE"

    return base_target


# =============================================================
# TRANSFORMATION ENGINE (ADAPTER-DRIVEN, DETERMINISTIC)
# =============================================================

def _apply_transform(
    udm: Dict[str, Any],
    concept: str,
    family: str,
    target_type: str,
    strategy: str,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Apply deterministic transformation rules.
    Returns (transformed_udm, log_entries).
    Returns (None, log_entries) if transformation cannot be completed.
    """
    log: List[str] = []

    if not target_type:
        log.append(f"error:no_target_type_for_concept:{concept}")
        return None, log

    # Build transformed output
    transformed = copy.deepcopy(udm)

    if strategy == "convert":
        log.append(f"transform:convert:{concept}:{target_type}")

        # Apply precision/scale constraints from UDM
        precision = udm.get("precision")
        scale = udm.get("scale")
        length = udm.get("length")

        if precision is not None:
            log.append(f"constraint:precision:{precision}")
        if scale is not None:
            log.append(f"constraint:scale:{scale}")
        if length is not None:
            log.append(f"constraint:length:{length}")

        transformed["target_type"] = target_type
        transformed["transformation_applied"] = "convert"

    elif strategy == "restructure":
        log.append(f"transform:restructure:{concept}:{target_type}")

        transformed["target_type"] = target_type
        transformed["transformation_applied"] = "restructure"

    else:
        log.append(f"warning:unknown_transform_strategy:{strategy}")
        return None, log

    return transformed, log
