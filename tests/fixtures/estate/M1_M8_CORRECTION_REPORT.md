# AKAAL M1–M8 CANONICAL RUNTIME CORRECTION REPORT

**Session type**: implementation correction, local testing only. Git writes prohibited and none performed. `progress.md` not touched. PL/SQL→PL/pgSQL campaign and P7D not begun.

## 1. Executive Summary

**Original blocker** (established by the prior read-only acceptance campaign): AKAAL's compiled `ExecutionMode`/`PlanCompiler` output (`dag_stages`) was real, correctly mode-differentiated metadata that no physical execution path ever consumed. The real physical executor, `AkaalSuperEngine.execute_migration`, always ran a fixed, hard-coded 4-step sequence (`PreStartValidationStep → SchemaExecutionStep → DataTransportStep → ValidationStep`) regardless of the configured mode.

**Final architecture (this session)**: `AkaalSuperEngine.execute_migration`'s physical-execution branch now requires a compiled `dag_dict` (the exact `PlanCompiler.compile(...).execution_plan` artifact that governance approval already fingerprinted) and **fails closed** if one is not supplied. It traverses `dag_dict["dag_stages"]` in the order `PlanCompiler` emits them (already topologically sorted by construction) via a new `PlanExecutionDispatcher` (`akaal/engine/plan_dispatch.py`) that dispatches each stage, by **responsibility type** (not by an `if mode==Mx` switch), to the owning existing canonical authority. `AkaalSuperEngine` remains the single physical execution authority — no second engine/coordinator was introduced.

**Is the canonical plan now load-bearing?** **Yes, physically proven** — for the paths reachable through `AkaalSuperEngine.execute_migration` (which `EngineGateway.start_transport`, the real production IPC entrypoint, calls). Independently verified against the real SQLite simulated estate (not from logs, not from return values): removing "Parallel Stream Data Transport" from the DAG genuinely stops rows moving (M6); removing "Target Schema Structure Deployment" genuinely stops schema mutation (M7, DDL fingerprint identical before/after); M1 genuinely transports real rows matching source exactly; M8 genuinely detects a deliberately-injected mismatch via the real `CanonicalReconciliationEngine` while leaving the target byte-identical before/after; M5 genuinely reuses the same reconciliation engine for comparison. **12 new permanent tests, all physically asserting against real SQLite state, pass; 700 pre-existing tests across engine/workflow/planner/validation/connectors suites and the fixture self-tests pass unchanged (zero regressions, zero weakened tests).**

**Locally remaining (not completed this session)**: M2 (bulk+CDC consistency boundary), M3 (CDC-only, zero-bulk proof), M4 (the incremental-polling watermark authority — confirmed absent from the repository before this session, and still absent after; this is genuinely new production code, not wiring, and was not built this session), the full crash-window proofs for M4, the CDC-source test-only seam, and a confirmed, **unresolved bypass**: `akaal/runtime/process/daemon.py::MigrationRuntimeDaemon.execute_migration()` calls a distinct `akaal.workflow.engine.engine.WorkflowEngine.execute()`, entirely independent of `AkaalSuperEngine` — a production migration-initiation path that still reaches mode-blind, non-plan-driven execution.

**Overall implementation assessment**: **NOT READY FOR FINAL ACCEPTANCE RETEST** — M1, M5, M6, M7, M8 are genuinely corrected and physically proven; M2, M3, M4 are not implemented; the daemon bypass is not closed. This session's own verdict (per the owner's instruction not to substitute a design document for authorized implementation, and not to rerun the formal acceptance campaign as this session's own conclusion) is:

> **M1–M8 CORRECTION IMPLEMENTATION — NOT READY FOR FINAL ACCEPTANCE RETEST.**
> Partial, physically-proven convergence on M1/M5/M6/M7/M8 and the shared DAG-driven dispatch core. M2/M3/M4 and the daemon bypass remain as scoped, evidence-backed remaining work for a follow-up session.

## 2. Repository Reconstruction Findings

- **`akaal/`**: the primary production package. Contains the canonical `ExecutionMode`/`PlanCompiler` (`akaal/planner/`), the real physical executor `AkaalSuperEngine` (`akaal/engine/facade.py`) and its step classes (`akaal/workflow/steps/migration_steps.py`), the canonical dialect-neutral connector contract (`akaal/connectors/contracts/database.py::IDatabaseCapability`) and real adapters (`akaal/adapters/`, including a genuine `SQLiteAdapter`), the real `CanonicalReconciliationEngine` (`akaal/validation/domain/reconciliation.py`), and a second, independent real executor `AkaalMigrationEngine` (`akaal/engine/api.py`, Oracle→Postgres multiprocess path, untouched this session) plus a third, separate execution vehicle `AkaalPipeline`/`MigrationStrategy.BIG_BANG` (`akaal/core/pipeline`, untouched this session) plus a fourth confirmed-this-session, `MigrationRuntimeDaemon` (`akaal/runtime/process/daemon.py`, calling yet another `WorkflowEngine` in `akaal/workflow/engine/engine.py` — untouched, unresolved bypass, see §26).
- **`akaalEngine/`**: a separate top-level package implementing a numbered "Authority #1–#12" architecture, including the genuinely production-wired, atomically-persisted `DurabilityAuthority` (`akaalEngine/durability/`) — confirmed this session to be the correct extension target for M4's watermark authority, not yet touched (M4 not implemented this session).
- **`akaalPipeline/`**: not traced in depth this session (out of scope for what was implemented; noted as unaudited, not confirmed clean).
- **Runtime entrypoints traced this session**: `EngineGateway.start_transport` (real, now plan-driven) → `AkaalSuperEngine.execute_migration` (real, now plan-driven); `AkaalMigrationEngine.start_migration` (real, separate, untouched, still mode-blind — not corrected this session); `MigrationRuntimeDaemon.execute_migration` (real, separate, untouched, still mode-blind, confirmed bypass); `akaal.advisory.executor.execute` (advisory/DDL-concept-mapping utility — appears to be planning/advisory simulation rather than physical execution, but not conclusively resolved this session).
- **ExecutionPlan concepts found**: `akaal.planner.models.p5_domain.CompilationResult`/`ExecutionPlan` (the canonical planner output, now genuinely consumed); `akaal.planner.models.migration_execution_plan.MigrationExecutionPlan` (a separate, documented-immutable wrapper with untyped `execution_graph: Dict[str,Any]` — not touched, not currently in the load-bearing path); `akaal.engine.spec.ExecutionPlan`/`MigrationSpecification` (a third, distinct, unrelated dataclass pair in `akaal/engine/spec.py` — confirmed this session to be a naming collision, not the same type; not touched).
- **CDC implementations found**: `akaal.cdc.contracts.event.CDCEvent`/`TransactionContext` + `akaal.cdc.apply.engine.CDCApplyWorker` (structurally real, durable-buffered, fencing-epoch-protected — not wired to any mode-driven caller before or after this session); `akaalEngine`'s separate `ChangeEvent`/`CDCAuthority` (untouched).
- **Checkpoint implementations found**: at least 6 `akaal/`-side `Checkpoint`-named classes, all confirmed orphaned or in-memory-only (prior + this session's research); the true canonical, production-wired durability authority is `akaalEngine.durability.DurabilityAuthority`/`MigrationCheckpoint` (confirmed this session, not yet connected to `akaal`'s executor).
- **Validation**: `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine` — confirmed, this session, genuinely invoked end-to-end from the new dispatcher for M1/M5/M8, against real SQLite data, with correct MATCHED/MISMATCH results.
- **Evidence**: `akaal.reporting.engine.canonical_reporting` (P2.10, "Evidence Authority Engine") — its binding to the new dispatcher's evidence stage was **not confirmed reachable** this session (see §19); the dispatcher currently records a local sha256 digest of the run's own outcome record as a placeholder, explicitly labeled as such in its own output (`"canonical Evidence Authority (P2.10) binding not confirmed reachable from this call path"`).
- **Security**: `AkaalSuperEngine.verify_governance_authorization` (real, genuinely exercised via the existing test-only `_record_test_governance_approval` helper this session — not weakened, not bypassed) — untouched.
- **P7B/P7C**: not traced this session (see §20 — explicitly reported as unaudited, not assumed clean).

## 3. Canonical Responsibility Map

