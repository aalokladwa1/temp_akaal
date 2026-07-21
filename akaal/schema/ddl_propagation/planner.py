"""
AKAAL Platform 5 — DDLPlanner

Computes statement hashes and idempotency tokens for online DDL.
"""

import hashlib
from akaal.schema.domain.changes import DDLStatement


class DDLPlanner:
    """Plans DDL statements and computes cryptographic idempotency hashes."""

    @staticmethod
    def compute_statement_hash(stmt: DDLStatement) -> str:
        raw = f"{stmt.target_object}:{stmt.sql.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
