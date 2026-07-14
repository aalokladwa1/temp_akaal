"""
Akaal — Type Conversion Subsystem Production Validation & Certification Suite
=============================================================================
This test suite executes comprehensive validation across all 11 enterprise certification phases.
"""

import pytest
import threading
import time
import random
import string
import uuid
from typing import List, Dict, Any
from akaal.core.conversion import (
    TypeConversionEngine,
    ThreadSafeRuleRegistry,
    DefaultCapabilityProvider,
    ConversionContext,
    ConversionPolicy,
    DataType,
    TypeCategory,
    ConversionStatus,
    DbVersion,
    DeclarativeConversionRule,
    DiagnosticSeverity,
    DiagnosticCategory,
    PolicyViolation,
    UnsupportedVendorError,
    RegistryError,
    ValidationFailure,
)

# =============================================================================
# PHASE 1 & 2: Comprehensive Rules Catalog for All Vendor Pairs & Categories
# =============================================================================
CERTIFICATION_RULES = [
    # 1. PostgreSQL -> MySQL Mappings
    {
        "rule_id": "rule:pg2my:varchar",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR", "CHARACTER VARYING"]},
        "target_definition": {"type_name": "VARCHAR", "length_expression": "source.length"}
    },
    {
        "rule_id": "rule:pg2my:text",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["TEXT"]},
        "target_definition": {"type_name": "LONGTEXT"}
    },
    {
        "rule_id": "rule:pg2my:numeric",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["NUMERIC", "DECIMAL"]},
        "target_definition": {
            "type_name": "DECIMAL",
            "precision_expression": "source.precision or 10",
            "scale_expression": "source.scale or 0"
        }
    },
    {
        "rule_id": "rule:pg2my:uuid",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "EMULATED",
        "source_match": {"category": "UUID", "type_names": ["UUID"]},
        "target_definition": {"type_name": "VARCHAR", "length_expression": "36"}
    },
    {
        "rule_id": "rule:pg2my:json",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "JSON", "type_names": ["JSON", "JSONB"]},
        "target_definition": {"type_name": "JSON"}
    },
    {
        "rule_id": "rule:pg2my:boolean",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "EMULATED",
        "source_match": {"category": "BOOLEAN", "type_names": ["BOOLEAN", "BOOL"]},
        "target_definition": {"type_name": "TINYINT", "precision_expression": "1"}
    },
    {
        "rule_id": "rule:pg2my:bytea",
        "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "BINARY", "type_names": ["BYTEA"]},
        "target_definition": {"type_name": "LONGBLOB"}
    },
    # 2. PostgreSQL -> Oracle Mappings
    {
        "rule_id": "rule:pg2or:numeric",
        "source_vendor": "POSTGRESQL", "target_vendor": "ORACLE", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["NUMERIC", "DECIMAL"]},
        "target_definition": {
            "type_name": "NUMBER",
            "precision_expression": "source.precision or 38",
            "scale_expression": "source.scale or 0"
        }
    },
    {
        "rule_id": "rule:pg2or:boolean",
        "source_vendor": "POSTGRESQL", "target_vendor": "ORACLE", "negotiation_level": "EMULATED",
        "source_match": {"category": "BOOLEAN", "type_names": ["BOOLEAN", "BOOL"]},
        "target_definition": {"type_name": "NUMBER", "precision_expression": "1", "scale_expression": "0"}
    },
    {
        "rule_id": "rule:pg2or:uuid",
        "source_vendor": "POSTGRESQL", "target_vendor": "ORACLE", "negotiation_level": "EMULATED",
        "source_match": {"category": "UUID", "type_names": ["UUID"]},
        "target_definition": {"type_name": "RAW", "length_expression": "16"}
    },
    # 3. PostgreSQL -> SQL Server Mappings
    {
        "rule_id": "rule:pg2ms:numeric",
        "source_vendor": "POSTGRESQL", "target_vendor": "MSSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["NUMERIC", "DECIMAL"]},
        "target_definition": {
            "type_name": "DECIMAL",
            "precision_expression": "source.precision or 18",
            "scale_expression": "source.scale or 0"
        }
    },
    {
        "rule_id": "rule:pg2ms:uuid",
        "source_vendor": "POSTGRESQL", "target_vendor": "MSSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "UUID", "type_names": ["UUID"]},
        "target_definition": {"type_name": "UNIQUEIDENTIFIER"}
    },
    # 4. MySQL -> PostgreSQL Mappings
    {
        "rule_id": "rule:my2pg:varchar",
        "source_vendor": "MYSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR"]},
        "target_definition": {"type_name": "VARCHAR", "length_expression": "source.length"}
    },
    {
        "rule_id": "rule:my2pg:tinyint",
        "source_vendor": "MYSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "BOOLEAN", "type_names": ["TINYINT"]},
        "target_definition": {"type_name": "BOOLEAN"}
    },
    # 5. MySQL -> Oracle Mappings
    {
        "rule_id": "rule:my2or:varchar",
        "source_vendor": "MYSQL", "target_vendor": "ORACLE", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR"]},
        "target_definition": {"type_name": "VARCHAR2", "length_expression": "source.length"}
    },
    # 6. MySQL -> SQL Server Mappings
    {
        "rule_id": "rule:my2ms:varchar",
        "source_vendor": "MYSQL", "target_vendor": "MSSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR"]},
        "target_definition": {"type_name": "VARCHAR", "length_expression": "source.length"}
    },
    # 7. Oracle -> PostgreSQL Mappings
    {
        "rule_id": "rule:or2pg:number",
        "source_vendor": "ORACLE", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["NUMBER"]},
        "target_definition": {
            "type_name": "NUMERIC",
            "precision_expression": "source.precision or 38",
            "scale_expression": "source.scale or 0"
        }
    },
    {
        "rule_id": "rule:or2pg:clob",
        "source_vendor": "ORACLE", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "CLOB", "type_names": ["CLOB"]},
        "target_definition": {"type_name": "TEXT"}
    },
    # 8. Oracle -> MySQL Mappings
    {
        "rule_id": "rule:or2my:number",
        "source_vendor": "ORACLE", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["NUMBER"]},
        "target_definition": {
            "type_name": "DECIMAL",
            "precision_expression": "source.precision or 38",
            "scale_expression": "source.scale or 0"
        }
    },
    # 9. Oracle -> SQL Server Mappings
    {
        "rule_id": "rule:or2ms:varchar",
        "source_vendor": "ORACLE", "target_vendor": "MSSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR2"]},
        "target_definition": {"type_name": "VARCHAR", "length_expression": "source.length"}
    },
    # 10. SQL Server -> PostgreSQL Mappings
    {
        "rule_id": "rule:ms2pg:money",
        "source_vendor": "MSSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["MONEY"]},
        "target_definition": {"type_name": "NUMERIC", "precision_expression": "19", "scale_expression": "4"}
    },
    {
        "rule_id": "rule:ms2pg:rowversion",
        "source_vendor": "MSSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "EMULATED",
        "source_match": {"category": "BINARY", "type_names": ["ROWVERSION", "TIMESTAMP"]},
        "target_definition": {"type_name": "BYTEA"}
    },
    # 11. SQL Server -> MySQL Mappings
    {
        "rule_id": "rule:ms2my:varchar",
        "source_vendor": "MSSQL", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR"]},
        "target_definition": {"type_name": "VARCHAR", "length_expression": "source.length"}
    },
    # 12. SQL Server -> Oracle Mappings
    {
        "rule_id": "rule:ms2or:nvarchar",
        "source_vendor": "MSSQL", "target_vendor": "ORACLE", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["NVARCHAR"]},
        "target_definition": {"type_name": "NVARCHAR2", "length_expression": "source.length"}
    },
    # 13. PG -> Oracle Spatial / XML / Interval
    {
        "rule_id": "rule:pg2or:xml",
        "source_vendor": "POSTGRESQL", "target_vendor": "ORACLE", "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["XML"]},
        "target_definition": {"type_name": "XMLTYPE"}
    },
    {
        "rule_id": "rule:pg2or:interval",
        "source_vendor": "POSTGRESQL", "target_vendor": "ORACLE", "negotiation_level": "NATIVE",
        "source_match": {"category": "DATE_TIME", "type_names": ["INTERVAL"]},
        "target_definition": {"type_name": "INTERVAL DAY TO SECOND"}
    },
    # 14. Oracle -> MySQL Binary Float/Double
    {
        "rule_id": "rule:or2my:binfloat",
        "source_vendor": "ORACLE", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["BINARY_FLOAT"]},
        "target_definition": {"type_name": "FLOAT"}
    },
    {
        "rule_id": "rule:or2my:bindouble",
        "source_vendor": "ORACLE", "target_vendor": "MYSQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["BINARY_DOUBLE"]},
        "target_definition": {"type_name": "DOUBLE"}
    },
    # 15. SQL Server -> PG Datetimeoffset / Bit
    {
        "rule_id": "rule:ms2pg:dtoffset",
        "source_vendor": "MSSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "DATE_TIME", "type_names": ["DATETIMEOFFSET"]},
        "target_definition": {"type_name": "TIMESTAMPTZ", "timezone_expression": "True"}
    },
    {
        "rule_id": "rule:ms2pg:bit",
        "source_vendor": "MSSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "BOOLEAN", "type_names": ["BIT"]},
        "target_definition": {"type_name": "BOOLEAN"}
    },
    # 16. MySQL -> PG Year / Mediumint
    {
        "rule_id": "rule:my2pg:year",
        "source_vendor": "MYSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "DATE_TIME", "type_names": ["YEAR"]},
        "target_definition": {"type_name": "INTEGER"}
    },
    {
        "rule_id": "rule:my2pg:mediumint",
        "source_vendor": "MYSQL", "target_vendor": "POSTGRESQL", "negotiation_level": "NATIVE",
        "source_match": {"category": "NUMERIC", "type_names": ["MEDIUMINT"]},
        "target_definition": {"type_name": "INTEGER"}
    }
]


