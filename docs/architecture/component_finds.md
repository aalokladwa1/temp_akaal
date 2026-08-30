# 1. Step-1 Executive Truth

AKAAL has no single authoritative Migration Definition component.

The strongest durable foundation is P5.1’s SQLite-backed `MigrationProject` / `MigrationPlan` / `PlanVersion` / `ExecutionPlan` set in [p5_domain.py](A:/temp_akaal/akaal/planner/models/p5_domain.py:442) and [project_store.py](A:/temp_akaal/akaal/planner/persistence/project_store.py:57). It is not sufficient as-is: it conflates project and migration identity, requires source/target references at project creation, has only `SIMPLE`/`ADVANCED`, and stores a free-form `migration_strategy`.

The shipping UI does collect some Step-1 metadata, but it sends it only as nested manifest metadata late in a seven-step wizard. There is no canonical M1–M8 field, migration-window model, template provenance, clone implementation, or durable project reassignment.

# 2. Whole-Repository Coverage Map

Semantic sweep covered:

- Current UI, Tauri registration, TypeScript repositories/services.
- Gateway, CentralStateStore, P5 models/store/compiler.
- `core`, `migration`, `planner`, `workflow`, `orchestration`, `cdc`, `replication`, `validation`, `schema`, `connectors`, `agents`.
- Legacy ManagerAgent/project/session/checkpoint paths.
- Archived UI/NexusForge-style material.
- Unit/integration/CDC/P5 tests and persisted-state artifacts.
- Templates, clone/replay/rerun, scheduling/window, strategy/mode representations.

# 3. Current Step-1 Physical UI Structure

The shipping Step-1 UI is [NewMigrationWizard.tsx](A:/temp_akaal/akaal_software/src/screens/MigrationModule/NewMigrationWizard.tsx:330), “Overview” in the current seven-step wizard.

It has local React state for:

- `migName`, `description`
- `migScope`
- `strategy`
- `projectName`
- `environment`
- `priority`
- `businessOwner`

It shows a disabled hardcoded Migration Window. It has no real planning-mode selector, template chooser, clone chooser, workspace/project ID picker, or M1–M8 selector.

# 4. Current 7-Step Wizard → New Step-1 Mapping

| Current UI control | New Step-1 destination | Truth |
|---|---|---|
| Migration name | Identity | Local until late manifest creation |
| Description | Identity/description | Sent under `operator_metadata` |
| Project name | Optional project/workspace | Free-text field, not a durable project relation |
| Owner | Owner | Free text |
| Environment | Environment | UI enum-like string |
| Priority | Priority | UI enum-like string |
| Migration scope | Not Step 1 | Actually Step 4 scope intent |
| Execution strategy | Execution mode candidate | Free-text strategy, not M1–M8 |
| Disabled migration window | Migration-window intent | Static display only |

# 5. Candidate Inventory

