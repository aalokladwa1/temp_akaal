# AKAAL — CLAUDE CODE INITIAL REPOSITORY RECONSTRUCTION & CAMPAIGN B PRECONDITION REPORT

Date: 2026-09-01
Method: read-only reconnaissance (Read/Grep/Glob + read-only git/pytest-collect commands) via six parallel research passes. No production, test, or UI files were modified. No git write operations performed.

---

## 1. Executive Understanding

AKAAL is a heterogeneous enterprise data-migration and continuous-synchronization platform. Physically, it is split across five top-level Python/Go packages:

- **`akaal/`** — the original, large monolithic implementation (37+ subpackages: cdc, planner, schema, engine, governance, operations, transformation, connectors, reporting, etc.). Described by supplied context as "frozen," but the working tree shows active, uncommitted edits to it (see §13).
- **`akaalIPC/`** — thin northbound transport/contract boundary (protocol, security context, subscriptions).
- **`akaalPipeline/`** — newer canonical orchestration authority (execution planning, security, policy, identity, fleet, health, observability, operations).
- **`akaalEngine/`** — newer physical execution kernel (connectors, CDC capture, discovery, durability, validation, gateway).
- **`akaalSoftware/`** — Go/Wails + Angular desktop frontend, out of scope for this pass.

The critical structural finding is that **`akaal/` was never retired** when `akaalIPC`/`akaalPipeline`/`akaalEngine` were split out. Both trees are live simultaneously, and several core authorities (ExecutionPlan, PlanCompiler, execution-mode enum, the entire P6 operations plane) now exist **twice**, once in each generation of the architecture, with different shapes. This is the single most consequential fact for planning any future work.

---

## 2. Repository Reality vs Supplied Context