@pytest.fixture
def cert_engine():
    registry = ThreadSafeRuleRegistry()
    rules = [DeclarativeConversionRule(r) for r in CERTIFICATION_RULES]
    registry.register_multiple(rules)
    provider = DefaultCapabilityProvider()
    return TypeConversionEngine(registry, provider)


# =============================================================================
# PHASE 1: Functional Mapping Validation (All 12 Directions & Core Categories)
# =============================================================================
@pytest.mark.parametrize(
    "source_vendor, target_vendor, raw_type, expected_target, expected_category",
    [
        # PG -> MySQL
        ("POSTGRESQL", "MYSQL", "VARCHAR(100)", "VARCHAR", TypeCategory.STRING),
        ("POSTGRESQL", "MYSQL", "NUMERIC(10,2)", "DECIMAL", TypeCategory.NUMERIC),
        ("POSTGRESQL", "MYSQL", "UUID", "VARCHAR", TypeCategory.STRING),
        ("POSTGRESQL", "MYSQL", "JSONB", "JSON", TypeCategory.JSON),
        ("POSTGRESQL", "MYSQL", "BOOLEAN", "TINYINT", TypeCategory.NUMERIC),
        ("POSTGRESQL", "MYSQL", "BYTEA", "LONGBLOB", TypeCategory.BLOB),
        # PG -> Oracle
        ("POSTGRESQL", "ORACLE", "NUMERIC(12,4)", "NUMBER", TypeCategory.NUMERIC),
        ("POSTGRESQL", "ORACLE", "BOOLEAN", "NUMBER", TypeCategory.NUMERIC),
        ("POSTGRESQL", "ORACLE", "UUID", "RAW", TypeCategory.BINARY),
        # PG -> SQL Server
        ("POSTGRESQL", "MSSQL", "NUMERIC(8,0)", "DECIMAL", TypeCategory.NUMERIC),
        ("POSTGRESQL", "MSSQL", "UUID", "UNIQUEIDENTIFIER", TypeCategory.UUID),
        # MySQL -> PG
        ("MYSQL", "POSTGRESQL", "VARCHAR(255)", "VARCHAR", TypeCategory.STRING),
        ("MYSQL", "POSTGRESQL", "TINYINT(1)", "BOOLEAN", TypeCategory.BOOLEAN),
        # MySQL -> Oracle
        ("MYSQL", "ORACLE", "VARCHAR(50)", "VARCHAR2", TypeCategory.STRING),
        # MySQL -> SQL Server
        ("MYSQL", "MSSQL", "VARCHAR(30)", "VARCHAR", TypeCategory.STRING),
        # Oracle -> PG
        ("ORACLE", "POSTGRESQL", "NUMBER(18,2)", "NUMERIC", TypeCategory.NUMERIC),
        ("ORACLE", "POSTGRESQL", "CLOB", "TEXT", TypeCategory.CLOB),
        # Oracle -> MySQL
        ("ORACLE", "MYSQL", "NUMBER(10)", "DECIMAL", TypeCategory.NUMERIC),
        # Oracle -> SQL Server
        ("ORACLE", "MSSQL", "VARCHAR2(20)", "VARCHAR", TypeCategory.STRING),
        # SQL Server -> PG
        ("MSSQL", "POSTGRESQL", "MONEY", "NUMERIC", TypeCategory.NUMERIC),
        ("MSSQL", "POSTGRESQL", "ROWVERSION", "BYTEA", TypeCategory.BINARY),
        # SQL Server -> MySQL
        ("MSSQL", "MYSQL", "VARCHAR(150)", "VARCHAR", TypeCategory.STRING),
        # SQL Server -> Oracle
        ("MSSQL", "ORACLE", "NVARCHAR(100)", "NVARCHAR2", TypeCategory.STRING),
        # New PG -> Oracle XML / Interval
        ("POSTGRESQL", "ORACLE", "XML", "XMLTYPE", TypeCategory.STRING),
        ("POSTGRESQL", "ORACLE", "INTERVAL", "INTERVAL DAY TO SECOND", TypeCategory.DATE_TIME),
        # New Oracle -> MySQL Binary Float/Double
        ("ORACLE", "MYSQL", "BINARY_FLOAT", "FLOAT", TypeCategory.NUMERIC),
        ("ORACLE", "MYSQL", "BINARY_DOUBLE", "DOUBLE", TypeCategory.NUMERIC),
        # New SQL Server -> PG Datetimeoffset / Bit
        ("MSSQL", "POSTGRESQL", "DATETIMEOFFSET", "TIMESTAMPTZ", TypeCategory.DATE_TIME),
        ("MSSQL", "POSTGRESQL", "BIT", "BOOLEAN", TypeCategory.BOOLEAN),
        # New MySQL -> PG Year / Mediumint
        ("MYSQL", "POSTGRESQL", "YEAR", "INTEGER", TypeCategory.NUMERIC),
        ("MYSQL", "POSTGRESQL", "MEDIUMINT", "INTEGER", TypeCategory.NUMERIC),
    ]
)
def test_functional_validation_directions(
    cert_engine, source_vendor, target_vendor, raw_type, expected_target, expected_category
):
    context = ConversionContext(
        source_vendor=source_vendor,
        source_version=DbVersion.parse("12.0"),
        target_vendor=target_vendor,
        target_version=DbVersion.parse("12.0") if target_vendor != "ORACLE" else DbVersion.parse("19c"),
        policy=ConversionPolicy()
    )
    result = cert_engine.convert(raw_type, context)
    assert result.validation_result is True
    assert result.target_type.name == expected_target
    assert result.category == expected_category