| Candidate | What it owns now | Classification |
|---|---|---|
| [P5 `MigrationProject`](A:/temp_akaal/akaal/planner/models/p5_domain.py:534) | Project-level metadata, source/target references, free-form strategy | `KEEP_CANDIDATE`, `RENOVATE`, `MERGE` |
| [P5 `MigrationPlan`](A:/temp_akaal/akaal/planner/models/p5_domain.py:506) | Draft topology/routing/scope/configuration | `KEEP_CANDIDATE`; remains Step 7-adjacent, not Step 1 authority |
| [P5 `PlanVersion`](A:/temp_akaal/akaal/planner/models/p5_domain.py:442) | Version/fingerprint/approval fields | `KEEP_CANDIDATE`, `REWIRE` |
| [P5 `ProjectStore`](A:/temp_akaal/akaal/planner/persistence/project_store.py:34) | SQLite persistence under `artifacts/state.db` | `KEEP_CANDIDATE`, `RECTIFY` |
| [EngineGateway `create_migration`](A:/temp_akaal/akaal/gateway/engine_gateway.py:588) | Late manifest registration, credential handling | `EXTRACT`, `REWIRE`; not canonical definition authority |
| [EngineGateway `create_project`](A:/temp_akaal/akaal/gateway/engine_gateway.py:575) | Minimal project state | `DUPLICATE_AUTHORITY`, `RETIRE` |
| [EngineGateway `move_migration_to_project`](A:/temp_akaal/akaal/gateway/engine_gateway.py:2467) | Returns “reparented” response only | `FAKE_SUCCESS`, `KILL` |
| [CentralStateStore](A:/temp_akaal/akaal/core/state/state_store.py:62) | Generic persisted migration/runtime blobs | `COMPATIBILITY_BRIDGE`; not Step-1 authority |
| [Legacy `MigrationStrategy`](A:/temp_akaal/akaal/core/models/enums.py:166) | `BIG_BANG`, `PHASED`, `INCREMENTAL`, `CDC_BASED`, etc. | `EXTRACT`, `REPLACE` |
| ManagerAgent project/session world | Project-driven legacy runtime orchestration | `LEGACY_ONLY`, `EXTRACT` ID lessons only |
| [Frontend projectRepository](A:/temp_akaal/akaal_software/src/repositories/projectRepository.ts:1) | In-memory project cards/drafts | `DUPLICATE_AUTHORITY`, `RETIRE` |
| Archived migration/template UI | Visual ideas only; mock records/templates | `STATIC_DISPLAY`, `LEGACY_ONLY` |
| P5 mapping templates | Mapping-only template feature | `EARLY_FUTURE_IMPLEMENTATION`; remains Step 5 |

# 6. Repository Lineage / World Map

- **Current AKAAL shipping world:** wizard → Rust capability registry → EngineGateway → CentralStateStore/runtime.
- **P5 planning world:** `MigrationProject` → `MigrationPlan` → `PlanVersion` → `ExecutionPlan` in SQLite.
- **Legacy/NexusForge-like world:** ManagerAgent, project-based state machines, checkpoints, migration sessions.
- **CDC world:** durable CDC identities and runtime session models; useful downstream consumers, not Step-1 ownership.
- **Archive UI world:** mock migration/template/clone presentation, no implementation proof.

# 7. Migration Definition Authority Map

There are competing authorities:

1. **Wizard React state** — operator input before launch; process-memory only.
2. **Frontend project repository** — in-memory UI projects/drafts.
3. **Gateway `_migrations` map** — process-memory migration record.
4. **CentralStateStore `migration` category** — persisted raw manifest.
5. **P5 `projects` table** — persisted project metadata.
6. **P5 plans/versions tables** — persisted planning artifacts.
7. **Legacy ManagerAgent project model** — project-driven runtime identity.

No one representation consistently owns all Step-1 fields.

# 8. Migration Identity Audit

- Gateway creates IDs as `mig-<uuid prefix>` in [create_migration](A:/temp_akaal/akaal/gateway/engine_gateway.py:592). This is independent from project ID at creation.
- P5’s principal entity is `MigrationProject(project_id=...)`, not a separate migration-definition ID.
- Gateway P5 plan generation defaults missing migration IDs to `"mig-default"` and project IDs to `"proj-default"` in [engine_gateway.py](A:/temp_akaal/akaal/gateway/engine_gateway.py:1481). This is a collision and correctness risk.
- Runtime/checkpoints often namespace by `(project_id, migration_id)`, exposing historical project/migration coupling.
- Clone UI exists as a confirmation choice, but no clone operation was found. Therefore clone isolation is **NOT IMPLEMENTED**.
- Execution/run identity is separate only inconsistently: operation IDs, CDC run/session IDs, and workflow IDs exist, but Step 1 does not establish a canonical relationship.

Verdict: a durable migration identity exists in some paths, but no canonical, cross-store migration-definition identity exists.

# 9. Project / Workspace Audit

- P5 `projects.workspace` is nullable at schema level but modeled as a string and populated with a default.
- P5 project creation requires source and target references, which violates “definition may exist before source/target.”
- Gateway `create_project` persists only `{project_id, project_name, status, created_at}` in CentralStateStore.
- `move_migration_to_project` does not update any store, history, plan, or inheritance; it merely returns success.
- P5 foreign keys use `ON DELETE CASCADE`; deleting a project can delete plans, versions, and execution plans. This is unacceptable if project membership is organizational rather than migration identity.
- No assignment history, effective-default provenance, move authorization, replan/reapproval behavior, or workspace entity authority was proven.

