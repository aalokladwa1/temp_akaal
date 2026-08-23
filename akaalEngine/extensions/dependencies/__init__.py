"""
akaalEngine.extensions.dependencies
===================================
Lazy, isolated dependency inspection and diagnostic reporting for Python, native, and executable requirements.
"""

from akaalEngine.extensions.dependencies.python import PythonDependencyInspector
from akaalEngine.extensions.dependencies.native import NativeDependencyInspector
from akaalEngine.extensions.dependencies.diagnostics import DependencyDiagnosticReport
from akaalEngine.extensions.dependencies.inspector import (
    DependencyInspector,
    default_dependency_inspector,
)

__all__ = [
    "PythonDependencyInspector",
    "NativeDependencyInspector",
    "DependencyDiagnosticReport",
    "DependencyInspector",
    "default_dependency_inspector",
]