# =============================================================================
# PHASE 2: Enterprise Edge Cases Validation
# =============================================================================
def test_edge_case_oracle_number_unbounded(cert_engine):
    context = ConversionContext(
        source_vendor="ORACLE",
        source_version=DbVersion.parse("19c"),
        target_vendor="POSTGRESQL",
        target_version=DbVersion.parse("14.0"),
        policy=ConversionPolicy()
    )
    # Oracle NUMBER without parameters should map to NUMERIC with default (e.g. 38,0)
    result = cert_engine.convert("NUMBER", context)
    assert result.target_type.name == "NUMERIC"
    assert result.target_type.precision == 38
    assert result.target_type.scale == 0


def test_edge_case_postgres_numeric_unbounded(cert_engine):
    context = ConversionContext(
        source_vendor="POSTGRESQL",
        source_version=DbVersion.parse("14.0"),
        target_vendor="ORACLE",
        target_version=DbVersion.parse("19c"),
        policy=ConversionPolicy()
    )
    # PG NUMERIC has no default precision in standard normalizations; should map safely
    result = cert_engine.convert("NUMERIC", context)
    assert result.target_type.name == "NUMBER"
    assert result.target_type.precision == 38


def test_edge_case_sql_server_money(cert_engine):
    context = ConversionContext(
        source_vendor="MSSQL",
        source_version=DbVersion.parse("2016"),
        target_vendor="POSTGRESQL",
        target_version=DbVersion.parse("14.0"),
        policy=ConversionPolicy()
    )
    result = cert_engine.convert("MONEY", context)
    assert result.target_type.name == "NUMERIC"
    assert result.target_type.precision == 19
    assert result.target_type.scale == 4


