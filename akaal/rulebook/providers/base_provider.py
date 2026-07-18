"""
Akaal — Base Rule Provider Interface
====================================
Passive RuleProvider plugin interface for Rulebook rule packs.
Providers supply rules and metadata passively without executing engines.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from akaal.rulebook.models.rule import Rule


class BaseRuleProvider(ABC):
    """Abstract RuleProvider plugin interface."""

    provider_id: str = "base_provider"
    provider_name: str = "Base Rule Provider"
    provider_version: str = "1.0.0"
    target_engine: str = "GENERIC"

    @abstractmethod
    def rules(self) -> List[Rule]:
        """Return list of rules exposed by this provider."""

    def metadata(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "target_engine": self.target_engine,
            "rule_count": len(self.rules()),
        }

    def version(self) -> str:
        return self.provider_version

    def checksum(self) -> str:
        rule_ids = [r.rule_id for r in self.rules()]
        raw = f"{self.provider_id}:{self.provider_version}:{','.join(sorted(rule_ids))}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def validate(self) -> bool:
        return True
