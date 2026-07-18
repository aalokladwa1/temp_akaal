"""
Akaal — Passive Rule Registry
============================
Passive store holding Rule instances and initializing DependencyGraph.
Does NOT orchestrate execution pipeline.
"""

import threading
from typing import Dict, List, Optional
from akaal.rulebook.models.rule import Rule, RuleLifecycleState
from akaal.rulebook.engine.dependency_graph import DependencyGraph


class RuleRegistry:
    """Passive repository for enterprise rules and dependency graph."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rules: Dict[str, Rule] = {}
        self._graph = DependencyGraph()

    def register(self, rule: Rule) -> None:
        with self._lock:
            self._rules[rule.rule_id] = rule
            self._graph.build(list(self._rules.values()))

    def unregister(self, rule_id: str) -> None:
        with self._lock:
            self._rules.pop(rule_id, None)
            self._graph.build(list(self._rules.values()))

    def resolve(self, rule_id: str) -> Optional[Rule]:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule and rule.lifecycle_state == RuleLifecycleState.RETIRED:
                return None
            return rule

    def get_all_rules(self) -> List[Rule]:
        with self._lock:
            return [r for r in self._rules.values() if r.lifecycle_state != RuleLifecycleState.RETIRED]

    def dependencies(self, rule_id: str) -> List[str]:
        with self._lock:
            return self._graph.dependency_tree(rule_id)

    def validate(self) -> List[str]:
        with self._lock:
            return self._graph.validate()

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    def version(self) -> str:
        return "1.0.0"
