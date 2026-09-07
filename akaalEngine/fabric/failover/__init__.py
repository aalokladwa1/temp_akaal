"""P7B.28 -- Disaster Recovery & Geo Failover (composed over P7B.24/25 + Group-2 placement)."""

from akaalEngine.fabric.failover.coordinator import attempt_failover
from akaalEngine.fabric.failover.models import FailoverOutcome, FailoverResult

__all__ = ["attempt_failover", "FailoverOutcome", "FailoverResult"]
