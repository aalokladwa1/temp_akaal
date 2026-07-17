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
