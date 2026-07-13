"""
Akaal — Schema Comparison Subpackage Public API
===============================================
Exposes the stable public API interfaces for the Schema Comparison Engine.
Internal components, normalizers, and sub-comparers remain hidden.
"""

from akaal.core.comparison.engine import SchemaComparisonEngine
from akaal.core.comparison.validator import SchemaValidator
from akaal.core.comparison.serializer import SchemaDifferenceSerializer
from akaal.core.comparison.models import (
    ComparisonContext,
    Schema,
    TableSchema,
    ColumnSchema,
    PrimaryKeySchema,
    ForeignKeySchema,
    IndexSchema,
    ConstraintSchema,
    DifferenceReport,
    ComparisonSummary,
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
    AkaalComparisonError,
    InvalidSchemaError,
    NormalizationError,
    UnsupportedObjectTypeError,
    SerializationError,
)

__all__ = [
    # Main Engine components
    "SchemaComparisonEngine",
    "SchemaValidator",
    "SchemaDifferenceSerializer",
    
    # Models & Options
    "ComparisonContext",
    "Schema",
    "TableSchema",
    "ColumnSchema",
    "PrimaryKeySchema",
    "ForeignKeySchema",
    "IndexSchema",
    "ConstraintSchema",
    "DifferenceReport",
    "ComparisonSummary",
    
    # Polymorphic differences
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
    
    # Exceptions
    "AkaalComparisonError",
    "InvalidSchemaError",
    "NormalizationError",
    "UnsupportedObjectTypeError",
    "SerializationError",
]
