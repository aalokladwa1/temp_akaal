"""
akaalEngine.schema.procedural.transforms.exceptions
===================================================
Exception and error-handling transpilation rules (WHEN NO_DATA_FOUND, WHEN OTHERS, SQLERRM, RAISE_APPLICATION_ERROR).
"""

from __future__ import annotations

from typing import List, Tuple

from akaalEngine.schema.procedural.ast_nodes import (
    AOIRNode,
    ExceptionHandler,
    RaiseStatement,
)


class ExceptionTransformer:
    """Transforms Oracle / MSSQL exception handlers into PostgreSQL PL/pgSQL equivalents."""

    _EXCEPTION_MAPPING = {
        "NO_DATA_FOUND": "NO_DATA_FOUND",
        "TOO_MANY_ROWS": "TOO_MANY_ROWS",
        "DUP_VAL_ON_INDEX": "UNIQUE_VIOLATION",
        "ZERO_DIVIDE": "DIVISION_BY_ZERO",
        "VALUE_ERROR": "NUMERIC_VALUE_OUT_OF_RANGE",
        "INVALID_CURSOR": "INVALID_CURSOR_STATE",
        "OTHERS": "OTHERS",
    }

    @classmethod
    def transform_handler(cls, handler: ExceptionHandler) -> ExceptionHandler:
        mapped_names = []
        for name in handler.exception_names:
            u_name = name.upper()
            mapped = cls._EXCEPTION_MAPPING.get(u_name, "OTHERS")
            mapped_names.append(mapped)

        return ExceptionHandler(
            exception_names=tuple(mapped_names),
            statements=handler.statements,
        )

    @classmethod
    def transform_raise(cls, node: RaiseStatement) -> RaiseStatement:
        # Map RAISE_APPLICATION_ERROR(-20001, 'msg') to RAISE EXCEPTION 'msg'
        if node.error_code is not None:
            msg = node.message or f"Custom error {node.error_code}"
            return RaiseStatement(message=msg)
        return node
