"""
Akaal — Task Dependency Semantics
=================================
Explicit dependency type semantics preserved inside ExecutionGraph.
"""

from enum import Enum


class DependencySemantics(str, Enum):
    HARD_DEPENDENCY = "HARD_DEPENDENCY"
    SOFT_DEPENDENCY = "SOFT_DEPENDENCY"
    OPTIONAL_DEPENDENCY = "OPTIONAL_DEPENDENCY"
    SYNCHRONIZATION_DEPENDENCY = "SYNCHRONIZATION_DEPENDENCY"
    VALIDATION_DEPENDENCY = "VALIDATION_DEPENDENCY"
