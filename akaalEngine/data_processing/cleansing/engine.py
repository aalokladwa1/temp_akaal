"""
akaalEngine.data_processing.cleansing.engine
=============================================
CleansingEngine for string normalization, trimming, null defaulting, and value coercions.
Mined from `akaal/data_integrity/` and `akaal/core/conversion/`.
"""

from decimal import Decimal
from typing import Any, Optional


class CleansingEngine:
    """Executes data cleansing, string normalization, and value coercions."""

    @classmethod
    def apply_cleansing(cls, operation: str, value: Any, default_val: Any = None) -> Any:
        if value is None:
            return default_val

        op = operation.upper()
        if op == "TRIM":
            return str(value).strip()
        elif op == "UPPER":
            return str(value).upper()
        elif op == "LOWER":
            return str(value).lower()
        elif op == "DEFAULT":
            return value if value is not None else default_val
        return value

    @classmethod
    def coerce_value(cls, value: Any, target_type: str) -> Any:
        if value is None:
            return None

        t = target_type.upper()
        if "INT" in t:
            return int(value)
        elif "DECIMAL" in t or "NUMERIC" in t:
            return Decimal(str(value))
        elif "FLOAT" in t or "DOUBLE" in t:
            return float(value)
        elif "BOOL" in t:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "t", "yes", "y")
            return bool(value)
        elif "STR" in t or "VARCHAR" in t or "TEXT" in t:
            return str(value)
        return value
