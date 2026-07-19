"""
Akaal — Advisory Aggregation Engine
===================================
Deduplicates, resolves conflicts, ranks, prioritizes, and orders recommendations deterministically.
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple

from akaal.advisor.models.advisory_enums import (
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisorySeverity,
)
from akaal.advisor.models.advisory_manifest import AdvisoryManifest
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation


class AdvisoryAggregationEngine:
    """Enterprise Aggregation Engine for Recommendation Processing."""

    @classmethod
    def aggregate(
        cls,
        raw_recommendations: List[AdvisoryRecommendation],
        plan_id: str,
        plan_checksum: str,
        advisory_id: str = "ADV-001",
    ) -> Tuple[AdvisoryManifest, Tuple[AdvisoryRecommendation, ...]]:
        """
        Deduplicate, resolve conflicts, sort deterministically, and build manifest.
        Pure and deterministic.
        """
        # 1. Deduplication by SHA-256 fingerprint hash (keep highest severity/priority instance)
        dedup_map: Dict[str, AdvisoryRecommendation] = {}
        for rec in raw_recommendations:
            fp = rec.fingerprint
            if fp not in dedup_map:
                dedup_map[fp] = rec
            else:
                existing = dedup_map[fp]
                # Keep recommendation with higher priority (lower rank) or higher severity (lower rank)
                if (rec.priority.rank, rec.severity.rank) < (existing.priority.rank, existing.severity.rank):
                    dedup_map[fp] = rec

        unique_recs = list(dedup_map.values())

        # 2. Deterministic multi-key sort: Priority -> Severity -> Category -> ID
        sorted_recs = sorted(
            unique_recs,
            key=lambda r: (
                r.priority.rank if hasattr(r.priority, "rank") else AdvisoryPriority(r.priority).rank,
                r.severity.rank if hasattr(r.severity, "rank") else AdvisorySeverity(r.severity).rank,
                r.category.value if hasattr(r.category, "value") else str(r.category),
                r.recommendation_id,
            ),
        )

        # 3. Build summary statistics
        summary_by_category: Dict[str, int] = {}
        summary_by_severity: Dict[str, int] = {}
        summary_by_priority: Dict[str, int] = {}

        for rec in sorted_recs:
            cat_key = rec.category.value if hasattr(rec.category, "value") else str(rec.category)
            sev_key = rec.severity.value if hasattr(rec.severity, "value") else str(rec.severity)
            prio_key = rec.priority.value if hasattr(rec.priority, "value") else str(rec.priority)

            summary_by_category[cat_key] = summary_by_category.get(cat_key, 0) + 1
            summary_by_severity[sev_key] = summary_by_severity.get(sev_key, 0) + 1
            summary_by_priority[prio_key] = summary_by_priority.get(prio_key, 0) + 1

        timestamp = datetime.now(timezone.utc).isoformat()

        manifest = AdvisoryManifest(
            advisory_id=advisory_id,
            plan_id=plan_id,
            plan_checksum=plan_checksum,
            total_recommendations=len(sorted_recs),
            summary_by_category=summary_by_category,
            summary_by_severity=summary_by_severity,
            summary_by_priority=summary_by_priority,
            creation_timestamp=timestamp,
        )

        return manifest, tuple(sorted_recs)
