"""
Akaal — Comparer Subpackage
===========================
Orchestrates dynamic module loading to register all subclass comparers in COMPARER_REGISTRY.
"""

import importlib
import os
import pkgutil
from akaal.core.comparison.comparers.base import BaseComparer, COMPARER_REGISTRY

# Dynamically discover and load all modules in this package to trigger self-registration.
__path__ = [os.path.dirname(__file__)]
for _, module_name, _ in pkgutil.walk_packages(__path__, __name__ + "."):
    # Avoid double importing __init__ or base to prevent recursion loops
    if not module_name.endswith(".base") and not module_name.endswith(".__init__"):
        importlib.import_module(module_name)

__all__ = [
    "BaseComparer",
    "COMPARER_REGISTRY",
]
