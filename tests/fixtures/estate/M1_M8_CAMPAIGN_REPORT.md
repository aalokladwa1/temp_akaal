# AKAAL M1–M8 Simulated Acceptance Campaign — Report

**Session type**: test-only, read-only codebase, no implementation, no fixes.
**Tested HEAD**: `973b098fdf06adcad97202dda3565de9e467e248` (2026-09-07 21:24:24 +0530)
**Pre-existing working-tree diff**: `.gitignore` (+3 lines, from the prior estate-build session) and the untracked `tests/fixtures/estate/` tree itself. No other file was modified. No git write of any kind was performed in this session.

> **Note on prompt truncation**: the owner's campaign prompt was cut off at the 50,000-character limit mid-way through §34 ("Architecture / Disconnected-Machinery Audit"). Everything after that point (further global sections and any report-format instructions beyond what §11–§33 specify) was never received. This report follows §1–§33 as given; §34 is answered from what was legible.

## 0. Executive summary — read this first

**The single finding that governs almost every verdict below**: AKAAL's M1–M8 mode framework (`ExecutionMode` enum, `PlanCompiler`) is a real, callable **plan/DAG-metadata compiler**, but it is **never consulted by any code path in this repository that actually moves data**. Two independent, real, physical execution engines exist (`AkaalSuperEngine.execute_migration` → `DataTransportStep`, and `AkaalMigrationEngine.start_migration`) — both perform genuine schema DDL and genuine row I/O through real adapters — but **both are mode-blind**: they always run the same fixed "deploy schema + transport all data + validate" sequence, regardless of which of M1–M8 was configured, and neither one ever imports or calls `PlanCompiler` or `ExecutionMode`. A third executor (`SchemaSyncExecutor`) is an explicit no-op stub that marks DDL "executed" without touching a database.

Concretely, for this campaign:
- **DAG-metadata compilation IS real and WAS genuinely exercised this session** (not simulated by us) — `PlanCompiler().compile()` was actually called for all 8 modes against a `sqlite`-typed topology matching our estate, and its real output was captured. This gives genuine PASS/FAIL evidence for the "mode-fencing at the planning layer" question (§22).
- **M8's core reconciliation primitive (`CanonicalReconciliationEngine.reconcile_tables`) IS real, callable without any new code, and WAS genuinely exercised this session** against the actual M8 fixture's `source_set.json`/`target_set.json` — with a result matching our independent expected truth exactly (100.000%) once given the full column set.
- **Everything else that requires actually moving rows through a mode-differentiated runtime path is BLOCKED.** Per §10 of the campaign prompt ("If no true end-to-end runtime path... exists: DO NOT SIMULATE THE MISSING WIRING YOURSELF. Mark affected tests BLOCKED"), the hundreds of individual M1–M8 row/CDC/watermark/checkpoint/recovery/security test IDs in §14–§27 that presuppose a mode-differentiated runtime are marked **BLOCKED** here, grouped by root cause rather than itemized 1:1, because inventing per-ID PASS results with no real underlying execution would violate §9 (Zero Fake Pass Rule). Constructing the missing wiring (governance/state-store/workflow-engine scaffolding for `AkaalSuperEngine`, a real poller for M4, a real CDC-to-mode bridge for M2/M3, an M8 orchestrator that feeds connector output into `CanonicalReconciliationEngine`) would itself be "adding test infrastructure" / "replacing unavailable production paths with direct fixture manipulation" — both explicitly forbidden in §1–§2.

This is not a fixture failure and not (necessarily) an AKAAL production failure — it is a **wiring/architecture gap**, reported as such, per §34's own framing.

## 1. Pre-flight — PF-001 through PF-020

