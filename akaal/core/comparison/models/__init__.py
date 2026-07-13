"""
Akaal — Comparison Domain Models
================================
Consolidates and exports all public classes and exceptions inside models package.
"""

from akaal.core.comparison.models.context import ComparisonContext
from akaal.core.comparison.models.exceptions import (
    AkaalComparisonError,
    InvalidSchemaError,
    NormalizationError,
    UnsupportedObjectTypeError,
    SerializationError,
)
from akaal.core.comparison.models.schema import (
    ColumnSchema,
    PrimaryKeySchema,
    ForeignKeySchema,
    IndexSchema,
    ConstraintSchema,
    TableSchema,
    Schema,
)
from akaal.core.comparison.models.summary import ComparisonSummary
from akaal.core.comparison.models.differences import (
    SchemaComparisonStatus,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    TableDifference,
    ColumnDifference,
    PrimaryKeyDifference,
    ForeignKeyDifference,
    IndexDifference,
    ConstraintDifference,
    generate_deterministic_id,
    DifferenceReport,
)

__all__ = [
    "ComparisonContext",
    "AkaalComparisonError",
    "InvalidSchemaError",
    "NormalizationError",
    "UnsupportedObjectTypeError",
    "SerializationError",
    "ColumnSchema",
    "PrimaryKeySchema",
    "ForeignKeySchema",
    "IndexSchema",
    "ConstraintSchema",
    "TableSchema",
    "Schema",
    "ComparisonSummary",
    "SchemaComparisonStatus",
    "DifferenceCategory",
    "DifferenceAction",
    "DifferenceSeverity",
    "MigrationImpact",
    "SchemaDifference",
    "TableDifference",
    "ColumnDifference",
    "PrimaryKeyDifference",
    "ForeignKeyDifference",
    "IndexDifference",
    "ConstraintDifference",
    "generate_deterministic_id",
    "DifferenceReport",
]
