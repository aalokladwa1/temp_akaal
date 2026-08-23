"""
akaalEngine.schema.compat
=========================
Compatibility Pack foundation (akaal_compat) and requirement tracking.
"""

from akaalEngine.schema.compat.lifecycle import (
    CompatibilityPackReport,
    CompatibilityRequirement,
    CompatibilityRequirementTracker,
)
from akaalEngine.schema.compat.pack_definitions import (
    CompatibilityFunctionDef,
    CompatibilityPackDefinitions,
)

__all__ = [
    "CompatibilityFunctionDef",
    "CompatibilityPackDefinitions",
    "CompatibilityRequirement",
    "CompatibilityPackReport",
    "CompatibilityRequirementTracker",
]
