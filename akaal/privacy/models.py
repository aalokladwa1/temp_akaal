"""
AKAAL Privacy, Masking & Tokenization Data Models
=================================================
Type-safe models for PrivacyPolicy, PrivacyRule, MaskingStrategy,
SensitivityClass, and CompiledPrivacyPolicy.
"""

from dataclasses import dataclass, field
import enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Set


class SensitivityClass(str, enum.Enum):
    PII = "PII"
    PHI = "PHI"
    PCI = "PCI"
    CREDENTIAL = "CREDENTIAL"
    FINANCIAL = "FINANCIAL"
    INTERNAL = "INTERNAL"
    CUSTOM = "CUSTOM"


class PrivacyStrategy(str, enum.Enum):
    STATIC_REDACT = "STATIC_REDACT"
    PARTIAL_MASK = "PARTIAL_MASK"
    HASH = "HASH"
    KEYED_PSEUDONYM = "KEYED_PSEUDONYM"
    TOKENIZE = "TOKENIZE"
    FORMAT_PRESERVING_MASK = "FORMAT_PRESERVING_MASK"
    NULLIFY = "NULLIFY"


@dataclass
class PrivacyRule:
    rule_id: str
    column_name: str
    strategy: PrivacyStrategy
    sensitivity_class: SensitivityClass = SensitivityClass.PII
    privacy_domain: Optional[str] = None
    key_id: Optional[str] = None
    salt: Optional[str] = None
    mask_char: str = "*"
    unmasked_length: int = 4
    replacement_value: Optional[str] = None
    priority: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "column_name": self.column_name,
            "strategy": self.strategy.value if isinstance(self.strategy, PrivacyStrategy) else str(self.strategy),
            "sensitivity_class": self.sensitivity_class.value if isinstance(self.sensitivity_class, SensitivityClass) else str(self.sensitivity_class),
            "privacy_domain": self.privacy_domain,
            "key_id": self.key_id,
            "salt": self.salt,
            "mask_char": self.mask_char,
            "unmasked_length": self.unmasked_length,
            "replacement_value": self.replacement_value,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrivacyRule":
        return cls(
            rule_id=data.get("rule_id", f"prule-{data.get('column_name')}"),
            column_name=data["column_name"],
            strategy=PrivacyStrategy(data.get("strategy", "STATIC_REDACT")),
            sensitivity_class=SensitivityClass(data.get("sensitivity_class", "PII")),
            privacy_domain=data.get("privacy_domain"),
            key_id=data.get("key_id"),
            salt=data.get("salt"),
            mask_char=data.get("mask_char", "*"),
            unmasked_length=int(data.get("unmasked_length", 4)),
            replacement_value=data.get("replacement_value"),
            priority=int(data.get("priority", 10)),
        )


@dataclass
class PrivacyPolicy:
    object_name: str
    rules: List[PrivacyRule] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_name": self.object_name,
            "version": self.version,
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrivacyPolicy":
        raw_rules = data.get("rules", [])
        rules = [PrivacyRule.from_dict(r) for r in raw_rules]
        return cls(
            object_name=data.get("object_name", "CUSTOMERS"),
            rules=rules,
            version=data.get("version", "1.0.0"),
        )


@dataclass
class CompiledPrivacyPolicy:
    object_name: str
    rules: List[PrivacyRule]
    fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_name": self.object_name,
            "rules": [r.to_dict() for r in self.rules],
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def compute_fingerprint(cls, object_name: str, rules: List[PrivacyRule]) -> str:
        sorted_rules = sorted(rules, key=lambda r: (r.priority, r.column_name))
        rule_dicts = [r.to_dict() for r in sorted_rules]
        raw_json = json.dumps({"object_name": object_name, "rules": rule_dicts}, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
