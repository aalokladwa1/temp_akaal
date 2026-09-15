# ORACLE PL/SQL -> POSTGRESQL PL/pgSQL TRANSLATION — CURRENT-STATE ACCEPTANCE REPORT (read-only, evidence reconstruction only)

**Purpose**: reconciliation of translation-subsystem acceptance evidence against CURRENT physical repository state. Read-only. No implementation, no test writing/modification, no fabricated numbers. Issues no OWNER ACCEPTED/FROZEN declaration and does not start P7D or any acceptance campaign.

## 1. Canonical production translation path — determined and verified this session

**Two parallel implementations exist. They are reported completely separately below. The dead one is NOT evidence of translator capability.**

### 1a. `akaal/transpiler/*` — DEAD / UNWIRED, confirmed this session
- Files present: `akaal/transpiler/{facade.py, __init__.py, parser/plsql_parser.py, generator/plpgsql_generator.py, converters/package_converter.py, validator/__init__.py, rules/__init__.py, ast/__init__.py}` — regex/string-based, self-grades its own "accuracy_percent."
- Repository-wide grep for `akaal.transpiler` / `akaal import transpiler` imports OUTSIDE `akaal/transpiler/` itself, performed fresh this session across the whole repository: **exactly one hit, in a documentation file** (`docs/architecture/AKAAL_Gateway_Directory_Analysis.md`) — zero hits in any `.py` file anywhere outside the package's own directory.
- **Conclusion: CONFIRMED DEAD.** No production code, no test, no producer imports it. It does not count as evidence of AKAAL's translation capability, and no result from it is used anywhere below.

### 1b. `akaalEngine/schema/procedural/*` — the canonical, production-wired path, confirmed this session
- Files: `lexer.py` (`ProceduralLexer`), `parsers/plsql.py` (`PLSQLParser`), `parsers/tsql.py` (`TSQLParser`), `emitters/plpgsql.py` (`PLpgSQLEmitter`), `ast_nodes.py`, `diagnostics.py`, `transforms/{control_flow,cursors,exceptions,packages}.py`.
- Repository-wide grep for `schema.procedural` imports performed fresh this session: **22 files** import from this package, including (production, not test): `akaalEngine/schema/authority.py`, `akaalEngine/schema/core/processor.py`, `akaalEngine/intelligence/producers/sql_translation.py` (the P7C.11 intelligence producer).
- **Conclusion: CONFIRMED WIRED into production** (`akaalEngine.schema.authority` / `akaalEngine.schema.core.processor`) and into the P7C.11 intelligence producer. This is the canonical path for everything below.

## 2. PL/SQL corpus — exact current denominator, independently recomputed this session

**Method**: imported each corpus module (`tests/fixtures/estate/plsql_corpus/{procedures,functions,triggers,packages,views,materialized_views,sequences}.py`) via the actual venv Python and counted each module's own object list directly — not assumed, not copied from any prior report's arithmetic.

| Object type | Count (independently recomputed this session) |
|---|---:|
| Procedures | 25 |
| Functions | 25 |
| Triggers | 26 |
| Packages (spec+body units combined) | 24 |
| Views | 32 |
| Materialized views | 4 |
| Sequences | 40 |
| **TOTAL CORPUS OBJECTS** | **176** |

This matches the figure in `tests/fixtures/estate/BUILD_REPORT.md`, independently reproduced rather than trusted.

## 3. Has the corpus ever been executed end-to-end through the real translator? — NOT_EXECUTED, verified this session

