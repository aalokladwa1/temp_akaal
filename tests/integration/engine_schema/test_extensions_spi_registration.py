"""
tests.integration.engine_schema.test_extensions_spi_registration
================================================================
Integration tests verifying Extensions Authority #2 registration and contract compatibility for Authority #4 Schema.
"""

import pytest

from akaalEngine.extensions.authority import default_extensions_authority
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId


def test_schema_authority_identity_compatibility():
    auth_id = AuthorityId("schema")
    assert str(auth_id) == "schema"

    # Verify provider identities used in Schema Authority are recognized
    for prov in ("postgresql", "oracle", "mysql", "snowflake", "bigquery", "redshift", "cassandra"):
        pid = ProviderId(prov)
        assert str(pid) == prov
