import pytest
from datetime import date, datetime
from decimal import Decimal
from akaal.migration.models.partition import (
    CanonicalDataType,
    CanonicalScalarValue,
    BoundInclusivity,
    CanonicalDomainStep,
    CanonicalRangeBound,
    CanonicalRangeInterval,
    ObjectIdentity,
    PartitionStrategy,
    CanonicalRangePartition,
    CanonicalListPartition,
    MetadataConfidence,
    CanonicalPartitionScheme,
    CanonicalColumnPartitionKey,
    BoundarySpecialType,
    PartitionDiagnosticCode,
    PlanReadinessStatus,
    DowntimeClassification,
    DataMovementClassification
)
from akaal.migration.algorithms.partition_bounds import (
    shift_value,
    normalize_interval
)
from akaal.migration.comparison.partition import (
    PartitionCompatibilityAnalyzer,
    PartitionComparisonEngine
)
from akaal.migration.ddl.planning.partition_planner import PartitionMigrationPlanner
from akaal.migration.ddl.planning.partition_scheduler import PartitionDependencyScheduler
from akaal.migration.ddl.planning.partition_rollback import PartitionRollbackPlanner
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter

class MockConfig:
    def __init__(self, host, database_name="test_db"):
        self.host = host
        self.database_name = database_name

# --- 1. Basic Unit Tests ---

def test_canonical_scalar_value_serialization():
    val = CanonicalScalarValue(
        data_type=CanonicalDataType.INTEGER,
        int_val=42
    )
    assert val.serialize() == "I:42"

    val_dec = CanonicalScalarValue(
        data_type=CanonicalDataType.DECIMAL,
        decimal_val=Decimal("123.45")
    )
    assert "D:" in val_dec.serialize()

def test_boundary_value_shifting():
    val = CanonicalScalarValue(
        data_type=CanonicalDataType.INTEGER,
        int_val=10
    )
    step = CanonicalDomainStep(
        value_type=CanonicalDataType.INTEGER,
        step_value=1
    )
    shifted = shift_value(val, step, "successor")
    assert shifted.int_val == 11

    shifted_pred = shift_value(val, step, "predecessor")
    assert shifted_pred.int_val == 9

def test_range_interval_normalization():
    lower = CanonicalRangeBound(
        values=(CanonicalScalarValue(data_type=CanonicalDataType.INTEGER, int_val=10),),
        inclusivity=BoundInclusivity.INCLUSIVE,
        unbounded=False
    )
    upper = CanonicalRangeBound(
        values=(CanonicalScalarValue(data_type=CanonicalDataType.INTEGER, int_val=20),),
        inclusivity=BoundInclusivity.INCLUSIVE,
        unbounded=False
    )
    interval = CanonicalRangeInterval(lower=lower, upper=upper)
    step = CanonicalDomainStep(
        value_type=CanonicalDataType.INTEGER,
        step_value=1
    )
    normalized = normalize_interval(interval, CanonicalDataType.INTEGER, step)
    
    assert normalized.lower.inclusivity == BoundInclusivity.INCLUSIVE
    assert normalized.upper.inclusivity == BoundInclusivity.EXCLUSIVE
    assert normalized.upper.values[0].int_val == 21

def test_compatibility_analyzer():
    scheme = CanonicalPartitionScheme(
        table_identity=ObjectIdentity("public", "orders", "TABLE"),
        source_dialect="postgresql",
        source_version="14.0",
        confidence=MetadataConfidence.COMPLETE,
        strategy=PartitionStrategy.RANGE,
        keys=(),
        partitions=()
    )
    analyzer = PartitionCompatibilityAnalyzer()
    report = analyzer.analyze(scheme, "mysql", "8.0")
    
    assert len(report.decisions) == 1
    assert report.decisions[0].status == "LOSSY_APPROVAL_REQUIRED"

def test_comparison_engine():
    source = CanonicalPartitionScheme(
        table_identity=ObjectIdentity("public", "orders", "TABLE"),
        source_dialect="postgresql",
        source_version="14.0",
        confidence=MetadataConfidence.COMPLETE,
        strategy=PartitionStrategy.RANGE,
        keys=(),
        partitions=(
            CanonicalRangePartition(
                object_identity=ObjectIdentity("public", "orders_p1", "PARTITION"),
                partition_name="orders_p1",
                ordinal=0,
                boundary=CanonicalRangeInterval(
                    lower=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True),
                    upper=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True)
                )
            ),
        )
    )
    target = CanonicalPartitionScheme(
        table_identity=ObjectIdentity("public", "orders", "TABLE"),
        source_dialect="postgresql",
        source_version="14.0",
        confidence=MetadataConfidence.COMPLETE,
        strategy=PartitionStrategy.RANGE,
        keys=(),
        partitions=()
    )
    engine = PartitionComparisonEngine()
    report = engine.compare(source, target)
    
    assert len(report.differences) == 1
    assert report.differences[0].difference_type.value == "ADD"

# --- 2. Advanced Enterprise Testing & Edge Cases ---

