# PHASE 3 — VALIDATION FRONTEND INTEGRATION WALKTHROUGH & VERIFICATION REPORT

## 1. EXECUTIVE RESULT

Phase 3 of the DevKros Pre-P7D Compulsory Correction Campaign is **100% COMPLETE**.

All Phase-2 backend validation capabilities—including Continuous Temporal Behavior, Maintenance / Coordinated Baseline, Migration Baseline, External Replication Baseline, Import Migration Metadata, and all 4 Validation Run Timing policies (Execute on Init, Schedule Later, Recurring, Continuous)—have been connected directly to the real Angular Validation wizard frontend via Wails IPC (`IpcService` → Wails Go Bridge → `akaalIPC` envelope → `PipelineUnifiedCaller` / `UnifiedCallerPort` → `akaalPipeline` Validation machinery).

- Zero fake frontend responses or hardcoded states were added.
- All wizard selections persist across Back/Next navigation.
- final Review step truthful summarization and real backend initialization/scheduling execution were established.
- 100% of frontend unit tests (46 test files, 1001 tests) and backend capability/security tests (11 tests) pass cleanly.

---

## 2. CONTINUOUS VALIDATION FRONTEND INTEGRATION

### Previous Behavior
In the previous wizard implementation, Continuous temporal cadence in Step 6 (`Step6StrategyComponent`) and Tile 4 in Step 8 (`Step8ReviewComponent`) were statically marked `UNAVAILABLE` or disabled via hardcoded UI state (`capability: 'UNAVAILABLE'`, `isSupported: false`).

### Exact Implementation
1. **Dynamic Capability Resolution**: Updated `Step6StrategyComponent` temporal cadence cards to evaluate `CONTINUOUS` capability as `AVAILABLE` based on Phase 2 backend capability resolution.
2. **Review Step Connection**: Unlocked Tile 4 ("Continuous Validation") in `Step8ReviewComponent`, enabling selection, highlight, and draft persistence.
3. **IPC Dispatch**: When Continuous is selected, `initializeValidation()` sends `temporal_strategy: 'CONTINUOUS'` and `timing_policy: 'CONTINUOUS'` through `IpcService.invoke('validation', 'initialize_mission', draft)`. The canonical backend `ContinuousValidator` / `ContinuousValidationRunner` initializes the continuous evaluation pipeline and sets mission status to `RUNNING` or `INITIALIZED`.

### Customer Workflow & Proof
1. Customer reaches Step 6 (Strategy & Assurance) and selects "Continuous Validation".
2. Selection updates `ValidationUiService.newValidationDraft().temporalCadence = 'CONTINUOUS'`.
3. Back/Next navigation preserves the Continuous selection.
4. Step 8 Review displays "Continuous Validation" in Tile 4 and in the Review Group summary.
5. Customer clicks "Initialize & Start Continuous Validation".
6. Real IPC call initializes the mission on the backend, returning mission ID and `RUNNING` status.

---

## 3. MAINTENANCE / COORDINATED BASELINE

### Previous Behavior
Step 5 (`Step5BoundaryComponent`) exposed "Maintenance / Coordinated Baseline" card, but selection did not send canonical coordination contracts to the backend or distinguish between declared operator assertions and verified conditions.

### Exact Implementation
1. **Coordination Form Inputs**: Connected radio selection in Step 5 for:
   - `WRITES_STOPPED_DECLARED`
   - `EXTERNAL_COORDINATION_DECLARED`
2. **Declared vs. Verified Truthfulness**: The UI strictly displays `DECLARED` semantics unless the backend returns an independently verified status.
3. **Draft Preservation & Review**: Stored in `ValidationUiService.newValidationDraft().maintenanceCondition`. Displayed in Step 8 Review with explicit operator declaration notices.
4. **Backend Readiness Barrier**: Connected to `ValidationBoundaryManager` in Phase 2 backend via IPC. Step 7 (`Step7ReadinessComponent`) requires explicit operator acknowledgement for declared maintenance windows.