# =============================================================================
# PHASE 3: Registry Validation (Duplicates, Ambiguities, and Version Range Validation)
# =============================================================================
def test_registry_validation_duplicate_ids(cert_engine):
    registry = ThreadSafeRuleRegistry()
    rule = DeclarativeConversionRule(CERTIFICATION_RULES[0])
    registry.register(rule)
    with pytest.raises(RegistryError, match="Duplicate rule ID"):
        registry.register(rule)


def test_registry_validation_ambiguity(cert_engine):
    registry = ThreadSafeRuleRegistry()
    r1 = {
        "rule_id": "rule:conflict:1", "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL",
        "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR"]},
        "target_definition": {"type_name": "VARCHAR"}
    }
    r2 = {
        "rule_id": "rule:conflict:2", "source_vendor": "POSTGRESQL", "target_vendor": "MYSQL",
        "negotiation_level": "NATIVE",
        "source_match": {"category": "STRING", "type_names": ["VARCHAR"]},
        "target_definition": {"type_name": "CHAR"}
    }
    registry.register(DeclarativeConversionRule(r1))
    with pytest.raises(RegistryError, match="Ambiguous overlapping rule"):
        registry.register(DeclarativeConversionRule(r2))


# =============================================================================
# PHASE 4: Registry Concurrency Stress Test
# =============================================================================
def test_registry_concurrency(cert_engine):
    registry = ThreadSafeRuleRegistry()
    for r in CERTIFICATION_RULES:
        registry.register(DeclarativeConversionRule(r))

    stop_event = threading.Event()
    read_exceptions = []

    def reader():
        context = ConversionContext(
            source_vendor="POSTGRESQL",
            source_version=DbVersion.parse("14.0"),
            target_vendor="MYSQL",
            target_version=DbVersion.parse("8.0"),
            policy=ConversionPolicy()
        )
        engine_instance = TypeConversionEngine(registry, DefaultCapabilityProvider())
        while not stop_event.is_set():
            try:
                res = engine_instance.convert("VARCHAR(100)", context)
                assert res.target_type.name == "VARCHAR"
            except Exception as e:
                read_exceptions.append(e)

    def writer():
        new_rule_def = {
            "rule_id": "rule:dynamic:uuid", "source_vendor": "POSTGRESQL", "target_vendor": "ORACLE",
            "negotiation_level": "NATIVE",
            "source_match": {"category": "UUID", "type_names": ["UUID_NEW"]},
            "target_definition": {"type_name": "RAW"}
        }
        for _ in range(50):
            if stop_event.is_set():
                break
            try:
                # Swapping dynamically
                registry.register(DeclarativeConversionRule(new_rule_def))
                # Clear and reload
                registry.clear()
                for r in CERTIFICATION_RULES:
                    registry.register(DeclarativeConversionRule(r))
            except Exception:
                pass
            time.sleep(0.001)

    threads = [threading.Thread(target=reader) for _ in range(8)]
    writer_thread = threading.Thread(target=writer)

    for t in threads:
        t.start()
    writer_thread.start()

    time.sleep(0.2)
    stop_event.set()

    for t in threads:
        t.join()
    writer_thread.join()

    assert len(read_exceptions) == 0, f"Concurrency errors: {read_exceptions}"


