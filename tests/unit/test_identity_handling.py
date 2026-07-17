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


@pytest.mark.asyncio
async def test_adapters_discover_identity():
    """Asserts that all database adapters discover identity metadata in mock mode."""
    from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
    from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
    from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter
    from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
    
    class LocalMockConfig:
        def __init__(self, host: str):
            self.host = host
            self.database_name = "test_db"
            
    # PG
    pg_cfg = LocalMockConfig("source-db.example.com")
    pg_adapter = PostgreSQLAdapter(pg_cfg)
    await pg_adapter.connect()
    pg_state = await pg_adapter.discover_identity("public", "users", "id")
    assert pg_state is not None
    assert pg_state.current_generator_value == 1
    
    # Oracle
    ora_cfg = LocalMockConfig("source-db.example.com")
    ora_adapter = OracleAdapter(ora_cfg)
    ora_adapter._conn = "mock_oracle_conn"
    ora_state = await ora_adapter.discover_identity("public", "users", "id")
    assert ora_state is not None
    assert ora_state.current_generator_value == 1
    
    # SQL Server
    mssql_cfg = LocalMockConfig("source-db.example.com")
    mssql_adapter = MSSQLAdapter(mssql_cfg)
    mssql_adapter.is_connected = True
    mssql_state = await mssql_adapter.discover_identity("public", "users", "id")
    assert mssql_state is not None
    assert mssql_state.current_generator_value == 1
    
    # MySQL
    mysql_cfg = LocalMockConfig("source-db.example.com")
    mysql_adapter = MySQLAdapter(mysql_cfg)
    mysql_adapter.is_connected = True
    mysql_state = await mysql_adapter.discover_identity("public", "users", "id")
    assert mysql_state is not None
    assert mysql_state.current_generator_value == 1


def test_state_normalization_align_value():
    """Asserts that align_value correctly normalizes values to progression index steps."""
    from akaal.migration.algorithms.progression import IdentityProgressionEngine

    # Positive increment
    assert IdentityProgressionEngine.align_value(8, start=1, increment=5) == 6
    assert IdentityProgressionEngine.align_value(1, start=1, increment=5) == 1
    assert IdentityProgressionEngine.align_value(5, start=1, increment=5) == 1

    # Negative increment
    assert IdentityProgressionEngine.align_value(92, start=100, increment=-5) == 95
    assert IdentityProgressionEngine.align_value(100, start=100, increment=-5) == 100


def test_positive_safe_next_resolution():
    """Asserts that positive increments resolve to the correct safe-next values."""
    from akaal.migration.algorithms.progression import IdentityProgressionEngine
    from akaal.migration.models.identity import IdentityRuntimeState, GeneratorValueSemantics, IdentityStateConfidence

    # Worked Example 1: Positive unit step (S=1, I=1, max=10)
    v1 = IdentityProgressionEngine.resolve_safe_next(
        start=1, increment=1, min_value=1, max_value=100, cycle=False, table_max=10
    )
    assert v1 == 11

    # Worked Example 2: Positive non-unit step (S=5, I=5, max=22)
    v2 = IdentityProgressionEngine.resolve_safe_next(
        start=5, increment=5, min_value=5, max_value=100, cycle=False, table_max=22
    )
    assert v2 == 25

    # With source state LAST_EMITTED
    src = IdentityRuntimeState(
        current_generator_value=27,
        last_generated_value=27,
        restart_value=5,
        state_confidence=IdentityStateConfidence.EXACT,
        value_semantics=GeneratorValueSemantics.LAST_EMITTED
    )
    v3 = IdentityProgressionEngine.resolve_safe_next(
        start=5, increment=5, min_value=5, max_value=100, cycle=False, table_max=22, source_state=src
    )
    assert v3 == 30 # (27 normalized is 25, + 1 increment is 30)

    # With source state NEXT_TO_EMIT
    src_next = IdentityRuntimeState(
        current_generator_value=27,
        last_generated_value=None,
        restart_value=5,
        state_confidence=IdentityStateConfidence.EXACT,
        value_semantics=GeneratorValueSemantics.NEXT_TO_EMIT
    )
    v4 = IdentityProgressionEngine.resolve_safe_next(
        start=5, increment=5, min_value=5, max_value=100, cycle=False, table_max=22, source_state=src_next
    )
    assert v4 == 30 # ceil((27 - 5)/5) = 5 steps => 5 + 5*5 = 30


