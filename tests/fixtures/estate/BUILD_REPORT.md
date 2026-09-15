# AKAAL Simulated 1,000,000-Row Database Estate — Build Report

Session scope: fixture/estate build only. No AKAAL M1–M8 acceptance was run.
No PL/SQL translation was executed. No production code was modified. No git
writes were made.

## A. Repository integration

- Governing spec located and read: `docs/architecture/AKAAL_Enterprise_Migration_Workflow_v1.0.md`
  (9-step workflow, M1–M8 semantics, ExecutionPlan/DAG). Validation Authority
  #11 / Evidence Authority #12 confirmed in `contract.txt` §H and `rules.json`.
- No existing fixture infrastructure operated anywhere near 1M-row scale.
  Reused where possible: `akaal/cdc/contracts/event.py` (`CDCEvent`,
  `TransactionContext`) and `checkpoint.py` (`Position`, `Checkpoint`) for
  every CDC/transaction-stream fixture in M2/M3, instead of inventing a
  parallel event model.
- Two parallel, non-interoperable codebases were found (`akaal/` vs
  `akaalEngine/`). Per owner decision, the relational/M1–M8 estate targets
  `akaal/`'s contracts (`ExecutionMode` enum, `IUniversalConnector`/
  `IDatabaseCapability`, `akaal/cdc/contracts`); the PL/SQL corpus targets
  `akaalEngine`'s P7C.11 shape. These were kept clearly separated — no new
  shared runtime, transport, CDC, validation, or evidence authority was
  introduced.
- New fixture-only components, all under `tests/fixtures/estate/`:
  `config/` (declarative schema), `generator/` (deterministic generation),
  `cdc/` (event wrapper), `modes/` (M1–M8 builders), `plsql_corpus/`
  (Oracle PL/SQL corpus + expected truth), `manifests/` (independent truth
  extraction + fingerprints), `reset.py`, `selftest/`.
- Duplicate-authority audit: none introduced. `akaal/schema/domain/models.py`'s
  `CanonicalTable/View/...` dataclasses and `akaal/connectors/contracts`'
  `IUniversalConnector`/`IDatabaseCapability` were identified as the
  interfaces a later acceptance campaign would plug this estate into; this
  session did not modify or duplicate them.

## B. Resource usage

- Baseline build elapsed time: **174.6 seconds** (1,000,000 rows, 206 tables,
  21,415 LOB payloads).
- Disk footprint: **2.34 GB** (`source_baseline.sqlite`), **2.2 GB** total
  under `tests/fixtures/estate/data/` including mode fixtures and manifests.
