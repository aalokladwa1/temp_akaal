"""
tests.unit.engine_schema.test_dialect_translations
==================================================
Unit tests for SQL dialect translation of functions, datetime arithmetic, and sequences (SCH-053 to SCH-057).
"""

import pytest

from akaalEngine.schema.dialect.datetime import DateTimeDialectTranslator
from akaalEngine.schema.dialect.functions import FunctionDialectTranslator
from akaalEngine.schema.dialect.sequences import SequenceDialectTranslator


def test_function_translations():
    # 1. NVL(a, b) -> COALESCE(a, b)
    expr1 = "SELECT NVL(salary, 0) FROM employees"
    res1 = FunctionDialectTranslator.translate_expression(expr1, "oracle", "postgresql")
    assert "COALESCE(salary, 0)" in res1

    # 2. NVL appearing inside a string literal or column name must NOT be replaced!
    expr2 = "SELECT 'NVL is a function' AS nvl_col, NVL(val, 'none') FROM tbl"
    res2 = FunctionDialectTranslator.translate_expression(expr2, "oracle", "postgresql")
    assert "'NVL is a function'" in res2
    assert "nvl_col" in res2
    assert "COALESCE(val, 'none')" in res2

    # 3. NVL2(a, b, c) -> CASE WHEN a IS NOT NULL THEN b ELSE c END
    expr3 = "NVL2(bonus, salary + bonus, salary)"
    res3 = FunctionDialectTranslator.translate_expression(expr3, "oracle", "postgresql")
    assert "CASE WHEN bonus IS NOT NULL THEN salary + bonus ELSE salary END" in res3

    # 4. DECODE(x, 1, 'ONE', 2, 'TWO', 'OTHER') -> CASE WHEN ... ELSE ... END
    expr4 = "DECODE(status, 'P', 'PENDING', 'S', 'SHIPPED', 'UNKNOWN')"
    res4 = FunctionDialectTranslator.translate_expression(expr4, "oracle", "postgresql")
    assert "CASE WHEN status = 'P' THEN 'PENDING' WHEN status = 'S' THEN 'SHIPPED' ELSE 'UNKNOWN' END" in res4


def test_datetime_translations():
    # Oracle SYSDATE + 7 -> PostgreSQL CURRENT_TIMESTAMP + INTERVAL '7 DAY'
    expr1 = "WHERE created_at > SYSDATE - 30"
    res1 = DateTimeDialectTranslator.translate_datetime_expression(expr1, "oracle", "postgresql")
    assert "CURRENT_TIMESTAMP - INTERVAL '30 DAY'" in res1

    # MSSQL GETDATE() -> PostgreSQL CURRENT_TIMESTAMP
    expr2 = "SET v_time = GETDATE()"
    res2 = DateTimeDialectTranslator.translate_datetime_expression(expr2, "mssql", "postgresql")
    assert "CURRENT_TIMESTAMP" in res2


def test_sequence_translations():
    # Oracle order_seq.NEXTVAL -> PostgreSQL nextval('order_seq')
    expr1 = "INSERT INTO orders (id) VALUES (order_seq.NEXTVAL)"
    res1 = SequenceDialectTranslator.translate_sequence_expression(expr1, "oracle", "postgresql")
    assert "nextval('order_seq')" in res1

    # MSSQL NEXT VALUE FOR order_seq -> PostgreSQL nextval('order_seq')
    expr2 = "SELECT NEXT VALUE FOR order_seq"
    res2 = SequenceDialectTranslator.translate_sequence_expression(expr2, "mssql", "postgresql")
    assert "nextval('order_seq')" in res2
