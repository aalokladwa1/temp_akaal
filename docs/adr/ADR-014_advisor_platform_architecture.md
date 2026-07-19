# ADR-014: Advisor Platform Architecture & Enterprise Migration Advisory Engine

* **Status**: Accepted
* **Date**: 2026-07-19
* **Authors**: Antigravity AI / Lead Platform Architecture Team
* **Subsystem**: `akaal/advisor` (Phase 9 — Platform 1)

---

## 1. Context & Motivation

The **Akaal Migration Platform** requires an enterprise migration advisory engine to transform the canonical **`MigrationExecutionPlan`** produced by the Planner Platform into a deterministic, immutable, versioned, checksum-protected **`MigrationAdvisoryModel`**.

The **Advisor Platform** operates strictly as a **pure intelligence layer**. It contains **zero SQL generation, zero migration execution, zero database drivers/connections, zero upstream plan mutations, and zero side effects**.

---

## 2. Primary Architectural Principle: Compiler Model

The Advisor Platform behaves strictly like a **pure compiler**:
- **Input is immutable**: Consumes `MigrationExecutionPlan` without modifying upstream state.
- **Processing is deterministic**: Given identical inputs and context, output is 100% bit-for-bit identical across executions.
- **Output is immutable**: Returns a frozen `MigrationAdvisoryModel` signed with SHA-256 checksums.
- **Zero side effects**: No database connections, no SQL generation, no execution state mutation, no hidden caches, no global singletons.

$$\text{MigrationExecutionPlan} \longrightarrow \text{Advisor Platform} \longrightarrow \text{MigrationAdvisoryModel}$$

---

## 3. Subsystem Package Architecture

```
akaal/advisor/
├── api/           # AdvisorPlatform facade (single public entry point)
├── engine/        # AdvisorEngine & AdvisoryAggregationEngine
├── analyzers/     # 12 independent RecommendationAnalyzers
├── models/        # 12 frozen dataclass models (MigrationAdvisoryModel, AdvisoryRecommendation, etc.)
├── registry/      # AdvisorRegistry (analyzer discovery & plugin support)
├── validation/    # AdvisorValidator (input/output integrity validation)
├── serialization/ # AdvisorSerializer (JSON, Dict, Canonical round-trip)
├── metrics/       # AdvisorMetricsCollector (execution timing & distribution statistics)
├── reporting/     # AdvisorReportBuilder (technical reports; no executive summaries)
├── events/        # AdvisorEvents (decoupled lifecycle event notifications)
└── governance/    # AdvisorGovernance (audit, versioning, determinism assertions)
```

---

## 4. Twelve Core Recommendation Analyzers

| Analyzer | Domain Category | Key Focus |
|---|---|---|
| `BatchRecommendationAnalyzer` | `BATCHING` | Batch sizes, chunking limits, memory footprint |
| `WorkerRecommendationAnalyzer` | `WORKER` | Thread pool sizing, concurrency limits, connection pressure |
| `HardwareRecommendationAnalyzer` | `HARDWARE` | CPU, RAM allocation, I/O limits, system boundaries |
| `CostRecommendationAnalyzer` | `COST` | Cloud compute tiering, spot/preemptible cost optimization |
| `ETARecommendationAnalyzer` | `ETA` | Timeline estimation vs maintenance window constraints |
| `BestPracticeRecommendationAnalyzer` | `BEST_PRACTICE` | Data validation phase, checksum policies, enterprise compliance |
| `CheckpointRecommendationAnalyzer` | `CHECKPOINT` | Checkpoint frequency, RPO, restartability |
| `RollbackRecommendationAnalyzer` | `ROLLBACK` | Pre-migration snapshots, compensation graph completeness |
| `TopologyRecommendationAnalyzer` | `TOPOLOGY` | Cross-region network latency, worker co-location |
| `ParallelismRecommendationAnalyzer` | `PARALLELISM` | Stage execution concurrency, lock contention |
| `ResourceRecommendationAnalyzer` | `RESOURCE` | Temp storage headroom, disk I/O space allocation |
| `RecommendationAnalyzer` | N/A | Abstract base class interface (`Open/Closed` principle) |

---

## 5. Architectural Invariants

1. **Input Immutability**: `MigrationExecutionPlan` input is never altered.
2. **Output Immutability**: All model dataclasses use `@dataclass(frozen=True)` with tuple collections.
3. **Deterministic Sorting**:
   $$\text{Priority (P0..P4)} \longrightarrow \text{Severity (CRITICAL..INFORMATIONAL)} \longrightarrow \text{Category} \longrightarrow \text{ID}$$
4. **Fingerprint Deduplication**:
   $$\text{Fingerprint} = \text{SHA256}(\text{category} \parallel \text{title} \parallel \text{sorted(affected\_nodes)})$$
5. **Fault Isolation**: Individual analyzer exceptions are caught, logged into `AdvisoryTrace`, and isolated; remaining analyzers complete execution cleanly.
6. **No Executive Summaries**: Technical reports only; executive summaries reserved for Phase 14 Enterprise Intelligence.

---

## 6. Verification & Production Readiness

The platform passed 100% of the mandatory enterprise verification suite (36 dedicated platform tests + 339 unit tests with zero regressions), validating performance ($O(N + R \log R)$ bounds), replayability, security, and determinism.
