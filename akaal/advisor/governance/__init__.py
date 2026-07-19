"""
Akaal — Advisor Governance Package
==================================
Re-exports AdvisorGovernance and AdvisorGovernanceError.
"""

from akaal.advisor.governance.advisor_governance import (
    AdvisorGovernance,
    AdvisorGovernanceError,
)

__all__ = ["AdvisorGovernance", "AdvisorGovernanceError"]