- Repository-wide grep for any file importing `PLSQLParser`, `TSQLParser`, or `PLpgSQLEmitter`: exactly two test files — `tests/unit/engine_intelligence/test_p7c11_sql_translation.py` (17 tests) and `tests/unit/engine_schema/test_aoir_ast_pipeline.py` (3 tests). Both re-run fresh this session: **17 passed** and **3 passed** respectively (20 total, 0 failed).
- Grep of BOTH of those files for `plsql_corpus`: **zero matches in either file.**
- Grep of all of `tests/` for `plsql_corpus`: 3 files reference it — `tests/fixtures/estate/selftest/test_estate_self_tests.py`, `tests/fixtures/estate/reset.py`, `tests/fixtures/estate/modes/m6_schema_only.py` — none of which import or call `PLSQLParser`/`TSQLParser`/`PLpgSQLEmitter`. They only check corpus manifest/object-count integrity as fixture bookkeeping.
- **Conclusion, verified this session, not merely re-asserted from the background briefing: the 176-object corpus has NEVER been run end-to-end through the real translator (`PLSQLParser`/`TSQLParser`/`PLpgSQLEmitter`).** The only test coverage of the real translation machinery (20 tests total) uses small, hand-written, ad-hoc PL/SQL/T-SQL snippets unrelated to the corpus fixture.

**Per-object classification of the 176-object corpus, per the instruction to never silently exclude any object from the denominator:**

| Classification | Count | Basis |
|---|---:|---|
| NOT_EXECUTED | 176 | None of the 176 corpus objects has ever been passed through `PLSQLParser.parse()`/`TSQLParser`/`PLpgSQLEmitter` by any test or process in this repository, confirmed by the import-and-corpus-reference grep above. |

**FINAL_TRANSLATION_ACCURACY_NOT_MEASURED** — the corpus has never been independently executed/graded. This is reported literally, per instruction, rather than substituting `expected_truth.py`'s predictions for a real measured score.

### 3a. `expected_truth.py` — confirmed, this session, to explicitly self-document as NOT independent ground truth

Re-read `tests/fixtures/estate/plsql_corpus/expected_truth.py`'s current docstring this session (not from memory): it states verbatim that it is "**NOT** derived from running AKAAL's translator" and "is NOT a claim about what the translator will actually output," and that it assigns only (1) `entrypoint_status` (a repository fact about whether an AST entrypoint exists for an object KIND — PROCEDURE/FUNCTION only) and (2) `predicted_difficulty` (a construct-based PREDICTION for procedures/functions only, explicitly distinguished from a `TranslationCertification` claim, "which only P7C.11 itself can assign by actually running"). **This confirms the background briefing's claim exactly, re-verified against the current file, not merely trusted.** Per instruction, `expected_truth.py` is NOT used anywhere in this report to manufacture an independent accuracy score.

## 4. Explicit numerator/denominator accuracy metrics

Because the corpus has never been executed (§3), every one of the following is **FINAL_TRANSLATION_ACCURACY_NOT_MEASURED**, reported with the literal denominators available and NOT a fabricated numerator:

