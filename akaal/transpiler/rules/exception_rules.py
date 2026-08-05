"""
AKAAL PL/SQL Transpiler — Exception Rules
==========================================
Translates Oracle PL/SQL exception handlers (NO_DATA_FOUND, TOO_MANY_ROWS, DUP_VAL_ON_INDEX) to PL/pgSQL EXCEPTION blocks.
"""

import re
from typing import Dict


class ExceptionRulesEngine:
    """Translates Oracle exception names to PostgreSQL SQLSTATE condition names."""

    EXCEPTION_MAP: Dict[str, str] = {
        "NO_DATA_FOUND": "NO_DATA_FOUND",
        "TOO_MANY_ROWS": "TOO_MANY_ROWS",
        "DUP_VAL_ON_INDEX": "UNIQUE_VIOLATION",
        "ZERO_DIVIDE": "DIVISION_BY_ZERO",
        "VALUE_ERROR": "INVALID_TEXT_REPRESENTATION",
        "OTHERS": "OTHERS",
    }

    @classmethod
    def translate_exception(cls, oracle_exception: str) -> str:
        exc_upper = oracle_exception.strip().upper()
        return cls.EXCEPTION_MAP.get(exc_upper, "OTHERS")
