"""
Akaal — Rule Model & Metadata
=============================
Core Rule dataclass with lifecycle management, provenance tracking, capability requirements.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class RuleLifecycleState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class RuleProvenance(str, Enum):
    VENDOR_PACK = "VENDOR_PACK"
    ORGANIZATION_POLICY = "ORGANIZATION_POLICY"
    PROJECT_OVERRIDE = "PROJECT_OVERRIDE"
    MIGRATION_OVERRIDE = "MIGRATION_OVERRIDE"
    CUSTOM_RULE = "CUSTOM_RULE"
    EXTERNAL_PLUGIN = "EXTERNAL_PLUGIN"


class RuleCategory(str, Enum):
    VENDOR = "VENDOR"
    NAMING = "NAMING"
    CONVERSION = "CONVERSION"
    COMPLIANCE = "COMPLIANCE"
    CONSTRAINT = "CONSTRAINT"
    TRANSFORMATION = "TRANSFORMATION"
    SECURITY = "SECURITY"


class RuleScope(str, Enum):
    GLOBAL = "GLOBAL"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    MIGRATION = "MIGRATION"
    DATABASE = "DATABASE"
    SCHEMA = "SCHEMA"
    TABLE = "TABLE"
    COLUMN = "COLUMN"


@dataclass
class RuleCapabilityMetadata:
    supported_engines: List[str] = field(default_factory=lambda: ["*"])
    supported_versions: List[str] = field(default_factory=lambda: ["*"])
    required_scout_features: List[str] = field(default_factory=list)
    required_discovery_sections: List[str] = field(default_factory=list)
    minimum_rulebook_version: str = "1.0.0"
    maximum_rulebook_version: str = "99.9.9"
    feature_flags: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supported_engines": self.supported_engines,
            "supported_versions": self.supported_versions,
            "required_scout_features": self.required_scout_features,
            "required_discovery_sections": self.required_discovery_sections,
            "minimum_rulebook_version": self.minimum_rulebook_version,
            "maximum_rulebook_version": self.maximum_rulebook_version,
            "feature_flags": self.feature_flags,
        }


@dataclass
class Rule:
    """Core enterprise Rule model."""
    rule_id: str
    name: str
    description: str
    category: RuleCategory
    scope: RuleScope = RuleScope.GLOBAL
    priority: int = 100
    version: str = "1.0.0"
    author: str = "Akaal Subsystem"
    
    lifecycle_state: RuleLifecycleState = RuleLifecycleState.ACTIVE
    provenance: RuleProvenance = RuleProvenance.VENDOR_PACK
    capability_metadata: RuleCapabilityMetadata = field(default_factory=RuleCapabilityMetadata)
    
    prerequisites: List[str] = field(default_factory=list)  # rule_ids that must precede this rule
    conditions: Dict[str, Any] = field(default_factory=dict)
    action_payload: Dict[str, Any] = field(default_factory=dict)

    approved_by: Optional[str] = "System Administrator"
    approved_timestamp: Optional[str] = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deprecated_timestamp: Optional[str] = None
    retirement_timestamp: Optional[str] = None

    def is_active_or_deprecated(self) -> bool:
        return self.lifecycle_state in (RuleLifecycleState.ACTIVE, RuleLifecycleState.DEPRECATED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "scope": self.scope.value,
            "priority": self.priority,
            "version": self.version,
            "author": self.author,
            "lifecycle_state": self.lifecycle_state.value,
            "provenance": self.provenance.value,
            "capability_metadata": self.capability_metadata.to_dict(),
            "prerequisites": self.prerequisites,
            "conditions": self.conditions,
            "action_payload": self.action_payload,
            "approved_by": self.approved_by,
            "approved_timestamp": self.approved_timestamp,
            "deprecated_timestamp": self.deprecated_timestamp,
            "retirement_timestamp": self.retirement_timestamp,
        }
