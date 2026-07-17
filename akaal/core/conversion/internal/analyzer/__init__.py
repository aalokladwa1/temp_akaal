"""
Akaal — Semantic Analyzer Subsystem
===================================
Exports classes for scope tracking, transaction classification, and dependency graph cycle checks.
"""

from akaal.core.conversion.internal.analyzer.scope import SemanticAnalyzer, ScopeNode
from akaal.core.conversion.internal.analyzer.dependencies import DependencyAnalyzer, CycleResolutionResult, CycleResolutionKind
from akaal.core.conversion.internal.analyzer.transactions import TransactionAnalyzer
