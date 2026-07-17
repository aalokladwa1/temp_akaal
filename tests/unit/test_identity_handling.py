"""
Unit Tests for Phase 8 Feature 1: Identity Column Handling (Foundation Models)
"""

import json
import pytest
from akaal.core.comparison.models import (
    ColumnSchema,
    IdentityMode,
    IdentityDefinition
)
from akaal.migration.models import (
    IdentityRuntimeState,
    IdentityStateConfidence,
    GeneratorValueSemantics,
    IdentityCompatibilityClass,
    IdentityCompatibilityResult
)
from akaal.core.comparison.serializer import (
    _dataclass_to_dict,
    _deserialize_column
)


def test_identity_mode_enum():
    """Asserts that all required identity modes are present and have correct values."""
    assert IdentityMode.GENERATED_ALWAYS == "GENERATED_ALWAYS"
    assert IdentityMode.GENERATED_BY_DEFAULT == "GENERATED_BY_DEFAULT"
    assert IdentityMode.SERIAL_FALLBACK == "SERIAL_FALLBACK"
    assert IdentityMode.EMULATED_TRIGGER == "EMULATED_TRIGGER"


def test_identity_definition_validation():
    """Asserts that IdentityDefinition validates increment parameter in __post_init__."""
    with pytest.raises(ValueError, match="Identity increment cannot be zero."):
        IdentityDefinition(mode=IdentityMode.GENERATED_ALWAYS, increment=0)

    # Valid instantiation
    defn = IdentityDefinition(mode=IdentityMode.GENERATED_ALWAYS, start=10, increment=-5)
    assert defn.start == 10
    assert defn.increment == -5


def test_identity_runtime_state_instantiation():
    """Asserts that IdentityRuntimeState can be instantiated with valid fields."""
    state = IdentityRuntimeState(
        current_generator_value=100,
        last_generated_value=95,
        restart_value=100,
        state_confidence=IdentityStateConfidence.EXACT,
        value_semantics=GeneratorValueSemantics.LAST_EMITTED
    )
    assert state.current_generator_value == 100
    assert state.state_confidence == IdentityStateConfidence.EXACT
    assert state.value_semantics == GeneratorValueSemantics.LAST_EMITTED


def test_column_schema_identity_serialization():
    """Asserts that ColumnSchema with IdentityDefinition is correctly serialized and deserialized."""
    identity_defn = IdentityDefinition(
        mode=IdentityMode.GENERATED_BY_DEFAULT,
        start=5,
        increment=2,
        min_value=1,
        max_value=1000,
        cycle=True,
        cache=10,
        order=True,
        explicit_insert_policy="ALLOWED"
    )
    col = ColumnSchema(
        name="id",
        data_type="INTEGER",
        raw_type="INT",
        nullable=False,
        identity=identity_defn
    )

    serialized = _dataclass_to_dict(col)
    assert serialized["name"] == "id"
    assert serialized["identity"]["mode"] == "GENERATED_BY_DEFAULT"
    assert serialized["identity"]["start"] == 5
    assert serialized["identity"]["increment"] == 2
    assert serialized["identity"]["min_value"] == 1
    assert serialized["identity"]["max_value"] == 1000
    assert serialized["identity"]["cycle"] is True
    assert serialized["identity"]["cache"] == 10
    assert serialized["identity"]["order"] is True
    assert serialized["identity"]["explicit_insert_policy"] == "ALLOWED"

    # Test deserialization
    deserialized = _deserialize_column(serialized)
    assert deserialized == col
    assert deserialized.identity.mode == IdentityMode.GENERATED_BY_DEFAULT
    assert deserialized.identity.increment == 2
    assert deserialized.identity.cycle is True


