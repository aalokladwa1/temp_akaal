"""
Akaal — Enterprise Risk Taxonomy
================================
Hierarchical enterprise risk taxonomy model: RiskDomain -> RiskCategory -> RiskType -> RiskItem.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class RiskDomain(str, Enum):
    COMPATIBILITY = "COMPATIBILITY"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"
    OPERATIONAL = "OPERATIONAL"
    DATA_INTEGRITY = "DATA_INTEGRITY"
    SEMANTIC = "SEMANTIC"
    AVAILABILITY = "AVAILABILITY"
    SCALABILITY = "SCALABILITY"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class RiskCategory(str, Enum):
    DATATYPE = "DATATYPE"
    CONSTRAINT = "CONSTRAINT"
    FUNCTION = "FUNCTION"
    INDEX = "INDEX"
    LOB = "LOB"
    THROUGHPUT = "THROUGHPUT"
    LATENCY = "LATENCY"
    DOWNTIME = "DOWNTIME"
    MEMORY = "MEMORY"
    STORAGE = "STORAGE"
    DEPENDENCY_CYCLE = "DEPENDENCY_CYCLE"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    SEMANTIC_DRIFT = "SEMANTIC_DRIFT"


class RiskType(str, Enum):
    OPAQUE_TYPE = "OPAQUE_TYPE"
    PRECISION_LOSS = "PRECISION_LOSS"
    SCALE_LOSS = "SCALE_LOSS"
    NULLABILITY_SHIFT = "NULLABILITY_SHIFT"
    MISSING_INDEX = "MISSING_INDEX"
    UNSUPPORTED_FUNCTION = "UNSUPPORTED_FUNCTION"
    UNSUPPORTED_CONSTRAINT = "UNSUPPORTED_CONSTRAINT"
    LONG_RUNNING_TRANSACTION = "LONG_RUNNING_TRANSACTION"
    HIGH_LOB_VOLUME = "HIGH_LOB_VOLUME"
    HIGH_DEPENDENCY_DEPTH = "HIGH_DEPENDENCY_DEPTH"
    CAPABILITY_UNSUPPORTED = "CAPABILITY_UNSUPPORTED"
    SEMANTIC_PARTIAL_MAPPING = "SEMANTIC_PARTIAL_MAPPING"


@dataclass
class RiskTaxonomyNode:
    domain: RiskDomain
    category: RiskCategory
    type: RiskType

    def to_dict(self) -> Dict[str, str]:
        return {
            "domain": self.domain.value,
            "category": self.category.value,
            "type": self.type.value,
        }
