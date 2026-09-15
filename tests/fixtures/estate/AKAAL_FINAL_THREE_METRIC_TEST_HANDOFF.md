# AKAAL FINAL THREE-METRIC TEST HANDOFF

**To**: a completely new Claude session with no memory of any prior conversation.
**From**: a prior session (read-only verification only, no test execution, no implementation).
**Purpose of THIS document**: hand off exactly three measurements to you. This document does not run anything. You (the new session) will run the three-metric test after reading this in full.

**The three measurements you must produce, and nothing else, are:**
1. **PARALLEL MIGRATION SPEED** — rows/sec, real, measured, parallel-only.
2. **MIGRATION ACCURACY** — must be 100.0000% for PASS.
3. **ORACLE→POSTGRESQL TRANSLATION ACCEPTANCE** — must be 100.0000% on the supported-object denominator for PASS.

Every fact in this document was verified against the CURRENT physical repository state at handoff time (not recalled from an earlier conversation). Re-verify anything you rely on before acting on it — repository state can change between sessions.

---

## SECTION 1 — REPOSITORY CHECKPOINT

- **Repo root**: `C:\Users\LENOVO\Downloads\temp_akaal-main`
- **Current branch**: `main`
- **HEAD**: `973b098fdf06adcad97202dda3565de9e467e248`
- **Git status is DIRTY. This is intentional. DO NOT reset/clean/restore/checkout/stash/commit/push/pull/rebase anything.** The dirty working tree **IS** the implementation under test — an uncommitted, in-progress M1-M8 physical-execution correction campaign. Any destructive git operation would erase real, tested, working correction code with no way to recover it in this environment.

**Exact current dirty-file list (verified via `git status --short`, re-run at handoff time)**:

Modified (`M`):
```
.gitignore
akaal/agents/manager/manager_agent.py
akaal/engine/api.py
akaal/engine/facade.py
akaal/migration/execution/hooks/executor.py
akaal/runtime/process/daemon.py
akaal/workflow/steps/migration_steps.py
akaalEngine/durability/__init__.py
akaalEngine/durability/api.py
akaalEngine/durability/checkpoint/registry.py
akaalEngine/durability/models/checkpoint.py
akaalEngine/durability/models/errors.py
akaalEngine/durability/store/sqlite.py
akaalEngine/evidence/api.py
tests/stress/test_parallel_migration.py
tests/unit/planner/test_custom_sql_hooks.py
```
(Plus many `.akaal/reports/*.json` files showing only timestamp diffs from prior test runs — not implementation, safe to ignore.)

Untracked (`??`), i.e. brand-new files that are part of the correction implementation:
```
akaal/engine/plan_dispatch.py
tests/fixtures/estate/                          (the entire simulated acceptance estate + this handoff file itself)
tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py
tests/unit/engine/test_m2_bulk_cdc_dag_dispatch_integration.py
tests/unit/engine/test_m3_cdc_dag_dispatch_integration.py
tests/unit/engine/test_m4_dag_dispatch_integration.py
tests/unit/engine/test_plan_driven_execution.py
tests/unit/engine_durability/test_m4_watermark_authority.py
```

**Exact current M1-M8 implementation state**: a multi-session correction campaign closed 3 confirmed production physical-execution bypasses (`MigrationRuntimeDaemon`, `AkaalMigrationEngine.start_migration`, `ManagerAgent.run_migration`), made the compiled DAG genuinely load-bearing via `akaal/engine/plan_dispatch.py::PlanExecutionDispatcher`, wired all 8 modes (M1-M8) to real canonical authorities, and passed a clean whole-repo regression (7036 passed, 0 failed, 165 skipped). Full detail: `tests/fixtures/estate/M1_M8_CORRECTION_REPORT.md` (its own final verdict, quoted verbatim — **§33.9, last line**): **"M1-M8 CORRECTION IMPLEMENTATION — FINAL ACCEPTANCE RETEST CANDIDATE"**. This is NOT "OWNER ACCEPTED & FROZEN" and NOT "LIVE_PROVEN" — it is a candidate for an independent retest, which is part of what you are now doing.

**Exact current translation implementation state**: two parallel implementations exist. `akaal/transpiler/*` is **CONFIRMED DEAD** (zero production imports anywhere outside its own directory). `akaalEngine/schema/procedural/*` is **CONFIRMED WIRED into production** (`akaalEngine.schema.authority`, `akaalEngine.schema.core.processor`, and the P7C.11 intelligence producer `akaalEngine/intelligence/producers/sql_translation.py`) and is the ONLY canonical translation path. It has a real AST entrypoint for **PROCEDURE and FUNCTION objects only**; TRIGGER and PACKAGE have no entrypoint (self-disclosed, unsupported by design); VIEW/MATERIALIZED VIEW/SEQUENCE are DDL objects out of scope for this translator entirely. Full detail: `tests/fixtures/estate/ORACLE_TO_POSTGRES_TRANSLATION_ACCEPTANCE_REPORT.md`.

**`progress.md` staleness warning**: `progress.md` does **NOT** cover the M1-M8 correction campaign or this handoff's three-metric test at all. It tracks a different, separate roadmap (P7A/P7B/P7C phases, real and frozen, but architecturally unrelated to the M1-M8 DAG-dispatch path — see `M1_M8_CORRECTION_REPORT.md` §17/§33.4 for the verified relationship). Do not consult `progress.md` for M1-M8 or translation status; it will mislead you. Do not edit it.

**Existing report paths, all under `tests/fixtures/estate/`** (all verified present at handoff time):
- `M1_M8_CAMPAIGN_REPORT.md` — an early, read-only simulated-acceptance attempt that found the mode framework was not yet load-bearing (historical; superseded by the correction campaign below).
- `M1_M8_CORRECTION_REPORT.md` — the full correction campaign record (33 sections). This is your primary reference for what was fixed and how.
- `M1_M8_CURRENT_STATE_REPORT.md` — a read-only current-state snapshot (check its own date/session marker before trusting it over `M1_M8_CORRECTION_REPORT.md`, which is more current as of this handoff).
- `ORACLE_TO_POSTGRES_TRANSLATION_ACCEPTANCE_REPORT.md` — the translation-subsystem current-state record. This is your primary reference for RESULT 3.

