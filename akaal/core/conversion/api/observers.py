"""
Akaal — Type Conversion Observers
=================================
Declares interfaces for observing conversion events to support metrics, logging, and tracing.
"""

from abc import ABC, abstractmethod
from typing import Any
from akaal.core.conversion.api.models import ConversionContext, DataType

class ConversionObserver(ABC):
    """Abstract interface for observing the lifecycle of a type conversion execution."""

    @abstractmethod
    def on_conversion_start(self, context: ConversionContext, source: DataType) -> None:
        """Invoked when a type conversion request begins execution."""
        pass

    @abstractmethod
    def on_rule_evaluated(self, rule: Any, matched: bool, reason: str) -> None:
        """Invoked when a mapping rule is evaluated against the conversion criteria."""
        pass

    @abstractmethod
    def on_conversion_complete(self, result: Any, trace: Any) -> None:
        """Invoked when a type conversion successfully finishes execution."""
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        """Invoked when an unhandled exception is encountered during the conversion pipeline."""
        pass