Project/workspace is not correctly modeled as optional membership today.

# 10. Owner / Environment / Business Context / Priority Audit

| Field | Current form | Durability | Validation/consumer |
|---|---|---|---|
| Owner | `businessOwner` string | P5 owner string / manifest metadata | No identity-reference validation; used as PlanVersion creator |
| Environment | UI string, defaults Production | P5/free-form manifest | No environment entity/default provenance |
| Priority | UI label (`P0 - Critical`) | P5/free-form manifest | No canonical enum or scheduler contract |
| Business context | Description plus owner/project labels | Metadata only | No structured business context model |

All are strings, not durable references. No current entity registry validates owner or environment. These are useful fields but require canonical typing and provenance.

# 11. Planning Mode Audit

P5 defines only `SIMPLE` and `ADVANCED` in [p5_domain.py](A:/temp_akaal/akaal/planner/models/p5_domain.py:19). The required product values are Standard and Advanced.

- UI Step 1 exposes no planning mode.
- Gateway hardcodes `PlanningMode.SIMPLE` while generating a plan.
- Planning mode is persisted in `plans` and `plan_versions`.
- It does not currently represent a user-controlled canonical planning intent.

Classification: `PARTIAL_CONTROL`, `SILENT_DEFAULT`.

# 12. M1–M8 Execution Mode Representation Audit

| Existing representation | Semantic overlap | Canonical conversion |
|---|---|---|
| Wizard `migScope`: Full / CDC-only / DDL-only | M1/M3/M6-like labels | Lossy and incorrectly mixes scope/mode |
| Wizard `strategy`: Zero-Downtime / Scheduled Batch | Operational style | Not an M1–M8 mode |
| `enable_cdc: bool` | CDC participation | Ambiguous: cannot distinguish M2 from M3 |
| P5 `migration_strategy: str` | General strategy | Free-form, not safely lossless |
| Legacy `MigrationStrategy.CDC_BASED` | M2/M3-like | Ambiguous |
| Legacy `INCREMENTAL` | M4-like | Potentially mappable but requires semantics confirmation |
| `DRY_RUN`, `SIMULATION` | Non-production behavior | Not M8 |
| `validation_level` | Validation depth | Not M8 |
| Schema/data conversion actions | M6/M7-like execution stages | Downstream action, not authoritative intent |
| CDC/reconciliation implementations | M3/M5/M8 material | Runtime capability only |

Actual representability today:

- M1: partial/inferred.
- M2: partial/inferred through bulk + `enable_cdc`.
- M3: UI label only; backend cannot safely distinguish it from M2.
- M4: legacy strategy naming only.
- M5: no Step-1 representation.
- M6: UI label only.
- M7: no Step-1 representation.
- M8: no Step-1 representation.

Unknown historical values generally do **not** fail closed; defaults and free-form strings are used. This is a critical accuracy defect.

# 13. Migration Window / Time Semantics Audit

The wizard has a disabled static field at [NewMigrationWizard.tsx](A:/temp_akaal/akaal_software/src/screens/MigrationModule/NewMigrationWizard.tsx:1495). No persistence field, DTO, time-zone model, DST rule, allowed-start rule, blackout rule, deadline, recurrence, or validation was found for Step 1.

The advisor has maintenance-window analysis material, but that is not a migration-definition window authority.

Verdict: `STATIC_DISPLAY`; no real migration-window intent exists.

# 14. Template Audit

- P5 has [MappingTemplate](A:/temp_akaal/akaal/planner/models/p5_domain.py:199), which is mapping-specific and belongs to Step 5.
- UI supports mapping-template import/export, also Step 5.
- Archive migration templates are hardcoded mock data.
- YAML variable-template resolution is configuration parsing, not a migration template.
- No durable migration-template entity, version pinning, template application record, override ledger, or immutable template-origin reference was found.

Migration templates are `FUTURE_NOT_YET_REQUIRED` under the lifecycle roadmap, but Step 1 needs a compatible optional reference once that authority exists.