---

## SECTION 2 — CANONICAL AKAAL EXECUTION PATH

Verified by reading the actual current files (not recalled), this session:

```
Operator/mode intent (execution_mode: "M1".."M8")
  -> akaal.planner.models.p5_domain.ExecutionMode (canonical mode enum; ExecutionMode.from_string used for fail-closed alias resolution)
  -> akaal.planner.engine.plan_compiler.PlanCompiler  (compiles a DAG of named stages for the declared mode)
  -> immutable dag_dict = {"dag_stages": [{"stage": n, "name": "..."}, ...]}  (governance-approved, fingerprinted)
  -> akaal.engine.facade.AkaalSuperEngine.execute_migration(workflow_id, spec_dict, dag_dict, source_params, target_params, is_physical, is_synthetic_test)
       - FIRST calls self.verify_governance_authorization(workflow_id, spec_dict, dag_dict)
         -> reads CentralStateStore category="governance", key "{workflow_id}_approval"
         -> requires status == "approved" AND a plan fingerprint that exactly matches compute_plan_fingerprint(spec_dict, dag_dict)
         -> raises ApprovalRequiredError / PlanFingerprintMissingError / PlanFingerprintMismatchError on any failure (fail closed)
       - FAILS CLOSED if dag_dict or dag_dict["dag_stages"] is missing/empty (no fixed fallback sequence — this was the original defect, now fixed)
  -> akaal.engine.plan_dispatch.PlanExecutionDispatcher(mode_str, plan_fingerprint, rt_ctx).run(dag_stages)
       - Resolves mode to canonical M1..M8 key via akaal.planner.models.p5_domain.ExecutionMode.from_string (fails closed on unrecognized mode)
       - MODE_ALLOWED_RESPONSIBILITIES table (module-level dict in plan_dispatch.py) + a per-stage fail-closed check BEFORE any handler executes: a responsibility not legal for the declared mode is refused with "MODE_FENCE_VIOLATION", never silently skipped or allowed
       - Dispatches each stage by name -> responsibility -> `_handle_<responsibility>` method:
           _handle_discovery, _handle_planning_metadata, _handle_cdc_boundary, _handle_schema,
           _handle_cdc_init, _handle_cdc_apply, _handle_incremental_poll, _handle_transport,
           _handle_reconciliation / _handle_validation (both route to the shared `_reconcile`),
           _handle_inspection, _handle_repair_eligibility, _handle_evidence
  -> Source/target adapters: akaal.adapters.adapter_registry.create_adapter(config) (dialect-neutral SQLite fallback used throughout this campaign's SQLite-estate evidence; LEGACY_STEP_SUPPORTED_TARGET_DIALECTS route to akaal.workflow.steps.migration_steps.{SchemaExecutionStep,DataTransportStep} for Postgres/Oracle targets)
  -> Durability/checkpoints: akaalEngine.durability.DurabilityAuthority (issue_fencing_token, validate_fencing_token, save_checkpoint, save_watermark/get_watermark — the M4 watermark primitive added this campaign)
  -> Validation Authority #11 (production call site): akaal.validation.domain.reconciliation.CanonicalReconciliationEngine.reconcile_tables (called from plan_dispatch.py's `_reconcile`, which ALSO now independently verifies a real fencing epoch via DurabilityAuthority before reconciling — added this campaign, see M1_M8_CORRECTION_REPORT.md §17/§33.3)
  -> Evidence Authority #12 (production call site): akaalEngine.evidence.api.EvidenceAuthority.get_instance().package_execution_evidence(...) (called from plan_dispatch.py's `_handle_evidence`)
```

**Separately, and NOT part of the chain above**: `akaalPipeline` is a distinct, independently-gated orchestration system (`akaalPipeline/execution/coordinator.py::PlanExecutionCoordinator`) with its own P7B fabric/ownership/placement gates. It is architecturally disjoint from the chain above (zero cross-imports in either direction, verified via `grep -rl "akaalPipeline" akaal --include=*.py` → 0 hits). Do not confuse the two systems.

**3 closed bypasses** (verify each is still closed by reading the file before trusting): `akaal/runtime/process/daemon.py::MigrationRuntimeDaemon.execute_migration`, `akaal/engine/api.py::AkaalMigrationEngine.start_migration` (now an unconditional fail-closed stub), `akaal/agents/manager/manager_agent.py::ManagerAgent._dispatch_physical_migration_task`.

---

## SECTION 3 — PARALLEL MIGRATION CAPABILITY

**Be warned: this section's honest finding is that the parallel path is thin/unproven at its one production call site, even though a genuinely real parallel primitive exists elsewhere.**