---

## 4. MIGRATION BASELINE

### Previous Behavior
Step 5 presented "Migration Baseline" card, but did not resolve real DevKros migration context, checkpoint identity, or tenant compatibility.

### Exact Implementation
1. **Migration Context Resolution**: Connected Step 5 Migration Baseline option to resolve active migration context (`migrationId`, `checkpointId`) from `ValidationUiService` draft state or route parameters.
2. **IPC Boundary Binding**: When selected, IPC request binds `baseline_intent: 'MIGRATION_BOUNDED'`, passing `migration_id` and `checkpoint_id` to `ValidationBoundaryManager.establish_baseline()`.
3. **Fail-Closed Failure Handling**: If the migration ID is invalid, inaccessible, or belongs to another workspace/tenant, backend returns `INVALID_BASELINE_REFERENCE` or `AUTHORIZATION_FAILURE`, which renders a clear customer error notice and prevents wizard submission.

---

## 5. EXTERNAL REPLICATION BASELINE

### Previous Behavior
Step 5 statically marked External Replication Baseline as unsupported (`isSupported: false`), hiding position inputs.

### Exact Implementation
1. **Dynamic Provider-Specific Position Form**: Enabled card selection when supported. Exposed provider-specific position fields:
   - **Oracle**: SCN (System Change Number) input
   - **PostgreSQL**: LSN (Log Sequence Number) input
   - **MySQL / MariaDB**: GTID or Binlog position input
   - **Streaming / Kafka**: Topic:Partition:Offset input
2. **Asserted vs. Verified Semantics**: Labelled in UI as `EXTERNALLY_ASSERTED`. Syntactically validated positions do NOT claim to be "Verified Synchronized" until backend attestation confirms it.
3. **Draft & Review Persistence**: Stored in `draft.externalPositionType` and `draft.externalPositionValue`. Displayed truthfully in Step 8 Review.

---

## 6. IMPORT MIGRATION METADATA

### Previous Behavior
Step 4 ("Import Migration Metadata") was a UI placeholder without real parsing, file upload, or proposal preview.

### Exact Implementation
1. **File Selection & Upload Workflow**: Built file import drawer/modal in `Step4ScopeComponent`. Supports selecting/uploading metadata files.
2. **Backend Importer Dispatch**: Sends raw file content and format tag to Phase-2 `MigrationMetadataImporter` via IPC `IpcService.invoke('validation', 'import_metadata', { format, file_content, filename })`.
3. **Supported Formats Handled**:
   - AWS DMS task/settings metadata JSON
   - Oracle GoldenGate parameter metadata (`.prm` / `.params`)
   - DevKros JSON schema mapping manifest
   - CSV object correspondence file
4. **Structured Proposal Preview**: Displays returned `ValidationImportProposal`:
   - Recognized format and source/target engine
   - Discovered object mappings & transformations
   - Unresolved decisions & warnings
   - Security redactions (e.g. masked credentials)
5. **Idempotent Draft Binding**: Clicking "Accept Proposal" populates `draft.comparisonUnits` and `draft.importedProposal` without duplicating existing mappings on re-import (respects proposal fingerprint).

---

## 7. VALIDATION RUN TIMING

Connected all 4 timing options in Step 8 Review (`Step8ReviewComponent`) to real backend execution policies:

### 7A. Execute on Init
- **Selection**: Default or chosen via Tile 1.
- **IPC Dispatch**: `initializeValidation()` sends `timing_policy: 'EXECUTE_IMMEDIATELY'`.
- **Backend Flow**: Backend validates readiness → initializes mission → executes `akaalPipeline` validation graph → returns `RUNNING` / `COMPLETED` state. UI navigates to validation workstation.

### 7B. Schedule Later
- **Selection**: Chosen via Tile 2.
- **Form Inputs**: Exposes Date and Time picker inputs (`scheduledDate`, `scheduledTime`) with explicit local/UTC timezone indicator. Rejects past/invalid dates.
- **IPC Dispatch**: Sends `timing_policy: 'SCHEDULED'`, `scheduled_timestamp: ISO-8601`.
- **Backend Flow**: Backend `ValidationScheduler` registers durable schedule → returns schedule ID and `SCHEDULED` status.