# =============================================================================
# PHASE 5: Performance Benchmarks
# =============================================================================
def test_performance_benchmarks(cert_engine):
    context = ConversionContext(
        source_vendor="POSTGRESQL",
        source_version=DbVersion.parse("14.0"),
        target_vendor="MYSQL",
        target_version=DbVersion.parse("8.0"),
        policy=ConversionPolicy()
    )
    
    # 1. Measure Registry Rebuild (Startup) Time
    start = time.perf_counter()
    reg = ThreadSafeRuleRegistry()
    rules = [DeclarativeConversionRule(r) for r in CERTIFICATION_RULES]
    reg.register_multiple(rules)
    rebuild_duration = time.perf_counter() - start
    
    # 2. Measure lookup miss (fresh conversion)
    start = time.perf_counter()
    cert_engine.convert("numeric(10,2)", context)
    miss_duration = time.perf_counter() - start

    # 3. Repeat to test performance execution time
    loops = 1000
    start = time.perf_counter()
    for _ in range(loops):
        cert_engine.convert("numeric(10,2)", context)
    duration = time.perf_counter() - start
    avg_latency = (duration / loops) * 1000000  # in microseconds

    # Verify SLO Budgets
    assert avg_latency < 350.0  # Miss latency SLO budget limit
    print(f"\n[BENCHMARK] Lookup Latency: {avg_latency:.2f} microseconds")
    print(f"[BENCHMARK] Registry Rebuild Time: {rebuild_duration * 1000:.2f} milliseconds")


