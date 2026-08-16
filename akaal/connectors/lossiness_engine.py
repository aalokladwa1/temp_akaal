"""
Akaal — Semantic Lossiness & Risk Engine (P4.8)
================================================
Identifies potentially destructive semantic conversions, precision loss, scale reduction,
timezone loss, document flattening, and structural paradigm mismatches.
Emits machine-readable reason codes and actionable governance requirements.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from akaal.connectors.datatype_semantics import SemanticDatatypeFamily, DatatypeDimensions


class LossinessReasonCode(str, Enum):
    TARGET_PRECISION_INSUFFICIENT          = "TARGET_PRECISION_INSUFFICIENT"
    SCALE_REDUCTION_LOSSY                  = "SCALE_REDUCTION_LOSSY"
    TIMEZONE_SEMANTICS_LOSSY               = "TIMEZONE_SEMANTICS_LOSSY"
    COLLATION_DIFFERENCE                   = "COLLATION_DIFFERENCE"
    STRING_TRUNCATION_RISK                 = "STRING_TRUNCATION_RISK"
    BINARY_LENGTH_LIMITATION               = "BINARY_LENGTH_LIMITATION"
    DYNAMIC_SCHEMA_FLATTENING              = "DYNAMIC_SCHEMA_FLATTENING"
    RELATIONAL_TO_DOCUMENT_STRUCTURAL_CHANGE= "RELATIONAL_TO_DOCUMENT_STRUCTURAL_CHANGE"
    CDC_SOURCE_UNAVAILABLE                = "CDC_SOURCE_UNAVAILABLE"
    CDC_TARGET_APPLY_UNAVAILABLE          = "CDC_TARGET_APPLY_UNAVAILABLE"
    CDC_POSITION_INCOMPATIBLE              = "CDC_POSITION_INCOMPATIBLE"
    VALIDATION_METHOD_UNAVAILABLE          = "VALIDATION_METHOD_UNAVAILABLE"
    SEQUENCE_IDENTITY_MISMATCH             = "SEQUENCE_IDENTITY_MISMATCH"
    GENERATED_COLUMN_UNSUPPORTED           = "GENERATED_COLUMN_UNSUPPORTED"
    PROCEDURAL_OBJECT_REQUIRES_TRANSLATION = "PROCEDURAL_OBJECT_REQUIRES_TRANSLATION"
    EMPTY_STRING_NULL_SEMANTIC_MISMATCH    = "EMPTY_STRING_NULL_SEMANTIC_MISMATCH"
    UNSUPPORTED_TYPE_CONVERSION            = "UNSUPPORTED_TYPE_CONVERSION"


class LossinessIssue:
    def __init__(
        self,
        reason_code: LossinessReasonCode,
        affected_object: str,
        source_semantic: str,
        target_semantic: str,
        severity: str = "WARNING",  # INFO, WARNING, HIGH_RISK, BLOCKER
        mitigation: str = "",
        requires_human_approval: bool = False,
    ) -> None:
        self.reason_code = LossinessReasonCode(reason_code)
        self.affected_object = affected_object
        self.source_semantic = source_semantic
        self.target_semantic = target_semantic
        self.severity = severity.upper()
        self.mitigation = mitigation
        self.requires_human_approval = requires_human_approval

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason_code": self.reason_code.value,
            "affected_object": self.affected_object,
            "source_semantic": self.source_semantic,
            "target_semantic": self.target_semantic,
            "severity": self.severity,
            "mitigation": self.mitigation,
            "requires_human_approval": self.requires_human_approval,
        }


class LossinessEngine:
    """Evaluates semantic lossiness across datatype dimensions, schema features, and CDC streams."""

    @staticmethod
    def evaluate_datatype_lossiness(
        source_type: SemanticDatatypeFamily,
        target_type: SemanticDatatypeFamily,
        src_dims: Optional[DatatypeDimensions] = None,
        tgt_dims: Optional[DatatypeDimensions] = None,
    ) -> List[LossinessIssue]:
        issues: List[LossinessIssue] = []
        src_d = src_dims or DatatypeDimensions()
        tgt_d = tgt_dims or DatatypeDimensions()

        # 1. Fixed Decimal Precision Loss
        if source_type == SemanticDatatypeFamily.FIXED_DECIMAL:
            if src_d.precision and tgt_d.precision and tgt_d.precision < src_d.precision:
                issues.append(LossinessIssue(
                    reason_code=LossinessReasonCode.TARGET_PRECISION_INSUFFICIENT,
                    affected_object="COLUMN",
                    source_semantic=f"DECIMAL({src_d.precision},{src_d.scale or 0})",
                    target_semantic=f"DECIMAL({tgt_d.precision},{tgt_d.scale or 0})",
                    severity="HIGH_RISK",
                    mitigation="Increase target decimal precision or convert to double precision float.",
                    requires_human_approval=True,
                ))

        # 2. Timestamp Timezone Loss
        if source_type == SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE and target_type == SemanticDatatypeFamily.TIMESTAMP:
            issues.append(LossinessIssue(
                reason_code=LossinessReasonCode.TIMEZONE_SEMANTICS_LOSSY,
                affected_object="TIMESTAMP",
                source_semantic="TIMESTAMP_WITH_TIMEZONE",
                target_semantic="TIMESTAMP_WITHOUT_TIMEZONE",
                severity="WARNING",
                mitigation="Convert timestamp values to UTC prior to target insertion.",
                requires_human_approval=False,
            ))

        # 3. Document / Array Flattening
        if source_type in (SemanticDatatypeFamily.DOCUMENT, SemanticDatatypeFamily.JSON) and target_type == SemanticDatatypeFamily.VARIABLE_STRING:
            issues.append(LossinessIssue(
                reason_code=LossinessReasonCode.DYNAMIC_SCHEMA_FLATTENING,
                affected_object="DOCUMENT_COLUMN",
                source_semantic=source_type.value,
                target_semantic="VARIABLE_STRING",
                severity="WARNING",
                mitigation="Store JSON string payload or use native JSONB column if supported.",
                requires_human_approval=False,
            ))

        return issues