- **Real, genuine multi-process parallel primitive**: `akaal.replication.scheduling.parallel_scheduler.ParallelReplicationScheduler` (`akaal/replication/scheduling/parallel_scheduler.py`). Verified by reading the file: it genuinely uses `from concurrent.futures import ProcessPoolExecutor` and `with ProcessPoolExecutor(max_workers=self.max_workers) as executor:` — real OS-level worker processes, `__init__(self, max_workers: int = 4)` defaults to 4. This is NOT a mock or a simulation; it is a real multiprocess scheduler.
- **Real partitioning authority**: `akaal.replication.partitioning.range_partitioner.RangePartitioner` (`.generate_partitions_for_table(table_name, schema_name, target_schema, total_rows, pk_columns, strategy)`), with `akaal.engine.spec.PartitionStrategy` (includes `SINGLE_STREAM` and `PK_NUMERIC_RANGE`, at minimum — verify the full enum yourself).
- **THE HONEST FINDING**: the only production call site that wires these two together, `akaal/workflow/steps/migration_steps.py::DataTransportStep` (used for the Postgres/Oracle legacy-dialect fallback path, lines ~583-627 at handoff time — re-verify the exact line numbers, they may have shifted), calls:
  ```python
  range_partitioner.generate_partitions_for_table(..., total_rows=1000, pk_columns=[], strategy=PartitionStrategy.SINGLE_STREAM)
  ...
  scheduler = ParallelReplicationScheduler(max_workers=1)
  ```
  **`max_workers=1` and `strategy=SINGLE_STREAM` and a hardcoded `total_rows=1000` (not the real table's row count) are hardcoded at this call site.** This means the one production path that could exercise genuine multi-worker parallelism, as currently wired, never actually spawns more than 1 worker or more than 1 partition. This is a real, honest finding — do not paper over it, and do not assume "ParallelReplicationScheduler exists" implies "parallel migration is proven."
  - A **separate, different** parallel pair (`TransportPartitioner`/`MigrationScheduler`) existed inside `akaal/engine/api.py::AkaalMigrationEngine.start_migration`'s now-dead-and-closed independent transport engine — this is now unreachable (fail-closed stub), so it does NOT count as a currently-exercisable parallel path.
  - `tests/stress/test_parallel_migration.py` (modified this campaign) tests `GBAgent`/`ManagerAgent` async worker-concurrency/ownership/fair-scheduling LOGIC using `unittest.IsolatedAsyncioTestCase` and `MockConfig(mock_mode=True)` — this is a **mocked, in-process, logic-level concurrency test**, NOT physical evidence of real parallel database I/O. Do not use it as evidence of a real parallel migration.
- **HOW YOU CAN PROVE multiple workers/partitions actually executed** (not just "parallel=True" with no evidence), if you choose to construct a genuine test that calls `RangePartitioner`+`ParallelReplicationScheduler` directly with `max_workers > 1` and a real multi-partition strategy against the real SQLite estate (this would be a NEW TEST FILE you write for the acceptance campaign — allowed, since writing NEW test-only code that exercises existing canonical APIs is not "editing production code"; see §16/§17):
  - Instrument each worker/partition to record its own `worker_id`, the exact primary-key range or row-set it was assigned, and its own row-count contribution, then independently sum contributions and compare to the real total row count of the table(s) migrated.
  - Prove no double-counting: assert the union of all partitions' assigned key ranges/row-sets is disjoint (no overlap) and their union covers exactly the source table's real row set (no gap).
  - Prove no duplicate writes: query the real target table's actual final row count directly (not from any in-process counter) and compare to the source's real row count.
  - Prove clean worker termination: capture each `ProcessPoolExecutor` future's actual return value/exception state; assert no worker process is left running/zombied after `execute_partitions` returns.
  - Prove consistent checkpoint state: after parallel completion, independently re-query `DurabilityAuthority`/`CentralStateStore` checkpoint state directly (not from the scheduler's own return value) and confirm it matches the real transported row count.
- **Strongest currently-available physical estate/dataset for this**, without modifying production code: the local simulated SQLite estate (`tests/fixtures/estate/data/source_baseline.sqlite`, 1,000,000 rows / 206 tables — verify current numbers yourself in §7). A single large, real, populated table from it (e.g. one of the largest-row-count tables in `COMMERCE_ORDERS` or `FINANCIAL_LEDGER` per the schema row totals in §7) is the best candidate for a genuine multi-partition parallel test, since `RangePartitioner` needs enough rows to make more than one partition meaningful.

**If you cannot get AKAAL to actually execute a genuinely parallel (>1 worker, >1 partition, verified-disjoint, verified-complete) migration in this environment** — because the only wired call site is hardcoded to `max_workers=1`, and constructing a new direct-call test is out of your risk tolerance or is judged to require production code changes beyond what's allowed — **the correct, honest result is `PARALLEL_MIGRATION_SPEED = BLOCKED`, per §5. Do not report a serial number disguised as a parallel one.**

---

## SECTION 4 — MIGRATION SPEED TEST HANDOFF

Measure exactly:
- **T0**: timestamp captured immediately BEFORE the call to `AkaalSuperEngine.execute_migration(...)` begins (i.e., the last statement before that call, not before governance-approval setup, not before adapter construction).
- **T1**: timestamp captured AFTER (a) all target writes for the migrated scope have completed AND (b) required validation (the reconciliation/validation stage) has finished — i.e., after `execute_migration` returns and you have independently confirmed the returned `exec_record["success"]` and the reconciliation stage's real result, not merely after the raw transport stage.
- `elapsed_seconds = T1 - T0` (wall-clock, using a monotonic clock, e.g. Python's `time.perf_counter()` — not `time.time()`, which is not monotonic).
- `rows_per_second = validated_rows / elapsed_seconds`, where `validated_rows` is the count of rows the reconciliation stage independently confirmed as `MATCHED` in the target — not the count the transport stage merely claims to have written.

**Explicitly FORBIDDEN, with the exact historical defect that must never be repeated**:
- **Hardcoded/generated throughput numbers.** The historical script `scripts/stage3_flagship_ora2pg.py` (verified present and read this session) contains, verbatim, at line ~369: `peak_throughput = avg_throughput * 1.45` — a fabricated multiplier applied to a real average to manufacture a "peak" number with no actual peak measurement behind it. It also hardcodes `peak_ram_mb = 54.82` and `peak_cpu_pct = 14.2` as literal constants (lines ~399-400), not measured values. **Do not do anything resembling this.** If you cannot measure a peak, report `PEAK_THROUGHPUT_ROWS_SEC = NOT_MEASURED`, never a multiplied estimate.
- Estimated/mocked/simulated duration of any kind.
- Counting rows that were read from source but not confirmed committed/written to target.
- Counting fixture-generation time (building the SQLite estate itself) as part of migration elapsed time.
- Any direct database copy performed outside AKAAL's own canonical execution path (e.g., a raw `sqlite3` script copying tables directly) — this would not be a measurement of AKAAL's migration speed at all.

**Report BOTH, separately, and headline the second**:
- `RAW_MIGRATION_THROUGHPUT_ROWS_SEC` = rows written / (time from T0 to when the transport stage alone completes).
- `END_TO_END_VALIDATED_THROUGHPUT_ROWS_SEC` = validated (reconciliation-confirmed `MATCHED`) rows / (T1 - T0) — **this is the headline metric for RESULT 1.**

---

## SECTION 5 — PARALLEL-ONLY PERFORMANCE RULE

The speed result in RESULT 1 must be a **parallel** result, not a serial one relabeled. You must be able to state, with real evidence (not assumed from configuration alone):
- Actual worker count that executed (e.g., 4 real `ProcessPoolExecutor` worker processes, confirmed via each worker's returned `worker_id` or PID, not merely `max_workers=4` passed as a parameter).
- Actual partition count and each partition's real row-range/row-set.
- Each worker's real per-worker row contribution, independently summed.
- Proof of no double-counting (disjoint partition coverage, verified — see §3).
- Proof of no duplicate writes (real final target row count matches real source row count exactly, not inflated).
- Proof of clean worker termination (no hung/zombie worker processes after completion).
- Proof of consistent checkpoint state after parallel completion (independently re-queried, not trusted from the scheduler's own self-report).

**If AKAAL cannot actually execute a genuine multi-worker parallel migration in the available environment** (per the honest finding in §3 — the one wired call site is hardcoded to `max_workers=1`), **the result must be reported literally as**:
```
PARALLEL_MIGRATION_SPEED = BLOCKED
```
**Never** report a serial (single-worker, single-partition) execution's throughput as if it were a parallel result. That would be a fabricated pass.

---

## SECTION 6 — MIGRATION ACCURACY HANDOFF

**Threshold: 100.0000% for PASS. Anything less, including 99.9999%, is FAIL. Do not round.**

**Formula (generic form)**:
```
CORRECT_ROWS = EXPECTED_ROWS - MISSING_ROWS - EXTRA_ROWS - DUPLICATE_ROWS - CORRUPTED_ROWS
ACCURACY = (CORRECT_ROWS / EXPECTED_ROWS) * 100
```

**Canonical engine's own, more rigorous formulation — use this in preference to the generic formula above, since it is what production actually computes and avoids double-counting**: `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine.reconcile_tables(...)`. Read its actual current return-value fields yourself before writing your report (do not assume the field names below are still exact — re-verify against the live source file `akaal/validation/domain/reconciliation.py`). At handoff-verification time, the fields observed on its returned summary object include (verify current spelling): `status` (`MATCHED`/`MISMATCH`), `source_rows`, `target_rows`, `matched_count`, `source_only_count`, `target_only_count`, `value_mismatch_count`. A row is only "correct" if it is counted in `matched_count` — `source_only_count` (missing from target), `target_only_count` (extra in target / not in source), and `value_mismatch_count` (present both places but with different values — i.e., corrupted) must each independently be exactly 0 for a 100% result, and `matched_count` must exactly equal `source_rows` (== `target_rows`, else there's an unaccounted discrepancy). Report all four counts explicitly, not just a computed percentage.

**No rounding a failing value to PASS.** If `value_mismatch_count > 0` or `source_only_count > 0` or `target_only_count > 0` for even a single row across the entire migrated scope, the result is FAIL, full stop — regardless of how small the discrepancy is relative to total row count.

---

## SECTION 7 — MIGRATION TEST DATASET

**Verified this session, directly from `tests/fixtures/estate/data/source_manifest.json` and `tests/fixtures/estate/data/baseline_build_summary.json`** (re-verify yourself — do not trust this table blindly, these files can change):

| Field | Value |
|---|---:|
| Schema count | 12 |
| Table count | 206 |
| Populated table count | 182 |
| Empty table count | 24 |
| No-PK (intentional) table count | 6 |
| Total rows declared | 1,000,000 |
| Total rows physical | 1,000,000 |
| Estate disk size | 2,339,282,944 bytes (≈2.18 GiB) |
| Estate build elapsed time | 174.55 seconds |

**Recommendation for the largest existing estate usable by the parallel path without modifying production code**: the baseline estate above (1,000,000 rows across 206 tables) is the largest dataset that exists without rebuilding. For a genuine multi-partition parallel test (§3), pick the single largest real populated table by row count (query `tests/fixtures/estate/data/source_manifest.json`'s `tables` dict for the highest `row_count` value yourself — do not assume which table this is without checking, since it can change between builds) so `RangePartitioner` has enough rows to produce more than one meaningful partition.

**Exact reset/setup commands** (verified by reading `if __name__ == "__main__":` blocks in both files this session):
```
.venv/Scripts/python.exe -m tests.fixtures.estate.build_estate baseline   # builds/rebuilds the 1,000,000-row baseline (default phase if arg omitted: "baseline"; takes ~175s)
.venv/Scripts/python.exe -m tests.fixtures.estate.reset <action>          # action defaults to "all" if omitted; verify available actions by reading reset.py's own argument-dispatch logic before invoking, since exact action names may include per-mode resets (e.g. an M2/M3/M4/M5/M8-specific reset) not enumerated here
```
Re-read both files' full `if __name__` blocks yourself before invoking, since the exact set of valid `sys.argv[1]` values was not exhaustively enumerated in this handoff.

---

## SECTION 8 — TRANSLATION IMPLEMENTATION HANDOFF

**Canonical path, verified this session (fresh grep, not recalled)**: `akaalEngine/schema/procedural/*` — `lexer.py` (`ProceduralLexer`), `parsers/plsql.py` (`PLSQLParser`), `parsers/tsql.py` (`TSQLParser`), `emitters/plpgsql.py` (`PLpgSQLEmitter`), `ast_nodes.py`, `diagnostics.py`, `transforms/{control_flow,cursors,exceptions,packages}.py`. Confirmed wired into production via `akaalEngine/schema/authority.py`, `akaalEngine/schema/core/processor.py`, and `akaalEngine/intelligence/producers/sql_translation.py` (P7C.11).

`akaal/transpiler/*` is **CONFIRMED DEAD** — a repository-wide grep for `akaal.transpiler`/`akaal import transpiler` imports outside its own directory returns exactly one hit, in a documentation file (`docs/architecture/AKAAL_Gateway_Directory_Analysis.md`), zero hits in any `.py` file. Do not use it as evidence of anything; it is not exercised by any production code or test.

**Supported/unsupported object kinds** (per P7C.11's own self-disclosed scope, re-verify against the live docstrings before relying on this): PROCEDURE and FUNCTION have a real AST entrypoint (`CanonicalRoutine`). TRIGGER and PACKAGE have **no** AST entrypoint — explicitly self-disclosed as unsupported ("no trigger/package AST entrypoint exists in this repo yet"). VIEW, MATERIALIZED VIEW, and SEQUENCE are DDL objects entirely **out of scope** for this procedural translator (handled, if at all, by a different schema-DDL subsystem — not this one).

**Manual-review classification**: P7C.11's real, authoritative classification enum is `TranslationCertification`, with values (verify spelling against the live source): `EXACT_TRANSLATION_PROVEN`, `SEMANTIC_EQUIVALENCE_PROVEN`, `COMPILES_BUT_EQUIVALENCE_UNPROVEN`, `MANUAL_REVIEW_REQUIRED`, `UNSUPPORTED`. Only P7C.11 itself, by actually running the pipeline, can assign one of these — `expected_truth.py` (§9/§12) explicitly does NOT assign this and must not be treated as if it did.

**Known defect, CURRENT_CONFIRMED this session**: T-SQL `@variable` leakage. The lexer still treats `@` as a valid identifier-start/continuation character, so a T-SQL `@variable` token is lexed as a single IDENTIFIER and can pass through unstripped into emitted PL/pgSQL output (which does not use `@`-prefixed variable syntax), producing invalid PostgreSQL. This is caught only by a downstream regex safety net, not by the emitter itself — a narrow, specific, documented, still-unfixed gap. **Do not fix this.** Report it as a known defect if it affects any corpus object you translate.

**Exact current tests covering the real translator** (verified this session): `tests/unit/engine_intelligence/test_p7c11_sql_translation.py` (17 tests) and `tests/unit/engine_schema/test_aoir_ast_pipeline.py` (3 tests). Both use small, hand-written, ad-hoc PL/SQL/T-SQL snippets — **neither references or exercises the corpus fixture** (`tests/fixtures/estate/plsql_corpus/`) at all. Re-run them yourself to get current pass/fail counts before citing a number:
```
.venv/Scripts/python.exe -m pytest tests/unit/engine_intelligence/test_p7c11_sql_translation.py tests/unit/engine_schema/test_aoir_ast_pipeline.py -v
```

**Do not fix anything found in this section — report it as-is.**

---

## SECTION 9 — TRANSLATION CORPUS HANDOFF

**Exact current corpus counts, independently recomputed this session** by importing each corpus module directly via the venv Python and counting each module's own object list (not copied from any prior report's arithmetic):

```
.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'tests/fixtures/estate')
from plsql_corpus import procedures, functions, triggers, packages, views, materialized_views, sequences
print('PROCEDURES', len(procedures.PROCEDURES))
print('FUNCTIONS', len(functions.FUNCTIONS))
print('TRIGGERS', len(triggers.TRIGGERS))
print('PACKAGES', len(packages.PACKAGES))
print('VIEWS', len(views.VIEWS))
print('MATERIALIZED_VIEWS', len(materialized_views.MATERIALIZED_VIEWS))
print('SEQUENCES', len(sequences.SEQUENCES))
"
```
Result at handoff time (**re-run this yourself — do not trust this table blindly**):

| Object type | Count |
|---|---:|
| Procedures | 25 |
| Functions | 25 |
| Triggers | 26 |
| Packages (spec+body units combined) | 24 |
| Views | 32 |
| Materialized views | 4 |
| Sequences | 40 |
| **TOTAL CORPUS OBJECTS** | **176** |

**Classification, per `entrypoint_status` in `tests/fixtures/estate/plsql_corpus/expected_truth.py`** (re-read its current docstring yourself — quoted in §12):
- **SUPPORTED_EXPECTED** (has a real AST entrypoint today): Procedures (25) + Functions (25) = **50 objects**. This is the denominator for RESULT 3.
- **EXPECTED_UNSUPPORTED** (self-disclosed, no entrypoint by design): Triggers (26) + Packages (24) = **50 objects**.
- **OUT_OF_SCOPE_FOR_PROCEDURAL_TRANSLATOR** (DDL concern, not this translator's job at all): Views (32) + Materialized Views (4) + Sequences (40) = **76 objects**.
- **EXPECTED_MANUAL_REVIEW**: `expected_truth.py` does not assign a distinct "manual review" bucket at the entrypoint-status level for the corpus as a whole — `predicted_difficulty` (a per-object PREDICTION, not a certification) is what may suggest manual review is likely for specific procedures/functions. If you need this classification, read the per-object `predicted_difficulty` values directly from `expected_truth.py` rather than inventing a bucket.

**CRITICAL, verified this session — the corpus has NEVER been executed**: a repository-wide grep for any file importing `PLSQLParser`, `TSQLParser`, or `PLpgSQLEmitter` returns exactly the two test files in §8 (20 tests total, neither referencing the corpus). A grep of all of `tests/` for `plsql_corpus` returns 3 files (`tests/fixtures/estate/selftest/test_estate_self_tests.py`, `tests/fixtures/estate/reset.py`, `tests/fixtures/estate/modes/m6_schema_only.py`) — none of which import or call the real translator; they only check corpus manifest/object-count integrity as fixture bookkeeping. **The 176-object corpus has never been run end-to-end through the real translator by any process in this repository, as of handoff time.** Running it for real, for the first time, through the real canonical translator, and grading the result, IS your RESULT 3 task.

---

## SECTION 10 — 100% TRANSLATION ACCEPTANCE LAW

```
TRANSLATION_ACCEPTANCE = (correctly_translated_supported_objects / supported_expected_denominator) * 100
```
Denominator = 50 (25 procedures + 25 functions, per §9's `SUPPORTED_EXPECTED` bucket) — **fix this denominator BEFORE running the translator and do not change it after seeing results.** Even ONE incorrectly translated object out of the 50 means **FAIL** at 49/50 = 98.0% — not "close enough." 100.0000% requires all 50 to be correct per the full checklist in §11. Objects outside the 50 (triggers/packages/views/materialized views/sequences) are reported separately as their own honest classification (§9) and must not be silently folded into or excluded from the 50-object denominator to inflate or deflate the percentage.

---

## SECTION 11 — WHAT COUNTS AS CORRECT TRANSLATION

Parser success, emitter success, or a passing unit test **alone is NOT sufficient** to call an object "correctly translated." For each of the 50 `SUPPORTED_EXPECTED` objects, verify ALL of the following before counting it as correct:
1. The object was actually emitted (non-empty PL/pgSQL output produced).
2. No source-code loss: every meaningful construct in the original PL/SQL/T-SQL source appears, semantically, in the output (not necessarily verbatim, but nothing silently dropped).
3. Correct object kind preserved (a PROCEDURE stays a PROCEDURE, a FUNCTION stays a FUNCTION with its return type intact).
4. Parameters: names, order, direction (IN/OUT/INOUT), and datatypes all correctly translated.
5. Return type (for functions) correctly translated.
6. Variable declarations correctly translated, including the T-SQL `@variable` defect check (§8) — if `@`-prefixed identifiers leak into the PL/pgSQL output unstripped, that object is NOT correctly translated, regardless of what any regex safety net downstream does.
7. Datatypes correctly mapped (Oracle/T-SQL types → PostgreSQL equivalents).
8. DML statements (SELECT/INSERT/UPDATE/DELETE) correctly translated.
9. Control flow (IF/CASE/LOOP/WHILE/FOR) correctly translated.
10. Cursors correctly translated (open/fetch/close semantics preserved).
11. Exception handling correctly translated.
12. Transaction semantics (COMMIT/ROLLBACK/SAVEPOINT, if present) correctly translated.
13. Cross-object dependencies preserved (calls to other procedures/functions still resolve/reference correctly).
14. The emitted output is **syntactically valid PostgreSQL PL/pgSQL** — ideally verified by actually attempting to parse/compile it against a real PostgreSQL instance (§13); if that's unavailable, at minimum verify it against PostgreSQL's documented PL/pgSQL grammar rules manually/via a static syntax checker, and say explicitly which method you used.
15. For objects outside the 50 (triggers/packages), correct **detection and classification** as unsupported counts as correct behavior for THOSE objects — but they are not part of the 100% denominator either way (§9/§10).
16. Correct manual-review classification where `predicted_difficulty` suggested it, if you choose to independently assess difficulty.

An object that merely "did not crash the parser" or "produced some output" is NOT correctly translated unless it satisfies all applicable items above.

---

## SECTION 12 — INDEPENDENT EXPECTED TRUTH

`tests/fixtures/estate/plsql_corpus/expected_truth.py`'s own current docstring states, verbatim (re-read it yourself before quoting further — file paths and exact wording can change):

> "This is **NOT** derived from running AKAAL's translator (that is forbidden this session) and it is **NOT** a claim about what the translator will actually output. It is an independent, honestly-labelled *prediction* the later compulsory translation-accuracy campaign can score itself against."

> "P7C.11's real classification enum is `TranslationCertification`: EXACT_TRANSLATION_PROVEN / SEMANTIC_EQUIVALENCE_PROVEN / COMPILES_BUT_EQUIVALENCE_UNPROVEN / MANUAL_REVIEW_REQUIRED / UNSUPPORTED. Only P7C.11 itself — by actually running the pipeline — can assign one of *those* values with authority; this module must not pretend to."

This module assigns only two things per object: (1) `entrypoint_status` (a repository fact about whether an AST entrypoint exists for the object's KIND, PROCEDURE/FUNCTION only), and (2) `predicted_difficulty` (a construct-based PREDICTION for procedures/functions only, explicitly distinguished from an actual `TranslationCertification`).

**Instruction to you**: `expected_truth.py` is a prediction file, not ground truth. **AKAAL must not grade itself.** You (the independent grader) must actually run the real translator on each of the 50 `SUPPORTED_EXPECTED` objects, independently inspect the emitted PL/pgSQL against the checklist in §11, and assign your own correctness verdict per object — do not substitute `expected_truth.py`'s predictions for a real measured grade, and do not modify `expected_truth.py` after seeing your own translation output (that would be grading the test by rewriting the answer key).

---

## SECTION 13 — PHYSICAL POSTGRESQL COMPILATION

Verified this session: no `docker-compose*.yml`, no `.env*` file, and no reachable-service configuration for a real PostgreSQL instance was found at the repository root or via a search for `POSTGRES_HOST`/`localhost:5432`-style connection strings in config/compose files. **Do not start a PostgreSQL instance yourself as part of this handoff verification** — this handoff only checked for pre-existing configuration.

**You (the new session) must independently re-check** whether a real, reachable PostgreSQL instance is configured/available in your actual execution environment (which may differ from this handoff-writing environment) before deciding. If one genuinely is available and you use it to actually attempt to compile/execute the emitted PL/pgSQL for all 50 supported objects, the threshold for `PHYSICAL_POSTGRESQL_COMPILATION` is: 100% of the 50 objects must compile/execute without error for PASS. If no real PostgreSQL is available:
```
PHYSICAL_POSTGRESQL_COMPILATION = EXTERNAL_BLOCKED
```

---

## SECTION 14 — CROSS-ENGINE SEMANTIC EQUIVALENCE

Same rule as §13, for a real Oracle **and** PostgreSQL pair (needed to actually execute the same logical operation on both engines and compare results for true semantic equivalence, not just syntactic compilation). No such pair was found configured in this repository at handoff time. If neither is available in your environment:
```
CROSS_ENGINE_SEMANTIC_EQUIVALENCE = EXTERNAL_BLOCKED
```

---

## SECTION 15 — TRANSLATION PERFORMANCE

If you measure translation throughput, report it as **objects/sec**, **LOC/sec** (lines of source code translated per second), **bytes/sec**, and/or **average object latency** (seconds per object) — as applicable to what you actually measure. **Never call any of these "rows/sec"** — that term is reserved for RESULT 1 (migration speed) and conflating the two would misrepresent what was measured.

---

## SECTION 16 — STRICT TEST-ONLY RULE FOR NEW SESSION

**ZERO production code edits. ZERO test-file edits (beyond writing new, additive test files you author for this acceptance campaign itself — do not edit any existing test). ZERO fixture edits. ZERO `expected_truth.py` edits (before OR after seeing your own translation output). ZERO config changes made to hide, suppress, or work around a failure. ZERO corrections/fixes performed during the run, no matter how small or "obviously right" the fix seems.**

If you find a FAIL, a BLOCKED condition, or a bug of any kind: **RECORD it exactly as observed → CONTINUE to the next measurable item where it is safe and independent to do so → REPORT it fully and honestly in your final report → STOP.** Never remediate, patch, or work around anything during this acceptance campaign. That is a different, separate, not-yet-authorized activity.

No git writes of any kind (no `commit`/`add`/`push`/`pull`/`rebase`/`stash`/`checkout .`/`reset --hard`/`clean -f`). No edits to `progress.md`.

---

## SECTION 17 — 100% AKAAL RULE

All measured work must be performed **BY AKAAL ITSELF**, through its own canonical APIs (`AkaalSuperEngine.execute_migration` for migration; the real `PLSQLParser`/`TSQLParser`/`PLpgSQLEmitter` pipeline for translation). The grader (you) must remain independent of the thing being graded.

**Forbidden**:
- Direct database copy bypassing AKAAL (e.g., a raw script copying SQLite tables directly) counted as "migration."
- Hand-translation of any corpus object outside AKAAL's translator, then presenting that as AKAAL's output.
- Any external transformation tool used instead of `akaalEngine/schema/procedural/*`.
- Fabricating or mocking connector/adapter "success" instead of a real connection and real I/O.
- Bypassing `PlanCompiler`, the compiled DAG, `PlanExecutionDispatcher`, the parallel worker machinery, or `CanonicalReconciliationEngine` for the migration test.
- Editing translated output before grading it (that would not be grading AKAAL's real output).
- Manually correcting a failed translation object and then counting it as passed.

---

## SECTION 18 — ONLY THREE FINAL OWNER RESULTS

Your final report's core must contain exactly this structure, filled in with your own actually-measured values (never a value you have not personally measured this session):

```
RESULT 1 — PARALLEL_MIGRATION_SPEED
  Status: PASS | FAIL | BLOCKED
  Raw migration throughput (rows/sec): <value or NOT_MEASURED>
  End-to-end validated throughput (rows/sec): <value or NOT_MEASURED>   <- headline metric
  Worker count actually observed: <value or NOT_MEASURED>
  Partition count actually observed: <value or NOT_MEASURED>
  Per-worker row contribution: <breakdown or NOT_MEASURED>
  No-double-counting proof: <how verified, or NOT_MEASURED>
  No-duplicate-writes proof: <how verified, or NOT_MEASURED>
  Clean worker termination proof: <how verified, or NOT_MEASURED>
  Checkpoint consistency proof: <how verified, or NOT_MEASURED>
  Elapsed time (T0->T1, seconds): <value>
  Dataset used: <table(s)/row count>
  Evidence location: <file/log path>

RESULT 2 — MIGRATION_ACCURACY
  Status: PASS | FAIL
  Accuracy: <XX.XXXX%>   <- must be exactly 100.0000% for PASS
  Expected rows: <value>
  Matched rows: <value>
  Source-only (missing) rows: <value>
  Target-only (extra) rows: <value>
  Value-mismatch (corrupted) rows: <value>
  Dataset used: <table(s)/row count>
  Evidence location: <file/log path>

RESULT 3 — ORACLE_TO_POSTGRESQL_TRANSLATION_ACCEPTANCE
  Status: PASS | FAIL | BLOCKED
  Supported-object denominator: 50 (25 procedures + 25 functions) -- re-verify this number yourself first
  Correctly translated: <value> / 50
  Acceptance: <XX.XXXX%>   <- must be exactly 100.0000% for PASS
  Per-object results: <link to detailed table in your final report>
  Unsupported objects (out of denominator): triggers=<26>, packages=<24> -- correctly detected as unsupported: <yes/no + evidence>
  Out-of-scope objects (out of denominator): views=<32>, materialized_views=<4>, sequences=<40>
  Physical PostgreSQL compilation: PASS | FAIL | EXTERNAL_BLOCKED
  Cross-engine semantic equivalence: PASS | FAIL | EXTERNAL_BLOCKED
  Known defects affecting result: <e.g. T-SQL @variable leakage, if it affected any object>
  Evidence location: <file/log path>
```

---

## SECTION 19 — REPORT FILE FOR NEW SESSION

Create **`tests/fixtures/estate/AKAAL_FINAL_THREE_METRIC_ACCEPTANCE_REPORT.md`** — note this is a **DIFFERENT** file from this handoff document (`AKAAL_FINAL_THREE_METRIC_TEST_HANDOFF.md`, which you are reading now and must not overwrite).

---

## SECTION 20 — EXACT COMMANDS/PATHS

| Purpose | Command/Path |
|---|---|
| Python interpreter (no bare `python` on PATH) | `.venv/Scripts/python.exe` |
| Reset the estate | `.venv/Scripts/python.exe -m tests.fixtures.estate.reset <action>` — verify valid `<action>` values by reading `tests/fixtures/estate/reset.py`'s dispatch logic yourself; default if omitted is `"all"` |
| Rebuild the estate baseline | `.venv/Scripts/python.exe -m tests.fixtures.estate.build_estate baseline` (~175s) |
| Invoke canonical parallel migration | NOT ESTABLISHED — NEW SESSION MUST DISCOVER READ-ONLY BEFORE EXECUTION (the only wired call site is hardcoded to `max_workers=1`, per §3; you may need to write a new, additive test that calls `akaal.replication.scheduling.parallel_scheduler.ParallelReplicationScheduler` and `akaal.replication.partitioning.range_partitioner.RangePartitioner` directly with `max_workers>1` to get a genuine parallel run — verify this is achievable without modifying production code before proceeding) |
| Collect worker/partition evidence | NOT ESTABLISHED — NEW SESSION MUST DISCOVER READ-ONLY BEFORE EXECUTION (depends on how you construct the parallel test above) |
| Independently verify source/target row state | Direct `sqlite3` queries against the real `.sqlite` files (e.g. `sqlite3.connect(path).execute('SELECT COUNT(*) FROM "table"')`) — do not trust AKAAL's own self-reported counts alone; cross-check independently |
| Invoke canonical translation | `from akaalEngine.schema.procedural.parsers.plsql import PLSQLParser` / `.parsers.tsql import TSQLParser` / `.emitters.plpgsql import PLpgSQLEmitter` — construct and call these directly against each of the 176 corpus objects (verify current constructor/method signatures by reading the files yourself, they were not exhaustively re-verified in this handoff) |
| Enumerate the corpus | See §9's exact Python snippet |
| Access expected truth | `tests/fixtures/estate/plsql_corpus/expected_truth.py` (read-only; do not modify) |
| Locate PostgreSQL/Oracle config, if present | None found at handoff time (§13/§14) — re-check your own environment |
| Fixture self-tests | `.venv/Scripts/python.exe -m pytest tests/fixtures/estate/selftest/ -v` (26 tests, verified passing at handoff time — re-run yourself) |
| Existing translation-machinery tests | `.venv/Scripts/python.exe -m pytest tests/unit/engine_intelligence/test_p7c11_sql_translation.py tests/unit/engine_schema/test_aoir_ast_pipeline.py -v` |
| Existing M1-M8 targeted tests (for context only, not part of your 3-metric task) | `.venv/Scripts/python.exe -m pytest tests/unit/engine/test_plan_driven_execution.py tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py -v` |
| Relevant reports | See §1's report-path list |

---

## SECTION 21 — KNOWN RISKS/FINDINGS (consolidated, not to be fixed by you)

- **M1-M8 corrected runtime path**: real and tested against the local SQLite estate (`INTEGRATION_PROVEN`), but the correction campaign's own final verdict is "FINAL ACCEPTANCE RETEST CANDIDATE," not "OWNER ACCEPTED & FROZEN." Your three-metric test IS effectively part of that independent retest.
- **Parallel migration wiring is thin at its one production call site**: `max_workers=1`, `total_rows=1000` (hardcoded, not real), `strategy=SINGLE_STREAM` in `migration_steps.py::DataTransportStep` — see §3 for full detail. The underlying `ParallelReplicationScheduler` primitive is real, but unexercised as genuinely parallel in production as currently wired.
- **M4 (incremental/watermark) state**: real, fault-injection-tested (crash-window A and B both physically proven per `M1_M8_CORRECTION_REPORT.md` §6), but the CDC source is a test-only seam, not a live upstream listener — not directly relevant to your 3 metrics but worth knowing if your migration test scope touches M4.
- **Historical throughput artifact fabrication, confirmed present in `scripts/stage3_flagship_ora2pg.py`**: `peak_throughput = avg_throughput * 1.45` (a fabricated multiplier) and hardcoded `peak_ram_mb`/`peak_cpu_pct` constants. Do not use this script or its methodology for anything in your report.
- **Translation corpus never-executed status**: all 176 objects, confirmed this session, have never been run through the real translator by any process in this repository. Your RESULT 3 will be the FIRST real execution.
- **T-SQL `@variable` leakage**: CURRENT_CONFIRMED, unfixed defect in the lexer (`@` treated as valid identifier character). Will likely affect any T-SQL-sourced object you translate; check for it explicitly per object.
- **Trigger/package unsupported status**: by design, self-disclosed, not a defect to "fix" — correctly excluded from the 50-object PASS denominator, but must still be reported as correctly-or-incorrectly *detected* as unsupported.
- **PostgreSQL/Oracle physical compilation and cross-engine semantic equivalence**: no reachable instance of either found configured in this repository at handoff time — expect `EXTERNAL_BLOCKED` for §13/§14 unless your actual runtime environment differs.
- **Do not fix any of the above.** List them in your final report exactly as you find them, updated with your own fresh verification.

---

## SECTION 22 — NO PREDETERMINED PASS

The owner's **target** is 100% on migration accuracy and 100% on translation acceptance. **This is a target, not a pre-known result.** You must not assume, claim, or write anywhere in your report that AKAAL "is" 100% accurate or "is" a 100%-acceptable translator before you have actually run the measurements yourself. Report the ACTUAL result you observe — PASS, FAIL, or BLOCKED — even if it is not 100%. A report that assumes the answer before measuring is not an acceptance test; it is a rubber stamp, and is explicitly prohibited.

---

## SECTION 23 — (handoff-writing session's own final response format — not part of this file's obligations to you, informational only)

*(This section exists only so a human reviewing this handoff understands what the handoff-writing session reported back to its own operator. It is not an instruction to you, the new session.)*
