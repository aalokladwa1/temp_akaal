"""
AKAAL Platform 5 — Type Compatibility Matrix

Defines widening (safe) vs narrowing (unsafe) rules across numeric, string, temporal, decimal, and binary types.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Tuple


class ConversionSafety(str, Enum):
    SAFE_WIDENING = "SAFE_WIDENING"
    UNSAFE_NARROWING = "UNSAFE_NARROWING"
    INCOMPATIBLE = "INCOMPATIBLE"


class TypeCompatibilityMatrix:
    """Type compatibility matrix determining widening vs narrowing conversions."""

    _MATRIX: Dict[Tuple[str, str], ConversionSafety] = {
        # Numeric widening
        ("INT", "BIGINT"): ConversionSafety.SAFE_WIDENING,
        ("SMALLINT", "INT"): ConversionSafety.SAFE_WIDENING,
        ("SMALLINT", "BIGINT"): ConversionSafety.SAFE_WIDENING,
        ("FLOAT", "DOUBLE"): ConversionSafety.SAFE_WIDENING,
        ("INT", "DECIMAL"): ConversionSafety.SAFE_WIDENING,
        # Numeric narrowing
        ("BIGINT", "INT"): ConversionSafety.UNSAFE_NARROWING,
        ("INT", "SMALLINT"): ConversionSafety.UNSAFE_NARROWING,
        ("DOUBLE", "FLOAT"): ConversionSafety.UNSAFE_NARROWING,
        # String widening
        ("VARCHAR", "TEXT"): ConversionSafety.SAFE_WIDENING,
        ("CHAR", "VARCHAR"): ConversionSafety.SAFE_WIDENING,
        # Incompatible
        ("INT", "DATE"): ConversionSafety.INCOMPATIBLE,
        ("BOOLEAN", "TIMESTAMP"): ConversionSafety.INCOMPATIBLE,
    }

    @classmethod
    def evaluate_conversion(cls, from_type: str, to_type: str) -> ConversionSafety:
        from_base = from_type.upper().split("(")[0]
        to_base = to_type.upper().split("(")[0]

        if from_base == to_base:
            # Length/Precision check
            return cls._evaluate_parameterized(from_type, to_type)

        return cls._MATRIX.get((from_base, to_base), ConversionSafety.INCOMPATIBLE)

    @classmethod
    def _evaluate_parameterized(cls, from_type: str, to_type: str) -> ConversionSafety:
        # Check VARCHAR(10) -> VARCHAR(50)
        def extract_size(t: str) -> int:
            if "(" in t and ")" in t:
                try:
                    return int(t.split("(")[1].split(")")[0].split(",")[0])
                except ValueError:
                    return 0
            return 0

        sz_from = extract_size(from_type)
        sz_to = extract_size(to_type)

        if sz_from == 0 or sz_to == 0:
            return ConversionSafety.SAFE_WIDENING
        if sz_to > sz_from:
            return ConversionSafety.SAFE_WIDENING
        if sz_to < sz_from:
            return ConversionSafety.UNSAFE_NARROWING
        return ConversionSafety.SAFE_WIDENING
