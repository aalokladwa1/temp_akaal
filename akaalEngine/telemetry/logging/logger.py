"""
akaalEngine.telemetry.logging.logger
====================================
StructuredOperationalLogger providing secret-safe contextual logging over standard Python logging.
"""

import logging
from typing import Any, Dict, Optional

from akaalEngine.telemetry.bus.context import CorrelationContext
from akaalEngine.telemetry.security.sanitizer import TelemetrySanitizer

logger = logging.getLogger("akaalEngine.telemetry.operational")


class StructuredOperationalLogger:
    """
    Secret-safe structured logger automatically combining CorrelationContext
    and scrubbing sensitive values.
    """

    def __init__(self, logger_name: str = "akaalEngine.telemetry.operational") -> None:
        self._logger = logging.getLogger(logger_name)

    def log(
        self,
        level: int,
        message: str,
        extra_context: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None,
    ) -> None:
        ctx = CorrelationContext.get_current().to_dict()
        combined = {**ctx, **(extra_context or {})}
        sanitized_msg = TelemetrySanitizer.sanitize_string(message)
        sanitized_context = TelemetrySanitizer.sanitize_mapping(combined)

        log_data = f"[OperationalLog] {sanitized_msg} | Context: {sanitized_context}"
        if exc:
            log_data += f" | Exception: {TelemetrySanitizer.sanitize_string(str(exc))}"

        self._logger.log(level, log_data)

    def info(self, message: str, extra_context: Optional[Dict[str, Any]] = None) -> None:
        self.log(logging.INFO, message, extra_context=extra_context)

    def warning(self, message: str, extra_context: Optional[Dict[str, Any]] = None) -> None:
        self.log(logging.WARNING, message, extra_context=extra_context)

    def error(self, message: str, extra_context: Optional[Dict[str, Any]] = None, exc: Optional[Exception] = None) -> None:
        self.log(logging.ERROR, message, extra_context=extra_context, exc=exc)
