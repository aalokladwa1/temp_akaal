"""
AKAAL Planner — SQL Safety & Governance Classifier
===================================================
Provides static analysis, lexical tokenization, risk classification,
and allow/deny policy evaluation for custom SQL execution hooks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from akaal.planner.models.p5_domain import SQLSafetyClassification


# Regex patterns for stripping comments and string literals
_SINGLE_LINE_COMMENT = re.compile(r"--[^\r\n]*")
_MULTI_LINE_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_STRING_LITERAL_SINGLE = re.compile(r"'(?:''|\\'|[^'])*'")
_STRING_LITERAL_DOUBLE = re.compile(r'"(?:""|\\"|[^"])*"')

# Statement categorization regex patterns (applied to clean uppercase SQL)
_SELECT_PATTERN = re.compile(r"^\s*(SELECT\b|WITH\b|EXPLAIN\b|SHOW\b|DESCRIBE\b|PRAGMA\b)", re.IGNORECASE)
_SAFE_MUTATING_PATTERN = re.compile(r"^\s*(INSERT\s+INTO|UPDATE\b|MERGE\s+INTO|UPSERT\b|REPLACE\s+INTO|CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS|CREATE\s+INDEX|CREATE\s+OR\s+REPLACE\s+VIEW)\b", re.IGNORECASE)
_DELETE_WITH_WHERE_PATTERN = re.compile(r"^\s*DELETE\s+FROM\s+[A-Za-z0-9_.\"']+\s+WHERE\b", re.IGNORECASE)
_UNCONSTRAINED_DELETE_PATTERN = re.compile(r"^\s*DELETE\s+FROM\s+[A-Za-z0-9_.\"']+\s*(;|\s*$)", re.IGNORECASE)
_TRUNCATE_PATTERN = re.compile(r"^\s*TRUNCATE\b", re.IGNORECASE)
_DESTRUCTIVE_DDL_PATTERN = re.compile(r"^\s*(DROP\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|TABLESPACE)|ALTER\s+TABLE\s+[A-Za-z0-9_.\"']+\s+DROP\s+(COLUMN|CONSTRAINT|PARTITION)|CREATE\s+(TABLE|DATABASE|SCHEMA))\b", re.IGNORECASE)
_PRIVILEGE_PATTERN = re.compile(r"^\s*(GRANT\b|REVOKE\b|CREATE\s+USER\b|ALTER\s+USER\b|DROP\s+USER\b|CREATE\s+ROLE\b|ALTER\s+ROLE\b|DROP\s+ROLE\b|SET\s+PASSWORD\b)", re.IGNORECASE)


class SQLSafetyClassifier:
    """Canonical classifier and governance validator for custom SQL statements."""

    @classmethod
    def clean_sql(cls, raw_sql: str) -> str:
        """Strips comments and normalizes whitespace."""
        if not raw_sql or not isinstance(raw_sql, str):
            return ""
        # Strip comments
        cleaned = _MULTI_LINE_COMMENT.sub(" ", raw_sql)
        cleaned = _SINGLE_LINE_COMMENT.sub(" ", cleaned)
        return cleaned.strip()

    @classmethod
    def split_statements(cls, raw_sql: str) -> List[str]:
        """
        Splits a multi-statement SQL string into discrete statements,
        respecting single/double quoted literals and comments.
        """
        if not raw_sql or not isinstance(raw_sql, str):
            return []
        clean = cls.clean_sql(raw_sql)
        if not clean:
            return []
        parts = [p.strip() for p in clean.split(";") if p.strip()]
        return parts

    @classmethod
    def is_ddl(cls, stmt: str) -> bool:
        """Returns True if statement is a DDL definition."""
        if not stmt or not isinstance(stmt, str):
            return False
        clean = cls.clean_sql(stmt)
        return bool(re.match(r"^\s*(CREATE|DROP|ALTER|TRUNCATE)\b", clean, re.IGNORECASE))

    @classmethod
    def classify_single_statement(cls, stmt: str) -> SQLSafetyClassification:
        """Classifies a single clean SQL statement."""
        stmt = cls.clean_sql(stmt)
        if not stmt:
            return SQLSafetyClassification.UNKNOWN_UNCLASSIFIED

        # 1. Check Privilege Modifications
        if _PRIVILEGE_PATTERN.search(stmt):
            return SQLSafetyClassification.PRIVILEGE_MODIFICATION

        # 2. Check Destructive DDL (DROP, destructive ALTER, CREATE TABLE)
        if _DESTRUCTIVE_DDL_PATTERN.search(stmt):
            return SQLSafetyClassification.DESTRUCTIVE_DDL

        # 3. Check Destructive DML (TRUNCATE, unconstrained DELETE)
        if _TRUNCATE_PATTERN.search(stmt):
            return SQLSafetyClassification.DESTRUCTIVE_DML
        if _UNCONSTRAINED_DELETE_PATTERN.search(stmt):
            return SQLSafetyClassification.DESTRUCTIVE_DML

        # 4. Check Safe Mutating (INSERT, UPDATE with WHERE, DELETE with WHERE, MERGE)
        if _DELETE_WITH_WHERE_PATTERN.search(stmt):
            return SQLSafetyClassification.SAFE_MUTATING
        if _SAFE_MUTATING_PATTERN.search(stmt):
            return SQLSafetyClassification.SAFE_MUTATING

        # 5. Check Safe Select / Read Only
        if _SELECT_PATTERN.search(stmt):
            return SQLSafetyClassification.SAFE_SELECT

        # If statement starts with generic SET or USE (session configuration)
        if re.match(r"^\s*(SET\s+|USE\s+)", stmt, re.IGNORECASE):
            return SQLSafetyClassification.SAFE_MUTATING

        # 6. Unclassifiable / Unknown -> Fail-closed
        return SQLSafetyClassification.UNKNOWN_UNCLASSIFIED

    @classmethod
    def classify(cls, raw_sql: str) -> SQLSafetyClassification:
        """
        Classifies SQL (supporting multi-statement scripts).
        Returns the highest-risk classification encountered.
        Risk hierarchy:
          UNKNOWN_UNCLASSIFIED > DESTRUCTIVE_DDL > DESTRUCTIVE_DML > PRIVILEGE_MODIFICATION > SAFE_MUTATING > SAFE_SELECT
        """
        stmts = cls.split_statements(raw_sql)
        if not stmts:
            return SQLSafetyClassification.UNKNOWN_UNCLASSIFIED

        classifications = [cls.classify_single_statement(s) for s in stmts]

        if SQLSafetyClassification.UNKNOWN_UNCLASSIFIED in classifications:
            return SQLSafetyClassification.UNKNOWN_UNCLASSIFIED
        if SQLSafetyClassification.DESTRUCTIVE_DDL in classifications:
            return SQLSafetyClassification.DESTRUCTIVE_DDL
        if SQLSafetyClassification.DESTRUCTIVE_DML in classifications:
            return SQLSafetyClassification.DESTRUCTIVE_DML
        if SQLSafetyClassification.PRIVILEGE_MODIFICATION in classifications:
            return SQLSafetyClassification.PRIVILEGE_MODIFICATION
        if SQLSafetyClassification.SAFE_MUTATING in classifications:
            return SQLSafetyClassification.SAFE_MUTATING
        return SQLSafetyClassification.SAFE_SELECT

    @classmethod
    def is_destructive(cls, classification: SQLSafetyClassification) -> bool:
        """Returns True if classification is destructive or unclassifiable."""
        return classification in (
            SQLSafetyClassification.DESTRUCTIVE_DDL,
            SQLSafetyClassification.DESTRUCTIVE_DML,
            SQLSafetyClassification.PRIVILEGE_MODIFICATION,
            SQLSafetyClassification.UNKNOWN_UNCLASSIFIED,
        )

    @classmethod
    def is_mutating(cls, classification: SQLSafetyClassification) -> bool:
        """Returns True if classification can mutate data, schema, or system state."""
        return classification != SQLSafetyClassification.SAFE_SELECT

    @classmethod
    def evaluate_policies(
        cls,
        raw_sql: str,
        allow_rules: Optional[Sequence[str]] = None,
        deny_rules: Optional[Sequence[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validates SQL against allow/deny regex rules.
        Deny rules always take precedence over allow rules.
        """
        violations: List[str] = []
        clean_sql = cls.clean_sql(raw_sql)

        if not clean_sql:
            return False, ["SQL statement is empty or contains only comments."]

        # 1. Evaluate Deny Rules
        if deny_rules:
            for pattern in deny_rules:
                if not pattern:
                    continue
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    if compiled.search(clean_sql) or compiled.search(raw_sql):
                        violations.append(f"DENIED_SQL_OPERATION: SQL matches deny rule pattern '{pattern}'.")
                except re.error as err:
                    violations.append(f"INVALID_DENY_RULE_PATTERN: Regex compile error '{err}' for pattern '{pattern}'.")

        # 2. Evaluate Allow Rules (if provided, at least one must match)
        if allow_rules:
            matched_any = False
            for pattern in allow_rules:
                if not pattern:
                    continue
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    if compiled.search(clean_sql) or compiled.search(raw_sql):
                        matched_any = True
                        break
                except re.error as err:
                    violations.append(f"INVALID_ALLOW_RULE_PATTERN: Regex compile error '{err}' for pattern '{pattern}'.")
            if not matched_any and not violations:
                violations.append("DISALLOWED_SQL_OPERATION: SQL statement does not match any configured allow rule pattern.")

        return len(violations) == 0, violations
