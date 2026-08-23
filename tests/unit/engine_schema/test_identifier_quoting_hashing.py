"""
tests.unit.engine_schema.test_identifier_quoting_hashing
========================================================
Unit tests for vendor identifier quoting, length clamping, and deterministic collision hashing (SCH-028, SCH-029).
"""

import pytest

from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer


def test_vendor_quoting_styles():
    # PostgreSQL: double quotes
    assert IdentifierSanitizer.quote_identifier("order_items", "POSTGRESQL") == '"order_items"'
    assert IdentifierSanitizer.quote_identifier('user"name', "POSTGRESQL") == '"user""name"'

    # Oracle: double quotes
    assert IdentifierSanitizer.quote_identifier("ORDER_ITEMS", "ORACLE") == '"ORDER_ITEMS"'

    # MySQL / BigQuery: backticks
    assert IdentifierSanitizer.quote_identifier("order_items", "MYSQL") == '`order_items`'
    assert IdentifierSanitizer.quote_identifier('order`items', "MYSQL") == '`order``items`'
    assert IdentifierSanitizer.quote_identifier("order_items", "BIGQUERY") == '`order_items`'

    # MSSQL: brackets
    assert IdentifierSanitizer.quote_identifier("order_items", "MSSQL") == '[order_items]'
    assert IdentifierSanitizer.quote_identifier("order]items", "MSSQL") == '[order]]items]'


def test_qualified_name_formatting():
    assert IdentifierSanitizer.format_qualified_name("public", "users", "POSTGRESQL") == '"public"."users"'
    assert IdentifierSanitizer.format_qualified_name("dbo", "users", "MSSQL") == '[dbo].[users]'
    assert IdentifierSanitizer.format_qualified_name("sales", "orders", "MYSQL") == '`sales`.`orders`'
    assert IdentifierSanitizer.format_qualified_name(None, "orders", "POSTGRESQL") == '"orders"'


def test_length_clamping_and_deterministic_hashing():
    # Oracle max length 30
    very_long_name = "extremely_long_table_name_exceeding_oracle_limits_by_far"
    sanitized_1 = IdentifierSanitizer.sanitize_identifier(very_long_name, "ORACLE")
    sanitized_2 = IdentifierSanitizer.sanitize_identifier(very_long_name, "ORACLE")

    assert len(sanitized_1) <= 30
    assert sanitized_1 == sanitized_2  # Must be deterministic
    assert "_" in sanitized_1  # Suffix separator
    assert sanitized_1.isupper()  # Force uppercase for Oracle

    # PostgreSQL max length 63
    long_pg_name = "a" * 80
    sanitized_pg = IdentifierSanitizer.sanitize_identifier(long_pg_name, "POSTGRESQL")
    assert len(sanitized_pg) <= 63
    assert sanitized_pg.islower()
