"""
Akaal — Discovery Manifest Model
================================
Reproducibility, integrity verification, and audit manifest for Discovery Reports.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any


@dataclass
class DiscoveryManifest:
    """Manifest for verifying DiscoveryReport integrity and origin."""
    report_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    report_version: str = "1.0.0"
    fingerprint: str = ""
    provider_versions: Dict[str, str] = field(default_factory=dict)
    engine: str = "POSTGRESQL"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    report_checksum: str = ""
    discovery_profile: str = "STANDARD"
    policy_checksum: str = ""

    def compute_checksum(self, report_dict: Dict[str, Any]) -> str:
        """Compute deterministic SHA256 checksum over report structure."""
        report_str = json.dumps(report_dict, sort_keys=True)
        self.report_checksum = hashlib.sha256(report_str.encode("utf-8")).hexdigest()
        return self.report_checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_uuid": self.report_uuid,
            "report_version": self.report_version,
            "fingerprint": self.fingerprint,
            "provider_versions": self.provider_versions,
            "engine": self.engine,
            "timestamp": self.timestamp,
            "report_checksum": self.report_checksum,
            "discovery_profile": self.discovery_profile,
            "policy_checksum": self.policy_checksum,
        }