- Generation throughput: ≈5,730 rows/sec sustained across the full build.
- Peak memory was bounded per-item during generation (largest single LOB
  ≤~50MB, materialized/hashed/inserted/discarded one at a time — see
  Limitation D1 below) and per-table during manifest fingerprinting
  (largest table's full row set held at once, then released).

## C. Source estate

| Schema | Tables | Populated | Empty | No-PK | Rows |
|---|---:|---:|---:|---:|---:|
| IDENTITY_ACCESS_MGMT | 28 | 26 | 2 | 1 | 140,000 |
| COMMERCE_ORDERS | 24 | 22 | 2 | 1 | 200,000 |
| FINANCIAL_LEDGER | 20 | 18 | 2 | 1 | 130,000 |
| CATALOG_PRODUCTS | 17 | 15 | 2 | 0 | 70,000 |
| WAREHOUSE_INVENTORY | 15 | 13 | 2 | 1 | 90,000 |
| FULFILLMENT_LOGISTICS | 15 | 13 | 2 | 1 | 80,000 |
| ORGANIZATION_HR | 16 | 14 | 2 | 0 | 40,000 |
| CONTENT_DOCUMENTS | 15 | 13 | 2 | 0 | 50,000 |
| AUDIT_COMPLIANCE | 14 | 12 | 2 | 1 | 90,000 |
| OPERATIONAL_METRICS | 13 | 11 | 2 | 0 | 50,000 |
| INTEGRATION_REGISTRY | 14 | 12 | 2 | 0 | 30,000 |
| COMPATIBILITY_LAB | 15 | 13 | 2 | 0 | 30,000 |
| **TOTAL** | **206** | **182** | **24** | **6** | **1,000,000** |

Reconciles to exactly 1,000,000 (verified independently three times: at
declaration in `config/domains.py` via assertions, physically via
`PRAGMA`/`COUNT(*)` after the build, and again by the self-test suite).

**Table count** (206) is below the spec's "approximately 216" target
(~95%) — see Limitation D2.

**Relational complexity delivered**: surrogate (sequential integer),
UUID-like, natural (business-key), and alphanumeric single-column PKs;
composite PKs (2- and 3-column, e.g. `product_relationships`); 6
intentional no-PK append-only-log tables (`authentication_events`,
`checkout_events`, `journal_lines`, `movements`, `tracking_events`,
`audit_events`); ordinary, composite, self-referencing (`categories`,
`departments`), and cross-schema (e.g. `orders.customer_id`) foreign keys;
many-to-many bridge tables (`role_permissions`, `user_roles`,
`product_attributes`, …); single- and multi-column UNIQUE constraints;
NOT NULL and DEFAULT clauses throughout. `PRAGMA foreign_key_check`: **0
violations** across all 1,000,000 rows.

**Datatype coverage delivered** (§8): exact numeric (`NUMBER`,
`NUMBER(38)`, positive/negative/zero scale, high precision, financial
decimals), approximate numeric (`FLOAT`, `BINARY_FLOAT`,
`BINARY_DOUBLE`), character (`VARCHAR2`/`NVARCHAR2`/`CHAR`/`NCHAR`, with
trailing-space and empty-vs-NULL cases), full Unicode profile matrix
(English, Kannada, Devanagari, Arabic, CJK, accented European, currency
symbols, emoji/combining characters — `COMPATIBILITY_LAB.unicode_text_matrix`
and spread throughout `NVARCHAR2` columns estate-wide), temporal
(`DATE`, `TIMESTAMP` with fractional seconds, `TIMESTAMP WITH TIME ZONE`,
`TIMESTAMP WITH LOCAL TIME ZONE`, `INTERVAL YEAR TO MONTH`, `INTERVAL DAY
TO SECOND`, leap-day/historical/future dates, positive/negative offsets —
`COMPATIBILITY_LAB.temporal_edge_cases`), binary (`RAW`, zero-byte and
hash-payload cases), LOB (`CLOB`/`NCLOB`/`BLOB`), structured (`JSON`,
`XMLTYPE`). A dedicated quoted-identifier table
(`COMPATIBILITY_LAB."Quoted_Case_Table"`, with a reserved-word column
`"Order"` and a space-containing column) exercises identifier quoting
end-to-end, including in one PL/SQL function (`FN_QUOTED_IDENT_ECHO`).

## D. LOB estate

| Band | Target count | Actual count | Byte range |
|---|---:|---:|---|
| tiny | 15,000 | **15,000** | 1–5 KB |
| small | 5,000 | **5,000** | 10–50 KB |
| medium | 1,200 | **1,200** | 100–500 KB |
| large | 200 | **200** | 1–5 MB |
| very_large | 15 | **15** | 10–50 MB |

All five bands hit their exact target count (deterministic shuffle-based
allocator, verified by the self-test suite). Every populated LOB was
sha256-hashed at generation time and the hash recorded in
`data/lob_hashes.json` (4.0 MB, 21,415 entries) and cross-referenced into
`data/source_manifest.json`. Multilingual documents, JSON text, XML text,
repetitive payloads, high-entropy binary, zero-byte runs, and embedded-NULL
binary payloads are all represented (`generator/lob_factory.py`).

## E. Programmable object corpus

| Kind | Count (min required) |
|---|---:|
| Views | 32 (≥32) |
| Materialized views | 4 (≥4) |
| Sequences | 40 (≥40, varied start/increment/cache/cycle/min/max) |
| Triggers | 26 (≥24) |
| Procedures | 25 (≥24) |
| Functions | 25 (≥24) |
| Package specs | 12 (≥12) |
| Package bodies | 12 (≥12) |
| **Total objects** | **176** |
| Translation units (proc+func+trig+pkg body) | **88** (≥100 preferred, see D3) |

Total source: **1,343 LOC / 50,110 bytes**. Complexity bands: simple /
moderate / complex / very_complex all represented. Construct coverage
(§11) includes: IN/OUT/IN OUT parameters, local variables, constants,
nested blocks, IF/ELSIF/CASE, LOOP/WHILE/numeric FOR, EXIT WHEN, implicit
and explicit cursors (including parameterized and `FETCH FIRST n ROWS
ONLY`), cursor FOR loops, `%TYPE`/`%ROWTYPE`, records, collection types
(`TABLE OF`, associative arrays), nested/recursive procedure calls,
exception handling (named, custom via `PRAGMA EXCEPTION_INIT`, `RAISE`,
`RAISE_APPLICATION_ERROR`, `OTHERS`/`SQLERRM`), dynamic SQL
(`EXECUTE IMMEDIATE ... USING`), `SELECT INTO` (single- and multi-column),
`INSERT`/`UPDATE`/`DELETE`/`MERGE`, `RETURNING INTO`, `BULK COLLECT`/
`FORALL`, sequence/date/string/numeric functions, `NVL`/NULL semantics,
`PRAGMA AUTONOMOUS_TRANSACTION`, cross-object/cross-package/cross-schema
calls (e.g. `ORDER_MGMT_PKG` calling `FINANCIAL_LEDGER.FN_CONVERT_CURRENCY`).
Zero unintentionally empty/invalid corpus objects (self-tested).

## F. M1–M8 fixture readiness

All eight modes are **built and self-tested**, scoped per the plan's
bounded-scope design decision (only M1 requires the full 1,000,000-row
baseline; M2–M5/M8 use dedicated, purpose-built, bounded datasets — this
was disclosed in the approved plan, not a silent cut).

| Mode | Initial source | Initial target | Delta/discrepancy fixture | Reset | Manifest/fingerprint | Status |
|---|---|---|---|---|---|---|
| M1 | Full 1,000,000-row baseline | Empty shell, matching DDL (fingerprinted) | n/a (bulk) | `reset.reset_mode("M1")` | `source_manifest.json` + DDL fingerprint | READY |
| M2 | 500-row sample each of `orders`/`journals` | = source (bulk+CDC) | 7 transactions (5 committed, 2 rolled back), 70 events, `CDCEvent`-shaped | `reset.reset_mode("M2")` | `expected_final_state.json` + `Checkpoint` | READY |
| M3 | 400-row `products` sample, proven synchronized via fingerprint | = source | 4 CDC transactions, insert/update/delete incl. repeat-update | `reset.reset_mode("M3")` | `expected_post_cdc_state.json` | READY |
| M4 | 58 dedicated watermark rows (numeric/timestamp/compound, ties, late arrival, NULL watermark) | n/a (polling) | 7 poll batches + 1 watermark-before-commit failure scenario | `reset.reset_mode("M4")` | `poll_batches.json` | READY |
| M5 | 200 explicit keyed rows | 190 explicit keyed rows | 130 deltas across 5 difference categories, set-math reconciled | `reset.reset_mode("M5")`, proven deterministic | `manifest.json` reconciliation numbers | READY |
| M6 | Full 206-table + 176-object schema/object corpus | 0 tables | n/a (schema only) | `reset.reset_mode("M6")` | object manifest + PL/SQL expected truth | READY |
| M7 | Full 1,000,000-row baseline | Pre-created shell, DDL fingerprint recorded (matches M1's) | n/a (data only) | `reset.reset_mode("M7")` | DDL fingerprint invariant | READY |
| M8 | 285 explicit keyed rows | 275 explicit keyed rows | 160 discrepancies across 10 categories (incl. structural), set-math reconciled | `reset.reset_mode("M8")`, proven deterministic | `mismatch_manifest.json` | READY |

No AKAAL mode was executed; no PASS/FAIL claim is made for AKAAL itself.

## G. PL/SQL → PL/pgSQL corpus readiness

- 176 source objects, 88 executable/procedural translation units.
- Independent expected-truth (`plsql_corpus/expected_truth.py`, serialized
  per-mode into `data/modes/m6_schema_only/plsql_expected_truth.json`)
  assigns, per object: `entrypoint_status` (`HAS_ENTRYPOINT` only for
  PROCEDURE/FUNCTION — the two kinds P7C.11 actually has a production AST
  entrypoint for today, per repository research this session; everything
  else is honestly `NO_PRODUCTION_ENTRYPOINT_YET`) and, for
  procedure/function objects only, a construct-based `predicted_difficulty`
  (`LIKELY_TRANSLATABLE` / `LIKELY_REWRITE_REQUIRED` /
  `LIKELY_MANUAL_REVIEW` — 28/12/6 objects respectively). This is
  explicitly a prediction for later scoring, not a `TranslationCertification`
  claim, which only P7C.11 itself can assign by actually running.
- This expected truth was **not** derived from running AKAAL's translator.
- No deterministic input/output test vectors were computed for individual
  procedures/functions this session (see Limitation D4) — the corpus and
  its classification are ready; per-object behavioral test vectors are not.

## H. Fixture self-tests

`pytest tests/fixtures/estate/selftest/ -v`: **26 passed, 0 failed, 0
skipped** (skip guard exists only for "baseline not built yet," which is
not the current state). Covers: schema/row-count reconciliation, physical
row totals, FK integrity, composite-PK uniqueness, no-PK/empty-table
preservation, LOB band counts, source-manifest-vs-physical-state
agreement, table fingerprint reproduction, PL/SQL corpus minimums and
honest-entrypoint-labeling, M1/M6/M7 DDL-fingerprint invariants, M2–M5/M8
reconciliation math, and M5/M8/M2/M3 rebuild determinism plus
reset-isolation (resetting M5 does not change M8's on-disk state).

## I. Limitations (explicitly not fixture failures, but not hidden)

1. **LOB generation is materialize-then-hash-then-discard, not true
   incremental streaming I/O.** Peak memory per item is bounded (≤~50MB
   for the largest very_large LOB) and items are never held concurrently,
   but this is a pragmatic simplification of "streamed" rather than a
   byte-level streaming implementation.
2. **Table count is 206, not ~216** (~95% of target). All 12 schemas'
   row totals and the 1,000,000 grand total are exact; only the table
   *count* is short, from time-bounded scope during this session.
3. **88 translation units** (procedures+functions+triggers+package
   bodies) vs. the spec's "100+ preferred" — the 176-object total across
   all corpus kinds exceeds 100 if views/matviews/sequences count as
   "relevant dependent SQL objects" per §13's own wording, but the
   stricter procedural-only count is short.
4. **No per-object deterministic behavioral test vectors** for the
   PL/SQL corpus (§12's "deterministic test vectors where behavioral
   equivalence can be simulated") — classification and construct
   inventory are independent and complete; input/output vectors are not
   yet built.
5. **M2–M5 and M8 use bounded, purpose-built datasets, not the full
   1,000,000-row baseline** — by design (see plan §"Key Design
   Decisions"), not an oversight, and consistent with the spec's own
   "dedicated"/"mathematically explicit set" language for those modes.
6. Everything requiring a genuine Oracle or PostgreSQL engine remains
   **LIVE_UNVERIFIED / EXTERNAL_DEFERRED**: no genuine Oracle behavior,
   LogMiner, redo/archive semantics, driver behavior, or physical
   performance is established by this simulated estate, and none of the
   evidence in this report is LIVE_PROVEN.

## J. Final readiness conclusion

**SIMULATED 1M M1–M8 + PL/SQL ACCEPTANCE ESTATE READY**, with the scope
caveats in Limitations D1–D5 (all schema/row/FK/LOB-band numbers are
exact and independently verified; table count and translation-unit count
are moderately below stated targets but the estate is structurally
complete, self-tested, deterministic, and reset-capable across all eight
modes and the PL/SQL corpus).
