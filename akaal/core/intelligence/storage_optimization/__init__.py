"""
Akaal — Storage Optimization Subsystem
======================================
Exposes storage layout analyzers, partition optimization validators,
scored recommendation advisors, and placement registries.
"""

import abc
from akaal.core.comparison.models import Schema
from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.models import StorageReport


class IStorageAnalyzer(abc.ABC):
    """Abstract interface defining the tablespace allocations and partition specifications calculations."""
    @abc.abstractmethod
    def analyze_storage_layout(self, schema: Schema, target_dialect: SystemType) -> StorageReport:
        pass


from akaal.core.intelligence.storage_optimization.models import (
    TablespaceAllocation,
    PartitionStrategy,
    StorageProjection,
    StorageConstraint,
)
from akaal.core.intelligence.storage_optimization.analyzer import StorageLayoutAnalyzer
from akaal.core.intelligence.storage_optimization.validator import StorageLayoutValidator
from akaal.core.intelligence.storage_optimization.recommendation import StorageRecommendationAdvisor
from akaal.core.intelligence.storage_optimization.registry import StorageRuleMetadata, StorageRulesRegistry
from akaal.core.intelligence.storage_optimization.report import StorageReportBuilder

__all__ = [
    "IStorageAnalyzer",
    "TablespaceAllocation",
    "PartitionStrategy",
    "StorageProjection",
    "StorageConstraint",
    "StorageLayoutAnalyzer",
    "StorageLayoutValidator",
    "StorageRecommendationAdvisor",
    "StorageRuleMetadata",
    "StorageRulesRegistry",
    "StorageReportBuilder",
]