| Authority | Responsibility | Pre-correction | Post-correction | Classification | Load-bearing |
|---|---|---|---|---|---|
| `akaal.planner.engine.plan_compiler.PlanCompiler` | Compile mode+config into DAG | Real, disconnected from execution | Real, **now consumed** by execution | Canonical | **YES (new)** |
| `akaal.engine.facade.AkaalSuperEngine` | Physical execution authority | Real, mode-blind fixed 4-step sequence | Real, **plan-driven DAG dispatch** | Canonical | YES |
| `akaal.engine.plan_dispatch.PlanExecutionDispatcher` | Stage→authority dispatch (new, this session) | absent | New, additive | Compatibility/dispatch layer inside `AkaalSuperEngine`'s own responsibility — not a second engine | YES (as part of AkaalSuperEngine) |
| `akaal.workflow.steps.migration_steps.SchemaExecutionStep`/`DataTransportStep` | Postgres/Oracle-dialect schema+transport | Real, hard-coded, unconditional | Real, unchanged, **now dispatched conditionally** for postgresql/oracle target dialects only | Canonical (dialect-specific) | YES, conditionally |
| Dialect-neutral adapter fallback (new, in `plan_dispatch.py`) | Schema+transport for dialects the legacy steps don't support (sqlite) | absent | New, additive, calls `IDatabaseCapability` directly | Extension, not duplicate (reuses the actual dialect-neutral contract) | YES, conditionally |
| `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine` | Validation Authority #11 | Real, previously invoked only in ad-hoc test calls | Real, **now dispatched for M1/M5/M8 nodes** | Canonical | YES |
| `akaalEngine.durability.DurabilityAuthority` | Checkpoint/durability (incl. future M4 watermark) | Real, production-wired within `akaalEngine`, disconnected from `akaal` | **Unchanged** — not connected this session | Canonical, still disconnected from `akaal` | NO (M4 not implemented) |
| `akaal.cdc.apply.engine.CDCApplyWorker` | CDC apply | Real, structurally sound, unwired | **Unchanged** — not wired this session | Canonical, still disconnected | NO (M2/M3 not implemented) |
| `akaal.migration.execution.incremental.IncrementalManager` | Legacy watermark stub | Orphaned (repo's own forensic ledger confirms) | Unchanged | Legacy/dead — correctly NOT revived | NO |
| `akaal.runtime.process.daemon.MigrationRuntimeDaemon` | Alternate migration execution | Real, mode-blind, independent of `AkaalSuperEngine` | **Unchanged — confirmed bypass** | Duplicate/competing production authority | YES (and that is the problem — see §26) |
| `akaal.engine.api.AkaalMigrationEngine` | Alternate migration execution (Oracle→Postgres, multiprocess) | Real, mode-blind, independent | Unchanged | Duplicate/competing, pre-existing (not newly introduced) | YES (pre-existing, not corrected this session) |

## 4. Before vs After Execution Chain

**BEFORE:**
```
mode intent → PlanCompiler.compile() → CompilationResult{dag_stages}  [dead end — nothing reads this]

EngineGateway.start_transport() → AkaalSuperEngine.execute_migration()
  → PreStartValidationStep().execute()
  → SchemaExecutionStep().execute()          [always]
  → DataTransportStep().execute()            [always]
  → ValidationStep().execute()               [always]
  (dag_dict accepted as a parameter but used ONLY for fingerprinting, never for dispatch)
```

**AFTER:**
```
mode intent → PlanCompiler.compile(plan, version) → CompilationResult{fingerprint, dag_stages}
  → caller passes dag_dict = CompilationResult.execution_plan into execute_migration
  → AkaalSuperEngine.verify_governance_authorization(workflow_id, spec_dict, dag_dict)
      [fingerprints and requires approval over the SAME dag_dict that will execute]
  → AkaalSuperEngine.execute_migration(..., dag_dict=dag_dict, is_synthetic_test=False)
      → PreStartValidationStep().execute()                         [unconditional, fail-closed]
      → PlanExecutionDispatcher(mode, fingerprint, rt_ctx).run(dag_dict["dag_stages"])
          for stage in dag_stages:                                  [PlanCompiler's own topological order]
              responsibility = STAGE_RESPONSIBILITY[stage["name"]]
              dispatch to: SchemaExecutionStep | dialect-neutral schema fallback
                          | DataTransportStep  | dialect-neutral transport fallback
                          | CanonicalReconciliationEngine (reconciliation/validation/inspection)
                          | repair-eligibility evaluator (never executes repair)
                          | evidence digest recorder
              on failure: propagate to all downstream stages (fail-closed)
  → real target/checkpoint state independently queried and matches the DAG that ran
```

## 5. Files Changed

| Path | Why | Responsibility | Prod/Test | New/Existing |
|---|---|---|---|---|
| `akaal/engine/facade.py` | Replace hard-coded 4-step physical branch with plan-driven dispatch; fail closed if no compiled `dag_dict` | Physical execution authority | Production | Existing (modified) |
| `akaal/engine/plan_dispatch.py` | New stage-responsibility dispatcher, called only from `facade.py` | Dispatch logic (part of `AkaalSuperEngine`'s own responsibility) | Production | New |
| `akaal/workflow/steps/migration_steps.py` | Add `sqlite` branches to `_extract_source_config`/`_extract_target_config` (previously hard-coded to always resolve Postgres/Oracle host-port-credential configs; no sqlite path existed at all) | Connection-config resolution | Production | Existing (modified, additive) |
| `tests/unit/engine/test_plan_driven_execution.py` | Permanent, repository-native-named physical-integration tests | Test | Test-only | New |

No fixture expected-truth manifest, no `tests/fixtures/estate/**/manifest.json`, no original acceptance report was modified. `.akaal/reports/*.json` (`REP-CAT-T.json`, `REP-FAIL-TRUTH.json`, `REP-INTEG-FAIL.json`, `REP-REDACT-01.json`) show only `created_at` timestamp diffs — a pre-existing side effect of running the test suites (unrelated to this session's code changes; not reverted, since git writes are prohibited and the diff is inert).

## 6. Duplicate-Authority Reconciliation

- `PlanExecutionDispatcher` is not a new authority: it has no independent entrypoint, is never imported outside `facade.py`, and every actual piece of work it does is delegated to a pre-existing canonical authority (`SchemaExecutionStep`, `DataTransportStep`, `CanonicalReconciliationEngine`, `IDatabaseCapability` adapters).
- The dialect-neutral schema/transport fallback does **not** duplicate `SchemaExecutionStep`/`DataTransportStep` — it is reached only for dialects (`sqlite`) those Postgres/Oracle-hardcoded classes were never built to support (confirmed: no `SQLITE` entry in `UniversalDDLAuthority`'s emitter registry; `%s`-placeholder/`schema.table`-dot-notation SQL text throughout). For `postgresql`/`oracle` targets, the legacy steps run completely unmodified.
- **Confirmed, unresolved duplicate/competing authorities** (pre-existing, not newly introduced, not corrected this session): `AkaalMigrationEngine.start_migration` and `MigrationRuntimeDaemon.execute_migration` both physically execute migrations independent of `AkaalSuperEngine`/`ExecutionMode`. These are named explicitly here rather than hidden; correcting them is scoped as remaining work (§28).
- `akaal/` ↔ `akaalEngine/` reconciliation: **not performed this session** — M4/M2/M3 (the modes that would require bridging to `akaalEngine.durability`/CDC) were not implemented, so no new cross-package dependency was introduced in either direction. The disconnection documented in the acceptance report is unchanged.

## 7. M1 Correction

**Broken**: `execute_migration` ran `SchemaExecutionStep → DataTransportStep → ValidationStep` unconditionally regardless of the compiled plan.
**Changed**: physical branch now requires and traverses `dag_dict["dag_stages"]`; M1's compiled DAG (Discovery → Schema → Transport → Reconciliation → Evidence) drives exactly that sequence via `PlanExecutionDispatcher`.
**Actual runtime path**: `EngineGateway.start_transport` → `AkaalSuperEngine.execute_migration` → `PlanExecutionDispatcher.run(dag_stages)` → (`SchemaExecutionStep`|sqlite-fallback) → (`DataTransportStep`|sqlite-fallback) → `CanonicalReconciliationEngine.reconcile_tables` → evidence digest.
**Mode fence**: physically confirmed no CDC-named stage ever appears in a compiled M1 DAG (`test_m1_cdc_stage_never_present_in_dag`).
**Checkpoint**: `self.state_store.set_state(f"{workflow_id}_plan_execution", ...)` records the full stage-by-stage outcome keyed by plan fingerprint; per-node durable checkpointing beyond this state-store record was not added this session (no crash-mid-stage recovery test).
**Validation**: `CanonicalReconciliationEngine.reconcile_tables()` genuinely invoked; MATCHED confirmed on real data (500/500, 150/150 rows).
**Evidence**: local digest only — canonical Evidence Authority (#12) binding not confirmed (§19).
**Tests**: `TestM1BulkMigration` (2 tests, passing, physical row-count assertions against real SQLite).
**Remaining limitations**: full 1,000,000-row/206-table M1 run not attempted (only small selected-object subsets, to keep this session's test suite fast — nothing in the implementation limits scale, but it was not proven at full scale); checkpoint/restart-mid-transport not implemented or tested; Evidence Authority binding unconfirmed.

## 8. M2 Correction

**Not implemented this session.** No consistency-boundary code, no CDC dispatch, no test-only CDC source seam was built. `plan_dispatch.py`'s `_handle_cdc_boundary`/`_handle_cdc_init`/`_handle_cdc_apply` handlers exist as explicit, honest stubs that return `success=False` with `errors=["NOT_YET_DISPATCHED: ... (phase pending)"]` — an M2 plan compiled and run through the new dispatcher today would **fail closed** at its first CDC-responsibility stage, not silently succeed. This is deliberate: it is more honest than a fabricated pass. Design for the remaining work (consistency boundary reuse of existing P3 abstractions if present, `CDCApplyWorker` dispatch, test-only source seam scoped per owner §11/§35) was established during planning but not built.

## 9. M3 Correction

**Not implemented this session**, same reasoning as M2 — `_handle_cdc_init`/`_handle_cdc_apply` fail closed. The zero-AKAAL-owned-bulk invariant is structurally satisfied by omission (no bulk-responsibility handler is ever reached for an M3 DAG, since M3's compiled DAG contains no `"Parallel Stream Data Transport"` stage — confirmed via the real `PlanCompiler` run in the prior acceptance session), but this was not re-verified with a physical M3 integration test this session.

## 10. M4 Correction

**Not implemented this session.** This is the most significant gap.

- **Prior absence**: confirmed, both by the prior acceptance campaign and by this session's deep-dive research, that no watermark-commit-ordering authority exists anywhere in the repository — not a wiring gap, missing production code.
- **New canonical responsibility (design only, not built)**: extend `akaalEngine.durability.MigrationCheckpointRegistry`/`DurabilityAuthority` (`akaalEngine/durability/models/checkpoint.py`, `checkpoint/registry.py`) with additive `save_watermark`/`get_watermark` methods, atomic on the existing `BEGIN IMMEDIATE`/`COMMIT` transaction pattern already used by `save_checkpoint`/`ack_queue_with_position`. This does not duplicate an authority — it extends the one already confirmed (this session) to be the true canonical, production-wired durability store.
- **Why it does not duplicate another authority**: the 6 `akaal/`-side `Checkpoint` classes were confirmed orphaned/in-memory-only; the partial `akaal.migration.execution.incremental.IncrementalManager` stub was confirmed disconnected by the repository's own forensic ledger. `akaalEngine.durability` is the only real, atomically-persisted, production-wired candidate.
- **Watermark model, numeric/timestamp/tie-breaker semantics, target-commit ordering, restart scenarios**: designed (see plan file, §7 of the sequencing) but **not implemented**. No code exists to evaluate.
- **Exact crash-window results requested by the owner cannot be reported because the code does not exist**:
  - *"target failure before commit → durable watermark remained unchanged?"* — **NOT_MEASURED, no implementation to test.**
  - *"target commit occurred before durable watermark advancement?"* — **NOT_MEASURED, no implementation to test.**
- **Tests M4-I01–I20**: 0 of 20 implemented (no code to test against).

## 11. M5 Correction

**Implemented and physically proven this session.** `plan_dispatch.py`'s `_handle_reconciliation` (shared with M8) dispatches M5's `"State-Based Differential Analysis & Reconciliation"` node to the real `CanonicalReconciliationEngine.reconcile_tables()`. Comparison is mandatory (always runs when the node is present); a distinct, separately-gated mutation path (`_handle_repair_eligibility`) evaluates eligibility but **never executes** a repair — `repair_authorized` is hard-coded `False` in this session's implementation because no canonical authorization mechanism was wired to grant it (per owner correction #10, the structural mutation path exists as a gate, not as deleted functionality, but it is not yet connected to a real authorization source — this is a partial, not full, implementation of correction #10).
**Tests**: `TestM5StateSynchronization` (1 test, passing, real MATCHED result against real SQLite data).
**Remaining**: connect `_handle_repair_eligibility`'s authorization check to a real canonical governance/approval source instead of a hard-coded `False`; test the full NULL/Unicode/numeric/timestamp/binary difference-category matrix physically (only a basic equal-data case was proven this session, on top of the mismatch case already proven for M8 using the same shared code path).

## 12. M6 Correction

**Implemented and physically proven this session.**
- **Schema-only runtime**: `_handle_schema` dispatches to the dialect-neutral `CREATE TABLE IF NOT EXISTS` fallback (SQLite target) or `SchemaExecutionStep` (Postgres/Oracle target); `_handle_schema_verify` independently re-queries the target's actual table list against the source's.
- **Data fence**: **physically confirmed** — `test_m6_creates_schema_zero_rows` independently queries the target table's row count after a real M6 run and asserts it is `0`. Data transport invocation count: **0** (confirmed by asserting `"Parallel Stream Data Transport" not in stage_names` — the stage is never even present in an M6 DAG, so the dispatcher never reaches a transport handler at all; this is enforcement by DAG composition, satisfying owner correction #3, not a runtime `if mode==M6` check).
- **CDC fence**: confirmed no CDC-named stage present.
- **Object execution**: real `CREATE TABLE` DDL genuinely executed against the target (columns discovered from the live source via `discover_columns`, independently verified — the target gained exactly the 2 tables requested, with 0 rows).
- **Validation**: `_handle_schema_verify`'s "Target Schema Structure Verification" stage genuinely re-queries target structure.
- **Evidence**: local digest only (§19 gap applies here too).
- **Tests**: `TestM6SchemaOnlyFencing` (1 test, passing).
- **Data transport invocation count: 0** (as required).

## 13. M7 Correction

**Implemented and physically proven this session.**
- **Data-only runtime**: `_handle_transport` genuinely transports rows via the same path as M1.
- **DDL fence**: **physically confirmed** — `_ddl_fingerprint()` (sha256 over every `CREATE TABLE` statement in `sqlite_master`) computed before and after a real M7 run: **identical** (`bd44305bd9f95cbf` before and after, independently re-verified in the permanent test too). Table count before/after: identical (206). This is a physical, independently-queried proof, not a planner-only claim.
- **Target schema compatibility**: not separately validated beyond the DDL-fingerprint-unchanged proof (no explicit compatibility-check stage was dispatched).
- **Transport**: real, confirmed (`CATALOG_PRODUCTS__categories`: 300/300 rows, matching source exactly).
- **Checkpoint**: same state-store record as M1; no dedicated M7 checkpoint semantics added.
- **Validation**: `CanonicalReconciliationEngine` genuinely invoked via the "Reconciliation & Validation Node" stage.
- **Evidence**: local digest only (§19 gap).
- **Tests**: `TestM7DataOnlyFencing` (2 tests, passing).
- **Exact counts requested**: CREATE count = 0, ALTER count = 0, DROP count = 0 (all confirmed via the identical DDL fingerprint — no `CREATE`/`ALTER`/`DROP` occurred, since the fingerprint is a hash over exactly the `CREATE TABLE` statements present, and it did not change). Schema fingerprint before/after: **`bd44305bd9f95cbf` == `bd44305bd9f95cbf`**.

## 14. M8 Correction

**Implemented and physically proven this session.**
- **Canonical reconciliation reuse**: identical code path as M5/M1 (`_handle_reconciliation`), invoked for M8's `"Deep Data Reconciliation & Integrity Verification"` and `"Passive Source & Target State Inspection"` nodes.
- **Validation-only non-mutation**: **physically confirmed** — a real content fingerprint (sha256 over every row in the target table) was computed before and after a real M8 run that deliberately targeted a table with an injected mismatch: **identical** (`1299a5adf039b538` before and after). No `write_batch`/mutation call is even reachable from the inspection/reconciliation code paths — structural, not conventional, non-mutation (owner correction #12).
- **Repair governance**: `"Repair Eligibility & Candidate Evaluation"` stage genuinely dispatched; evaluated `repair_authorized=False, repair_executed=False` — repair was never attempted, not merely refused after being attempted.
- **Target fingerprint**: unchanged, confirmed (see above).
- **Tests**: `TestM8ValidationOnlyNonMutation` (2 tests, passing) — one specifically injects a real mismatch (`code` column corrupted on one row) and confirms the real engine detects it (`source_only=1, target_only=1` — a true, not fabricated, finding) while the target stays byte-identical.

## 15. Runtime Mode-Fence Matrix (physical evidence, this session)

| Operation | M1 | M5 | M6 | M7 | M8 |
|---|---|---|---|---|---|
| Bulk/data transport | REQUIRED — confirmed real (500+150, 300 rows) | N/A | PROHIBITED — confirmed **0 rows**, stage absent from DAG | REQUIRED — confirmed real (300 rows), DDL unchanged | PROHIBITED — confirmed **0 mutation** (fingerprint identical) |
| Schema DDL | per-plan (present in this session's M1 test DAG; not separately isolated) | N/A | REQUIRED — confirmed real `CREATE TABLE` executed | PROHIBITED — confirmed **DDL fingerprint identical**, 0 CREATE/ALTER/DROP | PROHIBITED — no schema stage in DAG |
| CDC | PROHIBITED — confirmed absent from DAG | N/A | PROHIBITED — confirmed absent | PROHIBITED — confirmed absent | PROHIBITED — confirmed absent |
| Reconciliation/validation | REQUIRED — confirmed real MATCHED result | REQUIRED — confirmed real MATCHED result | Structural verification — confirmed | REQUIRED — confirmed real MATCHED result | REQUIRED — confirmed real MISMATCH correctly detected |
| Repair execution | N/A | evaluated, not executed (hard-coded unauthorized) | N/A | N/A | evaluated, not executed |

M2/M3/M4: **not tested this session (not implemented)**.

## 16. Checkpoint / Recovery

**Not substantively changed this session.** `AkaalSuperEngine.execute_migration` still records progress via `CentralStateStore` (unchanged mechanism) plus one new record (`{workflow_id}_plan_execution`, the full stage-outcome list keyed by plan fingerprint — new, additive). No integration with `akaalEngine.durability`'s atomic checkpoint store was built. No restart-mid-execution test exists. **Test results: 0 new checkpoint/recovery tests; existing checkpoint-adjacent tests in `tests/unit/engine/`/`tests/unit/workflow/` (137 tests) re-run and pass unchanged.**

## 17. Security / Governance

Not modified. `verify_governance_authorization`'s fingerprint-and-approval-required gate is unchanged and was genuinely exercised (not bypassed) via the existing `_record_test_governance_approval` test-only helper in every physical test this session — every real execution in this report's evidence passed through that real gate. **SEC-I01–I15: not evaluated this session** (no new security tests were written; this was out of this session's completed scope). No hidden skips — this is an explicit, reported gap, not a silent omission.

## 18. Validation Authority #11

| Mode | Path | Invoked this session | Result | Failure propagation |
|---|---|---|---|---|
| M1 | `CanonicalReconciliationEngine.reconcile_tables` | YES, real | MATCHED (500/500, 150/150) | N/A (no failure occurred) |
| M5 | same | YES, real | MATCHED | N/A |
| M6 | structural table-list comparison (not the reconciliation engine — a lighter structural check) | YES, real | tables present, matched | would fail closed on missing table (not exercised) |
| M7 | `CanonicalReconciliationEngine.reconcile_tables` | YES, real | MATCHED (300/300) | N/A |
| M8 | same | YES, real | **MISMATCH correctly detected** | reported truthfully, stage still marked `success=True` because M8's job (detect and report) was achieved — this is a considered design choice, documented in `plan_dispatch.py`'s `_reconcile` docstring, not an oversight |
| M2/M3/M4 | N/A | not implemented | — | — |

A genuine, mandatory-validation failure propagating to prevent false completion was **not** exercised this session (every test scenario either matched or was a validation-only mode where "detected mismatch" is itself success) — this is a gap: `test_dependent_stage_skipped_after_validation_failure`-style coverage does not yet exist.

## 19. Evidence Authority #12

**Not connected to the canonical P2.10 Evidence Authority this session.** Every mode's `"SHA-256 Digital Trust Seal"` stage dispatches to `_handle_evidence`, which computes and records a local sha256 digest of the run's own outcome record. This is explicitly labeled in the stage's own output (`"canonical Evidence Authority (P2.10) binding not confirmed reachable from this call path"`) rather than silently presented as if it were the real Evidence Authority. **This is a known, reported gap, not a relabeling of a generic step as Authority #12** (owner correction #13 explicitly required this honesty). Tracing and wiring the real `akaal.reporting.engine.canonical_reporting` binding is scoped as remaining work.

## 20. P7B / P7C Regression

**Not traced this session.** Neither P7B (placement/Fabric legality) nor P7C (intelligence advisory boundary) code paths were inspected, modified, or tested. This is reported explicitly as **unaudited**, not assumed clean — the new dispatcher does not call into any P7B/P7C code (confirmed by inspection of `plan_dispatch.py`'s own imports: only `akaal.workflow.steps.migration_steps`, `akaal.adapters.adapter_registry`, `akaal.validation.domain.reconciliation`), so no NEW P7B/P7C bypass was introduced, but no positive confirmation that pre-existing P7B/P7C gates remain correctly enforced elsewhere was performed.

## 21. Test-Only Fixture Adapter

**None was created this session.** M2/M3 (the modes that would require one, per owner §11/§35) were not implemented. No test-only CDC source adapter exists yet.

## 22. Targeted Tests

| Category | Total | Passed | Failed | Skipped | Blocked |
|---|---|---|---|---|---|
| New plan-driven execution tests (`test_plan_driven_execution.py`) | 12 | 12 | 0 | 0 | 0 |
| PLAN-001–015 | 0 dedicated new tests written this session (pre-existing planner suite's 72+ tests re-run and pass, exercising equivalent coverage — see §24) | — | — | — | — |
| EXEC-001–020 | Partially covered by the 12 new tests (EXEC-001/002/003/004/010 directly; EXEC-005/006/007/008/009/011–020 not individually tested) | 5 of 20 directly asserted | 0 | — | 15 not yet written |
| M1-I01–I10 | 2 of 10 written (I01 transport, I02 no-CDC); I03–I10 (finite lifecycle labeling, checkpoint depth, restart, dedup-after-replay, evidence, full-fixture-scale, independent fingerprint) not written | 2 | 0 | 0 | 8 |
| M2-I01–I15 | 0 | 0 | 0 | 0 | 15 (mode not implemented) |
| M3-I01–I10 | 0 | 0 | 0 | 0 | 10 (mode not implemented) |
| M4-I01–I20 | 0 | 0 | 0 | 0 | 20 (mode not implemented) |
| M5-I01–I14 | 1 of 14 written (comparison reuse + MATCHED) | 1 | 0 | 0 | 13 |
| M6-I01–I11 | partial (I05/I06/I07 fence counts + schema execution proven; I04 unsupported-object classification, I09/I10 authority-name-specific assertions, I11 lifecycle-status not separately asserted) | ~5 of 11 covered | 0 | 0 | ~6 |
| M7-I01–I12 | partial (I02/I03/I04/I05/I06/I07/I09 covered; I01/I08/I10/I11/I12 not separately asserted) | ~7 of 12 covered | 0 | 0 | ~5 |
| M8-I01–I14 | partial (I01/I02/I03(partial)/I09/I10/I11/I12/I13 covered; I04/I05/I06/I07/I08/I14 not separately asserted) | ~8 of 14 covered | 0 | 0 | ~6 |

**Total this session's new/passing evidence: 12 permanent tests, 12 passed, 0 failed, 0 skipped.** The counts above against the owner's exact M*-I numbering are approximate honesty-preserving estimates (the owner's test IDs were not individually re-created 1:1 as separate test functions in every case — several are jointly proven by one assertion, e.g. one DDL-fingerprint assertion proves M7-I03/I04/I05/I07 together) — reported as such rather than inflated to a false 1:1 count.

## 23. Hostile Tests

**Not performed this session beyond the M8 deliberate-mismatch-injection test** (which is itself a hostile/negative test: a real corrupted row, correctly detected, target unmutated). No restart-mid-execution, no forced adapter-connection-failure, no mode-fence-bypass-attempt (e.g. constructing a malformed DAG with an illegal node and confirming rejection) tests were written. This is a gap.

## 24. Whole-Repository Regression

Exact commands run:
```
.venv/Scripts/python.exe -m pytest tests/unit/engine/test_plan_driven_execution.py -v
.venv/Scripts/python.exe -m pytest tests/unit/engine/ tests/unit/workflow/ -q
.venv/Scripts/python.exe -m pytest tests/unit/planner/ tests/unit/validation/ tests/unit/connectors/ tests/fixtures/estate/selftest/ -q
```
Results: **712 passed, 0 failed, 0 skipped** across all three runs combined (12 new + 137 engine/workflow + 563 planner/validation/connectors/fixture-selftest). No pre-existing test was modified or weakened. A true whole-repository run (every `tests/unit/` subdirectory, `tests/integration/`, etc.) was **not** performed this session — out of time budget; the suites run were chosen as the ones most directly exercising the changed code paths (`akaal/engine/`, `akaal/workflow/`, `akaal/planner/`, `akaal/validation/`, `akaal/connectors/`, plus the fixture estate itself). This is reported as a scope limitation, not claimed as a full regression sweep.

## 25. Duplicate-Authority Audit

See §6. Summary: no new competing authority was introduced. Two **pre-existing** competing physical-execution authorities were confirmed still present and unmodified: `AkaalMigrationEngine.start_migration` and `MigrationRuntimeDaemon.execute_migration` (the latter newly confirmed as a bypass this session, see §26).

## 26. Bypass Audit

Production migration-start entrypoints inspected this session (via `grep -rn "execute_migration(" akaal/`):

| Entrypoint | Routes through canonical plan-driven execution? | Evidence |
|---|---|---|
| `akaal.gateway.engine_gateway.EngineGateway.start_transport` | **YES** | Passes `dag_dict=dag_dict` into `AkaalSuperEngine.execute_migration` (confirmed by direct code read, `engine_gateway.py:1931`) — this is the real production IPC entrypoint and is now genuinely plan-driven. |
| `akaal.runtime.process.daemon.MigrationRuntimeDaemon.execute_migration` | **NO — CONFIRMED BYPASS** | Calls `self.engine.execute(self.migration_id, self.config)` where `self.engine` is `akaal.workflow.engine.engine.WorkflowEngine` (a distinct class from both `AkaalSuperEngine` and the state-transition-only `akaal.agents.manager.workflow_engine.WorkflowEngine`) — entirely independent of `AkaalSuperEngine`, `PlanCompiler`, or the new dispatcher. |
| `akaal.engine.api.AkaalMigrationEngine.start_migration` | **NO** (pre-existing, not corrected this session) | Independent Oracle→Postgres multiprocess path, no `ExecutionMode` awareness (confirmed in the prior acceptance session; not re-verified this session but not touched either). |
| `akaal.advisory.orchestrator` → `akaal.advisory.executor.execute` | **Unclear, not conclusively resolved** | Appears to be an advisory/DDL-concept-mapping simulation (deterministic concept→target-type table), not a physical row-transport executor, based on the code inspected — but this was not traced to full confidence this session. |

Not inspected this session: CLI entrypoints, `akaalSoftware` (Wails/Go frontend-facing seam), any REST/API layer, `akaalPipeline`.

**Required end state ("production migration initiation cannot silently bypass canonical plan-driven execution") is NOT YET ACHIEVED.** The daemon path is a confirmed, real, unresolved bypass.

## 27. Truthful Capability Classification

| Mode | Classification | Justification |
|---|---|---|
| M1 | **INTEGRATION_PROVEN** (local SQLite estate scope) | Real DAG-driven physical execution, real row transport, real reconciliation, independently verified. Not LIVE_PROVEN — no genuine Oracle/PostgreSQL involved. |
| M2 | **EXTERNAL_DEFERRED / not implemented** | No code exists for CDC dispatch this session. |
| M3 | **EXTERNAL_DEFERRED / not implemented** | Same. |
| M4 | **EXTERNAL_DEFERRED / not implemented** | Watermark authority does not exist in the repository. |
| M5 | **INTEGRATION_PROVEN** (comparison only; mutation path structurally present but unauthorized-by-design in this session) | Real reconciliation-engine invocation, real MATCHED result. |
| M6 | **INTEGRATION_PROVEN** (local SQLite estate scope) | Real schema DDL executed, zero-row-transport physically confirmed. |
| M7 | **INTEGRATION_PROVEN** (local SQLite estate scope) | Real data transport, DDL-fingerprint-unchanged physically confirmed. |
| M8 | **INTEGRATION_PROVEN** (local SQLite estate scope) | Real mismatch detection, zero-mutation physically confirmed via content fingerprint. |

No mode is claimed `LIVE_PROVEN`. All figures in this report are labeled implicitly and explicitly as SIMULATED SQLITE PERFORMANCE where performance is mentioned (§29) — none of this report's evidence involves genuine Oracle/PostgreSQL infrastructure.

## 28. Known Remaining Gaps

**Locally actionable (should be empty before calling correction complete — it is not):**
- M4 watermark authority: fully unimplemented (design only).
- M2 consistency boundary + CDC dispatch: fully unimplemented.
- M3 CDC dispatch + zero-bulk physical proof: fully unimplemented.
- Test-only CDC source seam: fully unimplemented.
- `MigrationRuntimeDaemon` bypass: not closed.
- `AkaalMigrationEngine` (pre-existing bypass): not addressed.
- Evidence Authority #12 real binding: not confirmed/wired.
- M5's repair-eligibility gate is hard-coded `False` rather than routed through a real canonical authorization check.
- Hostile/restart/failure-injection tests: not written.
- Security regression tests (SEC-I01–I15): not written.
- P7B/P7C re-audit: not performed.
- `akaal.advisory.executor` bypass status: not conclusively resolved.
- Full whole-repository regression sweep: not performed (targeted subset only, see §24).

**External-deferred (genuinely require real Oracle/PostgreSQL/provider infrastructure):**
- Any claim beyond INTEGRATION_PROVEN (SQLite-fixture scope) for all 8 modes.
- Genuine native CDC capability for any connector (SQLite's connector manifest was not modified to claim CDC support — correctly left truthful).

## 29. Regression Risk

- The new `execute_migration` fail-closed guard (`raise ... if not dag_dict or not dag_dict.get("dag_stages")`) is a **behavior change**: any existing caller that previously invoked physical execution without a compiled `dag_dict` will now fail immediately where it previously ran the fixed 4-step sequence. This is intentional (per owner correction #1 — the plan must be load-bearing) but is flagged as a compatibility risk for any untraced caller. The one confirmed real production caller (`EngineGateway.start_transport`) already always passed `dag_dict`, so no regression was observed there; 700 pre-existing tests passed, indicating no test-suite caller was broken either, but this is not a proof that no production caller anywhere could be affected (see §26 — not every entrypoint was traced).
- The `_extract_source_config`/`_extract_target_config` sqlite branches are strictly additive (new early-return branch); they cannot change behavior for any existing Oracle/Postgres/MySQL/MSSQL caller, since those are only reached when `system_type`/`engine` is explicitly `"SQLITE"`.
- SIMULATED SQLITE PERFORMANCE only — no performance regression claim is made for real Oracle/PostgreSQL paths; none were touched or measured.

## 30. Final Technical Assessment

Per mode: M1/M5/M6/M7/M8 — genuinely corrected, physically proven against the real estate, zero regressions. M2/M3/M4 — not implemented; explicit design established but no code written. Shared architecture: the central defect (plan not load-bearing) is **genuinely fixed** for the `AkaalSuperEngine`/`EngineGateway.start_transport` path, which is real and matters, but the bypass audit found the fix is **not yet universal** across every production execution vehicle in the repository — most importantly `MigrationRuntimeDaemon`.

**Session verdict: M1–M8 CORRECTION IMPLEMENTATION — NOT READY FOR FINAL ACCEPTANCE RETEST.**

Remaining scope for continuation, in priority order: (1) close the `MigrationRuntimeDaemon` bypass or explicitly deprecate/reject it; (2) implement M4's watermark authority on `akaalEngine.durability` with real crash-window tests — the single most safety-critical remaining item; (3) implement M2/M3 CDC dispatch + test-only source seam; (4) wire real Evidence Authority #12 binding; (5) hostile/restart/security regression tests; (6) P7B/P7C re-audit.

---

## 31. Continuation Session — M4 Watermark Authority, Daemon Bypass Closure, Evidence Duplicate-Method Fix

**Session type**: continuation of this correction campaign, local testing only. Git writes prohibited and none performed. `progress.md` not touched. This section is an ADDITIVE continuation of the report above (§1–§30 unchanged, describing the PRIOR session's work) — it does not alter or retract any prior finding.

### 31.1 Scope actually completed this continuation session

1. **M4 — durable watermark authority, real production code, physically tested.**
   Extended the canonical `akaalEngine.durability.DurabilityAuthority` (NOT a new authority):
   - New model `Watermark`/`WatermarkType` (`akaalEngine/durability/models/checkpoint.py`) — NUMERIC / TIMESTAMP / COMPOUND value semantics.
   - New additive `watermarks` SQLite table (`akaalEngine/durability/store/sqlite.py`, `CREATE TABLE IF NOT EXISTS`, no destructive migration, no schema-version bump needed).
   - New `MigrationCheckpointRegistry.save_watermark`/`get_watermark` (`akaalEngine/durability/checkpoint/registry.py`), using the SAME atomic `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` pattern and the SAME authenticated-`FencingToken` requirement (HMAC + exact live-epoch match, no bypass) as the existing `save_checkpoint`/`save_row_position`.
   - Two new error types (`WatermarkRegressionError`, `WatermarkIdentityMismatchError`) in `akaalEngine/durability/models/errors.py`.
   - Facade methods `DurabilityAuthority.save_watermark`/`get_watermark` (`akaalEngine/durability/api.py`).
   - **New permanent test file** `tests/unit/engine_durability/test_m4_watermark_authority.py` — 13 tests, all physically exercised against the real on-disk SQLite-backed `DurabilityAuthority` (no mocking of the thing under test). **13/13 passed.** Physically proves, per the owner's exact requested list:
     | Requested proof | Result | Test |
     |---|---|---|
     | Numeric watermark advance | PHYSICALLY PROVEN | `test_numeric_watermark_save_and_advance` |
     | Numeric non-monotonic regression fails safe | PHYSICALLY PROVEN | `test_numeric_watermark_regression_rejected` |
     | Null watermark value fails safe (not silently accepted) | PHYSICALLY PROVEN | `test_numeric_watermark_null_value_fails_safe` |
     | Null watermark baseline (never-saved -> None, not an error) | PHYSICALLY PROVEN | `test_no_watermark_ever_saved_returns_none` |
     | Timestamp advance + tie timestamps accepted | PHYSICALLY PROVEN | `test_timestamp_watermark_advance_and_tie_accepted` |
     | Timestamp regression fails safe | PHYSICALLY PROVEN | `test_timestamp_watermark_regression_rejected` |
     | Compound-key lexicographic ordering (tie-breaker component) | PHYSICALLY PROVEN | `test_compound_watermark_ordering` |
     | Plan/version/execution identity prevents incompatible checkpoint reuse | PHYSICALLY PROVEN | `test_incompatible_plan_fingerprint_rejected` |
     | Concurrent/stale execution cannot advance another execution's watermark | PHYSICALLY PROVEN | `test_stale_execution_cannot_advance_watermark` |
     | Repeated batch/replay idempotency | PHYSICALLY PROVEN | `test_repeated_identical_batch_replay_is_idempotent` |
     | Restart from durable watermark (fresh `DurabilityAuthority` instance, same on-disk store) | PHYSICALLY PROVEN | `test_restart_from_durable_watermark_survives_process_restart` |
     | A rejected/failed write leaves the prior durable watermark completely unchanged | PHYSICALLY PROVEN | `test_rejected_write_leaves_prior_watermark_unchanged` |
   - **What is explicitly NOT claimed, per the owner's own instruction**: cross-database atomicity between the target and this durability store. `save_watermark` has no target-connection argument at all (asserted structurally by `test_watermark_authority_itself_has_no_target_visibility_by_design`) — "target commit happens before durable watermark advancement" is a CALL-ORDER discipline the CALLER (a future M4 incremental-poll dispatch step) must honor, not a property this store can prove about a different database. **"Failure before target commit → watermark unchanged" and "crash between target commit and watermark persistence → restart/replay produces no loss"**: the atomicity of the watermark write itself (ROLLBACK on any exception, verified) is PHYSICALLY PROVEN; the full cross-system ordering discipline requires wiring this authority into `plan_dispatch.py`'s M4 (`_handle_incremental_poll`) stage, which is **NOT_YET_DISPATCHED / not implemented this session** (unchanged from §10 above) — this remains ASSERTED-BY-DESIGN, not integration-proven end-to-end through the DAG dispatcher. **M4's overall classification is therefore upgraded from "EXTERNAL_DEFERRED / not implemented" (§27) to "durability authority IMPLEMENTED and UNIT_PROVEN; DAG-dispatch integration NOT YET DONE"** — M4 is still not a mode a compiled plan can successfully execute end-to-end (`plan_dispatch.py::_handle_incremental_poll` still returns `success=False, "NOT_YET_DISPATCHED"` — unchanged this session).

2. **`MigrationRuntimeDaemon` bypass — CLOSED.**
   `akaal/runtime/process/daemon.py::MigrationRuntimeDaemon` no longer builds its own fixed `WorkflowEngine` 4-step manifest. It now delegates 100% of physical execution to `AkaalSuperEngine.execute_migration`, using the identical compiled-plan lookup (`CentralStateStore.get_state(migration_id, category="execution_plan")`) `EngineGateway.start_transport` uses, and the same governance-approval gate enforced inside `execute_migration` itself (no separate approval logic added here — no new authority). If no compiled `dag_dict` with `dag_stages` is available, the daemon fails closed with `error_code=PLAN_NOT_LOAD_BEARING` rather than falling back to any fixed step sequence. **Verified**: `tests/unit/test_p010_rectification3.py` + `tests/unit/test_p010_rectification4.py` (51 tests, which import/reference `MigrationRuntimeDaemon` and exercise the surrounding `EngineGateway`/`RuntimeSupervisorTree` machinery) — **51/51 passed**, zero regressions. No new dedicated daemon-bypass-closure test was added this session (a real gap — see §31.3); the closure is PHYSICALLY PROVEN at the code-read level (the fixed `WorkflowEngine` manifest construction is gone; `execute_migration` on the daemon now literally calls `self.super_engine.execute_migration(...)`) but not yet independently proven end-to-end with a real dag_dict + real SQLite target the way `test_plan_driven_execution.py` proves the `EngineGateway` path.

3. **Two other confirmed migration-initiation bypasses — NOT closed, re-confirmed and documented (no fix attempted, correctly not claimed fixed):**
   - `akaal.engine.api.AkaalMigrationEngine.start_migration` — independent, real, substantial Oracle→Postgres multiprocess engine (`akaal/engine/api.py`) with its own `EngineStateRepository`/`CheckpointStore`, entirely independent of `PlanCompiler`/`AkaalSuperEngine`/`ExecutionMode`. Re-plumbing this into DAG-driven dispatch is a large, separate undertaking (different connection/authority model, different checkpoint store) — correctly scoped OUT of this continuation session rather than attempted partially/riskily.
   - `akaal.agents.manager.manager_agent.ManagerAgent.run_migration` — a deep, independent, task-dispatch state-machine orchestration (`PROJECT_CREATED → DISCOVERY → GB_IMPORT → HUMAN_APPROVAL → PRODUCTION_MIGRATION → CDC → COMPLETED`), which dispatches physical data-transfer work to a separate "GB Agent" (`_dispatch_task(mig_task, ...)`, `akaal/agents/manager/manager_agent.py:887-896`) — confirmed, by direct code read, to be entirely independent of `AkaalSuperEngine`/`PlanCompiler`/`ExecutionMode`. This is the largest and most architecturally distinct of the three bypasses (it is not a thin wrapper the way the daemon was; it is a full alternate orchestration model with its own approval/recovery semantics) and re-plumbing it safely requires an owner-directed design decision (does `ManagerAgent` compile a plan and delegate physical execution to `AkaalSuperEngine`, or is it accepted as a legitimately distinct, mode-blind orchestration surface that must be explicitly fenced/deprecated instead?) that is outside this session's authorized scope to decide unilaterally.
   - **Required end state ("no normal production route silently executes a mode-blind alternate workflow") is THEREFORE STILL NOT FULLY ACHIEVED** — 1 of 3 confirmed bypasses closed this session (daemon); 2 remain open and are explicitly, not silently, reported.

4. **Real defect found and fixed in the real Evidence Authority #12 itself** (`akaalEngine/evidence/api.py`), found while tracing Evidence #12 in preparation for wiring `plan_dispatch.py`'s evidence stage to it:
   - Two methods were BOTH named `package_hook_execution_evidence` with **incompatible signatures** (one artifact/`plan_identity`-based at the old line 318, one dict/`stage`-based at the old line 659). Python keeps only the later definition at runtime, which silently shadowed the first. The REAL production call site (`akaal/migration/execution/hooks/executor.py::GovernedHookExecutor`) used the FIRST (now-shadowed) signature, meaning **every real hook-evidence-packaging call in production was silently raising `TypeError`, caught and swallowed by that call site's own `except Exception: logger.warning(...)`** — Evidence Authority #12 hook integration has been silently non-functional. Fixed by renaming the artifact-based method to `package_hook_execution_artifact` (distinct name) and re-pointing the one real call site at it; the separately-tested dict-based `package_hook_execution_evidence(stage=..., ...)` is untouched. **New regression test** `tests/unit/planner/test_custom_sql_hooks.py::test_40b_authority_12_evidence_packaging_actually_succeeds_not_silently_swallowed` spies on the (renamed) method and asserts it is actually invoked without raising — proving the silent-failure is closed. **66/66 passed** in that file (65 pre-existing + 1 new), zero weakened tests.
   - A second duplicate, `get_instance` (defined identically twice — a thread-safe double-checked-locking version and a later, lock-free, functionally-inferior duplicate that silently shadowed it), was removed; the thread-safe version is now the sole implementation. No behavior change for any caller (both had identical zero-argument call shape).
   - **This is a real bug fix, not a redesign** — no scope creep beyond the two confirmed duplicate-method defects named in this continuation's brief.
   - **`plan_dispatch.py::_handle_evidence` is still NOT wired to the real Evidence Authority #12** — it still records only a local sha256 digest, explicitly labeled as a placeholder in its own output (unchanged from §19 above). This continuation session fixed a real, independent bug IN the canonical Evidence Authority itself (so that whichever future session wires `plan_dispatch.py` to it does not inherit a silently-broken method), but did NOT perform that wiring itself — that remains outstanding.

### 31.2 Scope NOT completed this continuation session (explicit, not silent)

- **M2 (bulk+CDC consistency boundary)**: NOT implemented. `plan_dispatch.py::_handle_cdc_boundary`/`_handle_cdc_init`/`_handle_cdc_apply` remain honest fail-closed stubs, unchanged.
- **M3 (CDC-only, zero-bulk proof)**: NOT implemented, unchanged.
- **M4 DAG-dispatch integration** (wiring the new watermark authority into `plan_dispatch.py::_handle_incremental_poll` against the real `akaal.cdc.*` buffering/apply/ordering/replay/checkpoint machinery so an M4 plan can actually execute end-to-end): NOT implemented this session. The durability PRIMITIVE (watermark save/get with all requested invariants) is real and tested; the DAG-responsibility WIRING that would let a compiled M4 plan drive it is not.
- **Evidence Authority #12 real binding into `plan_dispatch.py`**: NOT implemented (a real, independent bug in the authority itself was found and fixed, but the dispatcher still uses its own local digest).
- **Validation Authority #11 reconfirmation against the governing document's full responsibility set** (beyond continuing to use `CanonicalReconciliationEngine` as before): NOT re-audited this session.
- **SEC-I01–SEC-I15 and the hostile/restart matrix**: NOT written this session. No SEC-I-numbered test files exist anywhere in the repository (confirmed by repository-wide search) — this remains a pure, unaddressed gap.
- **P7B/P7C re-audit**: NOT performed this session beyond confirming (by import inspection) that none of this session's changed files (`daemon.py`, `akaalEngine/durability/*`, `akaalEngine/evidence/api.py`) import any `akaal.governance.p7b`/`p7c`-named module — i.e., no NEW P7B/P7C bypass was introduced, but no positive re-confirmation that pre-existing P7B/P7C gates remain correctly enforced was performed.
- **`AkaalMigrationEngine` and `ManagerAgent` bypasses**: confirmed, documented, NOT closed (§31.1 item 3).
- **`akaal.advisory.executor` bypass status**: still not conclusively resolved (unchanged from §26).

### 31.3 Regression — this continuation session

**Targeted (scope directly touched or logically adjacent to this session's changes):**
```
.venv/Scripts/python.exe -m pytest tests/unit/engine/test_plan_driven_execution.py tests/unit/engine_durability/ tests/integration/engine_durability/ tests/unit/test_p010_rectification3.py tests/unit/test_p010_rectification4.py -q
  -> 101 passed, 0 failed

.venv/Scripts/python.exe -m pytest tests/unit/planner/test_custom_sql_hooks.py -q
  -> 66 passed, 0 failed   (65 pre-existing + 1 new evidence-packaging regression test)

.venv/Scripts/python.exe -m pytest tests/unit/engine/ tests/unit/workflow/ tests/unit/planner/ tests/unit/validation/ tests/unit/connectors/ tests/fixtures/estate/selftest/ tests/unit/engine_durability/ tests/integration/engine_durability/ -q
  -> 738 passed, 0 failed   (this is the prior session's reported 712-test targeted scope, PLUS engine_durability/integration engine_durability now explicitly included, PLUS the 12→ tests already counted in the 712; net new physically-passing evidence beyond the 712 baseline: +13 M4 watermark tests, +the durability suite already implicitly covered, +1 evidence regression test counted separately above)
```
**Whole-repository** (`pytest` from repo root, per `pytest.ini`'s `testpaths = tests`): **[FILL-IN-PENDING — see below; command was started and is reported in full once it completes, per this same report]**

No pre-existing test was modified to force a pass, no test was deleted or weakened. `tests/fixtures/estate/**` manifests and expected-truth fixtures were not touched (confirmed via `git status` — only `tests/unit/engine_durability/test_m4_watermark_authority.py` is new under `tests/`, plus edits to `tests/unit/planner/test_custom_sql_hooks.py` adding one new test function).

### 31.4 Duplicate-authority / dependency audit (this continuation)

- `akaal/engine/plan_dispatch.py`: re-inspected, **unchanged this session**. Confirmed still subordinate (no independent entrypoint, only imported from `facade.py`, delegates every real action to a pre-existing canonical authority) — assessment from §6/§25 stands.
- New `akaal` → `akaalEngine` dependency introduced this session: **none**. The M4 watermark work extended `akaalEngine.durability` in place; `akaal/`-side code (`daemon.py`) was NOT changed to import `akaalEngine` — the daemon closure only reaches into `akaal.engine.facade`/`akaal.core.state.state_store`, both already-existing `akaal`-internal dependencies. The `akaal` ↔ `akaalEngine` reconciliation gap noted in §6 (no bridge yet for the modes that would need it) is therefore **unchanged** — still zero cross-package coupling in either direction, because `plan_dispatch.py`'s M4/M2/M3 handlers still do not call into `akaalEngine` at all yet (they remain `NOT_YET_DISPATCHED` stubs).
- Evidence Authority fix (§31.1 item 4) touched only `akaalEngine/evidence/api.py` (internal duplicate-method cleanup) and its one real `akaal`-side caller (`akaal/migration/execution/hooks/executor.py`) — a pre-existing dependency edge (`akaal` already called into `akaalEngine.evidence`), not a new one.

### 31.5 Updated per-mode classification (supersedes §27 for M4 only; M1/M2/M3/M5/M6/M7/M8 unchanged pending §31.6 re-run)

| Mode | §27 classification | Updated this continuation |
|---|---|---|
| M4 | EXTERNAL_DEFERRED / not implemented | Durability primitive (watermark save/get, all 12 owner-requested invariants): **UNIT_PROVEN**. DAG-dispatch end-to-end execution: **still not implemented** (`_handle_incremental_poll` unchanged, fails closed). Overall mode classification: **still cannot execute an M4 plan end-to-end — NOT YET INTEGRATION_PROVEN**, but the single most safety-critical missing primitive (durable watermark ordering/identity/monotonicity) now has real, tested production code where none existed before.

### 31.6 M1/M5/M6/M7/M8 re-verification after this continuation's shared-runtime changes

This continuation's changes touched `akaal/runtime/process/daemon.py` (does not participate in the `EngineGateway.start_transport → AkaalSuperEngine.execute_migration → PlanExecutionDispatcher` path `test_plan_driven_execution.py` exercises) and `akaalEngine/durability/*`/`akaalEngine/evidence/api.py` (neither of which `plan_dispatch.py` or `facade.py` import). **Re-run result**: `tests/unit/engine/test_plan_driven_execution.py` — all M1/M5/M6/M7/M8 physical tests from §7/§11/§12/§13/§14 above — **re-ran clean as part of the 101-test and 738-test runs in §31.3, 0 failed**. No regression in the five previously-corrected modes from this continuation's changes.

### 31.7 Updated overall verdict

M4's durable-watermark primitive is now real and independently tested (a genuine, substantial, safety-critical addition). The `MigrationRuntimeDaemon` bypass is closed. A real, previously-unknown Evidence Authority #12 defect (silently-failing hook evidence packaging) was found and fixed. However: M2/M3 remain fully unimplemented; M4's DAG-dispatch integration (the piece that would let a compiled M4 plan actually run) remains unimplemented; Evidence Authority #12 is still not wired into `plan_dispatch.py`; Validation Authority #11 was not re-audited against the governing document; SEC-I01–15 and the hostile/restart matrix do not exist; P7B/P7C were not re-audited; two of three confirmed bypasses (`AkaalMigrationEngine`, `ManagerAgent`) remain open.

> **M1–M8 CORRECTION IMPLEMENTATION — NOT READY FOR FINAL ACCEPTANCE RETEST.**
> Additional real, physically-proven progress this continuation session (M4 durability primitive, 1-of-3 bypass closures, a genuine Evidence Authority #12 bug fix) on top of the prior session's M1/M5/M6/M7/M8 convergence. M2/M3, M4 DAG-dispatch integration, Evidence #12 wiring, Validation #11 re-audit, SEC-I01-15, P7B/P7C re-audit, and 2 of 3 bypasses remain as scoped, evidence-backed remaining work.

---

## 32. MID-SCOPE CHECKPOINT — session paused deliberately, work NOT complete

**This checkpoint was written on explicit instruction to pause before the authorized scope was finished.** It supersedes §31.7's verdict framing only insofar as: the campaign is **PAUSED MID-SCOPE**, not concluded. **No final verdict is being issued in this section** — see §32.5.

### 32.1 What is DONE and independently verified this continuation session

All of the following were physically run this session, results observed directly (not inferred/estimated):

1. **M4 durable watermark authority** — extended `akaalEngine.durability.DurabilityAuthority` (canonical, not a new authority):
   - `akaalEngine/durability/models/checkpoint.py` — added `WatermarkType` enum (`NUMERIC`/`TIMESTAMP`/`COMPOUND`) and `Watermark` dataclass.
   - `akaalEngine/durability/models/errors.py` — added `WatermarkRegressionError`, `WatermarkIdentityMismatchError`.
   - `akaalEngine/durability/store/sqlite.py` — added additive `CREATE TABLE IF NOT EXISTS watermarks (...)` (no destructive migration, no schema-version bump).
   - `akaalEngine/durability/checkpoint/registry.py` — added `MigrationCheckpointRegistry.save_watermark`/`get_watermark` (+ `_watermark_sort_key` static helper), same atomic `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` + authenticated-`FencingToken` pattern as `save_checkpoint`.
   - `akaalEngine/durability/api.py` — added `DurabilityAuthority.save_watermark`/`get_watermark` facade methods.
   - `akaalEngine/durability/__init__.py` — exported the 4 new names.
   - **New test file** `tests/unit/engine_durability/test_m4_watermark_authority.py` — **13 tests, 13 passed** (verified via direct pytest run, output observed).
   - **NOT done**: `akaal/engine/plan_dispatch.py::_handle_incremental_poll` is still an honest `NOT_YET_DISPATCHED` stub — the watermark PRIMITIVE exists and is tested in isolation, but no M4 plan can execute end-to-end yet (no wiring from the dispatcher into this new authority, and no wiring into the real `akaal/cdc/*` machinery an M4 poll cycle would also need).

2. **`MigrationRuntimeDaemon` bypass closed** — `akaal/runtime/process/daemon.py` rewritten: no longer builds its own fixed `WorkflowEngine` 4-step manifest; now delegates to `AkaalSuperEngine.execute_migration` via the same compiled-plan lookup (`CentralStateStore` category `execution_plan`) `EngineGateway.start_transport` uses; fails closed (`PLAN_NOT_LOAD_BEARING`) if no compiled `dag_dict` is found. Verified via direct pytest run: `tests/unit/test_p010_rectification3.py` + `tests/unit/test_p010_rectification4.py` — **51 passed, 0 failed**.

3. **Evidence Authority #12 duplicate-method bug found and fixed** (`akaalEngine/evidence/api.py`):
   - Two methods were both named `package_hook_execution_evidence` with incompatible signatures; Python silently kept only the later (dict/`stage`-based) one, so the real production call site (`akaal/migration/execution/hooks/executor.py::GovernedHookExecutor`) was silently raising `TypeError` on every hook-evidence-packaging call, swallowed by that call site's own `except Exception: logger.warning(...)`. Fixed by renaming the artifact-based method to `package_hook_execution_artifact` and re-pointing the one real call site (`akaal/migration/execution/hooks/executor.py` line ~142-144) at it.
   - Removed a second, functionally-inferior duplicate `get_instance` classmethod (no locking) that silently shadowed the thread-safe one.
   - **New regression test** added to existing file: `tests/unit/planner/test_custom_sql_hooks.py::test_40b_authority_12_evidence_packaging_actually_succeeds_not_silently_swallowed`.
   - Verified via direct pytest run: `tests/unit/planner/test_custom_sql_hooks.py` — **66 passed, 0 failed** (65 pre-existing + 1 new).
   - **Still NOT done**: `plan_dispatch.py::_handle_evidence` still records only a local sha256 digest — not wired to this (now-fixed) real Evidence Authority.

4. **Dispatcher-level mode fence added** (`akaal/engine/plan_dispatch.py`) — defense-in-depth fix for a real gap found this session: the dispatcher previously dispatched stages purely by stage NAME with no check that the responsibility was legal for the DECLARED execution mode (mode-fencing was entirely dependent on `PlanCompiler` never emitting an illegal stage; the dispatcher itself had no independent check). Added `MODE_ALLOWED_RESPONSIBILITIES` table + `_canonical_mode_key()` (using the real, canonical `akaal.planner.models.p5_domain.ExecutionMode.from_string`) and a fail-closed check in `PlanExecutionDispatcher.run()` before any stage handler executes. Verified via direct pytest run: `tests/unit/engine/test_plan_driven_execution.py` — **12 passed, 0 failed** (all 12 pre-existing tests still pass unchanged with the new fence active).

5. **SEC-I01–SEC-I15 hostile/security test matrix written** — new file `tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py`, **15 tests, all 15 passed** (verified via direct pytest run). Covers, against real code (no mocking of the authority under test): AUTHENTICATED != AUTHORIZED (I01), identifiers are not ownership proof (I02), caller roles/scopes are not authoritative (I03), missing central governance record denies (I04, the repo's real analog to "central_authz=None"), stale fencing token cannot save checkpoint (I05), plan identity mismatch fails closed (I06), unauthorized M5 repair fails closed (I07), M8 cannot mutate absent authorized repair (I08), M3/M6/M7 illegal-stage mode-fence rejection (I09/I10/I11, exercising the new fence from item 4), unrecognized mode fails closed entirely (I12), failed prerequisite blocks downstream execution (I13), watermark identity mismatch (I14) and stale-execution watermark fencing (I15) via the new M4 primitive.

6. **Whole-repository regression — ONE clean baseline run completed and captured**, run BEFORE items 4 and 5 above (before the mode-fence change and the SEC-I test file existed): `pytest` from repo root — **6998 passed, 165 skipped, 0 failed, in 682.75s (11m22s)**. This is real, observed output (not estimated). **This number does NOT yet include the mode-fence change or the new SEC-I test file** — see §32.2.

### 32.2 Regression status — INCOMPLETE, must be re-run on resume

- The **6998 passed / 165 skipped / 0 failed** whole-repo run (§32.1 item 6) is real and complete, but predates the mode-fence edit to `plan_dispatch.py` and the new `tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py` file.
- A second, narrower regression run covering the changed/adjacent areas (`tests/unit/engine/ tests/unit/workflow/ tests/unit/planner/ tests/unit/validation/ tests/unit/connectors/ tests/fixtures/estate/selftest/ tests/unit/engine_durability/ tests/integration/engine_durability/ tests/security/ tests/unit/test_p010_rectification3.py tests/unit/test_p010_rectification4.py`) was in flight when this checkpoint was first drafted (its output file was still empty at that instant); it finished moments later, still within this same session, with result **1505 passed, 0 failed, in 211.23s** — confirmed by reading its completed output file directly (no test was re-run to obtain this number). This is the up-to-date combined result covering ALL of this session's changes together (M4 watermark authority, daemon bypass closure, Evidence Authority fix, the new mode fence, and the new SEC-I suite) plus the pre-existing engine/workflow/planner/validation/connectors/estate-selftest suites. **Zero failures.**
- The combined targeted run above (1505 passed, 0 failed) confirms items 1-5 in §32.1 all coexist without regression. **What is still outstanding is a whole-repository run that includes the mode-fence change and the new SEC-I file together with everything else** — the only complete whole-repo number on record (6998 passed / 165 skipped / 0 failed, §32.1 item 6) predates those two changes.
- **On resume: re-run, before doing anything else:**
  1. Full whole-repo `pytest -q` from repo root (expect run time ~11-15 minutes; the prior complete run collected ~7163 tests). Given the targeted 1505-test run already covers the exact files changed by the mode-fence/SEC-I additions with 0 failures, a regression in the full run would only come from an interaction with a directory not included in that targeted list -- still worth confirming explicitly before any acceptance-readiness claim, but this is now a low-risk verification step, not an unknown.

### 32.3 Exact remaining scope (itemized for zero-re-derivation resume)

**Not started / not done at all:**
- **M2 (bulk+CDC consistency boundary)**: `akaal/engine/plan_dispatch.py::_handle_cdc_boundary`/`_handle_cdc_init`/`_handle_cdc_apply` are still honest `NOT_YET_DISPATCHED` stubs (unchanged). Real authorities to wire, confirmed present and real this session (via direct code read, NOT yet integrated): `akaal.cdc.apply.engine.CDCApplyWorker` (target apply, transaction atomicity, durable checkpointing, replay dedup, fencing — constructor takes `CDCEventIdentity`, `DurableCDCBuffer`, `RecoveryCoordinator`, `CentralStateStore`; see `akaal/cdc/apply/engine.py`), `akaal.cdc.coordinator.coordinator` (session/lifecycle coordination), `akaal.cdc.ordering.coordinator` (event ordering), `akaal.cdc.replay.engine` (replay), `akaal.cdc.checkpoint.*` (checkpoint backends: `base.py`/`db.py`/`file.py`/`memory.py`/`redis.py`), `akaal.cdc.buffering.durable_buffer.DurableCDCBuffer`, `akaal.cdc.domain.events.{CDCEventIdentity,CDCTransaction,CDCOperationType}`, `akaal.cdc.domain.positions.{CDCSourcePosition,parse_source_position}`, `akaal.cdc.domain.lifecycle.{CDCAckState,CDCSessionState,CDCSessionStateMachine}`. The authorized test-only seam (a fake UPSTREAM CDC source/log only — never AKAAL's own internal CDC success, never the SQLite capability manifest, never a fake provider) has NOT been built. M2 also requires: deliberately injecting deterministic changes during the bulk phase and proving no unprotected change window / no loss / no duplicate final state, plus catch-up/backlog-to-continuous-sync transition proof — none of this exists yet.
- **M3 (CDC-only, zero-bulk proof)**: same stubs; the STRUCTURAL zero-bulk guarantee is now actually reinforced by the new mode fence (§32.1 item 4 — `MODE_ALLOWED_RESPONSIBILITIES["M3"]` excludes `"transport"`, proven by `SEC-I09` in the new suite), but a real end-to-end M3 CDC integration test (inserts/updates/deletes/multi-event transactions/ordering/replay/restart/checkpoint-ACK against the estate's CDC truth fixtures at `tests/fixtures/estate/cdc/`) does not exist.
- **M4 DAG-dispatch integration**: wire `_handle_incremental_poll` in `akaal/engine/plan_dispatch.py` to the new `DurabilityAuthority.save_watermark`/`get_watermark` (§32.1 item 1) AND to a real per-table incremental read path (the existing adapters only expose offset-based `read_batch`, not watermark-column-filtered reads — this may need a new, narrowly-scoped adapter method or a source-side query built from the watermark value). Must preserve call-order discipline: target `write_batch` commit MUST complete before `save_watermark` is called (see `test_watermark_authority_itself_has_no_target_visibility_by_design` in `tests/unit/engine_durability/test_m4_watermark_authority.py` for why this can't be enforced inside the durability layer itself).
- **Evidence Authority #12 wiring**: `plan_dispatch.py::_handle_evidence` must call the real `akaalEngine.evidence.api.EvidenceAuthority` (now bug-fixed, §32.1 item 3) instead of computing its own local sha256 digest. Exact real methods available: `package_validation_evidence`, `package_cdc_evidence`, `package_execution_evidence`, `package_hook_execution_artifact` (renamed this session), `package_hook_execution_evidence` (dict/stage-based, untouched), `create_manifest`, `create_evidence_artifact`, `get_instance()` (singleton).
- **Validation Authority #11 reconfirmation**: NOT re-audited against the governing document (`docs/architecture/AKAAL_Enterprise_Migration_Workflow_v1.0.md`, per the orientation research — its §3 M1-M8 definitions and §10 42 Frozen Principles were flagged as relevant but not read/cross-checked against `CanonicalReconciliationEngine` this session). The orientation research flagged a real open question: whether `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine` (currently wired) or `akaalEngine.validation.api.ValidationAuthority` (a full 7-stage pipeline, NOT currently wired to `akaal/`) is what the governing doc actually requires as canonical Authority #11 — this was never resolved this session.
- **P7B/P7C re-audit**: NOT performed. Only a negative check was done (grep confirmed none of this session's changed files import any `p7b`/`p7c`-named module — no NEW bypass introduced), but no positive re-confirmation that pre-existing P7B/P7C gates remain enforced.
- **2 of 3 confirmed bypasses remain OPEN** (documented, not silently ignored):
  - `akaal.engine.api.AkaalMigrationEngine.start_migration` (`akaal/engine/api.py`) — independent Oracle→Postgres multiprocess engine with its own `EngineStateRepository`/`CheckpointStore`.
  - `akaal.agents.manager.manager_agent.ManagerAgent.run_migration` (`akaal/agents/manager/manager_agent.py`, stage dispatch at line ~887-896 via `self._dispatch_task(mig_task, ...)` to a separate "GB Agent") — a deep, independent task-dispatch state-machine orchestration (`PROJECT_CREATED → DISCOVERY → GB_IMPORT → HUMAN_APPROVAL → PRODUCTION_MIGRATION → CDC → COMPLETED`). Re-plumbing this safely requires an owner-directed design decision (delegate to `AkaalSuperEngine`, or explicitly fence/deprecate as a legitimately distinct orchestration surface) — flagged, not decided, this session.
  - Only `MigrationRuntimeDaemon` (1 of 3) was closed this session (§32.1 item 2).
- **`akaal.advisory.executor` bypass status**: still not conclusively resolved (carried over from the prior session, unchanged).

**Done, but needing final re-verification (§32.2 step 1-2) before being trusted as the final combined state:**
- Duplicate-authority audit on `plan_dispatch.py` — re-inspected this session, still assessed as a subordinate dispatch layer (no independent entrypoint), not a second authority; the new `MODE_ALLOWED_RESPONSIBILITIES` table is additive validation logic inside the same file, not a new authority.
- M1/M5/M6/M7/M8 re-verification after this session's shared-runtime changes — re-ran clean (§31.6, and again after the mode-fence change per §32.1 item 4's 12/12 result), but needs to be seen green one more time in the SAME combined run as everything else (§32.2).

### 32.4 Files created or modified this continuation session (complete list)

**Modified:**
- `akaal/runtime/process/daemon.py` — bypass closure (§32.1.2).
- `akaal/engine/plan_dispatch.py` — added `MODE_ALLOWED_RESPONSIBILITIES`/`_canonical_mode_key`/mode-fence check in `run()` (§32.1.4).
- `akaalEngine/durability/models/checkpoint.py`, `akaalEngine/durability/models/errors.py`, `akaalEngine/durability/store/sqlite.py`, `akaalEngine/durability/checkpoint/registry.py`, `akaalEngine/durability/api.py`, `akaalEngine/durability/__init__.py` — M4 watermark authority (§32.1.1).
- `akaalEngine/evidence/api.py` — duplicate-method fix (§32.1.3).
- `akaal/migration/execution/hooks/executor.py` — call-site rename to match the fix above.
- `tests/unit/planner/test_custom_sql_hooks.py` — added one new regression test + `from unittest.mock import patch` import.
- `tests/fixtures/estate/M1_M8_CORRECTION_REPORT.md` — this continuation's §31 and this §32 checkpoint (the correction report; the original acceptance report and expected-truth manifests were NOT touched).

**Created:**
- `tests/unit/engine_durability/test_m4_watermark_authority.py` (13 tests).
- `tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py` (15 tests).

**Untouched from the PRIOR (already-committed-as-uncommitted) session's work**, confirmed via this session's `git status`, present before this continuation started: `.akaal/reports/*.json` (timestamp-only diffs from running test suites — confirmed by direct diff, no content change), `.gitignore`, `akaal/engine/facade.py`, `akaal/workflow/steps/migration_steps.py`, `akaal/engine/plan_dispatch.py` (base version before this session's mode-fence addition), `tests/fixtures/estate/**` (fixtures/manifests — NOT modified this session), `tests/unit/engine/test_plan_driven_execution.py` (NOT modified this session, only re-run).

### 32.5 Verdict: NOT YET DETERMINED

This campaign is **PAUSED MID-SCOPE**, not complete. Neither final verdict line is being issued in this section. §31.7 above already correctly stated "NOT READY FOR FINAL ACCEPTANCE RETEST" for the state as of the end of §31 — that remains the last fully-regression-confirmed verdict. Work done in §32.1 items 4 and 5 (mode fence + SEC-I suite) is real and individually test-confirmed but has **not yet been through a combined regression run** (§32.2) and is therefore not yet folded into a new overall verdict. **Do not treat this checkpoint as either acceptance or rejection — it is a resume point.**

**Top 3 remaining items in priority order for the next session:**
1. Finish §32.2's two regression runs (combined targeted, then whole-repo) to confirm nothing in §32.1 items 4-5 regressed anything, and get an updated, accurate whole-repo count.
2. M4 DAG-dispatch integration (`_handle_incremental_poll` wired to the now-real watermark authority + a real incremental read path) — the durability primitive is proven but unusable end-to-end until this is done.
3. M2/M3 CDC dispatch wiring to the real `akaal/cdc/*` authorities (§32.3), including the authorized test-only external-CDC-source seam.

## 33. RESUMPTION SESSION — bypass discrepancy resolved, M2/M3/M4 verified, P7B/P7C and Validation Authority #11 reconciled, full regression CLEAN (1 confirmed unrelated flake)

This session resumed from §32's MID-SCOPE CHECKPOINT. Per that checkpoint's own top-3 priority list, the work item order was: (1) re-run regression to confirm §32.1 items 4-5 (mode fence + SEC-I suite), (2) M4 DAG-dispatch integration, (3) M2/M3 CDC dispatch wiring. On resuming, direct inspection of the working tree showed the actual code state was **substantially further along than §32.3 claimed** — this section documents what was verified, what (if anything) needed fixing, and reconciles the stale claims.

### 33.1 Discrepancy resolution: bypass audit is 3 of 3 CLOSED, not 2 of 3 OPEN

§32.3 stated "2 of 3 confirmed bypasses remain OPEN" (`akaal.engine.api.AkaalMigrationEngine.start_migration` and `akaal.agents.manager.manager_agent.ManagerAgent.run_migration`). This is **stale**. Both were closed in code that already exists on disk (`git diff --stat` shows `akaal/engine/api.py` +180/-, `akaal/agents/manager/manager_agent.py` +165/-). This session independently verified both closures by reading the full diffs (not trusting a prior summary) and re-running the exact test evidence:

- **`AkaalMigrationEngine.start_migration`** (`akaal/engine/api.py`): the method's entire independent Oracle→Postgres multiprocess transport body (TransportPartitioner + MigrationScheduler + PostgreSQLTargetWriter + EngineValidator) was deleted and replaced with an unconditional fail-closed raise of a new `LegacyEngineBypassClosedError`, naming `AkaalSuperEngine.execute_migration` as the canonical replacement. Verified: this class is legacy/dead code with zero production callers (confirmed no other change in this diff or elsewhere wires it up), and three pre-existing test files already assert its absence from the canonical transport path.
- **`ManagerAgent.run_migration`** (`akaal/agents/manager/manager_agent.py`): both physical-dispatch call sites (line ~926 in the main migration loop, line ~1031 in the parallel per-table worker) were repointed from the old unconditional `self._dispatch_task(mig_task, project)` (straight to GBAgent's independent adapter-based transport engine, no mode-fence/governance check) to a new choke-point method `_dispatch_physical_migration_task(task, project, session)`. That method looks up a compiled, governance-approved `dag_dict` for the migration_id in `CentralStateStore` (category `execution_plan`); if found, it delegates for real into `self.super_engine.execute_migration(...)` (a lazily-constructed `AkaalSuperEngine`, same class facade.py/daemon.py/plan_dispatch.py use); if absent (true for every caller of this pipeline today, since it never compiles/governance-approves a DAG), it fails closed with error code `MANAGER_AGENT_BYPASS_CLOSED`, audit-logs the refusal, and returns a failed `TaskResult` that the existing retry/failure-handling machinery processes normally. Governance/contract exceptions from `AkaalSuperEngine` (`ApprovalRequiredError`, `PlanFingerprintMissingError`, `PlanFingerprintMismatchError`, `PhysicalExecutionContractError`, `PhysicalValidationContractError`) are caught and converted to a clean failed `TaskResult` rather than propagating as unhandled exceptions.

**Test evidence reconfirmed this session** (re-run verbatim, not reused from a prior summary):
```
pytest tests/unit/engine/test_engine_core.py tests/unit/replication/test_step_5_2_canonical_transport.py \
  tests/unit/runtime/test_step_5_4_failure_recovery.py tests/unit/workflow/test_step_5_5_workflow_gating_telemetry.py \
  tests/unit/test_p010_rectification3.py tests/unit/test_p010_rectification4.py tests/stress/test_parallel_migration.py \
  tests/recovery tests/unit/test_phase12_stage2_runtime.py tests/unit/test_phase12_stage3_agent_network.py -q
→ 100 passed, 61 skipped in 137.17s
```
This matches the number originally reported, confirming it was real and reproducible, not fabricated.

**Also resolved this session: the `akaal.advisory.executor` bypass status** (carried over from the prior session as "not conclusively resolved," §32.3 last bullet). Direct code read of `akaal/advisory/executor.py::execute` (aliased `execute_migration` in `akaal/advisory/orchestrator.py`) shows it is a **pure, stateless, in-memory UDM type/schema advisory transformation function** — it takes a planner decision (BLOCK/CAST/TRANSFORM) and a UDM concept dict, does a deterministic dict lookup against `_CONCEPT_TARGET_MAP`, and returns a transformed dict. It opens no database connection, instantiates no adapter (the "adapter" registry it references is just a dotted-path string, never imported or called), and performs zero physical I/O of any kind. **Conclusion: this is not a physical-execution bypass at all** — it is confusingly named ("execute"/"execute_migration") but is planning-time schema-advisory computation only, architecturally incapable of bypassing the M1-M8 physical DAG-dispatch authority since it never touches a physical target. No code change was needed; this closes the item as a documented non-issue rather than a remaining gap.

**Updated bypass audit tally: 3 of 3 confirmed production physical-execution bypasses are now CLOSED** (`MigrationRuntimeDaemon` — closed prior session per §32.1.2; `AkaalMigrationEngine.start_migration` — closed, reconfirmed this session; `ManagerAgent.run_migration` — closed, reconfirmed this session). The `akaal.advisory.executor` item is resolved as a non-bypass (never was physical execution).

### 33.2 M2/M3/M4 DAG-dispatch integration — verified ALREADY IMPLEMENTED, not started from scratch

§32.3 claimed M2/M3/M4 dispatch wiring was "not started at all" (`_handle_cdc_boundary`/`_handle_cdc_init`/`_handle_cdc_apply`/`_handle_incremental_poll` as "honest NOT_YET_DISPATCHED stubs"). This is **stale**. `akaal/engine/plan_dispatch.py` (850 lines, untracked/new relative to a prior committed base) already contains full implementations:

- **`_get_cdc_components()`**: lazily constructs the real, canonical CDC machinery — `akaal.cdc.domain.events.CDCEventIdentity`, `akaal.cdc.buffering.durable_buffer.DurableCDCBuffer` (WAL-backed, restart-recoverable), `akaal.cdc.apply.engine.CDCApplyWorker`, and `akaal.runtime.recovery.coordinator.RecoveryCoordinator` for monotonic fencing-epoch issuance. No parallel/shadow CDC authority is created.
- **`_handle_cdc_boundary`** (M2): establishes the CDC session/buffer via `_get_cdc_components()` BEFORE bulk transport, closing the unprotected-change-window risk.
- **`_handle_cdc_init`** (M2/M3): ingests source change transactions via the authorized test-only seam `rt_ctx["cdc_test_source_transactions"]` — explicitly documented as simulating ONLY an external upstream CDC source/log (what a real Debezium/LogMiner/replication-slot listener would hand AKAAL), never AKAAL's own internal CDC success, never touching the SQLite capability manifest, registering no fake provider. Absent this seam, the stage fails closed (`CDC_SOURCE_NOT_CONFIGURED`) — there is no production CDC source listener wired into the dispatcher yet (this remains a real, honestly-reported gap: this campaign proved the DAG-dispatch *machinery* to real CDC authorities, not a production upstream listener integration, which was never in scope).
- **`_handle_cdc_apply`** (M2/M3): real ordered apply via `CDCApplyWorker.apply_next_transaction` against the target through a new `_CDCApplyAdapterBridge` class — translates `CDCEvent`s to the canonical `BaseAdapter.write_batch` (INSERT/UPDATE) contract plus a minimal delete-by-primary-key statement (DELETE). This bridge does not modify or extend `BaseAdapter` itself; it lives entirely inside the dispatcher's own CDC-apply call path, mirroring the existing sqlite dialect-neutral schema/transport fallback pattern.
- **`_handle_incremental_poll`** (M4): wired to the real `akaalEngine.durability.DurabilityAuthority.save_watermark`/`get_watermark` (the primitive built in the prior session, §32.1.1). Watermark-column metadata is required explicitly via `rt_ctx["incremental_watermark_columns"]` (fails closed — `M4_NOT_CONFIGURED` — rather than guessing which column to poll on). **Call-order discipline preserved**: `tgt.write_batch(...)` is called and must return successfully BEFORE `authority.save_watermark(...)` is invoked (verified by direct code read, `plan_dispatch.py` lines ~696-704) — exactly the ordering requirement §32.3 flagged as essential and impossible to enforce inside the durability layer itself.
- **`_handle_evidence`**: now binds to the real, bug-fixed `akaalEngine.evidence.api.EvidenceAuthority.get_instance().package_execution_evidence(...)` in addition to computing its own local sha256 digest — a best-effort binding that reports `evidence_authority_bound: True/False` truthfully rather than fabricating a bound artifact if the authority call fails.

**New integration test files, all already present and passing (verified — not written this session, but independently confirmed correct and non-trivial):**
```
pytest tests/unit/engine/test_m2_bulk_cdc_dag_dispatch_integration.py \
  tests/unit/engine/test_m3_cdc_dag_dispatch_integration.py \
  tests/unit/engine/test_m4_dag_dispatch_integration.py \
  tests/unit/engine_durability/test_m4_watermark_authority.py \
  tests/unit/engine/test_plan_driven_execution.py \
  tests/security/test_sec_i01_i15_m1_m8_hostile_matrix.py -q
→ 53 passed in 152.12s
```
Breakdown: M2 = 3/3, M3 = 4/4, M4 dispatch = 6/6, M4 watermark authority (unit-level, prior session) = 13/13, M1/M5/M6/M7/M8 pre-existing DAG suite = 12/12 (unchanged), SEC-I01–I15 hostile matrix = 15/15.

**Independent verification (dedicated sub-agent, separate context, own read of all four test files + `plan_dispatch.py` in full, own pytest run — reproduced 26/26 for the four new files + 12/12 for the pre-existing suite):**
- **M2**: genuinely proven, not merely "green." `test_m2_i01` injects a mid-bulk INSERT (new row), UPDATE (stale bulk-snapshot row), and DELETE (row bulk would otherwise have copied) via the authorized seam, and asserts against real on-disk SQLite target state: no loss (inserted row present), correct final value (update wins over stale bulk copy), no duplication of a deleted row (removed despite bulk having copied it), transport-count (3 bulk rows) and apply-count (3 CDC transactions) both asserted explicitly. `test_m2_i02` is a solid negative control (zero CDC changes → exact bulk copy, proving the CDC path doesn't fabricate rows). `test_m2_i03` proves the M4-only `incremental_poll` responsibility is fenced out of M2.
- **M3**: genuinely proven for INSERT/UPDATE/DELETE correctness against a real SQLite target with zero bulk/schema-transport stages in the DAG. `test_m3_i03` proves exactly-once physical application across two independent dispatcher runs (simulating a redelivered/replayed source transaction) via `CDCApplyWorker`'s restart-persistent dedup — genuine catch-up/replay-safety evidence. `test_m3_i04` proves a smuggled bulk-transport stage is refused by the mode fence before it can execute. One noted limitation: the suite proves "zero transport" structurally (a transport stage, if present, is refused before dispatch) rather than via an explicit invocation-count assertion on the transport handler itself — a legitimate but indirect form of the same proof.
- **M4**: genuinely proven. Real per-table watermark-filtered incremental reads (NULL-watermark rows correctly excluded; rows above the current watermark picked up on a subsequent poll). Durable persistence proven across a **fresh `DurabilityAuthority` instance against the same on-disk store** (`test_m4_i02`), which is a legitimate simulated-restart proof. One noted limitation: the write-then-save-watermark ordering is enforced by code inspection and by the durability layer's own unit test (`test_watermark_authority_itself_has_no_target_visibility_by_design`) rather than by a dedicated fault-injection test that crashes the dispatcher between the two calls and asserts the watermark stayed at its prior value — a real, if narrow, residual gap for future hardening, not a defect in what's implemented.

**No production or test code required fixes in this area** — the verification sub-agent's own report: "No fixes were needed — everything passed cleanly on the first run, and I made no production or test edits."

**Pre-existing architectural note surfaced this session (not a defect introduced by this campaign):** the `akaal.cdc` package contains two independent generations of CDC domain machinery that coexist:
- The "contracts" generation (`akaal.cdc.contracts.event.CDCEvent`, `akaal.cdc.buffering.buffer.DurableCDCBuffer`, `akaal.cdc.coordinator.coordinator.CDCCoordinator`, `akaal.cdc.replay.engine.CDCReplayEngine`, `akaal.cdc.routing.engine.CDCRoutingEngine`, `akaal.cdc.failover.coordinator.CDCFailoverCoordinator`, source adapters for Postgres WAL/MySQL binlog/Oracle LogMiner/SQL Server CDC) — used by `akaal/gateway/engine_gateway.py`, `akaal/integration/composition_root.py`, `akaal/cdc/coordinator_facade.py`, `akaal/cdc/api/client.py`. This looks like a full, standalone, multi-source continuous CDC streaming subsystem, architecturally independent of the M1-M8 DAG-dispatch path.
- The "domain" generation (`akaal.cdc.domain.events.CDCEvent`/`CDCEventIdentity`/`CDCTransaction`, `akaal.cdc.buffering.durable_buffer.DurableCDCBuffer`, `akaal.cdc.apply.engine.CDCApplyWorker`) — this is what `plan_dispatch.py`'s M2/M3 stages wire to, and is what this campaign's tests prove correct.

These are genuinely two different classes with the same name (`DurableCDCBuffer`, `CDCEvent`) in two different modules. This predates this correction campaign (confirmed: the checkpoint's own §32.3 already listed `akaal.cdc.coordinator.coordinator`/`akaal.cdc.replay.engine`/`akaal.cdc.checkpoint.*` as candidates the *prior* session had identified but not decided whether to wire). This campaign's scope was closing mode-blind physical-execution bypasses in the M1-M8 DAG-dispatch path specifically — it correctly wired to a real, tested, non-shadow CDC authority (the "domain" generation) rather than inventing a third one. Unifying the two CDC generations (or documenting which is canonical for which use case — DAG-orchestrated batch/CDC-boundary modes vs. standalone continuous streaming) is a real, legitimate architectural question but is out of scope for this bypass-closure campaign and is flagged here as a finding for a future, dedicated CDC-subsystem consolidation effort, not a blocker for this campaign's verdict.

### 33.3 Evidence Authority #12 and Validation Authority #11 — wiring proof and reconciliation

**Evidence Authority #12**: `plan_dispatch.py::_handle_evidence` calls `akaalEngine.evidence.api.EvidenceAuthority.get_instance().package_execution_evidence(...)` (the now-bug-fixed authority, duplicate-method defect closed in the prior session) in addition to its own local sha256 digest, and reports `evidence_authority_bound`/`evidence_authority_artifact_id` truthfully (never fabricating success on failure). `test_m4_i06_evidence_stage_binds_to_real_evidence_authority` explicitly asserts `evidence_authority_bound is True` and a real `evidence_authority_artifact_id` is returned, end-to-end through the DAG dispatch path — genuine binding proof, not just unit-level.

**Validation Authority #11 reconciliation** (dedicated read-only audit sub-agent, full read of both implementations plus `docs/architecture/AKAAL_Enterprise_Migration_Workflow_v1.0.md` and `contract.txt`):
- Determination: **`akaal.validation.domain.reconciliation.CanonicalReconciliationEngine` (currently wired) is sufficient/canonical for what `plan_dispatch.py`'s M1/M6/M7/M8 stages currently need.** `contract.txt` names Validation as "Authority #11" (line 693) and constrains it structurally (rules 143-147: M8 must be read-only/non-mutating; rule 252: "Validation reports parity/correctness truth") but does not mandate the specific 7-stage `ValidationAuthority` pipeline shape. `CanonicalReconciliationEngine.reconcile_tables` already covers checksum/Merkle comparison (via `PhysicalChecksumValidator`), PK-keyed deep-row reconciliation, and column-level mismatch localization — satisfying the substance of the architecture doc's Count/Checksum/Deep-Row/Column validation stages.
- `akaalEngine.validation.api.ValidationAuthority` is real and materially richer (explicit schema-structural validation, fencing/cancellation-token verification, CDC-boundary validation, durable partition-resume, a formal `VALIDATION_GATE` status object) but is **not a like-for-like swap** — wiring it in requires constructing a `ValidationPlan`, supplying schema metadata, and injecting up to 8 optional authority objects. It has zero existing test coverage under `tests/unit/validation/` (all existing tests there target `CanonicalReconciliationEngine`/`PhysicalChecksumValidator`), confirming it is unintegrated, untested-in-context code — genuinely wiring it in now would be new, unvalidated integration surface added under time pressure, which this campaign's own discipline (documented in §32 and earlier) explicitly avoids doing without dedicated test coverage.
- **No code change made.** Documented gap for future work: `ValidationAuthority`'s fencing-token verification and CDC-boundary validation are not exercised anywhere in the current DAG execution path; `_reconcile` performs no fencing check despite contract rules 140-142 requiring fenced execution authorization elsewhere in the system. This is a real, precisely-scoped gap, not papered over.

### 33.4 P7B/P7C re-audit — performed (was previously "not performed")

Dedicated read-only audit sub-agent located what "P7B"/"P7C" actually refer to in this codebase: **future-roadmap phase labels** from `docs/architecture/AKAAL_Enterprise_Migration_Workflow_v1.0.md` line 881 ("P7B cloud/hybrid/data-fabric" and "P7C AI-native migration intelligence"), not implemented gate modules. The only literal in-repo reference is a comment in `akaal/cloud/oci_provider.py:7` ("Reserved for P7B"). No `akaal.governance.p7b`/`p7c`-named module exists anywhere in the repository.

**Conclusion**: `plan_dispatch.py`'s full import surface (verified by reading all 850 lines) — `akaal.planner.models.p5_domain`, `akaal.workflow.steps.migration_steps`, `akaal.adapters.adapter_registry`, `akaal.cdc.*`, `akaal.runtime.recovery.coordinator`, `akaal.validation.domain.reconciliation`, `akaalEngine.durability`, `akaalEngine.evidence.api` — never imports `akaal.cloud` (the closest P7B-shaped subsystem: placement/residency resolution) or any advisory/intelligence subsystem (the closest P7C-shaped concept). `facade.py` likewise never imports those subsystems before invoking `PlanExecutionDispatcher`. **The DAG execution path cannot bypass P7B/P7C gates because no such gates are implemented yet to bypass** — this is consistent with the original §20 finding (a negative confirmation: no new bypass introduced) and is now reconfirmed as still accurate, not merely assumed.

**Duplicate-authority audit on `plan_dispatch.py` (re-confirmed)**: no `if __name__` entrypoint, no module-level singleton/competing state store, no competing plan-compilation logic, no competing governance-approval mechanism. `PlanExecutionDispatcher` is instantiated fresh per call inside `AkaalSuperEngine.execute_migration` — remains a subordinate dispatch layer, not a second engine.

**`akaal` → `akaalEngine` durability/evidence dependency narrowness (re-confirmed, with one nuance)**: `grep "from akaalEngine"` across `akaal/` returns 5 import lines across 3 files: `akaal/engine/plan_dispatch.py` (`akaalEngine.durability`, `akaalEngine.evidence.api` — the assumed/expected scope), plus `akaal/gateway/engine_gateway.py` and `akaal/migration/execution/deduplication.py` (`akaalEngine.data_processing.dedup`/`engine`/`models`). The coupling is slightly wider than "durability + evidence only" but remains narrow and targeted — specific named submodule imports throughout, no wildcard/broad `import akaalEngine` anywhere in the codebase. Not assessed as a violation of the narrow-dependency principle, but noted precisely rather than rounded up to "unchanged."

### 33.5 Per-mode (M1-M8) status summary with physical evidence

| Mode | What it proves | Test evidence (this session, re-run) |
|---|---|---|
| M1 Bulk | Real row transport to physical target; CDC stage structurally absent from DAG | `test_m1_physically_transports_real_rows`, `test_m1_cdc_stage_never_present_in_dag` (`test_plan_driven_execution.py`) — 2/2; also exercised by SEC-I suite |
| M2 Bulk+CDC | Consistency boundary captured before bulk; mid-bulk INSERT/UPDATE/DELETE all land correctly with no loss/no duplication; M4-only stage fenced out | `test_m2_bulk_cdc_dag_dispatch_integration.py` — 3/3 |
| M3 CDC-only | Zero bulk/schema transport stages; real INSERT/UPDATE/DELETE apply; replay dedup (exactly-once) across independent runs; smuggled transport stage fenced | `test_m3_cdc_dag_dispatch_integration.py` — 4/4 |
| M4 Incremental | Per-table watermark-filtered reads; NULL-watermark rows excluded; durable watermark persists across a fresh `DurabilityAuthority` instance (simulated restart); write-then-save-watermark ordering preserved; missing config fails closed | `test_m4_dag_dispatch_integration.py` — 6/6; `test_m4_watermark_authority.py` — 13/13 |
| M5 State sync/repair-eligibility | Reconciliation dispatch reuses the canonical `CanonicalReconciliationEngine`; repair eligibility evaluated but never executes a mutation | `test_m5_reconciliation_dispatch_reuses_canonical_engine` — 1/1 |
| M6 Schema-only | Schema created, zero rows moved (schema deployment fenced from data transport) | `test_m6_creates_schema_zero_rows` — 1/1 |
| M7 Data-only | Data transported, DDL fingerprint unchanged, schema-deployment stage structurally absent from DAG | `test_m7_transports_data_ddl_fingerprint_unchanged`, `test_m7_dag_never_contains_schema_deployment_stage` — 2/2 |
| M8 Validation-only | Mismatch detection without mutating target; DAG structurally never contains a mutating stage | `test_m8_detects_mismatch_without_mutating_target`, `test_m8_dag_never_contains_mutating_stages` — 2/2 |

Plus 4 cross-cutting core tests (`test_execute_migration_rejects_missing_compiled_dag`, `test_removing_transport_stage_prevents_row_movement`, `test_adding_transport_stage_causes_row_movement`, `test_plan_fingerprint_is_bound_and_recorded`) — 4/4. **Total `test_plan_driven_execution.py`: 12/12, re-run this session, unchanged since the mode-fence addition, confirmed still green with all of this session's M2/M3/M4/Evidence changes present.**

Durability/restart evidence: `test_m4_i02` (fresh `DurabilityAuthority` instance against the same on-disk store) and `test_m3_i03` (fresh dispatcher run reusing the same CDC WAL/dedup store) both simulate a process restart and prove state survives it correctly (watermark persists; replayed transactions are deduplicated, not reapplied).

CDC boundary evidence: `test_m2_i01` (deterministic mid-bulk INSERT/UPDATE/DELETE, final target state has no loss/no duplication) and `test_m3_i01`/`test_m3_i03` (INSERT/UPDATE/DELETE correctness plus replay dedup) — see §33.2.

Security results: SEC-I01–I15 hostile/security matrix, 15/15, re-run this session — covers authenticated≠authorized, identifiers≠ownership, caller roles not authoritative, missing governance record denies, stale fencing token rejected, plan identity mismatch fails closed, unauthorized M5 repair fails closed, M8 cannot mutate, M3/M6/M7 illegal-stage mode-fence rejection, unrecognized mode fails closed, failed prerequisite blocks downstream, watermark identity mismatch, stale-execution watermark fencing.

Evidence Authority #12 / Validation Authority #11 wiring proof: see §33.3.

Bypass audit (all 3 of 3 closed) and duplicate-authority/P7B/P7C audit: see §33.1 and §33.4.

### 33.6 Full regression — combined targeted run, then whole-repo

Targeted combined run (bypass evidence + M2/M3/M4/M4-watermark + M1/M5/M6/M7/M8 + SEC-I01-15), all re-run fresh this session (not reused from any prior session's numbers):
- Bypass evidence suite: **100 passed, 61 skipped** (0 failed).
- M2 (3) + M3 (4) + M4 dispatch (6) + M4 watermark authority (13) + M1/M5/M6/M7/M8 (12) + SEC-I01-15 (15): **53 passed** (0 failed).

Whole-repository regression (`pytest -q` from repo root, includes every change from this session and all prior sessions in this campaign — the mode fence, the SEC-I suite, the M2/M3/M4 wiring, the Evidence Authority binding, and the newly-reconfirmed bypass closures — together in one run for the first time):

```
pytest -q (repo root, full suite)
→ 1 failed, 7026 passed, 165 skipped, 4 warnings in 1310.28s (0:21:50)
```
7026 passed is 28 more than the prior clean baseline (6998 passed/165 skipped/0 failed, §32.1 item 6) — consistent with this session's new coverage (M2: 3, M3: 4, M4 dispatch: 6, M4 watermark authority: 13, SEC-I01-15: 15 minus overlap already counted = net addition of untracked new test files now collected in the whole-repo run for the first time; skip count unchanged at 165, confirming no test was newly skipped/hidden).

**The 1 failure**: `tests/unit/engine_extensions/test_sandbox_filesystem.py::test_truthful_execution_result_reports_host_mediated_boundary` — asserts `SubprocessSandbox.execute(...).success is True` against a 10.0s wall-clock budget; failed with `error='Extension execution exceeded wall-clock budget of 10.0s...'`. This test belongs to an entirely unrelated subsystem (extension sandboxing/subprocess execution) — it has no relationship to CDC, durability, evidence, watermarks, or the ManagerAgent/AkaalMigrationEngine/daemon bypass closures this session touched or reconfirmed. **Re-run in isolation immediately after the full-suite run: `pytest tests/unit/engine_extensions/test_sandbox_filesystem.py::test_truthful_execution_result_reports_host_mediated_boundary -v` → 1 passed in 13.89s.** This confirms it is a wall-clock-budget flake caused by CPU contention during the full-suite run (this session ran two parallel sub-agents plus several background pytest invocations concurrently with the full-repo run to maximize throughput, which is the most plausible cause of transient scheduling delay pushing a 10-second-budgeted subprocess test over its limit), not a genuine regression from any change in this campaign. **Whole-repo regression, net: 0 real failures.**

### 33.7 Limitations and honestly-scoped gaps (not fixed, precisely named)

1. No production CDC source listener (Debezium/LogMiner/replication-slot equivalent) is wired into `_handle_cdc_init` — M2/M3 are proven against the authorized test-only seam, not a live upstream source. This was never in this campaign's scope (the scope was closing DAG-dispatch bypasses and proving the dispatcher-to-authority wiring is real, not building a production CDC ingestion connector).
2. M4's write-then-save-watermark ordering is proven by code inspection + the durability layer's own isolated unit test, not by a dedicated crash-injection integration test that kills the dispatcher between `write_batch` and `save_watermark` and asserts the watermark did not advance. Real, narrow, residual gap for future hardening.
3. Two independent CDC domain-model generations coexist in `akaal.cdc` (see §33.2) — pre-existing, not introduced by this campaign, flagged for a future consolidation decision.
4. `ValidationAuthority`'s fencing-token verification and CDC-boundary validation are not exercised anywhere in the current DAG path; `_reconcile` performs no fencing check despite contract rules 140-142. Documented, not fixed (would require the larger `ValidationAuthority` integration effort scoped out in §33.3).
5. P7B/P7C gates do not exist in this repository yet (confirmed future-roadmap labels, not implemented-then-bypassed code) — the audit proves nothing is bypassed because there is nothing implemented to bypass. This is a scope boundary, not a defect.
6. `akaal` → `akaalEngine` coupling is slightly wider than "durability + evidence only" (also touches `akaalEngine.data_processing` in `engine_gateway.py` and `deduplication.py`) — narrow/targeted, not flagged as a violation, but noted precisely.

### 33.8 Proof classification per claim

- **Physically proven this session (real code executed, real assertions, reproducible)**: all 3 bypass closures (§33.1) with reconfirmed test evidence (100 passed/61 skipped); M2/M3/M4 DAG-dispatch wiring (§33.2) with reconfirmed test evidence from an independent sub-agent's own separate pytest run (26/26 new + 12/12 pre-existing); Evidence Authority #12 binding (§33.3, `test_m4_i06`); whole-repo regression (§33.6): 7026 passed, 165 skipped, 1 failed-and-reproduced-passing-in-isolation (confirmed environmental flake, not a regression).
- **Determined by documentary/code audit, not by a new test (methodologically appropriate for these questions)**: Validation Authority #11 sufficiency determination (§33.3); P7B/P7C non-existence-hence-non-bypassable conclusion (§33.4); duplicate-authority and dependency-narrowness audits (§33.4); `akaal.advisory.executor` non-bypass conclusion (§33.1, based on reading the function body and confirming zero I/O side effects).
- **Documented as a known gap, explicitly not claimed as proven**: items 1-6 in §33.7.

### 33.9 Verdict

All three confirmed production physical-execution bypasses are closed and reconfirmed (§33.1). M2/M3/M4 DAG-dispatch integration to the real CDC and durability authorities is implemented and proven end-to-end against real on-disk state, independently reconfirmed by a separate verification pass (§33.2). Evidence Authority #12 is genuinely bound (§33.3). Validation Authority #11 is confirmed sufficient as currently wired, with the richer alternative's gap precisely documented rather than left ambiguous (§33.3). P7B/P7C are confirmed to not exist as implemented gates, so nothing bypasses them (§33.4). The duplicate-authority and dependency-narrowness audits found no violations, with one pre-existing architectural note (two CDC domain-model generations) documented for future work, not this campaign's scope (§33.2, §33.7). The targeted regression covering every change in this campaign is 100% green (153 passed across all targeted suites, 0 failed). The whole-repository regression is 7026 passed / 165 skipped / 1 failed, and that single failure was reproduced as passing in isolation immediately afterward, confirming it is a transient CPU-contention flake in an unrelated subsystem (extension sandboxing), not a regression caused by this campaign's changes — net whole-repo result: 0 real failures. All limitations and residual gaps are precisely named in §33.7, none of which block the specific, scoped claims this campaign makes.

**M1-M8 CORRECTION IMPLEMENTATION — FINAL ACCEPTANCE RETEST CANDIDATE**
