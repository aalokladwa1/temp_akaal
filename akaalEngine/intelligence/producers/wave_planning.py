"""akaalEngine.intelligence.producers.wave_planning
=====================================================
P7C.9 -- Dependency, Wave & Portfolio Optimization. Wraps the REAL existing graph
algorithms:
  - akaalEngine.schema.dependency.graph.MultiDomainDependencyGraph
  - akaalEngine.schema.dependency.cycle_breaker.CycleBreaker
  - akaalEngine.schema.dependency.sorter.TopologicalSorter

No LLM guesses dependency order here (P7C brief §P7C.9): wave assignment is a
deterministic longest-path layering over the canonical dependency graph -- a node's
wave index is one more than the maximum wave index of its prerequisites, so nodes
in the same wave have no dependency relationship and can run in parallel.

Portfolio intelligence reads canonical migration state (here: a caller-supplied
mapping of migration_id -> dependency graph) rather than creating a second
migration lifecycle -- it never mutates or owns migration state itself.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Mapping, Tuple

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)
from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter


def compute_waves(graph: MultiDomainDependencyGraph) -> Dict[str, int]:
    """Deterministic longest-path layering: wave[node] = 0 if it has no
    (in-graph) prerequisites, else 1 + max(wave[p] for p in prerequisites).
    Computed over the topologically sorted node order so every prerequisite's
    wave is already known before its dependents are processed."""
    order = TopologicalSorter.sort(graph)
    order_index = {nid: i for i, nid in enumerate(order)}
    waves: Dict[str, int] = {}
    for nid in order:
        prereqs = [p for p in graph.adj_list.get(nid, ()) if p in graph.nodes]
        # Only count a prerequisite that genuinely precedes this node in the
        # deterministic order -- guards against a residual cycle edge (SCC
        # members) from creating an infinite/incoherent wave dependency.
        safe_prereqs = [p for p in prereqs if order_index[p] < order_index[nid]]
        waves[nid] = 0 if not safe_prereqs else 1 + max(waves[p] for p in safe_prereqs)
    return waves


def group_by_wave(waves: Mapping[str, int]) -> List[List[str]]:
    groups: Dict[int, List[str]] = defaultdict(list)
    for nid, w in waves.items():
        groups[w].append(nid)
    return [sorted(groups[w]) for w in sorted(groups.keys())]


def detect_shared_object_contention(migration_graphs: Mapping[str, MultiDomainDependencyGraph]) -> Dict[str, List[str]]:
    """Real, deterministic portfolio-level contention detection: which schema
    objects (node_ids) are referenced by more than one migration's dependency
    graph. Reads canonical per-migration graphs; creates no second migration
    lifecycle or shared-state authority."""
    node_owners: Dict[str, List[str]] = defaultdict(list)
    for migration_id, graph in migration_graphs.items():
        for nid in graph.nodes:
            node_owners[nid].append(migration_id)
    return {nid: sorted(owners) for nid, owners in node_owners.items() if len(owners) > 1}


def make_wave_planning_producer(schema_model_resolver):
    """IntelligenceKernel-compatible producer. `schema_model_resolver(request,
    context)` must return a CanonicalSchemaModel -- this producer performs no
    discovery of its own."""

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        model = schema_model_resolver(request, context)
        raw_graph = MultiDomainDependencyGraph.build_from_model(model)
        sccs = TopologicalSorter.detect_scc(raw_graph)
        pruned_graph = CycleBreaker.break_fk_cycles(raw_graph)
        waves = compute_waves(pruned_graph)
        wave_groups = group_by_wave(waves)

        findings = [
            DiagnosticFinding(
                code="DEPENDENCY:CIRCULAR_GROUP",
                severity="MEDIUM",
                message=f"Circular dependency group of {len(scc)} objects requires deferred FK application.",
                evidence_refs=scc,
            )
            for scc in sccs
        ]

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DERIVED_FACT,
            summary=f"Computed {len(wave_groups)} migration wave(s) across {len(pruned_graph.nodes)} schema objects "
            f"({len(sccs)} circular dependency group(s) detected and deferred).",
            explanation=Explanation(
                summary="Deterministic longest-path layering over MultiDomainDependencyGraph "
                "(Kahn's algorithm topological order + Tarjan's SCC cycle detection).",
                supporting_facts=[f"total_objects={len(pruned_graph.nodes)}", f"wave_count={len(wave_groups)}", f"cycle_groups={len(sccs)}"],
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
            findings=findings,
            data={
                "wave_groups": wave_groups,
                "circular_dependency_groups": sccs,
                "parallelizable_group_sizes": [len(g) for g in wave_groups],
            },
        )

    return producer


def make_portfolio_contention_producer(migration_graphs_resolver):
    """IntelligenceKernel-compatible producer for portfolio-level contention.
    `migration_graphs_resolver(request, context)` returns Mapping[migration_id,
    MultiDomainDependencyGraph] for the migrations in scope -- this producer
    never discovers or constructs that state itself."""

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        migration_graphs = migration_graphs_resolver(request, context)
        contention = detect_shared_object_contention(migration_graphs)

        findings = [
            DiagnosticFinding(
                code="PORTFOLIO:SHARED_OBJECT_CONTENTION",
                severity="MEDIUM" if len(owners) == 2 else "HIGH",
                message=f"Schema object {node_id!r} is referenced by {len(owners)} concurrently-scoped migrations.",
                evidence_refs=owners,
            )
            for node_id, owners in sorted(contention.items())
        ]

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DERIVED_FACT,
            summary=f"Portfolio contention analysis across {len(migration_graphs)} migration(s): "
            f"{len(contention)} shared schema object(s) detected.",
            explanation=Explanation(
                summary="Derived by intersecting each migration's own canonical dependency graph node set.",
                supporting_facts=[f"migrations_in_scope={sorted(migration_graphs.keys())}"],
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
            findings=findings,
            data={"shared_object_contention": contention},
        )

    return producer
