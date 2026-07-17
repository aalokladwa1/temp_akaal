"""
Akaal — Procedural Transaction Safety & Volatility Analyzer
============================================================
Analyzes procedure bodies for transaction boundaries, autonomous blocks,
dynamic statements, savepoint markers, and locks.
"""

from typing import Tuple, List, Optional
from akaal.core.conversion.api.aoir import (
    TransactionBehavior,
    SourceLocation,
    ParsedTokenRange,
    UnsupportedConstruct,
    ManualReviewRequirement
)
from akaal.core.conversion.internal.parser.base import Token, TokenType

class TransactionAnalyzer:
    def __init__(self, tokens: List[Token], source_text: str):
        self.tokens = tokens
        self.source_text = source_text

    def analyze(self) -> Tuple[TransactionBehavior, Tuple[UnsupportedConstruct, ...], Tuple[ManualReviewRequirement, ...]]:
        unsupported: List[UnsupportedConstruct] = []
        reviews: List[ManualReviewRequirement] = []
        
        has_commit = False
        has_rollback = False
        has_savepoint = False
        has_autonomous = False
        has_dynamic = False
        has_locks = False

        # Scan tokens case-insensitively
        idx = 0
        limit = len(self.tokens)
        while idx < limit:
            t = self.tokens[idx]
            val_upper = t.value.upper()

            if t.type == TokenType.KEYWORD:
                if val_upper == "COMMIT":
                    has_commit = True
                elif val_upper == "ROLLBACK":
                    has_rollback = True
                elif val_upper == "SAVEPOINT":
                    has_savepoint = True
                    end_tok = self.tokens[idx + 2] if idx + 2 < limit else t
                    rng = t.to_range(end_tok)
                    reviews.append(ManualReviewRequirement(
                        reason_code="SAVEPOINT_DETECTED",
                        description="Savepoints require manual validation of boundary lock scope.",
                        source_range=rng
                    ))
                elif val_upper == "PRAGMA":
                    # Check for AUTONOMOUS_TRANSACTION
                    next_tok = self.tokens[idx + 1] if idx + 1 < limit else None
                    if next_tok and next_tok.value.upper() == "AUTONOMOUS_TRANSACTION":
                        has_autonomous = True
                        rng = t.to_range(next_tok)
                        unsupported.append(UnsupportedConstruct(
                            construct_type="PRAGMA_AUTONOMOUS_TRANSACTION",
                            source_range=rng,
                            description="Autonomous transactions are not natively supported in standard PL/pgSQL."
                        ))
                elif val_upper == "EXECUTE":
                    # Check for EXECUTE IMMEDIATE
                    next_tok = self.tokens[idx + 1] if idx + 1 < limit else None
                    if next_tok and next_tok.value.upper() == "IMMEDIATE":
                        has_dynamic = True
                        rng = t.to_range(next_tok)
                        unsupported.append(UnsupportedConstruct(
                            construct_type="DYNAMIC_SQL_EXECUTE_IMMEDIATE",
                            source_range=rng,
                            description="Dynamic SQL with EXECUTE IMMEDIATE is blocked for auto-conversion."
                        ))
            elif t.type == TokenType.IDENTIFIER:
                # Check for lock packages or procedures like DBMS_LOCK
                if "DBMS_LOCK" in val_upper:
                    has_locks = True
                    rng = t.to_range()
                    reviews.append(ManualReviewRequirement(
                        reason_code="DBMS_LOCK_DETECTED",
                        description="Oracle DBMS_LOCK library calls cannot be converted automatically. Lock emulation required.",
                        source_range=rng
                    ))

            idx += 1

        # Classify overall transaction behavior
        if has_autonomous:
            behavior = TransactionBehavior.REQUIRES_AUTONOMOUS_TRANSACTION_PROVIDER
        elif has_dynamic or has_locks or has_savepoint:
            behavior = TransactionBehavior.REQUIRES_MANUAL_REWRITE
        elif has_commit or has_rollback:
            # PostgreSQL 15+ allows COMMIT/ROLLBACK in procedures called via CALL,
            # but they require orchestration changes (cannot be run in SELECT function contexts).
            behavior = TransactionBehavior.EQUIVALENT_WITH_ORCHESTRATION_CHANGE
        else:
            behavior = TransactionBehavior.SEMANTICALLY_EQUIVALENT

        return behavior, tuple(unsupported), tuple(reviews)