def test_special_boundaries_minvalue_maxvalue():
    val_min = CanonicalScalarValue(
        data_type=CanonicalDataType.INTEGER,
        special_type=BoundarySpecialType.MINVALUE
    )
    val_max = CanonicalScalarValue(
        data_type=CanonicalDataType.INTEGER,
        special_type=BoundarySpecialType.MAXVALUE
    )
    assert val_min.serialize() == "SPECIAL:MINVALUE"
    assert val_max.serialize() == "SPECIAL:MAXVALUE"

def test_default_partitions():
    part = CanonicalListPartition(
        object_identity=ObjectIdentity("public", "orders_default", "PARTITION"),
        partition_name="orders_default",
        ordinal=0,
        values=(),
        is_default=True
    )
    assert part.is_default is True

def test_composite_partition_keys():
    lower = CanonicalRangeBound(
        values=(
            CanonicalScalarValue(data_type=CanonicalDataType.INTEGER, int_val=10),
            CanonicalScalarValue(data_type=CanonicalDataType.INTEGER, int_val=100)
        ),
        inclusivity=BoundInclusivity.INCLUSIVE,
        unbounded=False
    )
    upper = CanonicalRangeBound(
        values=(
            CanonicalScalarValue(data_type=CanonicalDataType.INTEGER, int_val=20),
            CanonicalScalarValue(data_type=CanonicalDataType.INTEGER, int_val=200)
        ),
        inclusivity=BoundInclusivity.EXCLUSIVE,
        unbounded=False
    )
    interval = CanonicalRangeInterval(lower=lower, upper=upper)
    assert len(interval.lower.values) == 2

def test_empty_partition_scheme_handling():
    scheme = CanonicalPartitionScheme(
        table_identity=ObjectIdentity("public", "empty_table", "TABLE"),
        source_dialect="postgresql",
        source_version="14.0",
        confidence=MetadataConfidence.COMPLETE,
        strategy=PartitionStrategy.RANGE,
        keys=(),
        partitions=()
    )
    assert len(scheme.partitions) == 0

# --- 3. Database Adapter Discovery Verification ---

@pytest.mark.asyncio
async def test_postgresql_adapter_partition_discovery():
    cfg = MockConfig(host="source-db.example.com")
    adapter = PostgreSQLAdapter(cfg)
    await adapter.connect()
    
    scheme = await adapter.discover_partition_scheme("public", "orders")
    assert scheme is not None
    assert scheme.strategy == PartitionStrategy.RANGE
    assert len(scheme.partitions) == 1
    assert scheme.partitions[0].partition_name == "orders_p1"

@pytest.mark.asyncio
async def test_mysql_adapter_partition_discovery():
    cfg = MockConfig(host="source-db.example.com")
    adapter = MySQLAdapter(cfg)
    await adapter.connect()
    
    scheme = await adapter.discover_partition_scheme("public", "orders")
    assert scheme is not None
    assert scheme.strategy == PartitionStrategy.RANGE
    assert len(scheme.partitions) == 1

@pytest.mark.asyncio
async def test_oracle_adapter_partition_discovery():
    cfg = MockConfig(host="oracle-prod.example.com")
    adapter = OracleAdapter(cfg)
    await adapter.connect()
    
    scheme = await adapter.discover_partition_scheme("SYS", "ORDERS")
    assert scheme is not None
    assert scheme.strategy == PartitionStrategy.RANGE
    assert len(scheme.partitions) == 1

@pytest.mark.asyncio
async def test_mssql_adapter_partition_discovery():
    cfg = MockConfig(host="source-db.example.com")
    adapter = MSSQLAdapter(cfg)
    await adapter.connect()
    
    scheme = await adapter.discover_partition_scheme("dbo", "orders")
    assert scheme is not None
    assert scheme.strategy == PartitionStrategy.RANGE
    assert len(scheme.partitions) == 1

# --- 4. Pipeline Integration Testing ---

@pytest.mark.asyncio
async def test_end_to_end_planning_integration_pipeline():
    # 1. Discover via PG Adapter
    cfg = MockConfig(host="source-db.example.com")
    adapter = PostgreSQLAdapter(cfg)
    await adapter.connect()
    
    source_scheme = await adapter.discover_partition_scheme("public", "orders")
    
    # 2. Analyze compatibility for migration target
    analyzer = PartitionCompatibilityAnalyzer()
    compat_report = analyzer.analyze(source_scheme, "postgresql", "14.0")
    
    # 3. Form comparison differences
    engine = PartitionComparisonEngine()
    # Mocking target empty scheme to generate target differences
    target_scheme = CanonicalPartitionScheme(
        table_identity=source_scheme.table_identity,
        source_dialect="postgresql",
        source_version="14.0",
        confidence=MetadataConfidence.COMPLETE,
        strategy=PartitionStrategy.RANGE,
        keys=(),
        partitions=()
    )
    comp_report = engine.compare(source_scheme, target_scheme)
    
    # 4. Generate Planner execution plans
    planner = PartitionMigrationPlanner()
    plan = planner.plan(comp_report, compat_report)
    
    assert plan.plan_fingerprint != ""
    assert len(plan.ordered_actions) == 1
    
    # 5. Generate rollback recovery actions
    rollback_plan = PartitionRollbackPlanner.plan_rollback(plan.ordered_actions)
    assert len(rollback_plan.ordered_actions) == 1
