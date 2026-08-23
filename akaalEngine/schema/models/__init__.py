"""
akaalEngine.schema.models
=========================
Public domain and IR models for Authority #4 Schema.
"""

from akaalEngine.schema.models.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
    freeze_deep,
)

from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalExclusionConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)

from akaalEngine.schema.models.indexes import (
    CanonicalIndex,
    IndexAccessMethod,
)

from akaalEngine.schema.models.partitioning import (
    CanonicalPartitionBound,
    CanonicalPartitioning,
    CanonicalSubpartition,
    CanonicalTokenRange,
    PartitionStrategy,
)

from akaalEngine.schema.models.table import (
    CanonicalColumn,
    CanonicalTable,
    StorageFormat,
    TablePhysicalType,
)

from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalRoutineParameter,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
    ParameterMode,
    RoutineKind,
    TriggerTiming,
)

from akaalEngine.schema.models.mapping import (
    ColumnMapping,
    CompiledSchemaMapping,
    DataTypeOverride,
    SchemaMappingRule,
    TableMapping,
)

from akaalEngine.schema.models.schema import (
    CanonicalCatalog,
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalSynonym,
    CanonicalView,
)

__all__ = [
    "CanonicalType",
    "CanonicalTypeCategory",
    "ConversionSafety",
    "TargetTypeEmission",
    "freeze_deep",
    "CanonicalPrimaryKey",
    "CanonicalForeignKey",
    "CanonicalUniqueConstraint",
    "CanonicalCheckConstraint",
    "CanonicalExclusionConstraint",
    "CanonicalIndex",
    "IndexAccessMethod",
    "PartitionStrategy",
    "CanonicalPartitionBound",
    "CanonicalSubpartition",
    "CanonicalTokenRange",
    "CanonicalPartitioning",
    "TablePhysicalType",
    "StorageFormat",
    "CanonicalColumn",
    "CanonicalTable",
    "RoutineKind",
    "ParameterMode",
    "TriggerTiming",
    "CanonicalRoutineParameter",
    "CanonicalRoutine",
    "CanonicalPackage",
    "CanonicalTrigger",
    "CanonicalSequence",
    "CanonicalUDT",
    "DataTypeOverride",
    "ColumnMapping",
    "TableMapping",
    "SchemaMappingRule",
    "CompiledSchemaMapping",
    "CanonicalView",
    "CanonicalSynonym",
    "CanonicalSchema",
    "CanonicalCatalog",
    "CanonicalSchemaModel",
]