def test_column_schema_is_equivalent_with_identity():
    """Asserts that ColumnSchema.is_equivalent correctly compares identity definitions."""
    from akaal.core.comparison.models import ComparisonContext
    context = ComparisonContext()

    col1 = ColumnSchema(
        name="id",
        data_type="INTEGER",
        raw_type="INT",
        nullable=False,
        identity=IdentityDefinition(mode=IdentityMode.GENERATED_ALWAYS, start=1)
    )
    col2 = ColumnSchema(
        name="id",
        data_type="INTEGER",
        raw_type="INT",
        nullable=False,
        identity=IdentityDefinition(mode=IdentityMode.GENERATED_ALWAYS, start=1)
    )
    col3 = ColumnSchema(
        name="id",
        data_type="INTEGER",
        raw_type="INT",
        nullable=False,
        identity=IdentityDefinition(mode=IdentityMode.GENERATED_BY_DEFAULT, start=1)
    )
    col4 = ColumnSchema(
        name="id",
        data_type="INTEGER",
        raw_type="INT",
        nullable=False,
        identity=None
    )

    assert col1.is_equivalent(col2, context) is True
    assert col1.is_equivalent(col3, context) is False
    assert col1.is_equivalent(col4, context) is False


def test_package_decoupling_boundaries():
    """Asserts that core comparison modules do not import any migration or DDL files."""
    import sys
    
    # Verify no migration modules are in sys.modules from core imports
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("akaal.core.comparison"):
            # Ensure none of these modules imported migration packages
            module = sys.modules[mod_name]
            if module:
                module_source = getattr(module, "__file__", "")
                if module_source:
                    with open(module_source, "r", encoding="utf-8") as f:
                        content = f.read()
                        assert "akaal.migration" not in content, f"Circular dependency risk found: {mod_name} imports akaal.migration"


def test_legacy_serialization_serial_fallback():
    """Asserts that nextval default values are mapped to SERIAL_FALLBACK identities."""
    data = {
        "name": "id",
        "data_type": "INTEGER",
        "raw_type": "INT",
        "nullable": False,
        "default_value": "nextval('users_id_seq'::regclass)",
        "raw_default": "nextval('users_id_seq'::regclass)",
        "identity": None
    }
    col = _deserialize_column(data)
    assert col.identity is not None
    assert col.identity.mode == IdentityMode.SERIAL_FALLBACK
    assert col.identity.source_engine == "POSTGRESQL"


def test_identity_model_mapper():
    """Asserts that IdentityModelMapper converts definitions to/from metadata correctly."""
    from akaal.migration.mappers import IdentityModelMapper
    
    defn = IdentityDefinition(
        mode=IdentityMode.GENERATED_ALWAYS,
        start=10,
        increment=5,
        min_value=1,
        max_value=1000,
        cycle=True,
        cache=20
    )
    meta = IdentityModelMapper.to_metadata(defn)
    assert meta.always is True
    assert meta.generated_by_default is False
    assert meta.start == 10
    assert meta.increment == 5
    assert meta.min_value == 1
    assert meta.max_value == 1000
    assert meta.cycle is True
    assert meta.cache_size == 20
    
    # Convert back
    defn_back = IdentityModelMapper.from_metadata(meta)
    assert defn_back.mode == IdentityMode.GENERATED_ALWAYS
    assert defn_back.start == 10
    assert defn_back.increment == 5
    assert defn_back.cycle is True
    assert defn_back.cache == 20


def test_version_capability_matrix():
    """Asserts PostgreSQL, Oracle, SQL Server, and MySQL identity capabilities match versions."""
    from akaal.core.conversion.internal.capabilities import DefaultCapabilityProvider, CapabilityType
    from akaal.core.conversion.api.models import DbVersion
    
    provider = DefaultCapabilityProvider()
    
    # PostgreSQL
    pg9 = provider.get_matrix("POSTGRESQL", DbVersion(9, 6, 0))
    assert pg9.capabilities[CapabilityType.IDENTITY].supported is False
    
    pg10 = provider.get_matrix("POSTGRESQL", DbVersion(10, 0, 0))
    assert pg10.capabilities[CapabilityType.IDENTITY].supported is True
    
    # Oracle
    ora11 = provider.get_matrix("ORACLE", DbVersion(11, 2, 0))
    assert ora11.capabilities[CapabilityType.IDENTITY].supported is False
    
    ora12 = provider.get_matrix("ORACLE", DbVersion(12, 1, 0))
    assert ora12.capabilities[CapabilityType.IDENTITY].supported is True
    
    # Unknown version
    unknown = provider.get_matrix("POSTGRESQL", DbVersion(0, 0, 0))
    assert unknown.capabilities[CapabilityType.IDENTITY].supported is False