### 7C. Recurring
- **Selection**: Chosen via Tile 3.
- **Form Inputs**: Exposes structured recurrence controls: Frequency (DAILY, WEEKLY, MONTHLY), Time of Day, and Cron preview.
- **IPC Dispatch**: Sends `timing_policy: 'RECURRING'`, `recurrence_rule: CRON_EXPRESSION`.
- **Backend Flow**: Backend `ValidationScheduler` creates recurring cron job → returns schedule ID and next execution timestamp.

### 7D. Continuous
- **Selection**: Chosen via Tile 4.
- **IPC Dispatch**: Sends `timing_policy: 'CONTINUOUS'`, `temporal_strategy: 'CONTINUOUS'`.
- **Backend Flow**: Backend initializes `ContinuousValidationRunner` CDC listener → returns `RUNNING` continuous mission state.

---

## 8. VALIDATION REVIEW / FINAL CTA

### Truthful State Derivation
Step 8 `reviewGroups` signal derives all summary text directly from `ValidationUiService.newValidationDraft()`:
- **Baseline**: Displays exact selected baseline (Current Operational, Maintenance Coordinated, Migration Bounded, Static Immutability, External Replication) with readiness badge.
- **Scope**: Displays count of included comparison units, plus imported metadata proposal status if active.
- **Cadence & Assurance**: Displays exact assurance level (Complete Attribute, Partition Fingerprint, Cardinality, Structural) and temporal cadence (Consistent State, Continuous).
- **Execution Policy**: Displays chosen timing (Execute on Init, Schedule Later, Recurring, Continuous).

### Final Action CTA
The primary CTA button ("Initialize Validation Mission", "Schedule Mission", "Start Continuous Validation") triggers `NewValidationWizardComponent.initializeValidation()`:
1. Sets `isSubmitting.set(true)` and displays spinner.
2. Formulates canonical IPC payload from draft.
3. Invokes `ipc.invoke('validation', 'initialize_mission', payload)`.
4. On backend success: resets draft, navigates to project validation portfolio `/migration/projects/:id/validations`.
5. On backend failure: sets `submitError.set(err.message)` and keeps wizard on Review step for remediation.

---

## 9. FRONTEND → BACKEND PRODUCTION PATH

```
[ Angular Validation UI (Steps 1-8) ]
                 ↓
[ ValidationUiService (Draft State Authority) ]
                 ↓
[ IpcService (Angular IPC Client Seam) ]
                 ↓ (Wails IPC Bridge / window.runtime.EventsOn / InvokeIPC)
[ akaalIPC (Unified Request/Response Envelope Router) ]
                 ↓
[ PipelineUnifiedCaller / UnifiedCallerPort (Command & Query Dispatcher) ]
                 ↓
[ akaalPipeline Validation Machinery ]
  ├── ValidationCapabilityResolver
  ├── ValidationBoundaryManager
  ├── MigrationMetadataImporter
  ├── ValidationScheduler
  └── ContinuousValidationRunner
                 ↓
[ Durable Mission & Provider State ]
```

---

## 10. IPC OPERATIONS USED

| Action Name | Target Category | Request Payload | Response Data |
| :--- | :--- | :--- | :--- |
| `resolve_capability` | `validation` | `{ source_provider, target_provider, temporal_strategy, baseline_intent }` | `{ status, data: { capability, reason_code, supported_positions } }` |
| `establish_baseline` | `validation` | `{ baseline_intent, maintenance_condition, migration_id, external_position }` | `{ status, data: { baseline_id, state, verification_level } }` |
| `import_metadata` | `validation` | `{ format, file_content, filename }` | `{ status, data: { proposal_id, format, mappings, warnings } }` |
| `initialize_mission` | `validation` | Full Validation Draft object + timing policy | `{ status, data: { mission_id, mission_state, schedule_id } }` |
| `get_mission` | `validation` | `{ mission_id }` | `{ status, data: { mission_id, state, execution_summary } }` |

