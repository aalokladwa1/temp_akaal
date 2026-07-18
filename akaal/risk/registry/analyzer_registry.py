"""
Akaal — Analyzer Registry
=========================
Thread-safe registry for passive BaseAnalyzer plugins with governance validation.
"""

import threading
from typing import Any, Dict, List, Optional
from akaal.risk.analyzers.base_analyzer import BaseAnalyzer
from akaal.risk.analyzers.compatibility_analyzer import CompatibilityAnalyzer
from akaal.risk.analyzers.capability_gap_analyzer import CapabilityGapAnalyzer
from akaal.risk.analyzers.datatype_analyzer import DatatypeAnalyzer
from akaal.risk.analyzers.semantic_analyzer import SemanticAnalyzer
from akaal.risk.analyzers.dependency_analyzer import DependencyAnalyzer
from akaal.risk.analyzers.topology_analyzer import TopologyAnalyzer
from akaal.risk.analyzers.workload_analyzer import WorkloadAnalyzer


class AnalyzerRegistry:
    """Registry for managing Risk Platform passive analyzer plugins."""

    def __init__(self, auto_register_defaults: bool = True) -> None:
        self._lock = threading.RLock()
        self._analyzers: Dict[str, BaseAnalyzer] = {}
        if auto_register_defaults:
            self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        self.register(CompatibilityAnalyzer())
        self.register(CapabilityGapAnalyzer())
        self.register(DatatypeAnalyzer())
        self.register(SemanticAnalyzer())
        self.register(DependencyAnalyzer())
        self.register(TopologyAnalyzer())
        self.register(WorkloadAnalyzer())

    def register(self, analyzer: BaseAnalyzer) -> None:
        with self._lock:
            self._analyzers[analyzer.analyzer_id] = analyzer

    def unregister(self, analyzer_id: str) -> None:
        with self._lock:
            self._analyzers.pop(analyzer_id, None)

    def get_analyzer(self, analyzer_id: str) -> Optional[BaseAnalyzer]:
        with self._lock:
            return self._analyzers.get(analyzer_id)

    def list_analyzers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.metadata() for a in self._analyzers.values()]
