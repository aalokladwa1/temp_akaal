"""
Akaal — Storage Recommendation Advisor
======================================
Generates scored, ranked suggestions targeting indexes, partition plans,
and tablespace segment optimizations.
"""

from typing import List, Tuple

from akaal.core.comparison.models import Schema
from akaal.core.intelligence.common.models import (
    Recommendation,
    RecommendationScore,
    RecommendationReport,
    ReportMetadata,
)
from akaal.core.intelligence.storage_optimization.models import StorageProjection
from akaal.core.intelligence.common.models import StorageReport


class StorageRecommendationAdvisor:
    """Evaluates sizing estimations and generates prioritized storage suggestions."""
    def generate_recommendations(
        self,
        schema: Schema,
        report: StorageReport
    ) -> List[Recommendation]:
        """Scans database estimates and emits structured recommendations."""
        recommendations: List[Recommendation] = []

        for table in schema.tables:
            tbl_alloc = report.allocations.get(table.name)
            if not tbl_alloc:
                continue

            tbl_size = tbl_alloc["total_size_kb"]
            data_size = tbl_alloc["data_size_kb"]
            idx_size = tbl_alloc["index_size_kb"]
            avg_row_len = tbl_alloc["avg_row_len_bytes"]

            # 1. Recommendation for missing partitioning on large tables
            if tbl_size > 100 * 1024:  # > 100MB
                has_partitioning = any("PARTITION" in idx.name.upper() or "PART" in idx.name.upper() for idx in table.indexes)
                if not has_partitioning:
                    score = RecommendationScore(
                        confidence=0.95,
                        priority=8,
                        estimated_benefit=0.85,
                        implementation_complexity=3,
                        migration_risk=2,
                        rationale=f"Table '{table.name}' is {tbl_size} KB. Range partitioning by transaction date will isolate historical logs and improve query scans."
                    )
                    recommendations.append(Recommendation(
                        recommendation_id=f"rec:storage:part:{table.name}",
                        title=f"Partition Table '{table.name}'",
                        description=f"Implement RANGE/HASH partition scheme on large table '{table.name}' to optimize segment storage.",
                        target_object_path=f"tables.{table.name}",
                        score=score
                    ))

            # 2. Recommendation for high index overhead
            # Suggest index compression or merging if index size > data size
            if idx_size > data_size and data_size > 1024:
                score = RecommendationScore(
                    confidence=0.85,
                    priority=6,
                    estimated_benefit=0.75,
                    implementation_complexity=2,
                    migration_risk=1,
                    rationale=f"Index size ({idx_size} KB) exceeds table data footprint ({data_size} KB). Compression will reduce leaf block overhead."
                )
                recommendations.append(Recommendation(
                    recommendation_id=f"rec:storage:idx_comp:{table.name}",
                    title=f"Compress Indices on '{table.name}'",
                    description=f"Enable key block index compression or consolidate redundant indices on table '{table.name}'.",
                    target_object_path=f"tables.{table.name}",
                    score=score
                ))

            # 3. Recommendation for row size limits
            if avg_row_len > 2048:  # Row size > 2KB
                score = RecommendationScore(
                    confidence=0.90,
                    priority=7,
                    estimated_benefit=0.80,
                    implementation_complexity=4,
                    migration_risk=3,
                    rationale=f"Average row length {avg_row_len} bytes is wide. Storing large string segments out-of-line will optimize data blocks cache efficiency."
                )
                recommendations.append(Recommendation(
                    recommendation_id=f"rec:storage:lob_out:{table.name}",
                    title=f"Relocate Large Segments of '{table.name}' Out-of-Line",
                    description=f"Configure target LOB/TEXT columns to store out-of-line in dedicated tablespaces.",
                    target_object_path=f"tables.{table.name}",
                    score=score
                ))

        return recommendations