# 15. Clone / Rerun / Retry / Replay Distinction Audit

- “Clone Migration” appears in [MissionControlView.tsx](A:/temp_akaal/akaal_software/src/screens/MigrationModule/MissionControlView.tsx:713), but no backend clone behavior was found.
- Replay controls are UI interaction labels, not Step-1 cloning.
- Retry/recovery/checkpoint mechanisms are runtime concerns and must not copy Step-1 identity.
- No clone provenance, source definition/version pointer, isolated credentials, approval exclusion, checkpoint exclusion, schedule exclusion, CDC-session exclusion, or clone ID generation is implemented.

Clone is `NOT IMPLEMENTED`; attempting to treat current UI as functional would be `FAKE_SUCCESS`.

# 16. Persistence / Restart Reconstruction Audit

| Store | What survives restart | Step-1 suitability |
|---|---|---|
| React state | Nothing | No |
| Frontend `projectRepository` | In-memory only | No |
| Gateway `_migrations` / `_projects` | Nothing | No |
| CentralStateStore SQLite | Raw migration manifest/progress/status | Compatibility bridge, not normalized authority |
| P5 `artifacts/state.db` ProjectStore | Projects, plans, versions, execution plans | Strongest base, but project-centric |
| Legacy state/runtime stores | Project/session/checkpoint state | Runtime compatibility only |

P5 restart reconstruction works for its own objects. Shipping migration reconstruction works only if the CentralStateStore manifest is present and compatible. The two are not reconciled.

# 17. Mutability / Versioning / Fingerprint Audit

Strengths:

- P5 `PlanVersion` snapshots canonical payload and stores a fingerprint.
- P5 `ExecutionPlan` is marked immutable.

Defects:

- Step-1 data is mutable through P5 `save_project` upsert with no dedicated history.
- P5 PlanVersion is project-scoped, not migration-definition scoped.
- Gateway compiles the current mutable plan while accepting a requested version ID, so historical-version fidelity is not proven.
- Gateway runtime can merge caller payload changes into persisted migration configuration before execution.
- No field-level invalidation rule exists for definition changes.
- No approved-plan, exact-definition, and schedule coupling exists.

Required future distinctions:

- Immutable: `migration_id`, creation provenance.
- Mutable drafts: descriptive metadata, owner/project assignment where policy permits.
- Version/fingerprint-relevant: execution mode, planning mode, environment, effective inheritance, window constraints, template/clone provenance.
- Non-plan-impacting only where proven: cosmetic rename/description; even then retain audit history.

# 18. UI → IPC → Gateway → Model → Store Trace

Current real path:

```text
NewMigrationWizard local state
  → canonicalManifest
  → invokeEngineCapability("create_migration")
  → Rust capability registry: registered
  → EngineGateway.create_migration
  → gateway _migrations + runtime registry
  → CentralStateStore category "migration"

Separately:
wizard payload
  → invokeEngineCapability("generate_plan")
  → EngineGateway P5 creation
  → MigrationProject / MigrationPlan / PlanVersion / ExecutionPlan
  → ProjectStore SQLite artifacts/state.db
```

Field trace:

| UI field | Actual destination | Result |
|---|---|---|
| Name | `migration_name` | Stored in manifest; P5 title may separately derive it |
| Description | `operator_metadata.description` | P5 reads top-level `description`, so it is dropped from P5 metadata |
| Owner | `operator_metadata.business_owner` | P5 reads top-level `business_owner`; drift/drop risk |
| Environment | `operator_metadata.environment` | Same drift |
| Priority | `operator_metadata.priority` | Same drift |
| Strategy | `operator_metadata.execution_strategy` | P5 reads top-level `execution_strategy`; drift/drop risk |
| Project name | UI free text | Not a real project relation |
| Scope | `selected_scope` | Step 4 ownership; persisted in manifest/P5 plan |
| Migration window | none | Dropped |
| Planning mode | none | Gateway silently uses SIMPLE |
| M1–M8 | none | Not represented |

# 19. A–Z Feature Harvest Ledger

