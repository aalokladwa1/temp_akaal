"""
akaalEngine.schema.types.safety
===============================
Evaluation of 7-state conversion safety, precision/scale adaptation, string length clamping,
and lossiness classification across heterogeneous data engines.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from akaalEngine.schema.models.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)


class TypeSafetyEvaluator:
    """Evaluates type conversion safety and lossiness rationale."""

    @classmethod
    def evaluate_conversion(
        cls,
        source_type: CanonicalType,
        target_emission: TargetTypeEmission,
    ) -> TargetTypeEmission:
        """Evaluates and adjusts target type emission safety and lossiness reasons."""
        reasons: List[str] = list(target_emission.lossiness_reasons)
        safety = target_emission.safety
        warnings: List[str] = [target_emission.warning_message] if target_emission.warning_message else []

        # 1. Exact Numeric Precision / Scale lossiness
        if source_type.category == CanonicalTypeCategory.EXACT_NUMERIC:
            src_p = source_type.precision
            src_s = source_type.scale

            if src_p is not None and target_emission.extra.get("target_precision") is not None:
                tgt_p = target_emission.extra["target_precision"]
                if tgt_p < src_p:
                    safety = ConversionSafety.LOSSY
                    reasons.append("TARGET_PRECISION_INSUFFICIENT")
                    warnings.append(f"Target precision {tgt_p} is less than source precision {src_p}")

            if src_s is not None and target_emission.extra.get("target_scale") is not None:
                tgt_s = target_emission.extra["target_scale"]
                if tgt_s < src_s:
                    safety = ConversionSafety.LOSSY
                    reasons.append("SCALE_REDUCTION_LOSSY")
                    warnings.append(f"Target scale {tgt_s} is less than source scale {src_s}")

            if source_type.extra.get("oracle_negative_scale"):
                safety = ConversionSafety.LOSSY
                reasons.append("SCALE_REDUCTION_LOSSY")
                warnings.append("Oracle negative scale rounded to 0 on target")

        # 2. String Length Truncation
        elif source_type.category == CanonicalTypeCategory.CHARACTER:
            src_len = source_type.length
            tgt_len = target_emission.extra.get("target_length")
            if src_len is not None and tgt_len is not None and tgt_len < src_len:
                safety = ConversionSafety.LOSSY
                reasons.append("STRING_TRUNCATION_RISK")
                warnings.append(f"Target max length {tgt_len} is less than source length {src_len}")

        # 3. Timezone Semantic Loss
        elif source_type.category == CanonicalTypeCategory.DATETIME:
            if source_type.is_timezone_aware and not target_emission.extra.get("target_timezone_aware", False):
                safety = ConversionSafety.LOSSY
                reasons.append("TIMEZONE_SEMANTICS_LOSSY")
                warnings.append("Source is timezone-aware but target type lacks timezone offset")

        # 4. Binary Length Limitation
        elif source_type.category == CanonicalTypeCategory.BINARY:
            src_len = source_type.length
            tgt_len = target_emission.extra.get("target_length")
            if src_len is not None and tgt_len is not None and tgt_len < src_len:
                safety = ConversionSafety.LOSSY
                reasons.append("BINARY_LENGTH_LIMITATION")
                warnings.append(f"Target binary length {tgt_len} is less than source length {src_len}")

        # 5. Unsupported Category
        elif source_type.category == CanonicalTypeCategory.UNKNOWN:
            safety = ConversionSafety.UNSUPPORTED
            reasons.append("UNSUPPORTED_TYPE_CONVERSION")
            warnings.append(f"Source type '{source_type.raw_vendor_type}' is unknown and unsupported")

        warning_msg = "; ".join([w for w in warnings if w]) if warnings else None

        return TargetTypeEmission(
            target_engine=target_emission.target_engine,
            target_native_type=target_emission.target_native_type,
            safety=safety,
            warning_message=warning_msg,
            lossiness_reasons=tuple(reasons),
            requires_runtime_cast=target_emission.requires_runtime_cast,
            requires_compat_helper=target_emission.requires_compat_helper,
            extra=target_emission.extra,
        )
