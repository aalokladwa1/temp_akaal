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
    MetadataConfidence,
    CanonicalPartitionScheme,
    CanonicalColumnPartitionKey
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
