"""
AKAAL Platform 5 — Online Type Evolution Subsystem
"""

from akaal.schema.type_evolution.matrix import TypeCompatibilityMatrix, ConversionSafety
from akaal.schema.type_evolution.planner import ConversionPlanner, ConversionPlan
from akaal.schema.type_evolution.validator import TypeEvolutionValidator
from akaal.schema.type_evolution.engine import TypeEvolutionEngine

__all__ = [
    "TypeCompatibilityMatrix",
    "ConversionSafety",
    "ConversionPlanner",
    "ConversionPlan",
    "TypeEvolutionValidator",
    "TypeEvolutionEngine",
]