| Useful capability | Source | Preserve |
|---|---|---|
| UUID-like migration IDs | Gateway | Preserve with stronger ID contract |
| SQLite WAL durable store | ProjectStore | Preserve with rectification |
| Draft/plan/version/execution-plan separation | P5 | Preserve, keeping plan artifacts downstream |
| Canonical serialization/fingerprint | P5 | Preserve with corrected inputs/version loading |
| Created/updated timestamps | P5 | Preserve |
| Credential references and plaintext stripping | Gateway | Preserve outside Step 1 |
| Explicit target identifier validation | Gateway | Preserve in Step 3 |
| Runtime history/checkpoint identity lessons | Legacy/CDC | Preserve as compatibility constraints |
| Migration metadata visual controls | Current wizard | Preserve UI patterns only |
| Mapping template behavior | P5/UI | Preserve in Step 5 only |
| Archive template/clone UI | Archive | Do not preserve as implementation |

# 20. Duplicate Authority Map

| Responsibility | Competing authorities | Disposition |
|---|---|---|
| Migration identity | Gateway `mig-*`, P5 `project_id`, legacy project/session ID | Create one canonical migration ID; bridge old IDs |
| Definition metadata | Wizard, manifest, P5 project | Merge into one authority |
| Project/workspace | Gateway minimal project, P5 `projects`, UI repository | Keep a future administration authority referenced by Step 1 |
| Planning mode | P5 enum, gateway hardcoded SIMPLE | Keep P5 type but normalize to STANDARD/ADVANCED |
| Execution mode | UI labels, boolean CDC, free-form strategy, legacy enum | Replace with M1–M8 canonical enum |
| Persistence | CentralStateStore, ProjectStore, frontend memory | ProjectStore-like durable authority; bridge CentralStateStore |
| Move | registered IPC no-op | Kill and rebuild later |
| Templates/clones | archive mock/UI labels/P5 mapping templates | Keep only mapping templates in Step 5 |

# 21. Performance Impact Findings

1. **Yes:** weak mode intent can run irrelevant bulk, CDC, schema, or validation stages.
2. **Yes:** `enable_cdc` makes M2/M3 ambiguous.
3. **Yes:** project/migration identity divergence and defaults cause avoidable recompilation and cache misses.
4. **Yes:** reassignment has no invalidation logic.
5. **Yes:** definition-related state is duplicated across stores.
6. P5 does indexed primary-key lookups; no critical O(N) Step-1 lookup was proven.
7. JSON manifest/config blobs are repeatedly copied and rewritten.
8. Identity/provenance can be separated from mutable presentation metadata.
9. Deterministic definition fingerprints would enable safe plan eligibility/cache keys.
10. A canonical execution mode lets discovery/planning avoid irrelevant expensive work.

# 22. Accuracy / Correctness Impact Findings

- Two migrations can collide on `"mig-default"` / `"proj-default"` fallback paths.
- Project reassignment cannot change identity today because it does not actually persist; this is not safe movement.
- Checkpoint namespaces can involve project and migration IDs, making an identity migration dangerous without bridging.
- UI and persisted strategy/mode can drift because nested metadata is not consistently consumed.
- M8 has no canonical identity; mutation prevention cannot be guaranteed from Step 1.
- M6/M7 safeguards are not represented as first-class intent.
- M2 and M3 are indistinguishable to the current backend contract.
- Clone isolation is absent.
- Template mutation safety is unproven because migration templates do not exist.
- Exact restart reconstruction is unproven across the competing stores.
- Historical plan versions can refer to mutable current plan content.
- Environment/project defaults have no recorded provenance.

# 23. Failure / Fail-Closed Matrix