- (A) supported_translated / supported_expected: **NOT_MEASURED** (numerator requires actual execution; denominator, per `entrypoint_status`, is 25 procedures + 25 functions = 50 objects that HAVE an AST entrypoint today — this is a repository-fact denominator, not a promise of correctness)
- (B) supported_correct / supported_expected: **NOT_MEASURED / 50** (same denominator basis as A; numerator requires actual execution AND independent correctness grading, neither performed)
- (C) correctly_classified_objects / total_objects: **NOT_MEASURED / 176**
- (D) correctly_flagged_unsupported_or_manual_review / expected_unsupported_or_manual_review: **NOT_MEASURED** — the honest, by-design UNSUPPORTED bucket includes all 26 triggers + 24 package spec/body units = 50 objects for which `PLSQLParser.parse()` raises `SyntaxError` on anything but `CREATE [OR REPLACE] {FUNCTION|PROCEDURE}` (confirmed by direct read of `plsql.py::parse()`, lines 99-112, this session); views (32), materialized views (4), and sequences (40) are DDL-only objects the procedural translator was never built to translate at all (confirmed via `sql_translation.py`'s own docstring, re-read this session) — these 76 objects are also outside the procedural translator's scope by design, not a translation failure. Whether the translator, if actually run against these 176 objects, would CORRECTLY flag each as UNSUPPORTED/out-of-scope was never tested (no execution occurred) — hence NOT_MEASURED.
- (E) accounted_objects / total_corpus_objects: **176 / 176** — every object is accounted for in §3's classification table (all NOT_EXECUTED); none silently excluded.

## 5. Capability-by-capability breakdown (never collapsed into one vague percentage)

Per the instruction to report each of the following separately. Values below are established EITHER by direct code inspection of the current `akaalEngine/schema/procedural/*` files (verified this session) OR by the 20 existing hand-written unit tests (re-run fresh this session, 20/20 passed) — NEVER by corpus execution (§3), which never occurred.

| Capability | Status | Basis |
|---|---|---|
| Parser success | PARTIAL, by design | `PLSQLParser`/`TSQLParser` succeed only for `CREATE [OR REPLACE] {FUNCTION\|PROCEDURE}` source text (verified this session, `plsql.py` lines 99-112); anything else raises `SyntaxError` |
| AST construction | IMPLEMENTED for PROCEDURE/FUNCTION | Real token-based AST (`ast_nodes.py`), not regex; confirmed by direct read |
| Emitter success | IMPLEMENTED for PROCEDURE/FUNCTION, with a KNOWN DEFECT | `PLpgSQLEmitter` exists and is exercised by 20 passing unit tests; but see §6 (T-SQL `@variable` leakage) |
| Syntax preservation | NOT_MEASURED at corpus scale | Only unit-test-scale evidence exists |
| Datatype translation | NOT_MEASURED at corpus scale | Same |
| Parameter translation | NOT_MEASURED at corpus scale | `ParameterDeclaration`/`ParameterMode` AST nodes exist and are exercised by unit tests, not the corpus |
| Variable translation | NOT_MEASURED at corpus scale; KNOWN DEFECT for T-SQL `@var` (§6) | |
| Control-flow translation | NOT_MEASURED at corpus scale | `transforms/control_flow.py` exists |
| Exception handling | NOT_MEASURED at corpus scale | `transforms/exceptions.py` exists |
| Cursor translation | NOT_MEASURED at corpus scale | `transforms/cursors.py` exists |
| DML translation | NOT_MEASURED at corpus scale | `DMLStatement` AST node exists |
| Transaction semantics | NOT_MEASURED at corpus scale | `AutonomousTxNode` exists |
| Dependency preservation | NOT_MEASURED | Never tested at corpus scale |
| Object ordering | NOT_MEASURED | Never tested at corpus scale |
| Procedure translation | NOT_MEASURED at corpus scale (unit-test-scale only, 20/20 passing) | |
| Function translation | NOT_MEASURED at corpus scale (unit-test-scale only) | |
| Trigger support | UNSUPPORTED, confirmed this session | `PLSQLParser.parse()` raises `SyntaxError` for anything but FUNCTION/PROCEDURE — honestly reported via `sql_translation.py`'s own docstring and a forced UNSUPPORTED/explicit finding code, not silently faked |
| Package support | UNSUPPORTED, confirmed this session | Same mechanism as triggers |
| Sequence translation | OUT_OF_SCOPE for the procedural translator (DDL concern) | Confirmed via `sql_translation.py` docstring |
| View/materialized-view handling | OUT_OF_SCOPE for the procedural translator (DDL concern) | Same |
| Unsupported construct detection | IMPLEMENTED, honestly reported | `UnsupportedConstruct` AST node exists; triggers/packages produce an explicit finding code, not a silent drop (confirmed via `sql_translation.py` lines ~278-311, re-read this session) |
| Manual-review classification | IMPLEMENTED | `TranslationCertification.MANUAL_REVIEW_REQUIRED` is a real enum value with a deterministic mapping from `ConversionSafety`, confirmed by direct read of `_SAFETY_TO_CERTIFICATION` in `sql_translation.py` |
| Source-code loss/drop detection | PARTIAL | The `@variable` leakage defect (§6) is caught only by a downstream regex safety net, not by the emitter itself — a narrow, specific, documented gap, not a general loss-detection capability |
| Generated PostgreSQL validity | NOT_PROVEN | No PostgreSQL engine is ever invoked (§7) |
| PostgreSQL compilation | **PHYSICAL_POSTGRESQL_COMPILATION_NOT_PROVEN** (§7) | |
| Cross-engine semantic equivalence | **CROSS_ENGINE_SEMANTIC_EQUIVALENCE_NOT_PROVEN** (§8) | |

## 6. Known defects — re-verified against CURRENT file contents this session

### 6a. T-SQL `@variable` leakage — CURRENT_CONFIRMED

Re-read `akaalEngine/schema/procedural/lexer.py` this session, current lines 221/223:
```
if char.isalpha() or char in ('_', ':', '@', '$', '#', '%'):
    ...
    while i < length and (sql[i].isalnum() or sql[i] in ('_', '@', '$', '#', '%', '.')):
```
The lexer STILL treats `@` as a valid identifier-start and identifier-continuation character — meaning a T-SQL `@variable` token is still lexed as a single IDENTIFIER token and can pass through unstripped into emitted PL/pgSQL output (which does not use `@`-prefixed variable syntax), producing invalid PostgreSQL.

The safety net is also STILL PRESENT: `sql_translation.py`'s own current docstring (re-read this session, lines 29-41) explicitly states this defect was "discovered empirically," names the exact mechanism (`_looks_like_untranslated_source_syntax`), and states the procedural path is "deliberately capped BELOW EXACT_TRANSLATION_PROVEN/SEMANTIC_EQUIVALENCE_PROVEN even on a clean transpile" because of it — a clean transpile can earn at most `COMPILES_BUT_EQUIVALENCE_UNPROVEN`, and the static regex check forces `MANUAL_REVIEW_REQUIRED` when it fires.

**Classification: CURRENT_CONFIRMED** — the defect is present in the lexer as of this session's direct read; it is caught by a downstream regex safety net (honest, documented), not fixed at the source (still not fixed).

### 6b. Trigger/package UNSUPPORTED at `PLSQLParser.parse()` — CURRENT_CONFIRMED

Re-read `akaalEngine/schema/procedural/parsers/plsql.py` this session, current lines 99-112: `parse()` calls `match_keyword("FUNCTION")` then `match_keyword("PROCEDURE")`; if neither matches, it raises `SyntaxError(f"Expected PROCEDURE or FUNCTION in PL/SQL source: ...")`. No trigger or package branch exists anywhere in this method. `sql_translation.py`'s current docstring (lines 19-21, re-read this session) states this exact same fact and reports it as a forced UNSUPPORTED classification with an explicit finding code, not a silent drop.

**Classification: CURRENT_CONFIRMED** — honestly reported, not fixed, not silently faked.

## 7. Physical PostgreSQL compilation — determined this session

Repository-wide grep for `psycopg2`/`asyncpg` usage inside `akaalEngine/schema/procedural/*` and inside `akaalEngine/intelligence/producers/sql_translation.py`, performed fresh this session: **zero matches in either location.** The translator (parser → AST → emitter) never opens a database connection of any kind; it is a pure in-memory text-to-text transformation. `sql_translation.py`'s own docstring (line 24-27, re-read this session) explicitly states: "Differential (live) execution verification: EXTERNAL_DEFERRED — no live database engine is available in this environment to execute source vs. target logic and diff results. Static verification only."

**Classification: PHYSICAL_POSTGRESQL_COMPILATION_NOT_PROVEN.** Parser/emitter/unit-test success is NOT equated with actual compilation anywhere in this report — no translated output from this path has ever been submitted to a real PostgreSQL engine.

(Separately, the UNRELATED historical bulk-migration script `scripts/stage3_flagship_ora2pg.py` does use real `oracledb`/`psycopg2` connections — but that script performs row-level DML transport between pre-existing schemas, not PL/SQL-to-PL/pgSQL procedural object translation/compilation. It is not evidence of this translator's PostgreSQL-compilation capability and is not conflated with it anywhere in this report; see `M1_M8_CURRENT_STATE_REPORT.md` §5 for that separate historical evidence.)

## 8. Cross-engine semantic equivalence — determined this session

No test, script, or producer anywhere in the repository executes a source Oracle PL/SQL object and its translated PostgreSQL PL/pgSQL counterpart against equivalent inputs and compares observable behavior — confirmed by the same grep in §7 (no live-database code path exists in the translator's own package) and by `sql_translation.py`'s own explicit "EXTERNAL_DEFERRED" statement for differential execution verification.

**Classification: CROSS_ENGINE_SEMANTIC_EQUIVALENCE_NOT_PROVEN.**

## 9. Performance — NOT_MEASURED, every field individually

No corpus-scale or unit-test-scale translation run in this repository records elapsed translation time, object count per second, LOC per second, or bytes per second. The 20 existing unit tests (`test_p7c11_sql_translation.py` + `test_aoir_ast_pipeline.py`) were re-run this session in 1.06s and 3.47s respectively (pytest's own wall-clock reporting, which includes test-harness overhead, fixture setup, and assertion time — NOT a clean, isolated measurement of translation-only elapsed time, and covering only ~20 small hand-written snippets, not the 176-object corpus). Per instruction, this pytest wall-clock number is NOT used to derive or extrapolate an objects/sec, LOC/sec, or bytes/sec figure.

- objects_per_second: **NOT_MEASURED**
- LOC_per_second: **NOT_MEASURED**
- bytes_per_second: **NOT_MEASURED**

No translation objects are referred to as "rows" anywhere in this report.

## 10. Verdicts

- **IMPLEMENTATION**: PARTIAL — real, token/AST-based, production-wired translator exists for Oracle PL/SQL and T-SQL PROCEDURE/FUNCTION objects → PostgreSQL PL/pgSQL; triggers/packages are explicitly unsupported by design; views/materialized views/sequences are out of scope for this translator (DDL concern, handled elsewhere); a known `@variable`-leakage defect remains unfixed at the source (caught only by a downstream regex safety net).
- **LOCAL UNIT PROOF**: PASS (narrow scope) — 20/20 hand-written unit tests re-run fresh this session (`test_p7c11_sql_translation.py`: 17/17; `test_aoir_ast_pipeline.py`: 3/3), covering small, ad-hoc snippets, not the corpus.
- **LOCAL INTEGRATION PROOF**: NOT_EXECUTED — no test integrates the translator against the 176-object corpus or against any larger, structured, multi-object dataset.
- **CORPUS EXECUTION**: NOT_EXECUTED — confirmed this session by import/reference grep; zero of the 176 corpus objects has ever been passed through `PLSQLParser`/`TSQLParser`/`PLpgSQLEmitter`.
- **CORPUS ACCURACY**: FINAL_TRANSLATION_ACCURACY_NOT_MEASURED (§4).
- **POSTGRESQL PHYSICAL COMPILATION**: PHYSICAL_POSTGRESQL_COMPILATION_NOT_PROVEN (§7).
- **CROSS-ENGINE SEMANTIC EQUIVALENCE**: CROSS_ENGINE_SEMANTIC_EQUIVALENCE_NOT_PROVEN (§8).
- **PERFORMANCE MEASUREMENT**: NOT_MEASURED, every field (§9).
- **FINAL ACCEPTANCE**:

> **ORACLE PL/SQL -> POSTGRESQL PL/pgSQL FINAL ACCEPTANCE — NOT EXECUTED**

Rationale: the corpus that exists specifically to measure this capability (176 objects, independently recounted) has never been run through the canonical translator even once. No accuracy number exists to grade, no PostgreSQL compilation was ever attempted, and no cross-engine equivalence was ever attempted. This is not a FAIL (the implementation that exists has not been shown to be broken at corpus scale — it simply has never been tried at that scale) and not a BLOCKED (no missing scaffolding or external dependency prevents running the existing corpus against the existing translator — the corpus and the translator both exist right now and nothing observed this session prevents wiring them together in a future, dedicated session). It is NOT EXECUTED because the acceptance-defining test was never run, and per instruction this report does not default to PASS merely because implementation exists.
