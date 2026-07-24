"""
AKAAL Platform 7 — Alert Deduplicator.
"""

from typing import List, Set
from akaal.operational_reliability.domain.models import ReliabilityAlert


class AlertDeduplicator:
    """Deduplicates duplicate alerts generated during rapid incident cascades."""

    def deduplicate_alerts(self, alerts: List[ReliabilityAlert]) -> List[ReliabilityAlert]:
        seen_keys: Set[str] = set()
        deduped: List[ReliabilityAlert] = []

        for alert in alerts:
            key = f"{alert.service_id}:{alert.summary}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(alert)

        return deduped