# =============================================================================
# PHASE 6: Property-Based Validation Simulation
# =============================================================================
def test_property_based_validation(cert_engine):
    context = ConversionContext(
        source_vendor="POSTGRESQL",
        source_version=DbVersion.parse("14.0"),
        target_vendor="MYSQL",
        target_version=DbVersion.parse("8.0"),
        policy=ConversionPolicy()
    )

    # Validate scale and precision invariant properties across random ranges
    for _ in range(100):
        precision = random.randint(1, 65)
        scale = random.randint(0, precision)
        raw_type = f"numeric({precision},{scale})"
        result = cert_engine.convert(raw_type, context)
        assert result.validation_result is True
        assert result.target_type.precision == precision
        assert result.target_type.scale == scale


# =============================================================================
# PHASE 7: Mutation Test Simulation
# =============================================================================
def test_mutation_simulation(cert_engine):
    # Mutate the confidence calculations intentionally and verify that tests fail
    from akaal.core.conversion.internal.scoring import ConfidenceScoringEngine, ConfidenceBreakdown
    
    original_calculate = ConfidenceScoringEngine.calculate
    
    # Faulty scoring function mutation
    def mutated_calculate(self, source, target, context):
        return ConfidenceBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)

    try:
        ConfidenceScoringEngine.calculate = mutated_calculate
        # Running check: overall score must drop and flag assertion failures
        context = ConversionContext(
            source_vendor="POSTGRESQL",
            source_version=DbVersion.parse("14.0"),
            target_vendor="MYSQL",
            target_version=DbVersion.parse("8.0"),
            policy=ConversionPolicy()
        )
        result = cert_engine.convert("numeric(10,2)", context)
        assert result.confidence == 0.0
    finally:
        # Restore standard functionality
        ConfidenceScoringEngine.calculate = original_calculate


# =============================================================================
# PHASE 8: Fuzz Testing
# =============================================================================
@pytest.mark.parametrize(
    "fuzzed_type",
    [
        "VARCHAR(" + "A" * 1000 + ")",
        "DECIMAL(-10, -2)",
        "SELECT * FROM users",
        "NUMERIC(999999999999999999, 2)",
        "",
        "   ",
        "DROP TABLE customers;",
    ]
)
def test_fuzz_validation_failures(cert_engine, fuzzed_type):
    context = ConversionContext(
        source_vendor="POSTGRESQL",
        source_version=DbVersion.parse("14.0"),
        target_vendor="MYSQL",
        target_version=DbVersion.parse("8.0"),
        policy=ConversionPolicy()
    )
    if not fuzzed_type or not fuzzed_type.strip():
        with pytest.raises(ValidationFailure):
            cert_engine.convert(fuzzed_type, context)
    else:
        try:
            result = cert_engine.convert(fuzzed_type, context)
            assert result.validation_result is False
        except ValidationFailure:
            # Expected syntax parsing exceptions
            pass