**SUPPLIED CLAIM:** Campaign A (P7.1–P7.4) is "LOCALLY ACCEPTED & FROZEN."
**PHYSICAL FINDING:** The code and its 56 tests are real, non-stubbed, and pass (56/56, verified by direct execution). But `context.py`/`config.py`/`enums.py` are uncommitted modifications, and `pki.py`, `spiffe.py`, the whole `federation/` directory, and all five P7 test files are **untracked** — never committed to git. No commit, tag, or freeze marker exists anywhere in history for Campaign A (contrast: P4's frozen baseline cites an actual commit hash in `Roadmap.md`).
**CLASSIFICATION:** PARTIAL — implementation claim CONFIRMED, freeze claim CONTRADICTED.
**SAFE INTERPRETATION:** Campaign A is code-complete and unit/integration-proven in the working tree, but is not durably frozen in any git sense. Treat "FROZEN" as aspirational until it is actually committed.

**SUPPLIED CLAIM:** "56 executed / 56 passed / 0 failed / 0 errors" (Campaign A).
**PHYSICAL FINDING:** Independently re-ran the five `tests/security/test_p7*.py` files — 56 passed, 0 failed. CONFIRMED.

**SUPPLIED CLAIM:** 28 unique physical connectors + 2 managed profiles = 30 registered identities (list given, including `aws_rds`/`azure_sql` as the 2 managed profiles).
**PHYSICAL FINDING:** The real registry (`akaal/connectors/registry.py` + `bridge.py`) has 30 registered `connector_id`s too, but the composition differs: it includes `hdfs`, `confluent`, `msk` (not in the claimed list), and does **not** register `aws_rds`/`azure_sql` as connector identities at all — those exist only as a `ManagedServiceFamily` enum and in test fixtures, representing cloud variants of postgresql/mysql/mssql, not distinct registered connectors.
**CLASSIFICATION:** CONTRADICTED (count coincidentally matches at 30, composition does not).
**SAFE INTERPRETATION:** Treat "28+2" as an inaccurate/stale summary. The real, code-verified list is 27 non-streaming connectors (relational/warehouse/NoSQL/object-storage/hdfs) + 6 streaming identities (kafka, confluent[MANAGED], msk[MANAGED], kinesis, event_hubs, pubsub) = 30. `aws_rds`/`azure_sql` are not registered connectors.

**SUPPLIED CLAIM:** ~217 total/216 unique external/live certification obligations; ~148 external-deferred concrete pytest nodes.
**PHYSICAL FINDING:** 216 is corroborated by `reports/p512_external_deferred_complete_ledger.json` and `p512_final_consistency_audit.json` — but a third ledger in the same tree (`p512_repository_test_universe_ledger.json`) states **236**, an internal contradiction between two artifacts both presented as authoritative. The figures 217 and 148 do not appear anywhere in repo artifacts.
**CLASSIFICATION:** PARTIAL / UNKNOWN.
**SAFE INTERPRETATION:** 216 is the best-corroborated figure but is itself contested by a second ledger (236). 217 and 148 are UNVERIFIABLE and should not be repeated as fact until reconciled.

**SUPPLIED CLAIM:** "618/618 CDC tests green" (P3 historical evidence).
**PHYSICAL FINDING:** This string appears only in narrative docs (`Roadmap.md`, `P3.md`, `P4.md`), never in any actual pytest run-log found in the repo.
**CLASSIFICATION:** UNKNOWN — cannot be verified from physical run evidence, only from self-reported documentation.

**SUPPLIED CLAIM (implicit in framing of `.akaal/reports/*.json`):** these are current, trustworthy certification/test reports.
**PHYSICAL FINDING:** They are synthetic — hand-shaped JSON asserting `"outcome": "CERTIFIED"` with fabricated fingerprints, not generated from or linked to any real pytest run. The actual pytest run logs (plain-text files at repo root, `full_regression_output.txt` etc.) show **190 failed, 3923 passed, 13 skipped, 13 errors** as of the last full run (Aug 28).
**CLASSIFICATION:** CONTRADICTED. This is a Zero-Fake Law-relevant finding — see §15.
**SAFE INTERPRETATION:** Do not treat any `.akaal/reports/*.json` file as real test evidence. Use the plain-text pytest run logs at repo root instead.

**SUPPLIED CLAIM:** akaal/ changes are attributable, e.g. `akaalEngine/cdc/api.py` and `akaalEngine/data_processing/dedup/deduplicator.py` as "UNRELATED_REGRESSION_FIX," and ~10 akaal/ files as unrelated regression corrections.
**PHYSICAL FINDING:** Of the 10 modified `akaal/` files, only 2 (`state_store.py`, `engine_gateway.py`) look like genuine small, isolated fixes. The other 8 show real feature development: `quarantine.py` **removes** a sanitization call before persisting quarantine records (security regression, not a fix); `deduplication.py` silently drops a duplicate-disposition return value; `service_impl.py` adds a new `TransactionAnalyzer` code path; `transformer.py`/`transformation/engine.py`/`expression_compiler.py`/`models.py` add a coordinated new conditional-rule/expression-parser feature set (~90+ new lines).
**CLASSIFICATION:** CONTRADICTED for 8 of 10 files.
**SAFE INTERPRETATION:** Do not treat these as harmless drive-by fixes. Two are outright regressions (one security-relevant), and a coordinated feature (conditional transformation rules) is being built directly inside the supposedly frozen `akaal/` package.

---

## 3. Current Phase / Freeze State

- P0–P6: reported FROZEN by supplied context; not independently re-audited line-by-line in this pass (out of scope given time budget), but P6's operations-plane authorities were confirmed to physically exist in `akaal/operations/` — duplicated by a second, newer implementation in `akaalPipeline/{health,fleet,observability,operations}/`.
- P7 Campaign A (P7.1–P7.4): code-complete, 56/56 tests passing, but **uncommitted** — not frozen in any git-durable sense. See §2.
- P7 Campaign B (P7.5–P7.9): **not authorized**, not implemented. Substantial reusable foundations exist for P7.5/P7.6/P7.9; P7.7/P7.8 have only local, non-external primitives (see §8).
- Next authorized body: none — this task is reconnaissance only.

---

## 4. Canonical Architecture

```
OPERATOR/CALLER → akaalIPC (ActorContext, ActorReference, CorrelationContext)
                → akaalPipeline (orchestration, security, policy, identity, fleet, health, observability)
                → akaalPipeline/ports/engine.py (Protocol-typed southbound ports: Discovery/Assessment/Planning/
                  Execution/Checkpoint/Recovery/Validation/Resource/Event/SecretResolution)
                → akaalEngine/gateway (physical execution kernel: connectors, CDC capture, discovery, durability)
                → PHYSICAL SYSTEMS (30 registered connectors)
```

Caveat: `akaalPipeline/ports/engine.py`'s own docstring flags these as "for future akaalEngine integration" — i.e. the port layer is defined but its end-to-end wiring to `akaalEngine/gateway` was not confirmed to be fully live in this pass; treat as PARTIALLY VERIFIED.

Two ExecutionPlan/PlanCompiler implementations coexist (see §14) — the canonical-flow diagram above describes the newer (`akaalPipeline.orchestration`) path; the legacy `akaal.planner.engine.plan_compiler` path still exists and is still referenced elsewhere in `akaal/`.

The 9-step creation workflow is confirmed to exist as a documented concept (`docs/architecture/AKAAL_Enterprise_Migration_Workflow_v1.0.md`) and is referenced in both `akaal/planner/models/p5_domain.py` and the Angular UI — but was not verified to compile into a single canonical model end-to-end given the two competing ExecutionPlan implementations.

M1–M8 execution modes exist as **two parallel enums** with matching semantics but different member names: `akaalPipeline.contracts.enums.MigrationMode` (M1_BULK, M2_BULK_CDC, ...) vs `akaal.planner.models.p5_domain.ExecutionMode` (M1_BULK_MIGRATION, M3_CDC_CONTINUOUS, ...).

---

## 5. Authority Inventory

| Domain | Canonical authority (live) | Notes |
|---|---|---|
| Identity/actor context | `akaalIPC/security/context.py`, `akaalPipeline/security/context.py` | Two layers, IPC-level and Pipeline-level, intentionally distinct per architecture |
| Authentication | `akaalPipeline/contracts/enums.py`, `akaalPipeline/security/{pki,spiffe,federation/*}.py` | Real, non-stubbed crypto verification confirmed |
| Authorization | `akaalPipeline/security/central_authorization.py` (`CentralAuthorizationEngine`) | Composes RBAC→ABAC→SoD→cache; **canonical**, but see duplicate-risk in §14 |
| Approval/governance | `akaalPipeline/policy/{gates.py, approval_artifact.py}` | Real, tested |
| Sessions | `akaalPipeline/identity/sessions.py` (`SessionManager`) | Real, tested |
| JIT privilege | `akaalPipeline/security/jit.py` (`JITPrivilegeAuthority`) | Real, tested |
| SoD | `akaal/governance/sod/engine.py` (`SeparationOfDutiesEngine`) | Frozen legacy, but actively imported by `central_authorization.py` — a live dependency on "frozen" code |
| Secrets | `akaal/core/credential_vault.py` (in-memory only) + `akaalEngine/connection/security/secret_consumer.py` (ephemeral/wipeable) | Two non-integrated layers, neither is a real external Vault |
| Vault (broader) | Also `akaalPipeline/security/keystore.py`, `akaal/privacy/token_vault.py` | **Three+ competing "vault" concepts**, no single owner — see §14 |
| Key management | `akaalPipeline/security/keystore.py` (`KeyStoreAuthority`) | Real local envelope encryption (Ed25519/AES-GCM/HMAC), Master Root Key from env var — not real KMS/HSM |
| Certificate lifecycle | `akaalPipeline/security/pki.py` + `akaalEngine/connection/security/tls.py` | Real chain/SAN/hostname validation, real `ssl.SSLContext` mTLS construction |
| Tunnels | `akaalEngine/connection/routing/{ssh.py, proxy.py, resolver.py}` | Real SSH tunneling with host-key pinning + HTTP CONNECT/SOCKS proxying |
| Execution planning | **Duplicated**: `akaalPipeline/orchestration/{compiler.py, plans.py}` vs `akaal/planner/engine/plan_compiler.py` | See §14 |
| CDC | `akaal/cdc/*` and `akaalEngine/cdc/*` (parallel trees) | Native CDC confirmed for postgresql/mysql/mariadb/oracle/mssql/mongodb; see §9 |
| Validation | Not deep-audited this pass | Out of time budget |
| Evidence | Not deep-audited this pass | `.akaal/reports/*.json` confirmed synthetic — real evidence must come from raw pytest logs |
| Operations plane | **Duplicated**: `akaal/operations/*` vs `akaalPipeline/{health,fleet,observability,operations}/*` | See §14 |

---

## 6. Campaign A Reconstruction

| Item | Physical file(s) | What it actually does | Proof level |
|---|---|---|---|
| P7.1 Foundation/trust model | `akaalPipeline/security/context.py` (`PipelineActorContext`), `akaalPipeline/contracts/enums.py`, `akaalIPC/security/context.py` | `is_authenticated` requires `AUTHENTICATED` state AND non-NONE assurance; `from_untrusted_claims` downgrades wire-asserted auth to CLAIMED/NONE; fails closed on AUTHENTICATED+assurance=NONE | UNIT_PROVEN (15 tests) |
| P7.2 TLS/mTLS/PKI | `akaalPipeline/security/pki.py`, `akaalEngine/connection/security/tls.py` | Real chain walking with per-key-type signature verification, CA BasicConstraints enforcement, SAN/hostname matching incl. wildcards, CRL lookup, real `ssl.SSLContext` with `CERT_REQUIRED`+`check_hostname=True` and client-cert loading for mTLS. One config-gated `allow_self_signed` escape hatch exists (opt-in, not default) | UNIT_PROVEN (10 tests); no live-CA/live-TLS integration evidence |
| P7.3 SPIFFE/SPIRE | `akaalPipeline/security/spiffe.py` | Real X.509-SVID SAN+trust-domain+signature verification, real JWT-SVID signature/audience/exp/nbf checks, fails closed (raises, does not extend validity) on SPIRE outage | UNIT_PROVEN (9 tests); no live SPIRE server evidence |
| P7.4 Federation | `akaalPipeline/security/federation/{oidc,saml,ldap,manager,models}.py` | SAML uses real `signxml.XMLVerifier` (signxml 5.1.0 confirmed installed), rejects unsigned assertions, XXE-hardened, replay protection; OIDC does real JWK→crypto signature verification, rejects `alg=none`, checks iss/aud/exp/nbf; PKCE correctly not treated as an ID-token claim | UNIT_PROVEN (14 tests); no live IdP evidence |
| Cross-integration | `tests/security/test_p7_campaign_a_cross_integration.py` | Verifies Federation→P7.1→akaalIPC→akaalPipeline→P5 Authorization flow | INTEGRATION_PROVEN (internal wiring only) |

No fake/stub patterns found in any Campaign A file (no hardcoded `authenticated=True`, no default `verify=False`, no silent exception-swallowing turning failure into success).

**LIVE_PROVEN: not established for any Campaign A component** — no live external CA, IdP, or SPIRE server evidence exists in the repo.

---

## 7. Campaign A Freeze Integrity

No concrete defect was found that would justify reopening Campaign A's design. The one process-level issue — **it is not actually committed to git**, so "FROZEN" is not durable — is a documentation/process gap, not a security or correctness defect. Recommend: commit Campaign A as-is (owner decision, not performed here) rather than redesigning anything.

---

## 8. Campaign B Foundation Matrix

### P7.5 — MFA + SCIM + JIT Identity Lifecycle
- EXISTING AUTHORITY: `akaalPipeline/security/jit.py` (time-bound role grants, revision-bound cache invalidation), `akaalPipeline/identity/sessions.py` (absolute+idle timeout, revision-bound sessions)
- CURRENT CAPABILITY: solid JIT grant + durable session primitives
- ALREADY IMPLEMENTED: JIT issue/revoke/validity; session create/validate/authenticate/revoke
- MISSING: MFA (TOTP/WebAuthn) entirely absent server-side; SCIM provisioning/deprovisioning entirely absent server-side (only TS mockups exist in `archive/UI_clone`, not real)
- MUST BE EXTENDED: session/JIT layer to carry MFA assurance level
- MUST NOT BE DUPLICATED: `SessionManager`, `JITPrivilegeAuthority`
- FROZEN DEPENDENCY: none identified
- LIKELY PACKAGE BOUNDARY: `akaalPipeline/security/`, `akaalPipeline/identity/`
- OPEN QUESTIONS: MFA provider choice (TOTP-only vs WebAuthn) is an owner decision

### P7.6 — Zero-Trust Authorization (RBAC+ABAC+JIT+SoD)
- EXISTING AUTHORITY: `akaalPipeline/security/central_authorization.py` (`CentralAuthorizationEngine`) — canonical deny-first pipeline already composing `rbac.py`, `abac.py`, `akaal/governance/sod/engine.py`, and `jit.py`
- CURRENT CAPABILITY: full RBAC→ABAC→SoD→cache pipeline already integration-composed and tested (8 test files)
- ALREADY IMPLEMENTED: the entire structural pipeline
- MISSING: nothing structural for P7.6 scope; likely policy-content expansion only
- MUST NOT BE DUPLICATED: **high risk** — competing classes exist: `akaalPipeline/security/execution_authorization.py` (`ExecutionAuthorizationMinter`, different concern, likely fine), `akaal/resilience_eng/security/authorization.py` (`SecurityAuthorizationEngine`, frozen legacy), `akaal/api/auth/rbac.py` (`RBACEvaluator`, frozen legacy). Any Campaign B work must build exclusively on `central_authorization.py`.
- FROZEN DEPENDENCY: `akaal/governance/sod/engine.py` is frozen legacy but is a live, active import of the canonical authorizer — a real frozen-package dependency, not hypothetical
- LIKELY PACKAGE BOUNDARY: `akaalPipeline/security/`
- OPEN QUESTIONS: should the two legacy `akaal/` authorization classes be explicitly deprecated/removed, or left inert? (owner decision)

### P7.7 — Secrets Management + Vault + Dynamic Credentials + Rotation
- EXISTING AUTHORITY: `akaal/core/credential_vault.py` (`InProcessCredentialVault`, in-memory singleton dict, no persistence/encryption) and `akaalEngine/connection/security/secret_consumer.py` (`SecretConsumer`, ephemeral/wipeable/TTL-bound, used by connection factory)
- CURRENT CAPABILITY: two separate, non-integrated, process-local-only layers; neither talks to a real external Vault
- ALREADY IMPLEMENTED: ephemeral secret resolution with wipe semantics (Engine side)
- MISSING: real external Vault/secrets-manager backend, dynamic/leased credentials, automated rotation
- MUST NOT BE DUPLICATED: **high risk** — `class.*Vault` also hits `akaalPipeline/security/keystore.py` and `akaal/privacy/token_vault.py`. Three-plus "vault" concepts with no single owner. Campaign B should consolidate/clarify ownership before adding a real external Vault integration, not add a fourth concept.
- FROZEN DEPENDENCY: `akaal/core/credential_vault.py`, `akaal/privacy/token_vault.py` (frozen legacy)
- LIKELY PACKAGE BOUNDARY: unclear until ownership is consolidated — owner decision needed
- OPEN QUESTIONS: which of the 3 existing "vault" concepts (if any) becomes canonical before real Vault integration is added?

### P7.8 — KMS + HSM + CMK/BYOK + Key Lifecycle
- EXISTING AUTHORITY: `akaalPipeline/security/keystore.py` (`KeyStoreAuthority`)
- CURRENT CAPABILITY: real local envelope encryption/key lifecycle (generate/rotate/revoke, purpose separation, Ed25519/AES-GCM/HMAC), Master Root Key sourced from an env var
- ALREADY IMPLEMENTED: full local key lifecycle (12 test files)
- MISSING: actual cloud KMS/HSM backend, CMK/BYOK import flow, HSM-backed key custody
- MUST NOT BE DUPLICATED: no competing live keystore found (only an archived TS mockup)
- FROZEN DEPENDENCY: none identified
- LIKELY PACKAGE BOUNDARY: `akaalPipeline/security/keystore.py` (extend, don't replace)
- OPEN QUESTIONS: which cloud KMS/HSM to target first is an owner decision

### P7.9 — Secure Tunnels + Private Connectivity
- EXISTING AUTHORITY: `akaalEngine/connection/routing/{ssh.py, proxy.py, resolver.py}`
- CURRENT CAPABILITY: genuine, tested SSH tunneling with host-key pinning and HTTP CONNECT/SOCKS proxy routing
- ALREADY IMPLEMENTED: tunnel/proxy transport
- MISSING: broader "private connectivity" (PrivateLink/VPC peering-style constructs), if that is in scope
- MUST NOT BE DUPLICATED: none found
- FROZEN DEPENDENCY: none identified
- LIKELY PACKAGE BOUNDARY: `akaalEngine/connection/routing/`
- OPEN QUESTIONS: is PrivateLink/VPC-peering actually in P7.9 scope, or is SSH/proxy tunneling sufficient? (owner decision)

---

## 9. Connector / Capability Truth

**Verified registry** (`akaal/connectors/registry.py` + `bridge.py`), 30 registered identities:
- Relational (7): oracle, postgresql, mysql, mariadb, mssql, ibm_db2, sqlite
- Warehouse/Lakehouse (4): snowflake, bigquery, redshift, databricks
- Distributed FS (1): hdfs
- NoSQL/Specialized (8): mongodb, cassandra, scylladb, neo4j, redis, keydb, elasticsearch, opensearch
- Object Storage (4): s3, gcs, azure_blob, minio
- Streaming (6): kafka, confluent [MANAGED_PROFILE], msk [MANAGED_PROFILE], kinesis, event_hubs, pubsub

Deviations from supplied context: `hdfs`/`confluent`/`msk` are real but uncounted in the supplied "28+2" list; `aws_rds`/`azure_sql` are not registered connector identities (only an enum + test fixtures for cloud variants of postgresql/mysql/mssql).

**CDC classification (code-verified):**

| Provider | Classification |
|---|---|
| postgresql, mysql, mariadb, oracle, mssql, mongodb | NATIVE_CDC (confirmed dedicated capture source modules) |
| scylladb | Declared `can_cdc=True` but **no dedicated capture-source module found** — capability flag only, likely aspirational |
| cassandra | PARTIAL / NO_CDC (declared PARTIAL, not implemented) |
| redis | STREAM_CONSUMPTION (Streams/keyspace notifications declared; no dedicated capture-source module found — depth UNKNOWN) |
| kafka, kinesis, event_hubs, pubsub | STREAM_CONSUMPTION, but **mislabeled as `CDC_LOG` role in both code (`can_cdc=True`, `EndpointRole.CDC_LOG`) and `ENGINE_TRUTH_LEDGER.md`** | 

This is a real, code-confirmed mislabeling: streaming message systems have no underlying database to capture changes from — they only support offset/shard-based consumption — yet are tagged with the same `CDC_LOG` role as genuine database CDC sources.

---

## 10. Current Test State

Real pytest run logs (plain text at repo root; the `.akaal/reports/*.json` files are NOT real evidence — see §15):
- `full_regression_output.txt` (Aug 28, most recent full run): **3923 passed, 190 failed, 13 skipped, 13 errors, 3 warnings** (554.32s)
- `full_no_stop_output.txt` (Aug 28, earlier/partial): 3882 passed, 169 failed, 13 skipped, 13 errors
- `security_test_output.txt` (Aug 28, security suite only): **99 passed, 0 failed** (20.99s)
- Campaign A security tests, independently re-run this pass: **56 passed, 0 failed**

Failure clusters: `tests/unit/test_partition_migration.py`, `test_manifest_driven_execution.py`, `test_p010_rectification*.py`, `test_connection_dto_verification.py`, `test_transform_compilation.py`, `tests/unit/validation/test_physical_validation.py`, `tests/validation/test_production_validation_suite.py`. All 13 ERRORs are in `tests/integration/test_phase9_real_engine_certification.py` — live Postgres/MySQL/Oracle tests, consistent with no live DB daemons running (i.e., these should likely be EXTERNAL_DEFERRED, not ERROR, if the skip-gate isn't catching them — worth owner attention).

No `pytest.mark` custom markers exist for live/integration gating — gating is done via runtime `unittest.SkipTest("EXTERNAL_DEFERRED: ...")` calls in `tests/conftest.py`'s `require_postgres/mysql/oracle/mssql/mongodb()` functions, which check TCP reachability.

"618/618 CDC tests green" and "56 executed" (as a whole-repo claim, vs. the actual Campaign-A-only scope) do not appear in any real run log outside the Campaign A subset.

---

## 11. External Certification Debt

- 216 (external/live certification obligations) is corroborated by two ledger files, but a third ledger in the same `reports/` directory states 236 — **an unresolved internal contradiction**, not yet reconciled.
- 217 and ~148 (from supplied context) are **UNVERIFIABLE** — do not appear anywhere in repo artifacts.
- The 13 ERRORs in `test_phase9_real_engine_certification.py` (real DB integration tests) represent live infrastructure that is currently unavailable locally — correctly EXTERNAL_DEFERRED in spirit, though currently surfacing as ERROR rather than SKIP in the last run, which should be reconciled.
- Nothing found in this pass should be classified LIVE_PROVEN for any Campaign A or Campaign B-adjacent capability.

---

## 12. Dependency / Environment Reproducibility

No `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `Pipfile`, `setup.py`, or `setup.cfg` exists anywhere in the repository. A local `.venv/` (created Aug 28, gitignored) has `signxml==5.1.0` installed and is what Campaign A's SAML validation actually runs against — but there is no committed manifest that would let anyone else reproduce this environment. This is real, current `CURRENT_ENGINEERING_REPRODUCIBILITY_DEBT` / `LOCAL_ENVIRONMENT_ONLY` risk, not fixed in this pass per instructions.

---

## 13. Current Working-Tree Forensics

**Modified/untracked, categorized:**
- `.akaal/reports/*.json` — 43 files, all modified, trivial diffs. Confirmed synthetic (§15) — safe to treat as low-risk regenerated artifacts, but not as evidence.
- `akaal/` legacy package — 10 modified files. Judgment per file:
  - `state_store.py`, `engine_gateway.py` — genuine small, isolated fixes
  - `quarantine.py` — **regression**: removes a sanitization call before persisting quarantine records (security-relevant)
  - `deduplication.py` — **regression**: silently drops the duplicate-disposition return value (replaced with `[]`)
  - `canonical_reporting.py` — weakens typing (hard import → `Any`), plausibly avoids an import-cycle, but reduces type safety
  - `service_impl.py` — **feature-bleed**: new `TransactionAnalyzer` code path (~40 new lines)
  - `transformer.py`, `transformation/engine.py`, `expression_compiler.py`, `transformation/models.py` — **coordinated feature-bleed**: new conditional-rule system + infix expression parser/evaluator (~90+ new lines), clearly new feature work inside a package described as frozen
- `akaalPipeline/` — modified: `contracts/enums.py`, `security/config.py`, `security/context.py`. Untracked (never committed): `security/pki.py`, `security/spiffe.py`, entire `security/federation/` directory (6 files)
- `akaalIPC/` — modified: `security/context.py` only
- `akaalEngine/` — modified: `cdc/api.py`, `data_processing/dedup/deduplicator.py` (both previously classified "unrelated regression fix" by prior handoff — not independently re-verified line-by-line this pass, flagged for owner attention given the akaal/ pattern above)
- `akaalSoftware/` — 0 currently modified (already committed in `da16ec2`)
- Other untracked: `.reticle/.gitignore` (tooling, unrelated), `scratch/audit_production_security.py` + 2 more scratch files, `tests/conftest.py`, all 5 Campaign A security test files, plus ~40 modified test files across benchmark/cdc/integration/recovery/reporting/unit/validation (likely API-signature ripple from the akaal/akaalEngine changes above)

**Commit history sanity check:** `git log` shows recent commits are (a) unrelated Angular frontend work, (b) a large commit with a placeholder message "Your commit message here" that did commit substantial `akaalPipeline`/`akaalEngine`/`akaalIPC` operations/execution/health/fleet work plus some P6-campaign test scaffolding, and (c) a narrow blocker-closure fix. **None of these commits contain the actual Campaign A security primitives** (PKI/SPIFFE/federation) — that code exists only, and entirely, in the uncommitted working tree.

No files were modified, staged, committed, or discarded during this reconnaissance.

---

## 14. Duplicate-Authority Risk Register

Highest-risk places a future agent could accidentally build a second authority:

1. **ExecutionPlan / PlanCompiler** — `akaal.planner.engine.plan_compiler` + `akaal.planner.models.p5_domain.ExecutionPlan` vs `akaalPipeline.orchestration.compiler.GraphCompiler` + `akaalPipeline.orchestration.plans.ExecutionPlan`. Structurally distinct classes, same name, same conceptual role. **Real, current duplication**, not hypothetical.
2. **Execution mode enum** — `akaal.planner.models.p5_domain.ExecutionMode` vs `akaalPipeline.contracts.enums.MigrationMode`. Same M1–M8 semantics, different member names.
3. **Operations plane** — `akaal/operations/*` (alerts, health, incidents, scheduler, diagnostics, governance, monitoring, forecasting, topology, digital_twin) vs `akaalPipeline/{health,fleet,observability,operations}/*` re-implementing largely the same concerns.
4. **Secrets/Vault** — `akaal/core/credential_vault.py`, `akaal/privacy/token_vault.py`, `akaalPipeline/security/keystore.py`, `akaalEngine/connection/security/secret_consumer.py`. Three-plus competing "vault" concepts, no declared single owner.
5. **Authorization/RBAC** — canonical `akaalPipeline/security/central_authorization.py` (with `rbac.py`/`abac.py`) vs frozen-but-still-present `akaal/resilience_eng/security/authorization.py` and `akaal/api/auth/rbac.py`. Lower risk since the legacy copies are inert, but a future agent grepping for "RBAC" could easily latch onto the wrong one.
6. **CDC source trees** — `akaal/cdc/*` vs `akaalEngine/cdc/*` exist in parallel; not fully reconciled in this pass.

---

## 15. Security / Fail-Closed Risk Register

Concrete, verified risks (not speculative style complaints):

1. **Fabricated test evidence**: `.akaal/reports/*.json` (43 files) present hand-shaped `"outcome": "CERTIFIED"` JSON disconnected from any real pytest execution, while the actual last full run shows 190 failures and 13 errors. This is exactly the pattern the Zero-Fake Law prohibits ("placeholder success," "static success shortcuts") — even if these files were not written by an LLM agent, they are currently sitting in the repo functioning as false certification evidence and should not be relied upon or extended by any future agent.
2. **Unsanitized quarantine persistence**: `akaal/cdc/multi_master/quarantine.py`'s working-tree change removes a call to `LogAndDiagnosticSanitizer.sanitize_quarantine_record()` before persisting quarantine records — quarantine records (which likely contain conflict/PII-adjacent data) are now persisted unsanitized. This is a live, uncommitted regression in the current working tree.
3. **Silent data loss in deduplication**: `akaal/migration/execution/deduplication.py`'s working-tree change drops the duplicate-disposition return value (`disp_records` → `[]`) from `filter_batch_duplicates`/`run_full_dedup`, silently discarding disposition tracking that downstream code may depend on.
4. **Two contradicting "authoritative" external-deferred ledgers** (216 vs 236) sitting in the same `reports/` directory — a governance/evidence integrity gap, not just a documentation nit.
5. **CDC role mislabeling**: kafka/kinesis/event_hubs/pubsub are tagged `EndpointRole.CDC_LOG`/`can_cdc=True` in both code and `ENGINE_TRUTH_LEDGER.md`, conflating stream consumption with database change capture — a truthfulness-in-capability-claims issue directly relevant to the Zero-Fake Law's "never fake capability support" principle.
6. **13 ERRORs (not SKIPs) in live-DB integration tests**: `test_phase9_real_engine_certification.py` errors rather than cleanly skips when live Postgres/MySQL/Oracle are unavailable — suggests the EXTERNAL_DEFERRED skip-gate isn't uniformly applied, so a real failure could currently hide behind an expected-looking ERROR count.
7. **Zero dependency manifests**: the entire repo has no `pyproject.toml`/`requirements.txt`/lockfile; the environment (including the exact `signxml==5.1.0` that Campaign A's SAML security depends on) exists only in an untracked local `.venv`. A clean checkout cannot currently reproduce the security-relevant dependency set at all.

No evidence found of: fake authentication, `verify=False`, inappropriate `CERT_NONE` defaults, hardcoded production credentials, or allow-all authorization in the Campaign A code itself — that code is genuinely fail-closed where inspected.

---

## 16. Campaign B Preconditions

**READY_WITH_DECLARED_DEPENDENCIES.**

Reasoning: the security/identity/authorization/keystore/tunnel foundations relevant to P7.5, P7.6, and P7.9 are real, tested, and sufficient to extend without duplication, provided the risks in §14 items 4–5 (vault ownership, legacy RBAC files) are explicitly acknowledged before starting. P7.7 and P7.8 are ready to extend technically, but need an explicit owner decision on vault/KMS consolidation (§8) before writing new code, or a fourth competing vault concept will be created. Additionally, the uncommitted state of Campaign A (§2, §13) and the two live regressions in `akaal/` (§15 items 2–3) should be resolved or explicitly accepted before Campaign B work begins, since Campaign B will likely touch adjacent code paths.

---

## 17. Proposed Campaign B Write Boundary

Recommendation only — does not grant write authority:
- `akaalPipeline/security/` (extend: jit.py, keystore.py, central_authorization.py's composed rbac/abac policy content)
- `akaalPipeline/identity/` (extend: sessions.py for MFA assurance)
- `akaalEngine/connection/security/` and `akaalEngine/connection/routing/` (extend: secret_consumer.py, ssh.py/proxy.py)
- Explicitly **exclude** `akaal/` from the Campaign B write boundary given the regressions found in §15, unless a separate, narrowly-scoped authorization is given to fix those two specific regressions.
- A new, explicitly-designated module for real external Vault/KMS integration should not be created until the vault-consolidation question in §8 (P7.7) is answered by the owner.

---

## 18. Questions / Contradictions Requiring Owner Decision

1. Which of the three-plus existing "vault" concepts (`InProcessCredentialVault`, `token_vault.py`, `SecretConsumer`, `KeyStoreAuthority`) should become the single canonical secrets authority before P7.7 work begins?
2. Should the two legacy `akaal/` authorization classes (`SecurityAuthorizationEngine`, `RBACEvaluator`) be explicitly deprecated/deleted, or intentionally left inert as dead code?
3. Should Campaign A be committed to git now (to make "FROZEN" durable) before Campaign B begins, and if so, under whose authorization?
4. Are the two `akaal/` regressions found in §15 (unsanitized quarantine persistence, dropped dedup disposition records) already known/intentional, or should they be flagged as bugs to fix under a narrowly-scoped exception to the "akaal/ read-only" rule?
5. Which of the two conflicting external-deferred ledger totals (216 vs 236) is authoritative, and should the other be deleted/reconciled?
6. Is the conditional-rule/expression-parser feature work found inside `akaal/transformation/*` an intentional, authorized exception to the "akaal/ is frozen" rule, or unauthorized scope creep that should be reverted or relocated?
7. Does P7.9 "private connectivity" need PrivateLink/VPC-peering-style constructs, or is the existing SSH/proxy tunneling sufficient scope?

---

## 19. Final Declaration

PRODUCTION FILES MODIFIED BY THIS ONBOARDING TASK: 0

TEST FILES MODIFIED: 0

GIT WRITE OPERATIONS PERFORMED: 0

CAMPAIGN B IMPLEMENTATION PERFORMED: NO

CAMPAIGN A REOPENED: NO

KNOWN LOCAL BLOCKERS BEFORE CAMPAIGN B: 7 (see §18 owner-decision list; also the 190 failing / 13 erroring tests in the last full regression run, and the 2 live regressions in `akaal/` from §15)

UNRESOLVED AUTHORITY COLLISIONS: 6 (see §14: ExecutionPlan/PlanCompiler, execution-mode enum, operations plane, secrets/vault, authorization/RBAC, CDC source trees)

RECOMMENDED NEXT ACTION: Resolve the owner-decision list in §18 (especially vault consolidation and the akaal/ regression disposition) before any Campaign B write authorization is granted; separately, get Campaign A actually committed to git so "FROZEN" is durable rather than working-tree-only.
