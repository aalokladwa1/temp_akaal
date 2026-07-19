"""
AKAAL Enterprise Intelligence Governance Package
=================================================
Re-exports EnterpriseIntelligenceGovernance and governance exceptions.
"""

from akaal.intelligence.governance.enterprise_intelligence_governance import (
    EnterpriseIntelligenceGovernance,
    EnterpriseIntelligenceGovernanceError,
)

__all__ = [
    "EnterpriseIntelligenceGovernance",
    "EnterpriseIntelligenceGovernanceError",
]
