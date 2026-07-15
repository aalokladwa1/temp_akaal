"""
Akaal — Diagnostics & Linter Subsystem
"""

import abc
from typing import List
from akaal.core.comparison.models import Schema
from akaal.core.intelligence.common.models import Diagnostic

class IIntelligenceLinter(abc.ABC):
    """Abstract interface defining the diagnostic linter execution context."""
    @abc.abstractmethod
    def lint(self, schema: Schema) -> List[Diagnostic]:
        pass
