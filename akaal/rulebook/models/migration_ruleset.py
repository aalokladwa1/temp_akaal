"""
Akaal — Migration RuleSet Model
===============================
Canonical, versioned, immutable output document produced by Rulebook Platform.
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MigrationRuleSet:
    """
    Immutable, versioned, checksum-protected MigrationRuleSet artifact.
    Single public output consumed by downstream intelligence modules.
    """
    schema_version: str = "1.0.0"
    ruleset_version: str = "1.0.0"
    generator_version: str = "rulebook-1.0.0"
    ruleset_signature: str = "AKAAL-RULEBOOK-SIG-V1"
    sha256_checksum: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)
    vendor_rules: List[Dict[str, Any]] = field(default_factory=list)
    naming_rules: List[Dict[str, Any]] = field(default_factory=list)
    conversion_rules: List[Dict[str, Any]] = field(default_factory=list)
    compliance_rules: List[Dict[str, Any]] = field(default_factory=list)
    constraint_rules: List[Dict[str, Any]] = field(default_factory=list)
    transformation_rules: List[Dict[str, Any]] = field(default_factory=list)
    security_rules: List[Dict[str, Any]] = field(default_factory=list)

    inheritance_summary: Dict[str, Any] = field(default_factory=dict)
    rule_manifest: Dict[str, Any] = field(default_factory=dict)
    rule_metrics: Dict[str, Any] = field(default_factory=dict)
    audit_trail: Dict[str, Any] = field(default_factory=dict)
    execution_trace_summary: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def compute_sha256_checksum(self) -> str:
        d = self.to_dict()
        d.pop("sha256_checksum", None)
        canonical = json.dumps(d, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "ruleset_version": self.ruleset_version,
            "generator_version": self.generator_version,
            "ruleset_signature": self.ruleset_signature,
            "sha256_checksum": self.sha256_checksum,
            "metadata": self.metadata,
            "vendor_rules": self.vendor_rules,
            "naming_rules": self.naming_rules,
            "conversion_rules": self.conversion_rules,
            "compliance_rules": self.compliance_rules,
            "constraint_rules": self.constraint_rules,
            "transformation_rules": self.transformation_rules,
            "security_rules": self.security_rules,
            "inheritance_summary": self.inheritance_summary,
            "rule_manifest": self.rule_manifest,
            "rule_metrics": self.rule_metrics,
            "audit_trail": self.audit_trail,
            "execution_trace_summary": self.execution_trace_summary,
            "diagnostics": self.diagnostics,
        }
        if not res["sha256_checksum"]:
            canonical = json.dumps(res, sort_keys=True)
            res["sha256_checksum"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return res

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
