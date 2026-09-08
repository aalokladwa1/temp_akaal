"""akaalPipeline.observability.portfolio_resolver
====================================================
P7C.22 canonical resolver: lists this tenant's OWN migrations via the
canonical, already tenant-scoped akaalPipeline.state.repositories.
MigrationRepositoryPort.list_all(tenant_id=...) (never a caller-supplied
tenant), then reuses the SAME CanonicalRuntimeHealthResolver.resolve per
migration (P7C.13) to get each one's health -- never a second health
computation. Bounded to MAX_PORTFOLIO_PAGE_SIZE, never a full unbounded scan.
"""

from __future__ import annotations

from typing import Any, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.portfolio import (
    MAX_PORTFOLIO_PAGE_SIZE,
    PortfolioInputs,
    PortfolioMigrationSummary,
)
from akaalEngine.intelligence.producers.runtime_health import make_runtime_health_producer
from akaalPipeline.observability.runtime_health_resolver import CanonicalRuntimeHealthResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalPortfolioResolver:
    def __init__(self, repository: Any, health_resolver: CanonicalRuntimeHealthResolver) -> None:
        self._repository = repository
        self._health_resolver = health_resolver

    def resolve(
        self,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
        limit: int = MAX_PORTFOLIO_PAGE_SIZE,
        cursor: Optional[str] = None,
    ) -> PortfolioInputs:
        limit = max(1, min(limit, MAX_PORTFOLIO_PAGE_SIZE))
        tenant_id = actor.organization_id

        # Cursor is an opaque offset into the SAME deterministic
        # (migration_id ASC) canonical ordering the repository already uses
        # -- a caller cannot skip ahead into another tenant's rows because
        # the WHERE tenant_id=... clause still applies to every page.
        try:
            offset = max(0, int(cursor)) if cursor is not None else 0
        except (TypeError, ValueError):
            offset = 0

        # Canonical, tenant-scoped listing -- the WHERE clause enforces
        # tenant scope BEFORE any per-migration health read runs (authorize
        # before aggregate, never aggregate-then-filter).
        aggregates = self._repository.list_all(tenant_id=tenant_id, limit=limit + 1, offset=offset)
        has_more = len(aggregates) > limit
        aggregates = aggregates[:limit]
        next_cursor = str(offset + limit) if has_more else None

        summaries = []
        for agg in aggregates:
            health_inputs = self._health_resolver.resolve(agg.migration_id, actor, ownership_manager=ownership_manager)
            health_producer = make_runtime_health_producer(lambda _req, _ctx, hi=health_inputs: hi)
            probe_request = IntelligenceRequest(
                task=IntelligenceTask.QUERY, tenant_id=tenant_id, subject_type="migration",
                subject_id=agg.migration_id, subject_version="v1", requested_by="p7c22-internal",
                capability="runtime_health",
            )
            probe_context = IntelligenceContext(
                tenant_id=tenant_id, subject_type="migration", subject_id=agg.migration_id, subject_version="v1",
            )
            health_result = health_producer(probe_request, probe_context)
            summaries.append(
                PortfolioMigrationSummary(
                    migration_id=agg.migration_id,
                    overall_status=str(health_result.data.get("overall_status", "UNKNOWN")),
                    dimensions=health_result.data.get("dimensions", {}),
                )
            )

        return PortfolioInputs(tenant_id=tenant_id, migrations=summaries, next_cursor=next_cursor)
