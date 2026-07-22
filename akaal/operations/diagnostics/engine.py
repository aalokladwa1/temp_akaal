"""
Enterprise Diagnostics & Root Cause Analysis Engine.
Analyzes cross-platform event timelines and dependency graphs to deduce probable root causes.
"""

from typing import Dict, List, Any, Optional
from threading import RLock

from akaal.operations.timeline.history import OperationalTimeline
from akaal.operations.dependency_graph.graph import DependencyGraph


class DiagnosticsReport:
    """Output report of diagnostic analysis."""

    def __init__(self, target_issue: str, probable_root_cause: str, affected_components: List[str], timeline_slice: List[Dict[str, Any]]) -> None:
        self.target_issue = target_issue
        self.probable_root_cause = probable_root_cause
        self.affected_components = affected_components
        self.timeline_slice = timeline_slice


class DiagnosticsEngine:
    """Correlates timeline events and dependency graphs for root cause analysis."""

    def __init__(self, timeline: OperationalTimeline, dependency_graph: DependencyGraph) -> None:
        self._lock = RLock()
        self.timeline = timeline
        self.dependency_graph = dependency_graph

    def diagnose_incident(self, incident_title: str, failed_component: str) -> DiagnosticsReport:
        with self._lock:
            # 1. Analyze blast radius using dependency graph
            impact_analysis = self.dependency_graph.analyze_impact(failed_component)
            affected = impact_analysis["impacted_nodes"]

            # 2. Extract recent timeline events
            all_events = self.timeline.get_timeline()
            relevant_events = [
                e for e in all_events
                if e.get("source_platform") in affected or e.get("source_platform") == failed_component
            ]

            root_cause = f"Failure origin detected at component '{failed_component}' impacting {len(affected)} dependent nodes."
            return DiagnosticsReport(incident_title, root_cause, affected, relevant_events)
