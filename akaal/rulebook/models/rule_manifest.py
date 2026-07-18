"""
Akaal — Rule Manifest Model
===========================
Rulebook manifest artifact tracking rulebook version, pack versions, applied rules, and checksums.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List


@dataclass
class RuleManifest:
    manifest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rulebook_version: str = "1.0.0"
    pack_versions: Dict[str, str] = field(default_factory=dict)
    applied_rule_ids: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    policy_checksum: str = ""
    ruleset_checksum: str = ""

    def compute_ruleset_checksum(self, ruleset_dict: Dict[str, Any]) -> str:
        s = json.dumps(ruleset_dict, sort_keys=True)
        self.ruleset_checksum = hashlib.sha256(s.encode("utf-8")).hexdigest()
        return self.ruleset_checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "rulebook_version": self.rulebook_version,
            "pack_versions": self.pack_versions,
            "applied_rule_ids": self.applied_rule_ids,
            "timestamp": self.timestamp,
            "policy_checksum": self.policy_checksum,
            "ruleset_checksum": self.ruleset_checksum,
        }
