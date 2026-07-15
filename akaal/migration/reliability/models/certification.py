from dataclasses import dataclass

@dataclass(frozen=True)
class CertificationRuleSpec:
    rule_id: str
    description: str
    compliance_standard: str
