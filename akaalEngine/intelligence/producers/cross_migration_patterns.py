"""akaalEngine.intelligence.producers.cross_migration_patterns
================================================================
Cross-migration pattern intelligence (P7C brief §P7C.9 "Cross-migration
patterns" / §14 item 28). Real, deterministic frequency analysis over prior
finding codes across a tenant's migration history -- e.g. "14 previous
Oracle->PostgreSQL migrations shared the same LOB issue."

Permanent invariant enforced here (P7C brief): historical similarity != proof.
Every pattern surfaced by this producer is tagged EpistemicType.INFERENCE, never
FACT or DIAGNOSIS -- it may support a recommendation, but it can never override
a current, migration-specific canonical fact (see akaalEngine.intelligence.
knowledge.trust: T1 canonical derived facts always outrank a T5-adjacent
historical inference).

Data sourcing is injected, not owned: this module never queries the
IntelligenceArtifactStore itself (producers only ever see (request, context),
not a live db connection) -- the caller/orchestrator supplies each prior
migration's finding codes via request.parameters['prior_migration_findings'],
exactly the same "caller supplies canonical data, producer only computes"
discipline already used by every other Campaign B producer in this package.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Mapping, Sequence

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)


def detect_recurring_finding_patterns(
    migration_findings: Mapping[str, Sequence[str]], *, min_occurrences: int = 3
) -> List[Dict[str, object]]:
    """migration_findings: migration_id -> list of finding codes observed for
    that migration (e.g. from prior P7C.7 ASSESS artifacts). Returns patterns
    (finding_code, occurrence_count, migration_ids) for any code appearing in at
    least `min_occurrences` DISTINCT migrations, sorted by occurrence_count desc
    then code asc for determinism."""
    if min_occurrences < 2:
        raise IntelligenceValidationError("min_occurrences must be >= 2 for a pattern to be meaningful.")

    code_to_migrations: Dict[str, set] = defaultdict(set)
    for migration_id, codes in migration_findings.items():
        for code in codes:
            code_to_migrations[code].add(migration_id)

    patterns = [
        {"finding_code": code, "occurrence_count": len(mig_ids), "migration_ids": sorted(mig_ids)}
        for code, mig_ids in code_to_migrations.items()
        if len(mig_ids) >= min_occurrences
    ]
    patterns.sort(key=lambda p: (-p["occurrence_count"], p["finding_code"]))
    return patterns


def make_cross_migration_pattern_producer():
    """IntelligenceKernel-compatible producer. request.parameters:
      - prior_migration_findings: Mapping[migration_id, list[finding_code]] (required)
      - min_occurrences: int, default 3
    """

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        migration_findings = request.parameters.get("prior_migration_findings")
        if not migration_findings:
            raise IntelligenceValidationError(
                "Cross-migration pattern analysis requires request.parameters['prior_migration_findings']."
            )
        min_occurrences = int(request.parameters.get("min_occurrences", 3))

        patterns = detect_recurring_finding_patterns(migration_findings, min_occurrences=min_occurrences)

        findings = [
            DiagnosticFinding(
                code=f"PATTERN:{p['finding_code']}",
                severity="MEDIUM",
                message=f"Finding {p['finding_code']!r} recurred across {p['occurrence_count']} prior migrations.",
                evidence_refs=list(p["migration_ids"]),
            )
            for p in patterns
        ]

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.INFERENCE,
            summary=f"{len(patterns)} recurring finding pattern(s) detected across {len(migration_findings)} prior "
            f"migration(s) (threshold >= {min_occurrences} occurrences).",
            explanation=Explanation(
                summary="Deterministic frequency analysis over caller-supplied prior finding codes. A recurring "
                "pattern is INFERENCE, not FACT -- it may support a recommendation for the current migration but "
                "never overrides that migration's own canonical assessment facts.",
                supporting_facts=[f"migrations_analyzed={len(migration_findings)}", f"patterns_found={len(patterns)}"],
                assumptions=["historical similarity is not proof of the current migration's actual state"],
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0,
                source_freshness="historical",
                missing_information=["current migration's own canonical assessment, if not separately supplied"],
            ),
            findings=findings,
            data={"patterns": patterns},
        )

    return producer
