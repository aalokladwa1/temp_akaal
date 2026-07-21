"""
AKAAL Platform 5 — EvolutionValidator

Validates schema evolution state after execution.
"""

from akaal.schema.transactions.model import SchemaTransaction


class EvolutionValidator:
    """Validator performing post-evolution state verification."""

    def verify_evolution(self, tx: SchemaTransaction) -> bool:
        return tx.state == tx.state.COMMITTED