| Scenario | Current classification |
|---|---|
| Missing name | `SILENT_DEFAULT` |
| Duplicate name | `NOT_IMPLEMENTED` |
| Duplicate migration ID | `FAIL_OPEN` / overwrite-risk across maps |
| Missing/invalid owner | `SILENT_DEFAULT` |
| Missing/invalid environment | `SILENT_DEFAULT` |
| Unknown planning mode | `SILENT_DEFAULT` |
| Unknown execution mode | `NOT_IMPLEMENTED` |
| Legacy unknown strategy | `FAIL_OPEN` |
| `enable_cdc=true` with no M2/M3 | `SILENT_DEFAULT` |
| M8 represented as normal migration | `NOT_IMPLEMENTED` |
| Migration move | `FAKE_SUCCESS` |
| Project deletion | `FAIL_OPEN` for historical preservation due to cascade |
| Clone state reuse | `NOT_IMPLEMENTED` |
| Template later edited | `UNRESOLVED` |
| Timezone/window change | `NOT_IMPLEMENTED` |
| Mutation after plan/approval/schedule | `FAIL_OPEN` / `UNRESOLVED` |
| UI closes before persistence | `UNRESOLVED` |
| Backend restart | `PARTIAL`; store-dependent |
| Competing-store conflict | `UNRESOLVED` |
| M1 → M8 or M8 → M1 | `NOT_IMPLEMENTED` |
| Old record without mode | `SILENT_DEFAULT` |

# 24. Security / Secret / Sensitive Metadata Findings

- `create_migration` stores credentials in the vault and removes recognized plaintext password keys before persistence. This is useful reusable material.
- Step 1 must reference source/target configurations, not own credentials or endpoints.
- Owner/environment are unvalidated strings and cannot support robust access control/audit.
- `business_context` may contain ticket/system data and should be access-controlled/audited.
- Template/clone provenance must not disclose credential references or inherit secret material.

# 25. Current Gap vs Future Gap

| Gap | Classification |
|---|---|
| Single Migration Definition authority | `BUILD_REQUIRED` |
| Canonical migration ID independent of project | `REQUIRED_BY_CURRENT_BOUNDARY` |
| Explicit M1–M8 mode | `REQUIRED_BY_CURRENT_BOUNDARY` |
| Fail-closed unknown modes | `REQUIRED_BY_CURRENT_BOUNDARY` |
| Optional project/workspace membership + durable move history | `REQUIRED_BY_CURRENT_BOUNDARY` |
| Real planning mode operator intent | `REQUIRED_BY_CURRENT_BOUNDARY` |
| Real migration-window intent | `REQUIRED_BY_CURRENT_BOUNDARY` |
| Migration template lifecycle/version catalog | `FUTURE_NOT_YET_REQUIRED` |
| Full template reuse/version administration | `FUTURE_NOT_YET_REQUIRED` |
| Enterprise environment/owner/RBAC authority | Referenced dependency; broader administration remains future scope |
| M1–M8 runtime implementations | Not Step 1 scope |
| Mapping-template support | `EARLY_FUTURE_IMPLEMENTATION`, Step 5 |

# 26. Reusable Reconstruction Material

Strongest reusable pieces:

- P5 persistence, explicit version artifacts, canonical serialization, timestamps, and fingerprint mechanics.
- Gateway-generated migration ID and credential-redaction logic.
- P5 plan/version separation, retained downstream of Step 1.
- CDC/runtime identity models as constraints for non-reuse of run/session/checkpoint state.
- Wizard controls and visual patterns, without retaining its current information architecture.
- Existing capability registry pathway for a future validated API.

# 27. Kill / Retire / Legacy Candidates

- Gateway `move_migration_to_project`: kill as a functional implementation; it is a no-op.
- Frontend in-memory project repository: retire as authority.
- Gateway `_projects` and `_migrations`: compatibility caches only, not authorities.
- Hardcoded defaults such as `"mig-default"` / `"proj-default"`: rectify/remove from authoritative paths.
- Archive templates/clone UI: legacy/static display only.
- Free-form strategy as execution-mode authority: replace.

# 28. Canonical Step-1 Contract Proposal

A minimum future `MigrationDefinition` should contain:

| Field | Rule |
|---|---|
| `migration_id` | Required, immutable, globally unique durable ID |
| `name` | Required, validated human-readable name; uniqueness policy scoped separately |
| `description` | Optional mutable text |
| `business_context` | Optional structured metadata/reference |
| `owner_ref` | Required durable principal/team/service reference |
| `environment_ref` | Required durable environment reference |
| `priority` | Required closed enum/policy value |
| `workspace_ref` | Optional reference |
| `project_ref` | Optional reference; never identity |
| `planning_mode` | Required closed enum: `STANDARD`, `ADVANCED` |
| `execution_mode` | Required closed enum: `M1`–`M8`; unknown values rejected |
| `migration_window` | Optional validated intent object: timezone, bounds, recurrence/constraint semantics |
| `template_origin` | Optional immutable template ID/version/provenance reference |
| `clone_origin` | Optional immutable source migration-definition/version reference |
| `lifecycle_state` | Draft/archive status only; no runtime execution status |
| `created_at`, `updated_at`, `created_by`, `changed_by` | Required audit metadata |
| `revision` / history reference | Required for material mutations |
| `effective-default provenance` | Required when values inherit workspace/environment policy |

Fingerprint relevance: execution mode, planning mode, environment, effective defaults, membership where it changes inherited semantics, window constraints, template/clone origin. Name/description should only affect plan fingerprints if product policy says they change audit/approval semantics.

# 29. Canonical Single Entry-Point Proposal

Conceptual external interface:

```text
create_definition
load_definition
update_definition
validate_definition
assign_membership
move_membership
apply_template
clone_definition
list_definition_history
resolve_effective_definition
snapshot_for_planning
```

It must reject ambiguous or unknown execution intent, preserve immutable migration identity, write durable history atomically, and return a normalized contract. Planner, gateway, UI, and runtime should call this authority rather than maintain parallel definitions.

# 30. Proposed Future Component Home / Compartment

A dedicated migration-definition domain should own model, validation, persistence adapter, provenance/history, template/clone coordination, and contracts.

It should reference—not absorb:

- project/workspace administration;
- owner/identity administration;
- environment administration;
- credentials/connectors;
- discovery, mappings, runtime configuration;
- plan compiler;
- governance;
- schedule/run initialization;
- CDC/runtime/checkpoint engines.

# 31. Step-1 Dependency Map

```text
Future administration authorities
(project/workspace, owner, environment, policy defaults)
            ↓
Step 1: Migration Definition
            ↓
Steps 2–6: source, target, discovery, controls, configuration
            ↓
Step 7: planning / immutable plan
            ↓
Step 8: governance/readiness
            ↓
Step 9: execution initialization/scheduling
            ↓
M1–M8 runtime
```

Current dependency is fragmented: UI manifest and P5 project model independently feed different downstream paths.

# 32. Reconstruction Disposition Table

| Path | Recommended disposition |
|---|---|
| [p5_domain.py](A:/temp_akaal/akaal/planner/models/p5_domain.py:442) | `BUILD_AROUND`; extract version/fingerprint strengths |
| [project_store.py](A:/temp_akaal/akaal/planner/persistence/project_store.py:57) | `MOVE`/`RENOVATE`; preserve SQLite mechanics, replace project-as-definition schema |
| [engine_gateway.py](A:/temp_akaal/akaal/gateway/engine_gateway.py:588) | `EXTRACT` credential-safe creation behavior; `REWIRE` to canonical authority |
| [enums.py](A:/temp_akaal/akaal/core/models/enums.py:166) | `EXTRACT` legacy strategy migration mapping; `REPLACE` as canonical mode |
| [NewMigrationWizard.tsx](A:/temp_akaal/akaal_software/src/screens/MigrationModule/NewMigrationWizard.tsx:330) | `RENOVATE`; preserve controls, replace workflow and bindings |
| [projectRepository.ts](A:/temp_akaal/akaal_software/src/repositories/projectRepository.ts:1) | `RETIRE` as authoritative state |
| [MissionControlView.tsx](A:/temp_akaal/akaal_software/src/screens/MigrationModule/MissionControlView.tsx:713) | `KILL` clone implication until backend exists |
| Archive migration page | `LEGACY_ONLY`, UI inspiration only |
| Legacy manager/project model | `LEGACY_ONLY`; extract compatibility requirements |

# 33. Proof-Level Matrix

