"""
AKAAL Platform 5 — SchemaEvolutionEngine & EvolutionValidator

Provides the top-level Evolution Engine for Live Schema Evolution.
"""

from typing import Any, List, Optional

from akaal.schema.domain.changes import BaseSchemaChange
from akaal.schema.evolution_engine.coordinator import EvolutionCoordinator
from akaal.schema.evolution_engine.validator import EvolutionValidator
from akaal.schema.transactions.model import SchemaTransaction


class EvolutionValidator:
    """Validator performing post-evolution state verification."""

    def verify_evolution(self, tx: SchemaTransaction) -> bool:
        return tx.state == tx.state.COMMITTED


class SchemaEvolutionEngine:
    """Live Schema Evolution Engine."""

    def __init__(self, coordinator: Optional[EvolutionCoordinator] = None) -> None:
        self.coordinator = coordinator or EvolutionCoordinator()
        self.validator = EvolutionValidator()

    def evolve(self, changes: List[BaseSchemaChange], db_context: Any = None) -> SchemaTransaction:
        tx = self.coordinator.coordinate_evolution(changes, db_context)
        self.validator.verify_evolution(tx)
        return tx
