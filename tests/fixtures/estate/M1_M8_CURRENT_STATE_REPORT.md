# M1–M8 CURRENT PHYSICAL STATE — RECONCILIATION REPORT (read-only, evidence reconstruction only)

**Purpose**: independent reconciliation of the M1–M8 mode framework against the CURRENT physical repository state, as of this session. This is NOT a new acceptance campaign, NOT a fix session, and issues NO OWNER ACCEPTED/FROZEN declaration. It supersedes nothing in `progress.md` (which does not cover M1–M8 at all) and does not retract or duplicate `M1_M8_CAMPAIGN_REPORT.md` (the original planning-layer-only acceptance attempt) or `M1_M8_CORRECTION_REPORT.md` (the multi-session correction campaign, self-classified in its own final line as **"M1-M8 CORRECTION IMPLEMENTATION — FINAL ACCEPTANCE RETEST CANDIDATE"** — a candidate for retest, not an independent, owner-accepted PASS).

**HEAD at time of this reconciliation**: `973b098f` (branch `main`). Working tree has the uncommitted M1–M8 correction campaign changes described in `M1_M8_CORRECTION_REPORT.md` §5/§32.4/§33 still present (verified below, file-by-file, not assumed from the report's own narrative).

**Method**: every claim below was re-verified against the current on-disk files and/or by re-running already-existing test files (no test written, no test modified, no fixture modified, no production code touched). Where the correction report's narrative and the current physical file agreed, this is stated as "confirmed." Nothing below is inferred from code merely existing — status fields reflect actual test execution or direct code inspection.

## 0. Independent re-verification of the correction campaign's headline claims

| Claim (from `M1_M8_CORRECTION_REPORT.md`) | Re-verified how | Result |
|---|---|---|
| `akaal/engine/plan_dispatch.py` implements real (non-stub) `_handle_cdc_boundary`/`_handle_cdc_init`/`_handle_cdc_apply`/`_handle_incremental_poll` | `grep` of the file, read of the handler bodies | CONFIRMED — all four are implemented, not `NOT_YET_DISPATCHED` stubs |
| `akaal/runtime/process/daemon.py`'s `MigrationRuntimeDaemon` bypass is closed (delegates to `AkaalSuperEngine.execute_migration`, fails closed with `PLAN_NOT_LOAD_BEARING`) | Read of `daemon.py` | CONFIRMED |
| `akaal/engine/api.py`'s `AkaalMigrationEngine.start_migration` bypass is closed (`LegacyEngineBypassClosedError`) | Read of `api.py` | CONFIRMED — method body replaced with an unconditional fail-closed raise |
| `akaal/agents/manager/manager_agent.py`'s `ManagerAgent` bypass is closed via `_dispatch_physical_migration_task` / `MANAGER_AGENT_BYPASS_CLOSED` | Read of `manager_agent.py` | CONFIRMED |
| Corpus: 176 total PL/SQL-corpus objects (25 procedures, 25 functions, 26 triggers, 24 package spec+body units, 32 views, 4 materialized views, 40 sequences) | Independently re-counted this session by importing `tests/fixtures/estate/plsql_corpus/{procedures,functions,triggers,packages,views,materialized_views,sequences}.py` and counting each module's own object list, not trusting the prior report's arithmetic | CONFIRMED — 25+25+26+24+32+4+40 = **176**, exact match |
| `pytest tests/fixtures/estate/selftest/` still 26/26 | Re-ran fresh this session | CONFIRMED — **26 passed, 0 failed, 0 skipped** |
| Targeted M1–M8 dispatch/durability/security test set (`test_plan_driven_execution.py`, `test_m2_bulk_cdc_dag_dispatch_integration.py`, `test_m3_cdc_dag_dispatch_integration.py`, `test_m4_dag_dispatch_integration.py`, `test_m4_watermark_authority.py`, `test_sec_i01_i15_m1_m8_hostile_matrix.py`) | Re-ran fresh this session, exact command: `pytest tests/unit/engine/test_plan_driven_execution.py tests/unit/engine/test_m2_bulk_cdc_dag_dispatch_integration.py tests/unit/engine/test_m3_cdc_dag_dispatch_integration.py tests/unit/engine/test_m4_dag_dispatch_integration.py tests/unit/engine_durability/test_m4_watermark_authority.py tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py -q` | CONFIRMED — **62 passed, 0 failed, 0 skipped, in 22.54s** (12 + 3 + 4 + 6 + 13 + 15 = 53 named tests per the report's own breakdown; the extra 9 come from parametrization/additional cases not broken out in the report's headline count — not re-decomposed further this session, but the aggregate PASS count is directly, freshly observed) |

**A whole-repository regression run (the "7026 passed / 165 skipped / 1 failed-in-full-run-but-passed-in-isolation" figure in §33.6 of the correction report) was NOT re-run this session** — it takes ~22 minutes and this session's authorization is read-only reporting, not re-running large campaigns to "improve numbers." The targeted re-run above (62/62) is used instead, per the instruction that re-running *existing* evidence is permitted. **This targeted re-run is the freshest evidence in this report; the 7026-figure is carried forward from the correction report's own narrative, NOT independently reproduced this session, and is labeled as such below.**

## 1. Per-mode current state

### M1 — Bulk Migration
- **Intended semantics**: full bulk copy of all source rows/schema to an empty target; no CDC.
- **Implementation status**: IMPLEMENTED. `AkaalSuperEngine.execute_migration` → `PlanExecutionDispatcher.run(dag_stages)` → `SchemaExecutionStep`/sqlite-fallback → `DataTransportStep`/sqlite-fallback → `CanonicalReconciliationEngine.reconcile_tables` → evidence stage.
- **Production wiring status**: WIRED. Reachable from `EngineGateway.start_transport` (real IPC entrypoint), from the (now-closed) `MigrationRuntimeDaemon`, and from `ManagerAgent._dispatch_physical_migration_task` — all three confirmed this session to route through `AkaalSuperEngine.execute_migration`, which now requires and consumes a compiled `dag_dict` (fails closed otherwise).
- **Physical execution evidence**: `test_m1_physically_transports_real_rows`, `test_m1_cdc_stage_never_present_in_dag` (`tests/unit/engine/test_plan_driven_execution.py`) — re-run this session as part of the 62-test batch, PASS.
- **Exact tests executed**: `tests/unit/engine/test_plan_driven_execution.py::TestM1BulkMigration` (2 tests).
- **Result**: PASS.
- **Source rows / target rows / rows read / written**: per the correction report's own disclosed figures (not re-measured at full 1,000,000-row scale this session): 500+150 rows transported in the M1 dispatch test scope; the FULL 1,000,000-row/206-table baseline has NEVER been run end-to-end through this path (correction report §7 explicitly states this; not contradicted by anything found this session). **Rows changed/deleted**: N/A for bulk load into an empty target. **Duplicates/missing/extra/corrupted rows**: NOT_MEASURED at full scale; zero discrepancy reported at the tested (500+150-row) scale.
- **Validation result**: `CanonicalReconciliationEngine.reconcile_tables` — MATCHED (500/500, 150/150) at tested scale.
- **Checkpoint/durability evidence**: `CentralStateStore` record `{workflow_id}_plan_execution`; no per-node crash-mid-transport recovery test exists.
- **Restart/replay evidence**: NOT_MEASURED for M1 specifically (restart/replay evidence exists for M3/M4, not M1).
- **CDC evidence**: N/A (M1 has no CDC stage — physically confirmed absent from the compiled DAG).
- **Evidence #12 status**: BOUND (best-effort) — `_handle_evidence` now calls `akaalEngine.evidence.api.EvidenceAuthority.get_instance().package_execution_evidence(...)` in addition to a local digest, reporting `evidence_authority_bound` truthfully (per correction report §33.3; the binding proof itself, `test_m4_i06`, is on the M4 path, not independently re-run for M1 this session — carried forward, not fabricated as independently confirmed for M1).
- **Elapsed time**: NOT_MEASURED at any scale that would be meaningful (the small dispatch-test scope's timing was not captured as a standalone metric; the only large-scale timing that exists anywhere in this repository is the SQLite-fixture BUILD (174.6s to generate 1,000,000 rows — not a migration/transport time) and the historical Oracle→Postgres run, both reported separately below and NOT applicable to M1's own dispatch path).
- **Rows per second**: NOT_MEASURED (no measured elapsed time exists for an actual M1 dispatch-path transport run at any row count large enough to be meaningful; do not compute from the fixture-build time, which measures data generation, not migration).
- **Proof classification**: INTEGRATION_PROVEN (SQLite-fixture scope, small row counts). NOT LIVE_PROVEN.
- **Limitations**: full 1,000,000-row scale never run through the dispatch path; no crash/restart test for M1 specifically; Evidence #12 binding proof is on M4's test, not M1's.

### M2 — Bulk + CDC
- **Intended semantics**: bulk copy with a CDC boundary that captures concurrent source changes during the bulk phase, applied without loss/duplication after.
- **Implementation status**: IMPLEMENTED (per correction report §33.2, re-verified this session by reading `plan_dispatch.py`'s `_handle_cdc_boundary`/`_handle_cdc_init`/`_handle_cdc_apply` and confirming they are not stubs). Uses `akaal.cdc.domain.*` (`CDCEventIdentity`, `DurableCDCBuffer`, `CDCApplyWorker`) — the "domain" CDC generation, not the separate "contracts" CDC generation used elsewhere in the repo (two independent CDC generations coexist; documented, not a defect of M2 itself).
- **Production wiring status**: WIRED into `AkaalSuperEngine.execute_migration`'s dispatch path. **No real production upstream CDC source listener (Debezium/LogMiner/replication-slot equivalent) is wired** — M2/M3 are proven only against an authorized test-only seam (`rt_ctx["cdc_test_source_transactions"]`) that simulates what an external CDC source would hand AKAAL. Absent this seam, the stage fails closed (`CDC_SOURCE_NOT_CONFIGURED`).
- **Physical execution evidence**: `tests/unit/engine/test_m2_bulk_cdc_dag_dispatch_integration.py` — re-run this session as part of the 62-test batch, PASS. Per the correction report: `test_m2_i01` injects mid-bulk INSERT/UPDATE/DELETE via the test seam and asserts, against real on-disk SQLite target state, no loss/no duplication/correct final value; `test_m2_i02` is a zero-change negative control; `test_m2_i03` proves M4-only responsibility is fenced out of M2.
- **Exact tests executed**: `test_m2_bulk_cdc_dag_dispatch_integration.py` (3 tests, confirmed present in the file this session).
- **Result**: PASS (test-seam scope only — NOT against a live/production CDC source).
- **Source/target rows, rows read/written/changed/deleted**: not independently re-derived to exact numerators this session beyond what the correction report states (3 bulk rows transported, 3 CDC transactions applied in `test_m2_i01`); the actual assertions were re-run and passed, but per-row numerator/denominator arithmetic was not re-extracted from the test source this session.
- **Duplicates/missing/extra/corrupted rows**: reported by the correction report as zero at test scope; not independently re-derived.
- **Validation result**: `CanonicalReconciliationEngine` invoked for the reconciliation stage; specific M2 pass/fail per the re-run above.
- **Checkpoint/durability evidence**: `DurableCDCBuffer` is WAL-backed and restart-recoverable per its own module; no dedicated M2 crash-mid-CDC-boundary test exists (a documented gap, per correction report §33.7 item 2, which is about M4 specifically but the same class of gap applies to M2's boundary-capture moment — not independently tested this session).
- **Restart/replay evidence**: exists for M3 (`test_m3_i03`), not independently confirmed for M2 in this session's re-run beyond the tests re-passing.
- **CDC evidence**: real `CDCApplyWorker.apply_next_transaction` invoked via a bridge class (`_CDCApplyAdapterBridge`) that translates `CDCEvent`s to `BaseAdapter.write_batch`/delete-by-PK calls.
- **Evidence #12 status**: same best-effort binding as M1 (not independently re-verified for M2's specific stage this session).
- **Elapsed time / rows per second**: NOT_MEASURED (test-fixture scope, no timing captured).
- **Proof classification**: INTEGRATION_PROVEN (test-seam scope only). NOT LIVE_PROVEN — no real upstream CDC source was ever involved.
- **Limitations**: no production CDC source listener; test-only seam scope only; no dedicated crash-mid-CDC-boundary test; two independent CDC domain-model generations coexist in the repo (documented architectural note, not fixed).

### M3 — CDC Only
- **Intended semantics**: continuous CDC apply with zero bulk/schema transport.
- **Implementation status**: IMPLEMENTED (re-verified: `plan_dispatch.py`'s CDC handlers are shared with M2; the mode fence — `MODE_ALLOWED_RESPONSIBILITIES["M3"]` excludes `"transport"` — is what enforces zero-bulk, confirmed via the SEC-I09 test in the security suite re-run this session).
- **Production wiring status**: WIRED (test-seam scope only, same caveat as M2 — no live upstream CDC source).
- **Physical execution evidence**: `tests/unit/engine/test_m3_cdc_dag_dispatch_integration.py` — re-run this session, PASS. Per the correction report: `test_m3_i01` proves INSERT/UPDATE/DELETE correctness; `test_m3_i03` proves exactly-once apply across two independent dispatcher runs (simulated redelivery/replay) via `CDCApplyWorker`'s restart-persistent dedup; `test_m3_i04` proves a smuggled bulk-transport stage is refused by the mode fence.
- **Exact tests executed**: `test_m3_cdc_dag_dispatch_integration.py` (4 tests, confirmed present).
- **Result**: PASS (test-seam scope).
- **Rows read/written/changed/deleted, duplicates/missing/extra**: not independently re-extracted to exact numerators this session; the correction report describes a 400-row-scale zero-bulk CDC-only synchronized sample (consistent with the original acceptance campaign's fixture description) but the exact current dispatch-test row counts were not re-derived line-by-line this session.
- **Validation result**: real reconciliation stage invoked; PASS per re-run.
- **Checkpoint/durability evidence**: `CDCApplyWorker`'s restart-persistent dedup, exercised by `test_m3_i03`.
- **Restart/replay evidence**: PHYSICALLY PROVEN at test scope — `test_m3_i03` simulates a redelivered transaction across two independent dispatcher runs and confirms exactly-once application (per correction report; consistent with the file re-passing this session).
- **CDC evidence**: real, via the same "domain" CDC generation as M2.
- **Evidence #12 status**: not independently re-verified for M3's specific stage this session.
- **Elapsed time / rows per second**: NOT_MEASURED.
- **Proof classification**: INTEGRATION_PROVEN (test-seam scope). NOT LIVE_PROVEN.
- **Limitations**: no live upstream CDC source; "zero transport" for M3 is proven structurally (mode-fence rejection before dispatch) rather than by an explicit invocation-count assertion on the transport handler itself (an indirect but real proof, per correction report §33.2's own stated limitation).

### M4 — Incremental Query/Polling
- **Intended semantics**: watermark-based incremental polling; the single safety-critical invariant is "durable watermark must never advance before the corresponding target write commits."
- **Implementation status**: IMPLEMENTED, in two layers: (1) the durability PRIMITIVE — `akaalEngine.durability.DurabilityAuthority.save_watermark`/`get_watermark`, extending the existing atomically-persisted, `FencingToken`-protected `DurabilityAuthority` (NOT a new authority) — confirmed present this session by reading `akaalEngine/durability/checkpoint/registry.py` and `akaalEngine/durability/api.py`; (2) the DAG-dispatch wiring — `plan_dispatch.py::_handle_incremental_poll`, confirmed present (not a stub) this session, calling the watermark primitive with `tgt.write_batch(...)` required to complete BEFORE `save_watermark(...)` is invoked (call-order preserved by direct code structure, lines ~696-704 per the correction report — not independently re-read line-by-line this session, but the handler's non-stub status was confirmed).
- **Production wiring status**: WIRED into the DAG dispatcher. Watermark-column metadata must be supplied via `rt_ctx["incremental_watermark_columns"]` — absent this, the stage fails closed (`M4_NOT_CONFIGURED`). No production poller/scheduler that periodically re-invokes an M4 plan on a timer exists — only the one-shot dispatch-per-invocation path is wired.
- **Physical execution evidence**: `tests/unit/engine_durability/test_m4_watermark_authority.py` (13 tests, unit-level, against real on-disk SQLite-backed `DurabilityAuthority`, no mocking of the thing under test) and `tests/unit/engine/test_m4_dag_dispatch_integration.py` (6 tests, DAG-dispatch-level) — both re-run this session as part of the 62-test batch, PASS.
- **Exact tests executed**: `test_m4_watermark_authority.py::{test_numeric_watermark_save_and_advance, test_numeric_watermark_regression_rejected, test_numeric_watermark_null_value_fails_safe, test_no_watermark_ever_saved_returns_none, test_timestamp_watermark_advance_and_tie_accepted, test_timestamp_watermark_regression_rejected, test_compound_watermark_ordering, test_incompatible_plan_fingerprint_rejected, test_stale_execution_cannot_advance_watermark, test_repeated_identical_batch_replay_is_idempotent, test_restart_from_durable_watermark_survives_process_restart, test_rejected_write_leaves_prior_watermark_unchanged, test_watermark_authority_itself_has_no_target_visibility_by_design}` (13) plus `test_m4_dag_dispatch_integration.py` (6, including `test_m4_i02` restart-across-fresh-instance and `test_m4_i06` Evidence Authority binding, per correction report naming).
- **Result**: PASS, both files, this session.
- **Rows read/written/changed**: not independently re-extracted to exact numerators this session (unit-level watermark tests deal in watermark values, not bulk row counts; the DAG-dispatch integration test's exact row counts were not re-derived line-by-line).
- **Duplicates/missing/extra/corrupted rows**: NOT_MEASURED at any meaningful scale — this is unit/small-integration-test evidence, not a real poll-cycle-at-scale measurement.
- **Validation result**: N/A directly (M4 is a transport/polling mode, not a validation-only mode); reconciliation stage behavior not specifically re-examined for M4 this session.
- **Checkpoint/durability evidence**: PHYSICALLY PROVEN at the primitive level — numeric/timestamp/compound watermark advance and regression-rejection, null-safety, restart-across-fresh-`DurabilityAuthority`-instance survival, stale-execution fencing, replay idempotency, and "rejected write leaves prior watermark unchanged" are all independently, physically tested (re-confirmed passing this session, not merely re-read from the report).
- **Restart/replay evidence**: PHYSICALLY PROVEN for the watermark primitive (`test_restart_from_durable_watermark_survives_process_restart`) and for the DAG-dispatch level (`test_m4_i02`, per correction report naming — file re-run and passing this session, individual test name not re-grepped to exact string this session).
- **CDC evidence**: N/A (M4 is polling-based, not CDC-based, by its own `ExecutionModeSpec`: `uses_cdc=False`).
- **Evidence #12 status**: BOUND — `test_m4_i06_evidence_stage_binds_to_real_evidence_authority` (per correction report naming) specifically asserts `evidence_authority_bound is True` end-to-end through the M4 DAG-dispatch path. This is the ONE mode with an explicit, end-to-end Evidence Authority #12 binding test; re-run and passing this session as part of the 6-test M4-dispatch batch (individual sub-test name not independently re-grepped this session, but the file's aggregate PASS covers it).
- **Elapsed time / rows per second**: NOT_MEASURED. No real poll-cycle-at-scale timing exists anywhere in the repository.
- **What is explicitly NOT proven**: cross-database atomicity between the actual target write and the watermark persistence is a CALL-ORDER discipline enforced by the calling code's structure (verified by the primitive's own design — `save_watermark` takes no target-connection argument, so it structurally cannot see or wait on target commit state), not something the durability layer can independently guarantee across two different databases. No dedicated fault-injection test crashes the dispatcher between `write_batch` and `save_watermark` and asserts the watermark did not advance — this remains a real, narrow, residual gap (per correction report §33.7 item 2, not contradicted by anything found this session).
- **Proof classification**: watermark primitive — UNIT_PROVEN (physically proven, real on-disk store, no mocking of the authority itself). DAG-dispatch integration — INTEGRATION_PROVEN (small-scale). Full end-to-end incremental-poll-at-scale with a real periodic scheduler — NOT_EXECUTED, no such scheduler exists. NOT LIVE_PROVEN under any classification.
- **Limitations**: no production polling scheduler; no fault-injection test for the exact crash-window between target commit and watermark save; scale never exceeds small test fixtures.

### M5 — State-Based Synchronization
- **Intended semantics**: compare source/target state and classify differences (equal/modified/source-only/target-only); repair is a separately-gated, evaluated-but-not-executed capability.
- **Implementation status**: IMPLEMENTED. `plan_dispatch.py::_handle_reconciliation` (shared with M8) dispatches M5's differential-analysis node to the real `CanonicalReconciliationEngine.reconcile_tables()`. `_handle_repair_eligibility` evaluates eligibility but `repair_authorized` is hard-coded `False` — no real canonical authorization mechanism is wired to grant repair execution (confirmed unchanged this session; not re-read line-by-line but not claimed fixed anywhere in the correction report's later sections either).
- **Production wiring status**: WIRED for comparison; repair execution structurally cannot occur (no authorization path grants it).
- **Physical execution evidence**: `tests/unit/engine/test_plan_driven_execution.py::test_m5_reconciliation_dispatch_reuses_canonical_engine` — re-run this session as part of the 62-test batch, PASS.
- **Exact tests executed**: 1 test (per correction report naming; not independently re-grepped to the exact function name this session beyond confirming the file's aggregate pass).
- **Result**: PASS.
- **Rows**: 200 source / 190 target keys, 100 equal / 60 modified / 40 source-only / 30 target-only per the ORIGINAL acceptance campaign's fixture description (`M1_M8_CAMPAIGN_REPORT.md` §5, M5) — this fixture-level math was independently re-verified in that PRIOR session, not re-derived again in this session; the correction-report-era dispatch test uses "a basic equal-data case," per its own §11, not the full difference-category matrix.
- **Duplicates/missing/extra/corrupted rows**: NOT independently re-measured this session against the full M5 difference-category matrix through the real dispatch path (only a basic MATCHED case is dispatch-tested, per the correction report's own disclosed limitation).
- **Validation result**: MATCHED (basic case, real engine).
- **Checkpoint/durability evidence**: N/A (comparison-only mode; no target mutation to checkpoint).
- **Restart/replay evidence**: NOT_MEASURED for M5 specifically.
- **CDC evidence**: N/A (M5 `uses_cdc=False`).
- **Evidence #12 status**: not independently verified for M5's specific stage this session.
- **Elapsed time / rows per second**: NOT_MEASURED.
- **Proof classification**: INTEGRATION_PROVEN (basic-case, real engine, real fixture data). NOT LIVE_PROVEN. The repair-eligibility gate is a structural non-mutation guarantee (hard-coded `False`), not a tested authorization-and-repair flow.
- **Limitations**: only a basic equal-data case is dispatch-tested (not the full NULL/Unicode/numeric/timestamp/binary difference-category matrix); repair authorization is a stub `False`, not connected to a real governance source.

### M6 — Schema Only
- **Intended semantics**: deploy schema/DDL only; zero data rows transported.
- **Implementation status**: IMPLEMENTED. `_handle_schema` dispatches to a dialect-neutral `CREATE TABLE IF NOT EXISTS` fallback (sqlite target) or `SchemaExecutionStep` (postgresql/oracle target); `_handle_schema_verify` re-queries the target's actual table list.
- **Production wiring status**: WIRED. Data fence enforced by DAG composition (the "Parallel Stream Data Transport" stage is never even present in a compiled M6 DAG — confirmed by the ORIGINAL acceptance campaign's real `PlanCompiler` output, `M1_M8_CAMPAIGN_REPORT.md` §4a, unchanged by anything found this session), reinforced by the newer `MODE_ALLOWED_RESPONSIBILITIES` dispatcher-level fence (SEC-I10 test).
- **Physical execution evidence**: `test_m6_creates_schema_zero_rows` (`test_plan_driven_execution.py`) — re-run this session, PASS.
- **Exact tests executed**: 1 test.
- **Result**: PASS.
- **Source/target rows**: target row count after a real M6 run independently queried and asserted **0**; exact number of tables created not re-derived to a specific numerator this session beyond "the target gained exactly the 2 tables requested, with 0 rows" (correction report §12, not independently re-derived).
- **Data transport invocation count**: 0 (structurally — the transport handler is never reached because the stage never appears in the DAG).
- **Validation result**: structural table-list comparison (not the full reconciliation engine) — tables present, matched.
- **Checkpoint/durability evidence**: same state-store record as M1; no dedicated M6 checkpoint semantics.
- **Restart/replay evidence**: NOT_MEASURED.
- **CDC evidence**: N/A, confirmed absent.
- **Evidence #12 status**: local digest + best-effort binding, not independently re-verified for M6's specific stage this session.
- **Elapsed time / rows per second**: N/A (M6 moves zero rows by definition; rows/sec is not a meaningful metric for this mode).
- **Proof classification**: INTEGRATION_PROVEN (SQLite-fixture scope). NOT LIVE_PROVEN.
- **Limitations**: the ORIGINAL acceptance campaign's `M6M7-FENCE-001` finding (planning-layer fencing existed but the OLD executor didn't honor it) is now addressed by the corrected `AkaalSuperEngine`; the object-category-by-category accounting for the full 176-object PL/SQL/schema corpus deploying through M6 was never attempted at full scale (only a small subset).

### M7 — Data Only
- **Intended semantics**: transport data only into a pre-existing target shell; zero DDL/schema mutation.
- **Implementation status**: IMPLEMENTED. `_handle_transport` transports rows via the same path as M1.
- **Production wiring status**: WIRED. DDL fence enforced by DAG composition (no schema-deployment stage present in a compiled M7 DAG) plus the dispatcher-level mode fence.
- **Physical execution evidence**: `test_m7_transports_data_ddl_fingerprint_unchanged`, `test_m7_dag_never_contains_schema_deployment_stage` — re-run this session, PASS.
- **Exact tests executed**: 2 tests.
- **Result**: PASS.
- **Rows**: 300/300 (`CATALOG_PRODUCTS__categories`, matching source exactly) per correction report §13 — not independently re-derived to a fresh numerator this session, but the test re-passed.
- **DDL fingerprint before/after**: identical (`bd44305bd9f95cbf` == `bd44305bd9f95cbf`, sha256 over every `CREATE TABLE` statement in `sqlite_master`) — a physical, independently-queryable proof per its own design; not re-computed by hand this session, but the test asserting it re-passed.
- **CREATE/ALTER/DROP count**: 0/0/0 (implied by the unchanged fingerprint).
- **Validation result**: `CanonicalReconciliationEngine` — MATCHED (300/300) per correction report, not re-extracted to a fresh numerator this session.
- **Checkpoint/durability evidence**: same state-store record as M1; no dedicated M7 checkpoint semantics.
- **Restart/replay evidence**: NOT_MEASURED.
- **CDC evidence**: N/A, confirmed absent.
- **Evidence #12 status**: not independently re-verified for M7's specific stage this session.
- **Elapsed time / rows per second**: NOT_MEASURED.
- **Proof classification**: INTEGRATION_PROVEN (SQLite-fixture scope). NOT LIVE_PROVEN.
- **Limitations**: full 1,000,000-row scale never attempted through this path; target-schema-compatibility check beyond the DDL-fingerprint-unchanged proof was not separately validated.

### M8 — Validation/Reconciliation Only
- **Intended semantics**: read-only inspection/reconciliation; zero mutation of source or target under any circumstance, including when a mismatch is found.
- **Implementation status**: IMPLEMENTED. `_handle_reconciliation` (shared with M5/M1) dispatches M8's inspection/reconciliation nodes to `CanonicalReconciliationEngine`.
- **Production wiring status**: WIRED. Non-mutation is structural: no `write_batch`/mutation call is reachable from the inspection/reconciliation code path at all (not merely "not called this run") — confirmed by the correction report's own code-structure claim, consistent with the ORIGINAL acceptance campaign's finding that `reconcile_tables()` takes only in-memory row lists as input and has no database handle.
- **Physical execution evidence**: `test_m8_detects_mismatch_without_mutating_target`, `test_m8_dag_never_contains_mutating_stages` — re-run this session, PASS.
- **Exact tests executed**: 2 tests.
- **Result**: PASS.
- **Rows (ORIGINAL acceptance campaign's independently-re-verified M8 fixture math, unchanged by the correction campaign)**: source_rows=285, target_rows=275, matched(exact)=150, source_only=35, target_only=25, value_mismatch=100 — real `CanonicalReconciliationEngine.reconcile_tables()` output matched this independent expected truth **exactly, 285/285 = 100.000%** row accounting and **250/250 = 100.000%** classification accuracy (per `M1_M8_CAMPAIGN_REPORT.md` §4b; this arithmetic was NOT re-run again against the live engine in THIS session — it is carried forward from that prior session's own genuine, disclosed-with-correction real invocation, not fabricated here).
- **Target content fingerprint before/after a deliberately-injected mismatch**: identical (`1299a5adf039b538` == `1299a5adf039b538`, sha256 over every row) — per correction report §14; not recomputed by hand this session, but the asserting test re-passed.
- **Duplicates/corrupted rows**: the correction-campaign test deliberately injects one corrupted row (`code` column) and the real engine correctly reports `source_only=1, target_only=1` — a true, not fabricated, finding (per correction report, test re-passed this session).
- **Validation result**: MISMATCH correctly detected (deliberate injection); MATCHED on the clean original fixture math.
- **Checkpoint/durability evidence**: N/A (no mutation, nothing to checkpoint).
- **Restart/replay evidence**: N/A.
- **CDC evidence**: N/A, confirmed absent.
- **Evidence #12 status**: same best-effort binding pattern as other modes; the M8-specific binding was not independently re-verified this session (the one explicit binding test, `test_m4_i06`, is on the M4 path, not M8's).
- **Elapsed time / rows per second**: NOT_MEASURED (285/275-row fixture scope; no timing captured, and this scale is too small to extrapolate any meaningful rows/sec figure).
- **Proof classification**: INTEGRATION_PROVEN (SQLite-fixture scope). NOT LIVE_PROVEN.
- **Limitations**: repair-execution path structurally never runs (evaluated `repair_authorized=False, repair_executed=False`), which is correct-by-design for a validation-only mode, not a limitation of correctness — but it means M8's "repair" capability itself has zero execution evidence, by design.

## 2. Cross-mode summary table

| Mode | Impl. | Wiring | Tests (this session, fresh re-run) | Result | Proof class | Rows/sec |
|---|---|---|---|---|---|---|
| M1 | IMPLEMENTED | WIRED (3 entrypoints) | 2 | PASS | INTEGRATION_PROVEN | NOT_MEASURED |
| M2 | IMPLEMENTED | WIRED (test-seam only) | 3 | PASS | INTEGRATION_PROVEN | NOT_MEASURED |
| M3 | IMPLEMENTED | WIRED (test-seam only) | 4 | PASS | INTEGRATION_PROVEN | NOT_MEASURED |
| M4 | IMPLEMENTED (primitive + dispatch) | WIRED (no production scheduler) | 13 + 6 | PASS | UNIT_PROVEN (primitive) / INTEGRATION_PROVEN (dispatch) | NOT_MEASURED |
| M5 | IMPLEMENTED (comparison only) | WIRED | 1 | PASS | INTEGRATION_PROVEN | NOT_MEASURED |
| M6 | IMPLEMENTED | WIRED | 1 | PASS | INTEGRATION_PROVEN | N/A (zero rows by design) |
| M7 | IMPLEMENTED | WIRED | 2 | PASS | INTEGRATION_PROVEN | NOT_MEASURED |
| M8 | IMPLEMENTED | WIRED | 2 | PASS | INTEGRATION_PROVEN | NOT_MEASURED |

**Total tests re-run fresh this session across the above: 62 passed, 0 failed, 0 skipped** (single combined `pytest` invocation covering all six named test files, per the command in §0).

No mode is LIVE_PROVEN. No mode's rows-per-second is measured or extrapolated (per the owner's explicit prohibition on extrapolating small tests to larger row counts and on comparing SQLite throughput to Oracle/PostgreSQL throughput).

## 3. Bypass status (production migration-initiation entrypoints)

Per the correction report §33.1, re-verified by direct code read this session (not merely re-read from the narrative):

| Entrypoint | Routes through canonical plan-driven execution? |
|---|---|
| `EngineGateway.start_transport` | YES (always did) |
| `MigrationRuntimeDaemon.execute_migration` | YES — confirmed this session: delegates to `self.super_engine.execute_migration`, fails closed (`PLAN_NOT_LOAD_BEARING`) absent a compiled `dag_dict` |
| `AkaalMigrationEngine.start_migration` | N/A — confirmed this session: raises `LegacyEngineBypassClosedError` unconditionally; the entire independent Oracle→Postgres multiprocess body was removed |
| `ManagerAgent.run_migration` (via `_dispatch_physical_migration_task`) | YES (when a compiled `dag_dict` exists) / fails closed with `MANAGER_AGENT_BYPASS_CLOSED` otherwise — confirmed this session by reading the method and its two call sites (lines ~926, ~1031) |
| `akaal.advisory.executor.execute` | N/A — confirmed (per correction report, not re-independently traced line-by-line this session) to be a pure, stateless, in-memory advisory dict transformation with zero I/O; never was a physical-execution bypass |

**All three previously-confirmed production physical-execution bypasses are closed, confirmed by direct code read this session, not merely by trusting the correction report's narrative.**

## 4. Remaining known gaps (carried forward, not independently re-derived beyond confirming the relevant files still show them)

- No production CDC source listener for M2/M3 (test-seam scope only).
- No production polling scheduler for M4 (one-shot dispatch only).
- M4's target-write-then-watermark-save ordering is enforced by structural design + unit test, not by a dedicated crash-injection integration test.
- M5's repair-eligibility gate is hard-coded `False`, not connected to a real authorization source.
- Two independent CDC domain-model generations coexist in `akaal.cdc` ("contracts" vs. "domain") — architectural note, not a defect of M2/M3 specifically.
- `ValidationAuthority` (the richer, `akaalEngine`-side 7-stage pipeline) remains unwired; `CanonicalReconciliationEngine` was determined (by prior documentary audit, not re-litigated this session) to be sufficient for what the DAG dispatcher currently needs, per `contract.txt`'s Authority #11 requirements.
- No whole-repository regression run was performed in THIS session (the last one on record, per the correction report's own narrative, is 7026 passed / 165 skipped / 1 failed-then-passed-in-isolation — that number is NOT independently reproduced here, and should not be cited as this session's own evidence).
- Full 1,000,000-row/206-table scale was never run through the corrected dispatch path for any mode — everything above is proven only at small (hundreds-of-rows) fixture scale.

## 5. Historical Oracle → PostgreSQL migration evidence (re-verified against current repo state)

This is a SEPARATE, real, physical migration run using genuine `oracledb`/`psycopg2` connections to local Oracle/PostgreSQL instances — NOT part of the M1–M8 SQLite-fixture framework above, and NOT re-executed this session (read-only evidence retrieval only: existing artifact files were re-read, existing scripts were re-inspected for how their numbers were computed; nothing was re-run).

### 5a. `artifacts/stage3_flagship_results.json` (genuine row-count parity run)

Re-read this session, exact current contents:
```
oracle_rows: 10,000,115
postgres_rows: 10,000,115
delta: 0
tables: 303
pct: 100.0
checksum_matches: 303
merkle_match: true
checkpoints: 1,886
ckpt_rows_processed: 44,064,352
ckpt_rows_failed: 0
```
**Confirmed genuine**: 303 tables, 10,000,115 rows source and target, delta 0 — a real row-count-parity result. This is the strongest, most trustworthy piece of evidence in the historical-migration record.

### 5b. Timing claim — `reports/performance_benchmark_report.md`

Re-read this session: line 25 states **"Total Migration Time: 212.40 sec (~3.5 min)"** attributed to the corrected/optimized run, compared against a 1,482.50s baseline.

Re-read `scripts/stage3_flagship_ora2pg.py` this session, confirming the background briefing's claim:
- Line 369: `peak_throughput = avg_throughput * 1.45` — a **hardcoded 1.45× multiplier** applied to the measured average throughput, not an independently measured peak.
- Line 399: `peak_ram_mb = 54.82` — a **literal hardcoded constant**, not a measurement.
- No corresponding CPU-percent measurement call (e.g., no `psutil.cpu_percent()` or equivalent) was found near these lines in the file.

**Classification: HISTORICAL_THROUGHPUT_NOT_TRUSTWORTHILY_PROVEN.** The 212.40s figure itself may or may not be a genuinely measured wall-clock duration for the run it describes (a wall-clock `time.time()`-style duration IS plausible for the top-line "Total Migration Time" — this was not disproven), but the DERIVED figures built on top of it (peak throughput, peak RAM) are confirmed fabricated/hardcoded rather than measured, which undermines the trustworthiness of the entire performance table as an evidentiary artifact. No rows-per-second figure is reported here as trustworthy — even the "average_throughput" figure, while arithmetically derivable from total_rows/duration, inherits the same document's demonstrated pattern of mixing measured and hardcoded values without distinguishing them, so **NOT_MEASURED** is used for peak/derived figures and the average figure is not independently re-certified as trustworthy in this report.

### 5c. Integrity claim (checksum/Merkle)

Re-read this session: `merkle_pg`/`merkle_match` fields exist in the artifact. Per the background briefing, this reduces to `hash(table_name + row_count + seed)` rather than a hash of actual row content — this specific claim about the hash's input composition was NOT independently re-derived from the hashing function's source code in this session (would require locating and reading the exact hash-construction call site, not done here due to session scope). **This claim is carried forward from the prior forensic pass, UNVERIFIED in this session** — reported as such rather than re-asserted as independently confirmed. If true, the practical implication (a checksum that cannot detect row-content corruption, only table-existence/row-count agreement) stands as a real limitation on what "checksum_matches: 303/303" can be said to prove: it would prove row-count-per-table agreement and table-set agreement, not row-content correctness.

### 5d. Governance/approval

Re-read `scripts/stage3_flagship_ora2pg.py` this session, confirming the background briefing's claim:
- Line 211: `principal = ApprovalPrincipal(principal_id="ciso-admin-01", ...)` — a hardcoded principal identity.
- Lines 214-223: the SAME script requests AND approves all three governance gates itself, using this same hardcoded principal, within a single unattended process invocation (`app_engine.request_approval(...)` immediately followed by `app_engine.approve(...)` using the same `principal` variable).

**Confirmed: this is self-approval by a hardcoded, unauthenticated (no external identity provider, no human-in-the-loop) principal string within the same script/process — not a maker-checker or human-approved governance flow.**

### 5e. What this historical run proves and does not prove

**Proves**: genuine row-count parity (10,000,115 = 10,000,115) and table-set parity (303 tables) between a real Oracle instance and a real PostgreSQL instance, via real `oracledb`/`psycopg2` connections — this is real, LIVE_PROVEN evidence for bulk row-count transport correctness at this specific historical run's scale.

**Does not prove**: trustworthy timing/throughput (derived figures are confirmed hardcoded, not measured — HISTORICAL_THROUGHPUT_NOT_TRUSTWORTHILY_PROVEN); row-CONTENT integrity beyond row-count agreement (the checksum mechanism's exact construction was not re-verified this session, but per the carried-forward finding it would not detect content-level corruption even if re-confirmed); any human-approved or externally-authenticated governance/maker-checker discipline (confirmed self-approved by a hardcoded principal within the same process); any CDC/incremental/watermark/validation-only semantics (this run is a pure bulk copy — it exercises no M2–M8-class behavior at all).

**Which M-mode this legitimately corresponds to**: **M1-class (bulk migration) only.** It says nothing about M2 (CDC boundary), M3 (CDC-only), M4 (watermark/incremental), M5 (state-sync comparison), M6 (schema-only fencing), M7 (data-only fencing), or M8 (validation-only/non-mutation) — none of those semantics were exercised by this historical script. It is also NOT a substitute for a real Oracle/PostgreSQL run of the CORRECTED M1–M8 dispatch path described in §1 above — the two artifacts (this historical script, and the corrected `AkaalSuperEngine`/`PlanExecutionDispatcher`) are architecturally unrelated; the historical script does not go through `PlanCompiler`/`ExecutionMode`/`AkaalSuperEngine` at all.

### 5f. `artifacts/scaleup_50m_results.json` vs. `reports/akaal_50m_scaleup_benchmark_report.md` — self-contradiction re-confirmed

Re-read both files this session, exact current contents:
- `artifacts/scaleup_50m_results.json`: `"row_count_parity": false`, `"oracle_total_rows": 49999915`, `"postgres_total_rows": 55741706`, `"row_delta": 5741791` (5.74M-row delta — target has MORE rows than source, not fewer), `"table_checksum_match_pct": 77.8`, `"checksum_matches": 389`, `"parity_failures": 111` (out of 500 tables).
- `reports/akaal_50m_scaleup_benchmark_report.md`: line 140, **"GRADE AAA CERTIFIED FOR 50M+ ROW ENTERPRISE PRODUCTION MIGRATIONS"**; line 146, **"Zero failed rows, zero retries, zero data loss across the entire 50M row migration."**

**Confirmed, re-verified this session: this is a direct, load-bearing self-contradiction.** The underlying artifact's own `row_count_parity` field is `false` with a 5.74-million-row delta and 111 of 500 tables failing checksum parity, while the report built from this same run asserts zero data loss and an "AAA" certification grade. **This 50M-scale run cannot be cited as evidence of anything beyond "a run was attempted at this scale and produced a measurable, non-zero row-count discrepancy"; its own summary verdict is not trustworthy and should not be treated as a genuine acceptance result for any mode or scale.**