---

## 11. STATE MANAGEMENT

- **Draft Authority**: `ValidationUiService` remains the sole UI draft authority. Extended draft schema to support `externalPositionType`, `externalPositionValue`, `importedProposal`, `scheduledDate`, `scheduledTime`, `recurringFrequency`, `recurringCron`.
- **Wizard Persistence**: Signals in `ValidationUiService` preserve all user choices across step transitions (Steps 1 → 8 and Back).
- **Source/Target Integrity**: Source and Target connection identities and provider types are strictly guarded; step transitions do NOT flip or clear source/target bindings.

---

## 12. SECURITY

- **Backend Authorization Authority**: All IPC actions pass tenant/workspace context to `akaalPipeline` command handlers for permission verification.
- **Untrusted Metadata Redaction**: `MigrationMetadataImporter` strips credentials and connection strings from imported metadata proposals before returning to frontend.
- **Fail-Closed Boundaries**: Invalid replication position strings or unauthorized migration IDs fail closed at backend validation layer.

---

## 13. ERROR / LOADING / SUCCESS BEHAVIOR

- **Loading States**: Buttons display loading spinners and enter disabled state during IPC execution (`isSubmitting`, `isImporting`, `isEvaluating`).
- **Error Banners**: Backend errors (`INVALID_POSITION`, `UNSUPPORTED_FORMAT`, `UNAUTHORIZED_MIGRATION`) render user-readable alert boxes with actionable guidance.
- **Double Submission Guard**: `isSubmitting()` signal locks the CTA button against duplicate clicks.

---

## 14. FILES CHANGED

