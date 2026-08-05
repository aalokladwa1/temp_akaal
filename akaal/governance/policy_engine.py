from typing import Any, Dict, List, Optional
from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    AUDITOR = "AUDITOR"


class PolicyEngine:
    """Enterprise Policy Authority."""

    def __init__(self) -> None:
        pass

    def evaluate_action_permission(self, user_role: str, action: str) -> bool:
        if user_role.upper() == "ADMIN":
            return True
        elif user_role.upper() == "OPERATOR" and "MIGRATION" in action.upper():
            return True
        return False

    def evaluate_masking_rule(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        col_lower = column_name.lower()
        if "ssn" in col_lower or "social" in col_lower:
            return {"strategy": "REDACT_PARTIAL", "pattern": "XXX-XX-1234"}
        elif "card" in col_lower or "credit" in col_lower:
            return {"strategy": "REDACT_FULL", "value": "XXXX-XXXX-XXXX-XXXX"}
        elif "email" in col_lower:
            return {"strategy": "HASH_SHA256"}
        return None

    def evaluate_approval_gate(self, migration_id: str, risk_score: str) -> Dict[str, Any]:
        requires_approval = risk_score.upper() in ("HIGH", "CRITICAL")
        return {
            "migration_id": migration_id,
            "requires_approval": requires_approval,
            "required_approver_role": "ADMIN" if requires_approval else "OPERATOR",
            "gate_status": "PENDING" if requires_approval else "APPROVED",
        }
