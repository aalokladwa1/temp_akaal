# Current Phase: Phase 9 — Intelligence Subsystems & Rulebook Platform

---

## 🎯 Goal
To implement the autonomous intelligence subsystem layer of Akaal, incorporating **Scout Platform (Features 1–8)** for read-only database profiling and **Rulebook Platform (Feature 9)** as the enterprise policy decision engine converting `DiscoveryReport` objects into canonical, immutable, versioned `MigrationRuleSet` documents.

---

## 📈 Overall Progress
- **Status**: Phase 9 Scout Platform & Rulebook Platform Complete
- **Phase Completion**: 45% (Scout Platform and Rulebook Platform fully implemented, certified, tested with 274+ unit tests, and documented)
- **Sprint Iteration**: Sprint 2 (Phase 9 Intelligence Layer — Rulebook Platform)

---

## ✅ Completed Features
* **Rulebook Platform Subsystem (`akaal/rulebook/`)**: Built an enterprise policy decision engine decoupled from SQL generation and migration execution.
* **Immutable Context & Execution Trace (`RuleEvaluationContext`, `RuleExecutionTrace`)**: Standardized context object and deterministic execution trace recording all stage decisions and evaluation latencies.
* **Passive Registries & Provider Isolation (`RuleRegistry`, `RulePackRegistry`, `BaseRuleProvider`)**: Plugin interface for built-in (PostgreSQL, MySQL, Oracle, SQL Server, MongoDB, Generic) and external rule packs.
* **Decoupled Single-Responsibility Engine Sequence**:
  - `DependencyGraph`: DAG dependency resolution, topological sorting, and cycle detection.
  - `RuleResolutionEngine`: Candidate rule matching for target database engines.
  - `ValidationEngine`: Lifecycle state machine (`DRAFT`..`RETIRED`) and capability validation.
  - `PriorityEngine`: Scope precedence & priority score ordering.
  - `ConflictEngine`: Conflict detection & structured enterprise diagnostics (`RuleDiagnostic`).
  - `InheritanceEngine`: Deterministic 8-level policy hierarchy evaluation (`Global` → `Organization` → `Project` → `Migration` → `Database` → `Schema` → `Table` → `Column`).
  - `SimulationEngine`: Dry-run evaluation producing `SimulationReport`.
* **Single Immutable Public Output (`MigrationRuleSet`)**: Versioned, checksum-protected output document consumed exclusively by downstream modules (Decoder, Risk, Planner, Advisor, Enterprise Intelligence).
* **Architecture Decision Record**: Authored `docs/adr/ADR-010_rulebook_platform_architecture.md`.

---

## 📋 Remaining Features
1. **Schema Decoder (Feature 10)**: Deep AST parsing for stored procedures, triggers, and DDL object structures.
2. **Risk Assessor (Feature 11)**: Automated migration risk scoring and bottleneck prediction.
3. **Migration Planner (Feature 12)**: Topological parallel chunk scheduler.
4. **Advisory Subsystem (Feature 13)**: Autonomous target database sizing recommendations.