def test_negative_safe_next_resolution():
    """Asserts that negative increments resolve to the correct safe-next values."""
    from akaal.migration.algorithms.progression import IdentityProgressionEngine
    from akaal.migration.models.identity import IdentityRuntimeState, GeneratorValueSemantics, IdentityStateConfidence

    # Worked Example 3: Negative unit step (S=100, I=-1, min=90)
    v1 = IdentityProgressionEngine.resolve_safe_next(
        start=100, increment=-1, min_value=1, max_value=100, cycle=False, table_min=90
    )
    assert v1 == 89

    # Worked Example 4: Negative non-unit step (S=100, I=-5, min=83)
    v2 = IdentityProgressionEngine.resolve_safe_next(
        start=100, increment=-5, min_value=1, max_value=100, cycle=False, table_min=83
    )
    assert v2 == 80


def test_bounds_overflow_underflow():
    """Asserts that out of bounds progressions raise IdentityOverflowErrors."""
    import pytest
    from akaal.migration.algorithms.progression import IdentityProgressionEngine, IdentityOverflowError

    # Positive overflow
    with pytest.raises(IdentityOverflowError):
        IdentityProgressionEngine.resolve_safe_next(
            start=1, increment=10, min_value=1, max_value=15, cycle=False, table_max=12
        )

    # Negative underflow
    with pytest.raises(IdentityOverflowError):
        IdentityProgressionEngine.resolve_safe_next(
            start=100, increment=-10, min_value=85, max_value=100, cycle=False, table_min=82
        )


def test_cycle_and_exhaustion():
    """Asserts that cycling generators wrap values and raise CycleCollisionError on duplicates."""
    import pytest
    from akaal.migration.algorithms.progression import IdentityProgressionEngine, CycleCollisionError

    # Positive cycling: max_value = 10, v_emit resolves to 11 => wraps to 1 (min_value)
    v1 = IdentityProgressionEngine.resolve_safe_next(
        start=1, increment=1, min_value=1, max_value=10, cycle=True, table_max=10
    )
    assert v1 == 1

    # Cycle collision: wrapped value 1 already exists in existing_keys
    with pytest.raises(CycleCollisionError):
        IdentityProgressionEngine.resolve_safe_next(
            start=1, increment=1, min_value=1, max_value=10, cycle=True, table_max=10, existing_keys=[1, 2, 3]
        )


def test_empty_and_unknown_states():
    """Asserts fallback behavior for empty tables and unknown states."""
    from akaal.migration.algorithms.progression import IdentityProgressionEngine

    v1 = IdentityProgressionEngine.resolve_safe_next(
        start=1, increment=1, min_value=1, max_value=10, cycle=False, table_max=None, source_state=None
    )
    assert v1 == 1  # Empty state uses start value


def test_randomized_invariants():
    """Exhaustive randomized/property-based testing verifying mathematical invariants."""
    import random
    from akaal.migration.algorithms.progression import IdentityProgressionEngine, IdentityOverflowError

    # Test 100 randomized valid setups
    for _ in range(100):
        start = random.randint(-100, 100)
        increment = random.choice([-10, -5, -1, 1, 5, 10])
        min_value = -1000
        max_value = 1000
        cycle = False
        
        if increment > 0:
            table_max = random.randint(start, 500)
            table_min = None
        else:
            table_max = None
            table_min = random.randint(-500, start)

        try:
            v_emit = IdentityProgressionEngine.resolve_safe_next(
                start=start,
                increment=increment,
                min_value=min_value,
                max_value=max_value,
                cycle=cycle,
                table_max=table_max,
                table_min=table_min
            )
            # Invariant 1: Alignment (v_emit - start) mod increment == 0
            assert (v_emit - start) % increment == 0, f"Value {v_emit} is not aligned to sequence steps."

            # Invariant 2: Values strictly exceed bounds
            if increment > 0:
                assert v_emit > table_max, f"Positive progression {v_emit} not strictly above table_max {table_max}."
            else:
                assert v_emit < table_min, f"Negative progression {v_emit} not strictly below table_min {table_min}."
        except IdentityOverflowError:
            pass # Overflow is a valid mathematical result under strict limits



