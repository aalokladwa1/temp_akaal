"""
tests.unit.engine_extensions.test_identity
==========================================
Tests for identity models, normalization, immutability, and validation.
"""

import pytest
from akaalEngine.extensions.models.identity import (
    AuthorityId,
    ExtensionId,
    ProviderId,
    RegistryGeneration,
    StrategyId,
    normalize_identifier,
)


def test_identity_normalization():
    assert normalize_identifier(" PostgreSQL ") == "postgresql"
    assert normalize_identifier("My_Custom.Extension-1") == "my_custom.extension-1"
    
    with pytest.raises(ValueError):
        normalize_identifier("")
    with pytest.raises(ValueError):
        normalize_identifier("   ")
    with pytest.raises(ValueError):
        normalize_identifier("@invalid#name")


def test_immutable_identity_types():
    ext_id = ExtensionId("My-Extension")
    assert ext_id.value == "my-extension"
    assert str(ext_id) == "my-extension"

    prov_id = ProviderId("PostgreSQL")
    assert prov_id.value == "postgresql"

    auth_id = AuthorityId("Connection")
    assert auth_id.value == "connection"

    strat_id = StrategyId("PG-Native")
    assert strat_id.value == "pg-native"

    gen = RegistryGeneration(1)
    assert gen.value == 1
    assert str(gen) == "1"
    next_gen = gen.next()
    assert next_gen.value == 2

    with pytest.raises(ValueError):
        RegistryGeneration(0)
    with pytest.raises(ValueError):
        RegistryGeneration(-5)
