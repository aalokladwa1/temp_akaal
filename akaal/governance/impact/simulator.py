"""
AKAAL Platform 6 — Governance Policy Change Simulator.
"""

from typing import Dict, Any, List
from akaal.governance.domain.models import EnterprisePolicy


class PolicyChangeSimulator:
    """Simulates workflow execution and approval volume under modified policy rules."""

    def simulate_policy_execution(self, policy: EnterprisePolicy, sample_workload: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_sample = len(sample_workload)
        if total_sample == 0:
            return {"pass_count": 0, "fail_count": 0, "pass_rate_pct": 100.0}

        fail_count = 0
        for sample in sample_workload:
            if "FORBID_DESTRUCTIVE" in policy.declarative_rule and sample.get("is_destructive"):
                fail_count += 1

        pass_count = total_sample - fail_count
        pass_rate = round((pass_count / total_sample) * 100.0, 2)

        return {
            "total_simulated": total_sample,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate_pct": pass_rate,
        }
