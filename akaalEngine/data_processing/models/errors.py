"""
akaalEngine.data_processing.models.errors
==========================================
Typed exception hierarchy for Authority #8 Data Processing.
"""

from typing import Any, Mapping, Optional


class DataProcessingException(Exception):
    """Base exception for Authority #8 Data Processing."""
    def __init__(self, message: str, error_code: str = "PROCESSING_ERROR", details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})


class TransformationCycleError(DataProcessingException):
    """Raised when rule dependency graph contains a circular reference."""
    def __init__(self, cycle_nodes: str) -> None:
        super().__init__(
            f"Transformation rule dependency cycle detected involving: {cycle_nodes}",
            error_code="TRANSFORMATION_CYCLE",
            details={"cycle_nodes": cycle_nodes},
        )


class ExpressionExecutionError(DataProcessingException):
    """Raised when AST expression evaluation fails."""
    def __init__(self, expression_str: str, cause: str) -> None:
        super().__init__(
            f"Expression evaluation failed for '{expression_str}': {cause}",
            error_code="EXPRESSION_EXECUTION_ERROR",
            details={"expression": expression_str, "cause": cause},
        )


class MalformedDataException(DataProcessingException):
    """Raised when malformed row encounters MalformedDataPolicy.FAIL_JOB."""
    def __init__(self, column_name: str, rule_id: str, cause: str) -> None:
        super().__init__(
            f"Malformed data policy FAIL_JOB triggered on column '{column_name}' (rule '{rule_id}'): {cause}",
            error_code="MALFORMED_DATA_FAILURE",
            details={"column_name": column_name, "rule_id": rule_id, "cause": cause},
        )


class LOBMaterializationError(DataProcessingException):
    """Raised when oversized LOB materialization is attempted unsafely."""
    def __init__(self, column_name: str, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"Unsafe LOB materialization attempted on column '{column_name}' ({size_bytes} bytes > max {max_bytes} bytes).",
            error_code="LOB_MATERIALIZATION_UNSAFE",
            details={"column_name": column_name, "size_bytes": size_bytes, "max_bytes": max_bytes},
        )
