"""
Akaal — Canonical Object Model & Graph Nodes
=============================================
Vendor-neutral database object models acting as nodes within CanonicalObjectGraph.
Uses pure platform abstractions (e.g. GeneratedValueStrategy, EventHook, ReferenceStrategy).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from akaal.decoder.models.canonical_identity import CanonicalIdentity
from akaal.decoder.models.canonical_type import CanonicalType
from akaal.decoder.models.canonical_equivalence import SemanticEquivalence, SemanticEquivalenceType


@dataclass
class CanonicalObject:
    """Base Canonical Object Graph Node."""
    object_type: str = "CanonicalObject"
    name: str = ""
    identity: CanonicalIdentity = field(default_factory=CanonicalIdentity)
    parents: List[str] = field(default_factory=list)  # parent canonical_ids
    children: List[str] = field(default_factory=list)  # child canonical_ids
    references: List[str] = field(default_factory=list)  # referenced canonical_ids
    capabilities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    semantic_equivalence: SemanticEquivalence = field(
        default_factory=lambda: SemanticEquivalence(equivalence_type=SemanticEquivalenceType.EQUIVALENT)
    )

    def __post_init__(self):
        if self.name and not self.identity.source_identifier:
            self.identity = CanonicalIdentity(source_identifier=f"{self.object_type}:{self.name}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_type": self.object_type,
            "name": self.name,
            "identity": self.identity.to_dict(),
            "parents": self.parents,
            "children": self.children,
            "references": self.references,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "semantic_equivalence": self.semantic_equivalence.to_dict(),
        }


@dataclass
class CanonicalColumn(CanonicalObject):
    data_type: Optional[CanonicalType] = None
    is_nullable: bool = True
    is_primary_key: bool = False
    default_expression: Optional[Dict[str, Any]] = None
    generated_value_strategy: Optional[str] = None

    def __post_init__(self):
        self.object_type = "CanonicalColumn"
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "data_type": self.data_type.to_dict() if self.data_type else None,
            "is_nullable": self.is_nullable,
            "is_primary_key": self.is_primary_key,
            "default_expression": self.default_expression,
            "generated_value_strategy": self.generated_value_strategy,
        })
        return d


@dataclass
class CanonicalTable(CanonicalObject):
    schema_name: str = "public"
    columns: List[CanonicalColumn] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    partition_strategy: Optional[Dict[str, Any]] = None
    storage_strategy: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.object_type = "CanonicalTable"
        if self.name and not self.identity.source_identifier:
            self.identity = CanonicalIdentity(source_identifier=f"CanonicalTable:{self.schema_name}.{self.name}")
        else:
            super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "schema_name": self.schema_name,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": self.primary_key,
            "foreign_keys": self.foreign_keys,
            "indexes": self.indexes,
            "partition_strategy": self.partition_strategy,
            "storage_strategy": self.storage_strategy,
        })
        return d


@dataclass
class CanonicalView(CanonicalObject):
    schema_name: str = "public"
    definition_expression: Optional[Dict[str, Any]] = None
    is_materialized: bool = False

    def __post_init__(self):
        self.object_type = "CanonicalView"
        if self.name and not self.identity.source_identifier:
            self.identity = CanonicalIdentity(source_identifier=f"CanonicalView:{self.schema_name}.{self.name}")
        else:
            super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "schema_name": self.schema_name,
            "definition_expression": self.definition_expression,
            "is_materialized": self.is_materialized,
        })
        return d


@dataclass
class CanonicalSchema(CanonicalObject):
    tables: List[CanonicalTable] = field(default_factory=list)
    views: List[CanonicalView] = field(default_factory=list)

    def __post_init__(self):
        self.object_type = "CanonicalSchema"
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "tables": [t.to_dict() for t in self.tables],
            "views": [v.to_dict() for v in self.views],
        })
        return d
