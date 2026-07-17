"""
Akaal — Scope and Variable Analyzer
====================================
Performs scope tracking, local variable resolution, and shadowing checks.
"""

from typing import Dict, List, Optional, Set, Tuple
from akaal.core.conversion.api.aoir import RoutineParameter

class ScopeNode:
    def __init__(self, parent: Optional['ScopeNode'] = None):
        self.parent = parent
        self.symbols: Dict[str, RoutineParameter] = {}
        self.children: List['ScopeNode'] = []
        if parent:
            parent.children.append(self)

    def define(self, name: str, param: RoutineParameter) -> bool:
        """Returns True if the symbol was defined, False if it was already defined in this immediate scope."""
        key = name.upper()
        if key in self.symbols:
            return False
        self.symbols[key] = param
        return True

    def resolve(self, name: str) -> Optional[RoutineParameter]:
        key = name.upper()
        if key in self.symbols:
            return self.symbols[key]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def check_shadowing(self, name: str) -> bool:
        """Checks if a variable with this name shadows a definition in any ancestor scope."""
        if not self.parent:
            return False
        return self.parent.resolve(name) is not None

class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = ScopeNode()
        self.current_scope = self.global_scope

    def enter_scope(self) -> ScopeNode:
        new_scope = ScopeNode(self.current_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def define_variable(self, param: RoutineParameter) -> Tuple[bool, bool]:
        """Defines a variable in the current scope.
        Returns:
            (success, shadows_outer_definition)
        """
        shadowed = self.current_scope.check_shadowing(param.name)
        success = self.current_scope.define(param.name, param)
        return success, shadowed
