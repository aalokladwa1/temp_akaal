"""akaalEngine.intelligence.producers.portfolio
==================================================
P7C.22 -- Portfolio, Reporting & Executive Intelligence. Authorizes BEFORE
aggregating: the canonical migration listing is already tenant-scoped at the
SQL level (never "aggregate everything, filter after"), and each per-migration
health read reuses the SAME tenant-enforcing P7C.13 resolver -- a migration
this tenant cannot access can never appear, structurally, not by a
post-hoc filter. Bounded: the underlying listing is paginated (limit/offset),
never an unbounded full-table scan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)

MAX_PORTFOLIO_PAGE_SIZE = 100


@dataclass(frozen=True)
class PortfolioMigrationSummary:
    migration_id: str
    overall_status: str
    dimensions: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"migration_id": self.migration_id, "overall_status": self.overall_status, "dimensions": dict(self.dimensions)}


@dataclass(frozen=True)
class PortfolioInputs:
    """Bundled, ALREADY tenant-scoped per-migration health summaries -- this
    producer performs zero discovery/aggregation of its own beyond counting
    what it was handed. `next_cursor`, when not None, is an opaque token the
    caller passes back as `parameters['cursor']` on the next request to
    continue the SAME deterministically-ordered (migration_id ASC) listing --
    real continuation, not silent truncation (owner-review Blocker 13)."""

    tenant_id: str
    migrations: List[PortfolioMigrationSummary] = field(default_factory=list)
    next_cursor: Optional[str] = None


PortfolioResolver = Callable[[IntelligenceRequest, IntelligenceContext], PortfolioInputs]


def make_portfolio_producer(resolver: PortfolioResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Portfolio resolver returned no PortfolioInputs. Refusing to fabricate a "
                "portfolio view with no canonical facts."
            )

        counts: dict = {}
        at_risk: List[str] = []
        for m in inputs.migrations:
            counts[m.overall_status] = counts.get(m.overall_status, 0) + 1
            if m.overall_status in ("CRITICAL", "BOTTLENECKED", "NOT_READY"):
                at_risk.append(m.migration_id)

        has_more = inputs.next_cursor is not None
        summary = (
            f"Portfolio for tenant {inputs.tenant_id!r}: {len(inputs.migrations)} migration(s) evaluated"
            + (" (more available -- pass next_cursor to continue)" if has_more else "")
            + f", {len(at_risk)} at risk."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DERIVED_FACT,
            summary=summary,
            explanation=Explanation(
                summary="Every migration listed was already tenant-scoped by the canonical migration repository "
                "query before any per-migration health read ran -- no cross-tenant data was ever aggregated then "
                "filtered.",
                supporting_facts=[f"status_counts={counts}"],
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0,
                missing_information=(["More migrations exist beyond this page -- pass next_cursor to continue, never silently dropped."] if has_more else []),
            ),
            data={
                "tenant_id": inputs.tenant_id,
                "status_counts": counts,
                "at_risk_migration_ids": at_risk,
                "migrations": [m.to_dict() for m in inputs.migrations],
                "next_cursor": inputs.next_cursor,
                "truncated": has_more,
            },
        )

    return producer