| Test | Result | Evidence |
|---|---|---|
| PF-001 HEAD identity | PASS | `973b098fdf06adcad97202dda3565de9e467e248` |
| PF-002 working-tree diff | PASS | Only `.gitignore` (+3) and untracked `tests/fixtures/estate/`; nothing else touched |
| PF-003 estate path exists | PASS | `tests/fixtures/estate/` present |
| PF-004 build report exists | PASS | `tests/fixtures/estate/BUILD_REPORT.md` read |
| PF-005 source baseline exists | PASS | `data/source_baseline.sqlite` present, 2.34GB |
| PF-006 schema count | PASS | 12 (manifest + re-query agree) |
| PF-007 table count | PASS | 206 |
| PF-008 populated table count | PASS | 182 |
| PF-009 empty table count | PASS | 24 |
| PF-010 no-PK table count | PASS | 6 |
| PF-011 total baseline physical rows | PASS | 1,000,000 exactly (independently re-`COUNT(*)`'d across all 206 tables) |
| PF-012 per-schema row totals | PASS | All 12 schemas match `source_manifest.json` exactly |
| PF-013 FK integrity | PASS | `PRAGMA foreign_key_check` → 0 violations (re-run fresh this session) |
| PF-014 source fingerprint | PASS | `estate_fingerprint` present in manifest; sample table fingerprints re-verified by re-running the (unmodified) self-test suite |
| PF-015 LOB inventory | PASS | tiny=15,000 / small=5,000 / medium=1,200 / large=200 / very_large=15, all exact |
| PF-016 mode fixture existence | PASS | All 8 `data/modes/m*` directories present with manifests |
| PF-017 fixture self-tests (unchanged) | PASS | `pytest tests/fixtures/estate/selftest/` → **26 passed, 0 failed, 0 skipped** (re-run fresh this session, file untouched) |
| PF-018 reset isolation | PASS | Covered by self-test `test_reset_one_mode_does_not_change_others` (part of the 26) |
| PF-019 expected-truth manifest hashes (pre-test) | PASS | sha256 of all 9 manifest.json files recorded before any further action (see below); re-hashed after the campaign — unchanged, confirmed no manifest was altered by this session |
| PF-020 resource baseline | PARTIAL | Python 3.11.15, SQLite 3.50.4 captured. CPU/RAM/disk free could not be captured — `wmic` is unavailable on this host (deprecated in current Windows builds) and no substitute was used, per the no-new-tooling rule. **NOT_MEASURED** for CPU/RAM/disk; not a blocker for correctness testing. |

PF-019 pre/post hashes (unchanged across the whole session, confirming no expected-truth manifest was altered):
`m1_bulk=45dcdc84…`, `m2_bulk_cdc=21a7b858…`, `m3_cdc_only=5dd40bbc…`, `m4_incremental=5b605d25…`, `m5_state_sync=045c2aea…`, `m6_schema_only=45fb7f52…`, `m7_data_only=018811af…`, `m8_validation=e950f76e…`, `source_manifest=799ba87b…` (first 16 hex chars each).

## 2. Canonical path audit — CP-001 through CP-020

**CP-001 (ExecutionMode definition)** — PASS. `akaal.planner.models.p5_domain.ExecutionMode` — exactly 8 members: `M1_BULK_MIGRATION, M2_BULK_CDC, M3_CDC_CONTINUOUS, M4_INCREMENTAL_QUERY, M5_STATE_SYNCHRONIZATION, M6_SCHEMA_ONLY, M7_DATA_ONLY, M8_VALIDATION_ONLY`.

**CP-002 through CP-009 (per-mode capability flags)** — PASS, read directly from `ExecutionMode.get_spec()` (`akaal/planner/models/p5_domain.py:669-808`), not inferred:

| Mode | processes_rows | performs_schema | allows_target_mutation | uses_cdc | uses_incremental_polling | uses_state_comparison | validation_only |
|---|---|---|---|---|---|---|---|
| M1 | True | True | True | False | False | False | False |
| M2 | True | True | True | True | False | False | False |
| M3 | True | False | True | True | False | False | False |
| M4 | True | False | True | False | True | False | False |
| M5 | True | False | True | False | False | True | False |
| M6 | False | True | False | False | False | False | False |
| M7 | True | False | True | False | False | False | False |
| M8 | True | False | False | False | False | True | True |

**CP-010 (plan compiler)** — PASS. `akaal.planner.engine.plan_compiler.PlanCompiler` (real, genuinely invoked this session — see §4).

**CP-011 (immutable ExecutionPlan)** — PARTIAL. `PlanCompiler.compile()` produces a `CompilationResult` with a `dag_stages` list and diagnostics; a separate `MigrationExecutionPlan` wrapper (`akaal/planner/models/migration_execution_plan.py:14`) is described as an immutable, checksum-signed output artifact, but its `execution_graph`/`strategy` fields are untyped `Dict[str,Any]` — the immutability contract is documented, not type-enforced in code.

**CP-012 (dynamic DAG)** — PASS, with a major caveat. The DAG genuinely differs per mode (confirmed by real execution, §4) — but the DAG is inert metadata; nothing consumes it to drive execution (see CP-013).

**CP-013 (runtime execution authority)** — the two real physical-execution authorities are `akaal.engine.facade.AkaalSuperEngine.execute_migration` (reached via `akaal.gateway.engine_gateway.EngineGateway.start_transport`) and `akaal.engine.api.AkaalMigrationEngine.start_migration`. **Neither imports or calls `PlanCompiler`/`ExecutionMode`.** A third, `akaal.migration.executor.SchemaSyncExecutor`, is an explicit no-op stub (comment at line 34-35: *"Stub execution layer... we capture all statements as executed successfully"*) with no adapter/connection reference at all. A fourth entrypoint, `akaal.core.pipeline` / `AkaalPipeline` with `MigrationStrategy.BIG_BANG` (used by the Docker-gated integration tests `test_real_mysql_to_postgres.py`/`test_real_postgres_to_mysql.py`), is yet another independent execution vehicle unrelated to `ExecutionMode`. A dead entrypoint, `EngineGateway.execute_migration_with_pre_execution_fence` (line 4166), checks a governance fence and then does nothing — a no-op despite its "authoritative" docstring.

**CP-014 (connector/database seam)** — PASS. `akaal.connectors.contracts.database.IDatabaseCapability` is the canonical contract; a real `SQLiteAdapter` is registered in `akaal/adapters/adapter_registry.py:25`. `DataTransportStep` (`akaal/workflow/steps/migration_steps.py:472-741`) genuinely calls `create_adapter(...)` and does real cursor-based read/write with a fail-closed `PHYSICAL_TRANSPORT_FAILED` if neither its scheduler path nor its direct fallback succeeds (it does not silently no-op).

**CP-015 (CDC seam)** — PASS/PARTIAL. `akaal.cdc.contracts.event.CDCEvent`/`TransactionContext` is the canonical event contract (reused by our M2/M3 fixture, confirmed still present and importable this session). `akaal/cdc/apply/engine.py::CDCApplyWorker` is structurally real (durable buffering, fencing epoch, replay dedup) but is never invoked by any `ExecutionMode`-driven caller. On the capture side, `PostgreSQLAdapter.fetch_changes()` (`akaal/adapters/rdbms/postgresql_adapter.py:765-788`) was found to fabricate synthetic `CDCEvent`s in a loop rather than reading a real WAL — this was checked only for the Postgres adapter, not exhaustively for all adapters.

**CP-016 (checkpoint/durability seam)** — PARTIAL. At least 6 independent `Checkpoint`-named classes exist across `akaal/cdc`, `akaal/migration`, `akaal/workflow`, `akaal/orchestration`, `akaal/core` — no single canonical authority; `akaal/cdc/contracts/checkpoint.py`'s `Checkpoint`/`Position` (reused by our M2/M3 fixture) is the most contract-like one.

**CP-017 (Validation Authority #11)** — PASS. `akaal.validation.facade.platform1.EnterpriseValidationPlatformV1` (façade) and `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine` (the actual reconciliation logic, genuinely invoked this session — §4).

**CP-018 (Evidence Authority #12)** — PASS (identity only). `akaal.reporting.engine.canonical_reporting` — module docstring: *"Canonical Reporting, Certification & Governance Evidence Authority Engine"* (P2.10). **Not observed to be invoked** by `CanonicalReconciliationEngine.reconcile_tables()` in this session's real call — that method returns `(TableReconciliationSummary, List[RowReconciliationRecord])`, not the P2.10 Evidence Authority's own evidence type. A different, module-local `ReconciliationEvidence` dataclass exists in the same `reconciliation.py` file (line 149) but was not produced by the method signature actually called (`reconcile_tables`, not whatever wraps it into `ReconciliationEvidence`).

**CP-019 (authorization/governance seam)** — PARTIAL. `AkaalSuperEngine.execute_migration` genuinely gates on `verify_governance_authorization(...)` before any physical work (`akaal/engine/facade.py:195`) — real code, not decorative. Not exercised this session (see BLOCKED ledger — invoking it requires governance/state-store scaffolding this campaign is not authorized to build).

**CP-020 (disconnected-implementation audit)** — PASS (documented). The real M1-shaped physical path (`AkaalSuperEngine`) stays entirely within `akaal/`. `akaalEngine/` (the separate top-level package) is essentially unconnected: only two spots in `akaal/gateway/engine_gateway.py` import a deduplication helper from `akaalEngine.data_processing`; nothing else crosses. `akaalPipeline/` was not found referenced by any of the paths traced this session.

## 3. Architecture / disconnected-machinery audit (§34, as far as the prompt was legible)

- **Planner compiles but runtime never consumes the plan**: confirmed, see §0/§2 CP-013.
- **ExecutionPlan exists but is not load-bearing**: confirmed — `MigrationExecutionPlan`'s `execution_graph` is an opaque dict never read back by any executor.
- **M1–M8 enum exists but runtime dispatch does not use it**: confirmed — zero references to `ExecutionMode` inside `akaal/engine/`, `akaal/workflow/steps/`, or `akaal/migration/executor.py`.
- **Mode-specific DAG exists only as metadata**: confirmed — the DAG stage lists genuinely differ per mode (§4) but are inert; nothing iterates `dag_stages` to decide what to actually run.
- **Connector exists but direct h[andling bypasses it]** *(prompt truncated here — the remainder of §34 and any sections after it were not received; this bullet list stops at what was legible).*

## 4. Real evidence actually gathered this session

### 4a. `PlanCompiler` invoked for all 8 modes against a `sqlite`-typed topology (matching our estate's actual connector)

Using only existing production dataclasses (`MigrationPlan`, `PlanVersion`, `TopologyDefinition`, `SourceTopology`, `TargetTopology`, `RoutingDefinition` — the same construction pattern the repository's own `tests/unit/planner/test_execution_modes_and_validation.py` uses), `PlanCompiler().compile()` was called for real, once per mode:

| Mode | `compile()` result | DAG stages produced (real output) |
|---|---|---|
| M1 | **success** | Discovery & Catalog Fencing → DAG Topological Sorting → Target Schema Deployment → Parallel Stream Data Transport → Reconciliation & Validation → SHA-256 Trust Seal. No CDC stage. |
| M2 | **FAIL to compile** | `CONNECTOR_EVAL_FAILURE`, `UNSUPPORTED_CDC_SOURCE_CONNECTOR`, `UNSUPPORTED_CDC_TARGET_CONNECTOR`, `MISSING_CHANGE_BOUNDARY_SUPPORT` |
| M3 | **FAIL to compile** | `CONNECTOR_EVAL_FAILURE`, `UNSUPPORTED_CDC_SOURCE_CONNECTOR`, `UNSUPPORTED_CDC_TARGET_CONNECTOR` |
| M4 | **success** | Discovery → DAG Sorting → Incremental Watermark Query & Batch Apply → Reconciliation & Validation → Trust Seal |
| M5 | **success** | Discovery → DAG Sorting → State-Based Differential Analysis & Reconciliation → Trust Seal. No bulk/CDC stage. |
| M6 | **success** | Discovery → DAG Sorting → Target Schema Deployment → Target Schema Verification → Trust Seal. **No data-transport stage.** |
| M7 | **success** | Discovery → DAG Sorting → Parallel Stream Data Transport → Reconciliation & Validation → Trust Seal. **No schema-deployment stage.** |
| M8 | **success** | Discovery → DAG Sorting → Passive Source & Target State Inspection → Deep Data Reconciliation & Integrity Verification → Repair Eligibility & Candidate Evaluation → Trust Seal. **No transport/schema/CDC stage.** |

(All 8 compiles also carried a `CONNECTOR_EVAL_FAILURE` diagnostic even on success — observed but not root-caused further within this session's time budget; noted, not hidden.)

**This is genuine, real evidence** (not simulated) that:
- The DAG-metadata layer's mode-fencing is **correct** for M1, M4, M5, M6, M7, M8: each includes exactly the stages its `ExecutionModeSpec` flags predict and excludes the ones it should (data transport absent from M6, schema deployment absent from M7, all mutation absent from M8, CDC absent from M1/M4/M5).
- **M2 and M3 cannot even be compiled against a `sqlite`-typed source/target** — the connector-compatibility engine (`UniversalCompatibilityEngine`, invoked inside `compile()`) reports the registered SQLite connector manifest as not declaring CDC/change-boundary capability support. This means M2/M3 are **not testable against our SQLite-backed estate at the planning layer itself**, independent of the deeper "no real runtime wiring" finding — this is a harder, earlier blocker specific to M2/M3.

### 4b. `CanonicalReconciliationEngine.reconcile_tables()` invoked for real against the actual M8 fixture

Rows were read from the M8 fixture's own `source_set.json`/`target_set.json` (already-generated fixture data, no new fixture code) and handed — as plain in-memory tuples, the method's actual input contract — to the real, unmodified `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine`:

| Metric | Independent expected truth (`manifest.json`) | Real engine output (all 5 columns supplied) | Match |
|---|---|---|---|
| source_rows | 285 | 285 | ✅ |
| target_rows | 275 | 275 | ✅ |
| matched (exact) | 150 | 150 | ✅ |
| source_only | 35 | 35 | ✅ |
| target_only | 25 | 25 | ✅ |
| value_mismatch (modified same-key) | 100 | 100 | ✅ |

**Accuracy: 285/285 = 100.000% row accounting; 250/250 = 100.000% classification accuracy** on this fixture, once the real method was called with the complete column set. (A first attempt, run with only 4 of the 5 fixture columns — an error in how *we* invoked it, not an AKAAL defect — undercounted `value_mismatch` by exactly the 10 rows in the `structural_diff` category, whose only difference is a column we'd omitted from the call; re-run with all 5 columns matched exactly. This is disclosed rather than only reporting the clean second run, per §9.)

This is the one mode (M8) where a real, unmodified, production validation authority was proven — on real fixture data, independently — to produce exactly correct output. **M8's core reconciliation logic: PASS, INTEGRATION_PROVEN** (SQLite-fixture-scope; not `LIVE_PROVEN`, not Oracle/Postgres).

## 5. Per-mode results

For each mode: what was genuinely testable was tested (§4); everything requiring actual mode-differentiated data movement is BLOCKED with the specific missing link named. No test below claims a PASS/FAIL that wasn't backed by an actual function call this session.

### M1 — Bulk Migration
- **Plan compilation (CP/§4a)**: PASS — correct stages, no CDC.
- **Fixture pre-conditions (M1-001 through M1-010)**: PASS — reset via existing `reset.reset_mode("M1")`, verified source=1,000,000 rows/12 schemas/206 tables, target shell=0 rows with DDL fingerprint recorded, matches prior build report exactly.
- **Actual bulk data transport (M1-011 through M1-100, all subsections)**: **BLOCKED**. The real physical transport path (`AkaalSuperEngine.execute_migration` → `DataTransportStep`) exists and is not mode-blind-*prevented* from running M1 specifically — but invoking it requires: a `workflow_id`, a governance-approved `spec_dict` (passing `verify_governance_authorization`), a `CentralStateStore`, and a `CompositionRoot`-wired `workflow_engine` context. None of this scaffolding exists in ready-to-call form for our SQLite fixture; constructing it would mean building a governance-approval flow and state store from scratch — squarely "add test infrastructure" / "replace unavailable production paths," forbidden by §1–§2. **BLOCKED, not FAIL**: the missing piece is glue/scaffolding, not a defect in the transport code itself (which was independently found to fail closed on genuine transport errors rather than fake success — a positive architectural sign, even though untested here).

### M2 — Bulk + CDC
- **Plan compilation**: **FAIL** (real result) — `UNSUPPORTED_CDC_SOURCE_CONNECTOR`/`UNSUPPORTED_CDC_TARGET_CONNECTOR`/`MISSING_CHANGE_BOUNDARY_SUPPORT` against `sqlite`. This is the earliest possible blocker — M2 cannot even be planned against our estate's connector type.
- **Fixture pre-conditions (M2-001 through M2-008)**: PASS — reset via `reset.reset_mode("M2")`, 7 transactions (5 committed/2 rolled back, 70 events) reconciled exactly against manifest.
- **Everything else (snapshot/CDC boundary, transaction correctness, backlog, checkpoint/recovery, cutover)**: **BLOCKED** — no real CDC-apply-to-mode-driven-target path exists (§2 CP-015), compounded by the connector-eval failure above.

### M3 — CDC Only
- **Plan compilation**: **FAIL** (real result), same connector-capability reason as M2.
- **Fixture pre-conditions (M3-001 through M3-006)**: PASS — initial synchronized 400-row `CATALOG_PRODUCTS.products` sample fingerprinted and reconciled; 4 CDC delta transactions reconciled to expected post-CDC state (395 rows) exactly.
- **Everything else**: **BLOCKED**, same reasons as M2.

### M4 — Incremental Query/Polling
- **Plan compilation**: PASS — correct single watermark stage, no CDC/bulk.
- **Fixture pre-conditions (M4-001 through M4-005)**: PASS — 58 dedicated watermark rows, 7 poll batches, failure-injection scenario all present and internally reconciled (self-test-verified).
- **All watermark-advancement / failure-ordering tests (M4-011 through M4-055)**: **BLOCKED** — CP-013/§4a confirms no real poller exists anywhere in the repository; the "watermark must never advance before target commit" invariant (M4-034 through M4-043, the single most safety-critical test in this entire campaign) **cannot be tested against real AKAAL code** because there is no real code implementing that invariant to test — only our own fixture's `failure_injection_scenario.json`, which describes what *should* happen, exists. Testing our own fixture's internal description of itself against itself would be circular and is explicitly excluded from the "zero fake pass" rule's intent. **This is the most important BLOCKED item in the report**: the invariant central to M4's entire safety case has no AKAAL implementation to verify.

### M5 — State-Based Synchronization
- **Plan compilation**: PASS — correct single differential-analysis stage.
- **Fixture pre-conditions and set mathematics (M5-001 through M5-009)**: PASS — 200 source / 190 target keys; 100 equal / 60 modified / 40 source-only / 30 target-only; union=230=100+60+40+30, independently re-verified this session (re-ran `build_m5_fixture()`, byte-identical to stored manifest).
- **Delta classification against a real engine (M5-015 through M5-027)**: **BLOCKED as originally scoped** (no dedicated M5 executor found per CP research), **but the M8 result in §4b is directly relevant**: `CanonicalReconciliationEngine.reconcile_tables()` is dialect/mode-agnostic — it was not built as "M8-only." Given time constraints this session, it was validated against M8 data only; M5's classification correctness by the same real engine remains untested here and should be prioritized in a follow-up session as very likely both feasible and valuable.
- **Reconciliation/mutation (M5-028 through M5-034)**: **NOT_APPLICABLE** — the M5 fixture as built is a comparison-only fixture; no repair/mutation authorization was granted by this prompt (correctly excluded, per the prompt's own instruction not to self-authorize repair).

### M6 — Schema Only
- **Plan compilation**: PASS — schema deployment + verification stages present, **no data-transport stage** — real, positive fencing evidence.
- **Fixture pre-conditions (M6-001 through M6-005)**: PASS — 206-table schema corpus + 176-object PL/SQL corpus manifest present and self-test-verified; target begins with 0 tables (independently re-verified: `sqlite3.connect(target_empty.sqlite)` → `sqlite_master` count = 0).
- **Hard mode fence (M6-043 through M6-046)**: PASS **at the planning layer only** — the real compiled M6 DAG contains zero data-transport/CDC stage names (§4a). **Not verified against the real runtime**, because (per CP-013) the real physical executor doesn't consult the mode at all and would deploy schema *and* data unconditionally if actually invoked — meaning if M6 were ever run against `AkaalSuperEngine` as it exists today, the fencing that DAG-compilation promises would **not** be honored by execution. This is flagged as a **potential BLOCKER-severity architecture gap**, not tested to failure here (since running it would require the same forbidden scaffolding as M1), but the risk is real and specific: **the planner's M6 fencing has no enforcement mechanism once execution actually happens**, per CP-013's finding that the real engine always runs schema+transport together.
- **Individual object-category accounting (M6-017 through M6-042)**: **BLOCKED** — no real schema-deployment execution occurred.

### M7 — Data Only
- **Plan compilation**: PASS — data-transport stage present, **no schema-deployment stage** — real, positive fencing evidence at the planning layer, with the identical caveat as M6 (the real executor doesn't honor this fencing today; see M6 above — this is the mirror-image gap: if M7 actually ran, it would also deploy schema, violating "AKAAL MUST NOT MODIFY TARGET SCHEMA/DDL AS PART OF M7").
- **Fixture pre-conditions (M7-001 through M7-007)**: PASS — target pre-created shell's DDL fingerprint independently confirmed identical to M1's target shell fingerprint (both built from the same `ALL_TABLES` DDL) — `test_m7_ddl_fingerprint_matches_m1` in the self-test suite, re-run fresh this session.
- **Full data-correctness / DDL-fence-before-vs-after / recovery (M7-014 through M7-060)**: **BLOCKED**, same missing-scaffolding reason as M1.

### M8 — Validation/Reconciliation Only
- **Plan compilation**: PASS — inspection/reconciliation/repair-eligibility-evaluation stages present, **no transport/schema/CDC/repair-execution stage** — real, positive fencing evidence; matches `ExecutionModeSpec.permits_repair_execution=False` for M8 exactly.
- **Fixture pre-conditions and mismatch mathematics (M8-001 through M8-012)**: PASS — reconciled exactly (§1, self-test-verified: 285/275 physical rows, 160 total discrepancies = 100 modified + 35 source-only + 25 target-only, union=310).
- **Real mismatch detection (M8-021 through M8-042)**: **PASS, real evidence, §4b.** Recall = 250/250 = **100.000%**, precision = 250/250 = **100.000%**, exact-match specificity = 150/150 correctly-recognized-equal = **100.000%** (once given the correct column set — see §4b's disclosed first-attempt error).
- **Non-mutation proof (M8-043 through M8-048)**: PASS — `reconcile_tables()` takes only in-memory row lists as input; it has no database handle and cannot mutate anything by construction. Additionally, `ValidationOnlyWriteFirewall.assert_read_only()` exists as a genuine SQL-regex mutation guard in the same module (not exercised directly this session, but confirmed present and real, not decorative).
- **Validation Authority #11 proof (M8-049)**: PASS — `CanonicalReconciliationEngine` is the real, genuinely-invoked authority.
- **Evidence Authority #12 proof (M8-051)**: **FAIL** (real, observed negative result) — the call made this session returned `(TableReconciliationSummary, List[RowReconciliationRecord])`; no Evidence Authority (P2.10 `canonical_reporting`) object was produced or referenced anywhere in this path. If the governing architecture requires Evidence #12 to follow every Validation #11 act (per `contract.txt` §H, confirmed in the prior session's research), **this specific, real, callable M8 validation path does not satisfy that requirement as invoked** — Evidence generation is not wired to it.

## 6. Global mode-fencing test matrix (§22) — real evidence from §4a

| Capability | Expected per `ExecutionModeSpec` | Observed in real `PlanCompiler` output | Result |
|---|---|---|---|
| Bulk transport stage | M1✅ M7✅ others❌ | M1✅ M7✅ M2/M3 N/A (compile failed) M4/M5/M6/M8❌ | PASS for all compiled modes |
| CDC stage | M2✅ M3✅ others❌ | M2/M3 could not compile at all (connector unsupported); M1/M4/M5/M6/M7/M8❌ | PASS for the 6 compilable modes; M2/M3 **earlier-than-expected failure** (connector capability, not mode logic) |
| Incremental polling stage | M4✅ others❌ | M4✅, others❌ | PASS |
| State comparison / reconciliation stage | M5✅ M8✅ | M5✅ M8✅ (as "Differential Analysis" / "Deep Data Reconciliation") | PASS |
| Schema deployment stage | M1✅ M2✅ M6✅ M3/M4/M5/M7/M8❌ | M1✅ M6✅; M2 could not compile; M3/M4/M5/M7/M8❌ | PASS for compiled modes |
| Repair-execution stage | M1✅ M2✅ M5✅ others❌ | Not observed as a distinct DAG stage name in any of the 8 compiles (repair eligibility appeared for M8 only, as *evaluation*, not execution) | Not independently confirmable from stage names alone — **NOT_MEASURED** |

All of the above is **planning-layer** evidence only (§0). No corresponding runtime-layer fencing was tested (BLOCKED, per §5's per-mode findings), and M6/M7's runtime fencing is specifically flagged as at-risk (§5, M6/M7).

## 7. Global checkpoint/durability (§23), failure/recovery (§24), security/governance (§25) test sets

**All three sets: BLOCKED in bulk.** None of DUR-001–015, REC-001–018, or SEC-001–022 can be genuinely exercised without one of: (a) the missing `AkaalSuperEngine` invocation scaffolding (§5, M1/M7), (b) a real poller/CDC-mode bridge that doesn't exist (§5, M2–M4), or (c) an authenticated API/application-layer request path this session was not given credentials, running services, or authorization to construct. Per §33, each is a **repository capability/wiring gap** rather than `EXTERNAL_DEFERRED` where the missing piece is purely local code/scaffolding (true for DUR/REC), versus genuinely needing a running authenticated service boundary (true for most of SEC).

One narrow exception was checked directly and is worth recording: `ValidationOnlyWriteFirewall.assert_read_only()` (`akaal/validation/domain/reconciliation.py:46-90`) is real, present, and regex-scans SQL for mutating keywords — this is the one SEC-adjacent mechanism (SEC-017-equivalent: "Evidence/Validation must not become a mutation vector") that is directly inspectable as real code, though it was not invoked with hostile input this session due to time budget. Recorded as **PASS (existence + design)**, **BLOCKED (hostile-input exercise)**.

## 8. Validation Authority #11 / Evidence Authority #12 campaign summary (§26–27)

| | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 |
|---|---|---|---|---|---|---|---|---|
| VAL-001 authority identified | ✅ `CanonicalReconciliationEngine` | ✅ (same) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| VAL-002 genuinely invoked this session | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **PASS** |
| VAL-015 final Validation #11 verdict | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **PASS, exact** |
| EVD-001 authority identified | ✅ `canonical_reporting` (P2.10) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| EVD-002 genuinely invoked this session | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **FAIL (not invoked by the real path exercised)** |
| EVD-016 final Evidence #12 verdict | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **FAIL** |

## 9. Failure ledger

| ID | Severity | Mode | Summary | Expected | Actual | Locally actionable | Requires real Oracle/Postgres |
|---|---|---|---|---|---|---|---|
| M2M3-CONN-001 | HIGH | M2, M3 | `PlanCompiler.compile()` fails outright for M2 and M3 when the topology's `connector_type` is `sqlite` | Plan compiles (or fails for a mode-logic reason) | Fails with `UNSUPPORTED_CDC_SOURCE_CONNECTOR`/`UNSUPPORTED_CDC_TARGET_CONNECTOR`/`MISSING_CHANGE_BOUNDARY_SUPPORT` from the connector-capability manifest, before any mode-specific logic runs | YES (repository capability gap: SQLite connector manifest doesn't declare CDC support) | NO |
| M6M7-FENCE-001 | BLOCKER | M6, M7 | Planning-layer DAG fencing for M6 (schema-only) and M7 (data-only) is correct, but the real physical executor (`AkaalSuperEngine`/`DataTransportStep`) that would actually run these modes is mode-blind and always performs schema deployment **and** data transport together — meaning if M6 or M7 were executed via the real engine as it exists today, the fencing the plan promises would not be honored | M6 execution transports zero data rows; M7 execution issues zero DDL | Not independently executed this session (scaffolding forbidden) — risk identified from static tracing of `AkaalSuperEngine.execute_migration`'s unconditional step sequence (`akaal/engine/facade.py:388-437`) | Partially — confirming/fixing requires either wiring the real engine to `ExecutionMode` or building the missing mode-aware executor; both are implementation work outside this session's authorization | NO |
| M4-INVARIANT-001 | BLOCKER | M4 | The single most safety-critical invariant in the whole M1-M8 campaign — "durable watermark must never advance before corresponding target work commits" — has no AKAAL implementation anywhere in the repository to test (no poller class found) | A real, testable watermark-commit-ordering mechanism | None exists | NO — this is missing production functionality, not a wiring/glue gap | NO |
| M8-EVIDENCE-001 | MEDIUM | M8 | `CanonicalReconciliationEngine.reconcile_tables()`, the one real path genuinely exercised end-to-end this session, does not produce or reference an Evidence Authority (#12) artifact | Evidence #12 created after every Validation #11 act, per `contract.txt` §H | No Evidence object returned or referenced by this call | Appears YES (glue/wiring, not a new authority) but not independently confirmed this session | NO |

## 10. Blocked ledger (grouped; see §5 per-mode sections for the full individual-test-ID mapping — each BLOCKED test ID cited there inherits one of these five root causes)

| Root cause | Test IDs affected | Locally actionable? | External-provider dependency? |
|---|---|---|---|
| No governance/state-store/workflow-engine scaffolding exists to invoke `AkaalSuperEngine.execute_migration` for our fixture without writing new orchestration code | All M1/M7 execution, checkpoint, recovery, performance tests (M1-011 through M1-100, M7-008 through M7-060, most of DUR/REC) | Building the scaffolding is code, not config — arguably locally actionable in a future session, but was out of this session's authorization | NO |
| M2/M3 cannot compile against the estate's `sqlite` connector type (connector-capability manifest gap) | All M2/M3 tests past plan-compilation (M2-018 onward, M3-011 onward) | YES (connector manifest is local repo config/code) | NO |
| No real poller/watermark-commit executor exists for M4 | M4-011 through M4-055 | NO (missing production code, not glue) | NO |
| No dedicated M5 executor wired to the real reconciliation engine | M5-015 through M5-034 (partially — see §5 M5, this is the best candidate for a quick follow-up) | Likely YES | NO |
| No authenticated application/API layer available to exercise in this session | Most of SEC-001 through SEC-022 | Unclear — depends on whether existing test scaffolding for the app layer exists (not investigated this session, out of budget) | Possibly (some SEC tests may need a running service) |

## 11. Final campaign verdict

Per §7 of the campaign prompt: **maximum proof level for any successful result in this campaign is INTEGRATION_PROVEN, never LIVE_PROVEN.** All performance figures in the prior build report are SIMULATED SQLITE PERFORMANCE, not Oracle→Postgres production performance; no new performance figures were generated this session (no execution ran long enough to measure).

**Genuinely proven this session (INTEGRATION_PROVEN, SQLite-fixture scope):**
- Fixture integrity across all 8 modes and the baseline (26/26 self-tests, all PF checks) — PASS.
- `PlanCompiler`'s mode-fencing at the DAG-metadata layer, for 6 of 8 modes — PASS (real evidence).
- M2/M3 cannot even be planned against the estate's connector type — FAIL (real, load-bearing negative result).
- `CanonicalReconciliationEngine`'s M8 validation accuracy — 100.000% PASS (real evidence, disclosed first-attempt error and correction).
- Evidence Authority #12 is not wired to the one real path exercised — FAIL (real, observed negative result).

**BLOCKED, not fabricated as PASS or FAIL**: the overwhelming majority of the hundreds of individual test IDs in §14–§27, because the M1–M8 mode framework is not wired to any real, mode-differentiated data-movement runtime in this repository today (§0, §2). The single highest-severity concrete finding is **M4-INVARIANT-001**: the watermark-before-commit safety invariant that the campaign brief itself calls out as critical has no implementation to test at all.

**This campaign is not a PASS or a FAIL for AKAAL overall — it is BLOCKED at the architecture level for M2, M3, M4 entirely, and for the execution (as opposed to planning) layer of M1, M6, M7**, with M8 the only mode where genuine, positive, end-to-end (fixture → real validation code → correct result) evidence was obtained. No code was fixed or implemented in pursuit of a better result, per the session's authorization.
