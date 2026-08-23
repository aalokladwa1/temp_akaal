"""
Unit tests for cursor pagination and preview sampling redaction security.
"""

from akaalEngine.discovery.core.paginator import CatalogPaginator, DiscoveryCursor
from akaalEngine.discovery.core.sampling import DeterministicSampler, RedactionGuard
from akaalEngine.discovery.models.inventory import TableFacts


def test_cursor_encoding_and_decoding():
    cur = DiscoveryCursor(schema_index=2, offset=1500, last_object_name="tbl_xyz")
    encoded = cur.encode()
    assert isinstance(encoded, str)
    assert len(encoded) > 0

    decoded = DiscoveryCursor.decode(encoded)
    assert decoded.schema_index == 2
    assert decoded.offset == 1500
    assert decoded.last_object_name == "tbl_xyz"


def test_catalog_paginator_slicing():
    tables = [TableFacts(name=f"table_{i}", schema_name="public") for i in range(1250)]
    
    # Page 1
    page1 = CatalogPaginator.paginate_sequence(tables, cursor=None, page_size=500)
    assert len(page1.items) == 500
    assert page1.items[0].name == "table_0"
    assert page1.is_last_page is False
    assert page1.cursor is not None

    # Page 2
    page2 = CatalogPaginator.paginate_sequence(tables, cursor=page1.cursor, page_size=500)
    assert len(page2.items) == 500
    assert page2.items[0].name == "table_500"
    assert page2.is_last_page is False
    assert page2.cursor is not None

    # Page 3
    page3 = CatalogPaginator.paginate_sequence(tables, cursor=page2.cursor, page_size=500)
    assert len(page3.items) == 250
    assert page3.items[0].name == "table_1000"
    assert page3.is_last_page is True
    assert page3.cursor is None


def test_redaction_guard_sensitive_masking():
    raw_record = {
        "user_id": 1001,
        "username": "johndoe",
        "password_hash": "secret$hashed_pass",
        "api_key": "live_key_983749827349",
        "ssn": "000-12-3456",
        "credit_card": "4111-2222-3333-4444",
        "bio": "Normal bio text",
    }

    sanitized = RedactionGuard.sanitize_record(raw_record)
    assert sanitized["user_id"] == 1001
    assert sanitized["username"] == "johndoe"
    assert sanitized["password_hash"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["ssn"] == "[REDACTED]"
    assert sanitized["credit_card"] == "[REDACTED]"
    assert sanitized["bio"] == "Normal bio text"
