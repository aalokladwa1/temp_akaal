"""
AKAAL Platform 5 — SchemaTransaction & Context Models
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional

from akaal.schema.domain.changes import BaseSchemaChange, DDLStatement
from akaal.schema.domain.enums import TransactionState
from akaal.schema.domain.identifiers import TransactionID
from akaal.schema.transactions.state_machine import TransactionStateMachine


@dataclass
class RollbackPlan:
    rollback_statements: List[DDLStatement] = field(default_factory=list)
    compensation_hooks: List[str] = field(default_factory=list)


@dataclass
class SchemaTransaction:
    tx_id: TransactionID
    parent_tx_id: Optional[TransactionID] = None
    changes: List[BaseSchemaChange] = field(default_factory=list)
    state_machine: TransactionStateMachine = field(default_factory=TransactionStateMachine)
    rollback_plan: RollbackPlan = field(default_factory=RollbackPlan)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    @property
    def state(self) -> TransactionState:
        return self.state_machine.state

    def add_audit_entry(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.audit_trail.append({
            "timestamp": time.time(),
            "action": action,
            "state": self.state.value,
            "details": details or {},
        })
