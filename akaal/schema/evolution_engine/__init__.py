"""
AKAAL Platform 5 — Evolution Engine Subsystem
"""

from akaal.schema.evolution_engine.state_machine import EvolutionStateMachine
from akaal.schema.evolution_engine.executor import EvolutionExecutor
from akaal.schema.evolution_engine.coordinator import EvolutionCoordinator
from akaal.schema.evolution_engine.validator import EvolutionValidator
from akaal.schema.evolution_engine.engine import SchemaEvolutionEngine

__all__ = [
    "EvolutionStateMachine",
    "EvolutionExecutor",
    "EvolutionCoordinator",
    "EvolutionValidator",
    "SchemaEvolutionEngine",
]