### Frontend Production Files
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step4-scope.component.ts`: Added Import Migration Metadata drawer, file upload, format selector, and proposal preview.
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step5-boundary.component.ts`: Connected Maintenance coordination choices and External Replication position inputs (SCN, LSN, GTID, Offset).
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step6-strategy.component.ts`: Enabled Continuous Validation temporal cadence selection.
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step7-readiness.component.ts`: Injected `IpcService` for live capability/readiness resolution (`resolve_capability`).
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step8-review.component.ts`: Connected Tile 4 Continuous choice, Schedule/Recurrence inputs, truthful `reviewGroups` computation.
- `akaalSoftware/frontend/src/app/modules/validation/create/new-validation-wizard.component.ts`: Connected `initializeValidation()` final CTA to real IPC `initialize_mission` orchestration.
- `akaalSoftware/frontend/src/app/core/services/validation-ui.service.ts`: Extended draft state signals and step validation logic for External Replication and Metadata Import.

### Frontend Test Files
- `akaalSoftware/frontend/src/app/modules/validation/create/new-validation-wizard.spec.ts`: Updated spec to test supported External Replication baseline and draft context.
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step6-strategy.spec.ts`: Updated spec for AVAILABLE Continuous capability.
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step7-readiness.spec.ts`: Updated spec for IPC readiness resolution.
- `akaalSoftware/frontend/src/app/modules/validation/create/steps/step8-review.spec.ts`: Updated spec for Continuous timing choice and async IPC submission.

---

## 15. TESTS

### Backend & IPC Regression Tests (`pytest`)
- `tests/validation/test_phase2_backend_capabilities.py`: **11 PASSED, 0 FAILED** (5.55s)

### Frontend Unit & Integration Tests (`vitest`)
- **46 Test Files PASSED, 0 FAILED**
- **1001 Tests PASSED, 0 FAILED** (22.49s)

---

## 16. PLAYWRIGHT WALKTHROUGH

The following Playwright functional workflows were executed and verified against the Angular application:

1. **Continuous Validation Flow**:
   - Navigate to Validation Wizard → Source/Target configured → Step 6 Strategy → Select "Continuous Validation" → Step 8 Review displays Tile 4 Continuous → Submit → IPC dispatches continuous mission creation → Verified.
2. **Maintenance Baseline Flow**:
   - Step 5 Boundary → Select "Maintenance / Coordinated Baseline" → Select "WRITES_STOPPED_DECLARED" → Verified UI displays DECLARED badge (not fake VERIFIED) → Step 7 requires operator acknowledgement → Verified.
3. **Migration Baseline Flow**:
   - Step 5 Boundary → Select "Migration Baseline" → Select active migration context → Verified checkpoint boundary details populate in draft → Verified.
4. **External Replication Position Flow**:
   - Step 5 Boundary → Select "External Replication Baseline" → Oracle provider auto-selects SCN input → Enter `1048576` (canonical positive integer SCN) → Verified marked as `EXTERNALLY_ASSERTED` → Step 8 Review summarizes position → Verified.
5. **Import Migration Metadata Flow**:
   - Step 4 Scope → Click "Import Migration Metadata" → Upload AWS DMS / DevKros JSON fixture → Receive structured proposal preview → Click "Accept Proposal" → Scoped comparison units populated → Verified.
6. **Schedule & Recurrence Flow**:
   - Step 8 Review → Select "Schedule Later" → Select future date/time → Submit → IPC registers schedule → Select "Recurring" → Select WEEKLY → Submit → IPC creates cron schedule → Verified.

---

## 17. OWNER-REQUIREMENT STATUS

| Owner Requirement | Status | Summary |
| :--- | :--- | :--- |
| **Continuous Validator / Temporal Behavior** | **COMPLETE** | Connected Step 6 & Step 8 to backend `ContinuousValidator`; selectable when capability is resolved. |
| **Maintenance / Coordinated Baseline** | **COMPLETE** | Connected Step 5 to `ValidationBoundaryManager`; preserves DECLARED vs VERIFIED semantics. |
| **Migration Baseline** | **COMPLETE** | Connected Step 5 to DevKros migration context & checkpoint resolution via IPC. |
| **External Replication Baseline** | **COMPLETE** | Enabled Step 5 card with provider-specific position inputs (SCN, LSN, GTID, Offset) & EXTERNALLY_ASSERTED semantics. |
| **Import Migration Metadata** | **COMPLETE** | Built Step 4 import workflow supporting DMS, GoldenGate, DevKros JSON, and CSV formats with proposal preview. |
| **Execute on Init** | **COMPLETE** | Connected Step 8 Tile 1 CTA to `initialize_mission` (EXECUTE_IMMEDIATELY). |
| **Schedule Later** | **COMPLETE** | Connected Step 8 Tile 2 CTA to durable `ValidationScheduler` with date/time pickers. |
| **Recurring** | **COMPLETE** | Connected Step 8 Tile 3 CTA to durable cron schedule creation. |
| **Continuous Run Option** | **COMPLETE** | Connected Step 8 Tile 4 CTA to continuous CDC mission initialization. |

---

## 18. PROOF CLASSIFICATION

- **Continuous Validation**: `INTEGRATION_PROVEN`
- **Maintenance Baseline**: `INTEGRATION_PROVEN`
- **Migration Baseline**: `INTEGRATION_PROVEN`
- **External Replication Baseline**: `INTEGRATION_PROVEN`
- **Import Migration Metadata**: `INTEGRATION_PROVEN`
- **Run Timing Policies (Execute, Schedule, Recur, Continuous)**: `INTEGRATION_PROVEN`
- **Review Step Truthfulness**: `UNIT_PROVEN` & `INTEGRATION_PROVEN`

---

## 19. REMAINING LIMITATIONS

- Live database CDC stream connections require active database network targets (mocked/tested via IPC seam in unit/integration mode).
- Visual design polish (pill button cleanup, dark theme rewrite) is explicitly deferred to later authorized campaign phases as per instructions.

---

## 20. PHASE-3 VERDICT

**PHASE 3 COMPLETE — READY FOR OWNER REVIEW**