| Capability | Proof |
|---|---|
| P5 SQLite create/load/version persistence | `UNIT_PROVEN` |
| Gateway migration manifest persistence | `IMPLEMENTED`; restart integration not fully proven |
| UI-to-create_migration registered transport | `IMPLEMENTED` |
| Real Step-1 migration-definition authority | Not implemented |
| M1–M8 canonical mode contract | Not implemented |
| Durable project reassignment | Not implemented |
| Clone isolation | Not implemented |
| Template version pinning | Not implemented |
| Current wizard end-to-end exact metadata persistence | Not integration-proven |
| Production/live behavior | `LIVE_PROVEN` not established by repository evidence |

# 34. Reconstruction Estimate

| Category | Estimate |
|---|---|
| KEEP | P5 persistence mechanics, version artifacts, ID/credential-safe primitives |
| MOVE/RECTIFY/MERGE | Main effort: unify metadata, IDs, history, defaults, UI/API pathways |
| BUILD | Canonical definition model, M1–M8 enum, membership history, window model, clone/template provenance |
| KILL/LEGACY | In-memory repositories, move no-op, archive mocks, free-form strategy authority |

# 35. Lineage Estimate

| World | Step-1 value |
|---|---|
| Current AKAAL | UI controls, gateway manifest creation, CentralStateStore bridge |
| Early AKAAL/P5 | Strongest durable planning/versioning material |
| Nexus/NexusForge legacy | Project/session/checkpoint compatibility lessons |
| Compatibility bridge | CentralStateStore and gateway maps |
| Ambiguous | Archive UI and mock template/clone features |

# 36. Unresolved Questions

- Whether an external organization/workspace/environment authority exists outside the inspected repository boundary.
- Whether data in existing `artifacts/state.db` has production migration history requiring migration tooling.
- Name uniqueness policy: global, workspace-scoped, or no uniqueness constraint.
- Whether owner must be person, team, or service principal.
- Exact migration-window recurrence/blackout requirements.
- Whether project reassignment should always invalidate approvals/plans or only when effective inherited values change.
- Which historical strategy strings exist in persisted records and whether their intended behavior can be mapped losslessly.

# 37. Final Step-1 Reconstruction Verdict

A. The canonical authority should be a dedicated durable Migration Definition domain, using P5 persistence/versioning strengths but with a separate immutable `migration_id`.

B. The strongest base is P5 `ProjectStore` plus P5 version/fingerprint models—not P5 `MigrationProject` unchanged.

C. Harvest durable SQLite/WAL persistence, version snapshots, fingerprints, timestamps, gateway ID/credential safety, and runtime-ID compatibility constraints.

D. Kill in-memory frontend authority, gateway move no-op, static template/clone claims, and free-form strategy authority.

E. Move/rewire migration-definition handling out of the wizard and Gateway into one authority.

F. Keep connectors/secrets in Step 2/3, mapping templates in Step 5, planning artifacts in Step 7, and runtime/CDC/checkpoint identities in their subsystems.

G. A migration ID exists, but is not canonical across all stores.

H. It is partially independent from project/workspace, but P5 and legacy paths conflate it.

I. Project/workspace is not correctly optional today.

J. No: current move is not persistent or safe.

K. No: exact Step-1 restart reconstruction is not proven.

L. No: there is not one persisted source of truth.

M. No: planning mode is not canonical; it is hardcoded `SIMPLE` in the gateway.

N. No: M1–M8 execution mode is not canonical.

O. No: legacy strategy conversion is not safely determinable without a migration map and historical data review.

P. Yes: ambiguous values can silently alter behavior.

Q. No: migration window is static and not timezone-safe.

R. No: migration template version pinning does not exist.

S. No: cloning is not implemented or isolated.

T. Yes, if cloning were inferred from current controls; no isolation guarantee exists.

U. No: current changes do not have reliable plan/approval/schedule invalidation.

V. Current controls are mostly local-only or late-bound metadata controls.

W. The greatest performance improvement is explicit, fingerprinted M1–M8 intent and effective-definition resolution before discovery/planning.

X. The greatest accuracy improvement is one immutable migration identity plus fail-closed canonical execution-mode validation.

Y. Exact boundary: deterministic, durable operator intent and provenance only; no source/target credentials, scope, mappings, runtime config, compilation, approval, scheduling, or execution.

Z. Step 1 is ready for reconstruction design, but not ready for implementation by merely reusing current code.
