"""
AKAAL Schema Compatibility Classification & Evolution Policy Engine.
====================================================================
Evaluates DDL schema changes deterministically, classifying compatibility
(SAFE_AUTOMATIC, SAFE_WITH_BARRIER, REQUIRES_DATA_TRANSFORMATION, REQUIRES_APPROVAL,
CUTOVER_BLOCKING, UNSUPPORTED, DESTRUCTIVE, AMBIGUOUS) and computing backend-authoritative
policy decisions (AUTO_APPLIES, PAUSES_AND_APPLIES, REQUIRES_APPROVAL, REQUIRES_TRANSFORMATION, BLOCKS_CDC).
"""

from typing import Dict, Any, Optional, List
import logging

from akaal.cdc.schema_evolution.domain import (
    CDCSchemaVersion,
    CDCDDLEvent,
    DDLOperationType,
    SchemaCompatibilityClassification,
    SchemaEvolutionPolicyDecision,
)

logger = logging.getLogger(__name__)


class CDCSchemaCompatibilityEvaluator:
    """Evaluates old vs proposed schema versions deterministically."""

    @classmethod
    def evaluate_compatibility(
        cls,
        old_version: CDCSchemaVersion,
        proposed_version: CDCSchemaVersion,
        ddl_event: CDCDDLEvent,
    ) -> SchemaCompatibilityClassification:
        op = ddl_event.canonical_operation

        if op in {DDLOperationType.UNKNOWN_DDL, DDLOperationType.UNSUPPORTED_DDL}:
            return SchemaCompatibilityClassification.UNSUPPORTED

        if op == DDLOperationType.ADD_COLUMN:
            # Check if newly added column is NOT NULL without default value
            added_cols = [c for c in proposed_version.columns if not old_version.get_column(c["name"])]
            for c in added_cols:
                if not c.get("nullable", True) and c.get("default") is None:
                    logger.warning(f"[Compatibility] ADD_COLUMN '{c['name']}' is NOT NULL without default value -> REQUIRES_APPROVAL / UNSUPPORTED.")
                    return SchemaCompatibilityClassification.REQUIRES_APPROVAL
            return SchemaCompatibilityClassification.SAFE_WITH_BARRIER

        if op in {DDLOperationType.DROP_COLUMN, DDLOperationType.DROP_TABLE, DDLOperationType.TRUNCATE_TABLE}:
            return SchemaCompatibilityClassification.DESTRUCTIVE

        if op == DDLOperationType.RENAME_COLUMN:
            return SchemaCompatibilityClassification.REQUIRES_DATA_TRANSFORMATION

        if op == DDLOperationType.RENAME_TABLE:
            return SchemaCompatibilityClassification.REQUIRES_DATA_TRANSFORMATION

        if op == DDLOperationType.ALTER_COLUMN_TYPE:
            old_col = old_version.get_column(ddl_event.operation_metadata.get("column_name", ""))
            new_type = ddl_event.operation_metadata.get("new_type", "").upper()

            if old_col:
                old_type = old_col.get("type", "").upper()
                # Type widening check (e.g. INT -> BIGINT, VARCHAR(50) -> VARCHAR(255))
                if cls._is_type_widening(old_type, new_type):
                    return SchemaCompatibilityClassification.SAFE_WITH_BARRIER
                elif cls._is_type_narrowing(old_type, new_type):
                    return SchemaCompatibilityClassification.REQUIRES_APPROVAL

            return SchemaCompatibilityClassification.REQUIRES_APPROVAL

        if op in {DDLOperationType.ADD_PRIMARY_KEY, DDLOperationType.DROP_PRIMARY_KEY}:
            return SchemaCompatibilityClassification.REQUIRES_APPROVAL

        return SchemaCompatibilityClassification.SAFE_WITH_BARRIER

    @classmethod
    def _is_type_widening(cls, old_type: str, new_type: str) -> bool:
        widening_pairs = [
            ("INT", "BIGINT"),
            ("INTEGER", "BIGINT"),
            ("SMALLINT", "INT"),
            ("FLOAT", "DOUBLE"),
            ("REAL", "DOUBLE"),
        ]
        for src, dst in widening_pairs:
            if src in old_type and dst in new_type:
                return True
        return False

    @classmethod
    def _is_type_narrowing(cls, old_type: str, new_type: str) -> bool:
        narrowing_pairs = [
            ("BIGINT", "INT"),
            ("DOUBLE", "FLOAT"),
            ("TEXT", "VARCHAR"),
        ]
        for src, dst in narrowing_pairs:
            if src in old_type and dst in new_type:
                return True
        return False


class CDCSchemaEvolutionPolicyEngine:
    """Backend-authoritative schema evolution policy engine."""

    @classmethod
    def determine_policy(
        cls,
        compatibility: SchemaCompatibilityClassification,
        allow_auto_ddl: bool = True,
    ) -> SchemaEvolutionPolicyDecision:
        if compatibility == SchemaCompatibilityClassification.SAFE_AUTOMATIC:
            return SchemaEvolutionPolicyDecision.AUTO_APPLIES
        elif compatibility == SchemaCompatibilityClassification.SAFE_WITH_BARRIER:
            return SchemaEvolutionPolicyDecision.PAUSES_AND_APPLIES if allow_auto_ddl else SchemaEvolutionPolicyDecision.REQUIRES_APPROVAL
        elif compatibility in {SchemaCompatibilityClassification.REQUIRES_APPROVAL, SchemaCompatibilityClassification.DESTRUCTIVE}:
            return SchemaEvolutionPolicyDecision.REQUIRES_APPROVAL
        elif compatibility == SchemaCompatibilityClassification.REQUIRES_DATA_TRANSFORMATION:
            return SchemaEvolutionPolicyDecision.REQUIRES_TRANSFORMATION
        elif compatibility == SchemaCompatibilityClassification.UNSUPPORTED:
            return SchemaEvolutionPolicyDecision.BLOCKS_CDC
        else:
            return SchemaEvolutionPolicyDecision.REQUIRES_MANUAL_INTERVENTION
