# AKAAL Phase 10 Part 2 – Detailed Task Breakdown

**Architectural Blueprint Contract:** `PHASE10_PART1_IMPLEMENTATION_PLAN.md` (v1.3.0 Frozen)  
**Master Plan Reference:** [MASTER_IMPLEMENTATION_PLAN_PART2.md](file:///c:/Users/LENOVO/Downloads/temp_akaal-main/MASTER_IMPLEMENTATION_PLAN_PART2.md)  
**Status:** Implementation Task Checklist  

---

## Phase 1: Approval Engine & Token Subsystem

### Task 1.1: Approval Data Models (`akaal/workflow/approval/models.py`)
- [ ] Define `ApprovalStatus` Enum (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`).
- [ ] Define `@dataclass(frozen=True)` `ApprovalToken` with `token_id`, `workflow_id`, `step_id`, `requested_by`, `approved_by`, `status`, `expires_at`, and `checksum`.
- [ ] Define `@dataclass(frozen=True)` `ApprovalRequest` with `request_id`, `workflow_id`, `required_role`, `timeout_seconds`.
- **Dependencies**: `akaal/workflow/models/`, `akaal/workflow/utils/serialization.py`.
- **Test File**: `tests/unit/workflow/test_approval_models.py`.
- **Acceptance Criteria**: Immutability enforced; checksum verified; serialized JSON round-trip passing.

### Task 1.2: Approval Engine (`akaal/workflow/approval/engine.py`)
- [ ] Implement `ApprovalEngine` class.
- [ ] Methods: `request_approval()`, `approve_token()`, `reject_token()`, `get_token()`, `evaluate_expirations()`.
- [ ] Inject `IClock` and `IIdGenerator`.
- **Dependencies**: Task 1.1, `IClock`, `IIdGenerator`.
- **Test File**: `tests/unit/workflow/test_approval_engine.py`.
- **Acceptance Criteria**: Thread-safe token state transitions; automatic token expiration via `IClock`.

### Task 1.3: Approval Gate Step (`akaal/workflow/approval/gate.py`)
- [ ] Implement `ApprovalGateStep` implementing `IStep`.
- [ ] `validate_preconditions()`: Ensures valid `ApprovalRequest`.
- [ ] `execute()`: Pauses execution if approval token is pending; returns `StepStatus.COMPLETED` once approved.
- [ ] `rollback()`: Revokes pending approval requests.
- **Dependencies**: Task 1.2, `IStep`.
- **Test File**: `tests/unit/workflow/test_approval_gate_step.py`.
- **Acceptance Criteria**: Pauses workflow in `WAITING_FOR_APPROVAL` state; resumes cleanly upon token sign-off.

---

## Phase 2: Concrete Enterprise Workflows & Steps

### Task 2.1: Pre-Migration Workflow & Steps (`akaal/workflow/concrete/pre_migration.py`)
- [ ] Implement `EnvironmentDiscoveryStep` (discovers database metadata, network bounds).
- [ ] Implement `PreflightCheckStep` (verifies schema compatibility & permissions).
- [ ] Implement `SourceSnapshotStep` (triggers read-only source snapshot).
- [ ] Implement `PreMigrationWorkflow` manifest builder returning valid `WorkflowManifest`.
- **Dependencies**: `akaal/workflow/models/`, `IStep`.
- **Test File**: `tests/unit/workflow/test_pre_migration_workflow.py`.
- **Acceptance Criteria**: Manifest passes `ManifestValidator`; steps execute in sequence with precondition verification.

### Task 2.2: Migration Workflow & Steps (`akaal/workflow/concrete/migration.py`)
- [ ] Implement `DataExtractStep` (streams table data).
- [ ] Implement `DataTransformStep` (applies type conversion mappings).
- [ ] Implement `BatchLoadStep` (loads data in checkpointed batches).
- [ ] Implement `MigrationWorkflow` manifest builder.
- **Dependencies**: Task 2.1.
- **Test File**: `tests/unit/workflow/test_migration_workflow.py`.
- **Acceptance Criteria**: Batch progress tracked in `ExecutionContext`; step checkpoints generated at configurable batch intervals.

### Task 2.3: Validation Workflow & Steps (`akaal/workflow/concrete/validation.py`)
- [ ] Implement `RowCountValidationStep` (compares source vs target row counts).
- [ ] Implement `ChecksumValidationStep` (compares table checksum hashes).
- [ ] Implement `GoldenBenchmarkValidationStep` (asserts Golden Benchmark rules).
- [ ] Implement `ValidationWorkflow` manifest builder.
- **Dependencies**: Task 2.2.
- **Test File**: `tests/unit/workflow/test_validation_workflow.py`.
- **Acceptance Criteria**: Fails gracefully if row counts or checksums mismatch; triggers `on_failure` lifecycle hook.

### Task 2.4: Cutover Workflow & Steps (`akaal/workflow/concrete/cutover.py`)
- [ ] Implement `SourceLockStep` (locks source database for read-only window).
- [ ] Implement `CdcCatchupStep` (drains remaining CDC change log queue).
- [ ] Implement `DnsCutoverStep` (switches active connection endpoint).
- [ ] Implement `CutoverWorkflow` manifest builder.
- **Dependencies**: Task 2.3.
- **Test File**: `tests/unit/workflow/test_cutover_workflow.py`.
- **Acceptance Criteria**: Preconditions strictly verify CDC queue zero-lag before DNS cutover.

### Task 2.5: Rollback Workflow & Steps (`akaal/workflow/concrete/rollback.py`)
- [ ] Implement `CutoverAbortStep` (aborts active cutover window).
- [ ] Implement `SourceUnlockStep` (re-enables source database writes).
- [ ] Implement `TargetTeardownStep` (cleans up incomplete target tables).
- [ ] Implement `RollbackWorkflow` manifest builder.
- **Dependencies**: Task 2.4.
- **Test File**: `tests/unit/workflow/test_rollback_workflow.py`.
- **Acceptance Criteria**: Successfully reverses cutover actions; restores system state to pre-cutover baseline.

### Task 2.6: Approval Workflow (`akaal/workflow/concrete/approval.py`)
- [ ] Implement `ApprovalWorkflow` manifest builder wrapping `ApprovalGateStep`.
- **Dependencies**: Task 1.3.
- **Test File**: `tests/unit/workflow/test_approval_workflow.py`.
- **Acceptance Criteria**: Provides standalone human approval sign-off manifest.

---

## Phase 3: Workflow Composition Subsystem

### Task 3.1: Workflow Composer (`akaal/workflow/composition/composer.py`)
- [ ] Implement `WorkflowComposer` class.
- [ ] Method: `compose(manifests: Sequence[WorkflowManifest], global_metadata: WorkflowMetadata) -> WorkflowManifest`.
- [ ] Merges step definitions, updates cross-workflow step dependency IDs, and validates combined DAG.
- **Dependencies**: `akaal/workflow/models/`, `ManifestValidator`.
- **Test File**: `tests/unit/workflow/test_composer.py`.
- **Acceptance Criteria**: Combines `PreMigration` + `Migration` + `Validation` manifests; detects cross-workflow circular dependencies.

### Task 3.2: Workflow Chain Builder (`akaal/workflow/composition/chain.py`)
- [ ] Implement `WorkflowChain` fluent builder facade.
- [ ] Methods: `then()`, `with_approval()`, `with_timeout()`, `build()`.
- **Dependencies**: Task 3.1.
- **Test File**: `tests/unit/workflow/test_chain.py`.
- **Acceptance Criteria**: Provides readable fluid API for pipeline assembly.

---

## Phase 4: Workflow Scheduling Subsystem

### Task 4.1: Schedule Triggers (`akaal/workflow/scheduling/triggers.py`)
- [ ] Implement `CronSchedule` (5-field cron expression parser: `minute`, `hour`, `day_of_month`, `month`, `day_of_week`).
- [ ] Implement `OneShotSchedule` (fixed timestamp trigger).
- **Dependencies**: `IClock`.
- **Test File**: `tests/unit/workflow/test_triggers.py`.
- **Acceptance Criteria**: Accurately computes next execution timestamp relative to `IClock`.

### Task 4.2: Workflow Scheduler (`akaal/workflow/scheduling/scheduler.py`)
- [ ] Implement `WorkflowScheduler` class.
- [ ] Methods: `schedule_workflow()`, `unschedule_workflow()`, `list_schedules()`, `poll_and_trigger()`.
- [ ] Inject `WorkflowEngine`, `IClock`, and `IIdGenerator`.
- **Dependencies**: Task 4.1, `WorkflowEngine`.
- **Test File**: `tests/unit/workflow/test_scheduler.py`.
- **Acceptance Criteria**: Triggers workflow execution at scheduled time; handles missed schedule recovery cleanly.

---

## Phase 5: Notifications & Subsystem Integration Adapters

### Task 5.1: Notification Service (`akaal/workflow/notifications/service.py`)
- [ ] Implement `WorkflowNotificationService` subscribing to `IEventDispatcher`.
- [ ] Dispatches alerts on `WorkflowStateChangedEvent` (state changes, failures, completions, approval requests).
- **Dependencies**: `IEventDispatcher`, `WorkflowEvent`.
- **Test File**: `tests/unit/workflow/test_notification_service.py`.
- **Acceptance Criteria**: Receives state events and invokes notification handlers without blocking core engine execution.

### Task 5.2: Audit Integration Adapter (`akaal/workflow/integration/audit_adapter.py`)
- [ ] Implement `AuditIntegrationAdapter` subscribing to `IEventDispatcher`.
- [ ] Converts workflow events to AKAAL audit log entries (`akaal/audit/`).
- **Dependencies**: `IEventDispatcher`, `akaal/audit/`.
- **Test File**: `tests/unit/workflow/test_audit_adapter.py`.
- **Acceptance Criteria**: Writes append-only, checksum-verified audit records for all workflow state transitions.

### Task 5.3: External Subsystem Adapters (`akaal/workflow/integration/adapters.py`)
- [ ] Implement `IntelligenceAdapter` (interfaces with `akaal/intelligence/`).
- [ ] Implement `MigrationEngineAdapter` (interfaces with `akaal/migration/`).
- **Dependencies**: `akaal/intelligence/`, `akaal/migration/`.
- **Test File**: `tests/unit/workflow/test_integration_adapters.py`.
- **Acceptance Criteria**: Wraps external domain calls cleanly behind abstract interfaces.

---

## Phase 6: E2E Integration, Verification & Distributed Preparedness

### Task 6.1: E2E Migration Pipeline Test Suite (`tests/integration/workflow/test_e2e_migration_pipeline.py`)
- [ ] Build end-to-end integration test executing `PreMigration` → `Migration` → `Validation` → `Approval` → `Cutover`.
- [ ] Test simulated crash injection and resumption from intermediate step checkpoint.
- [ ] Test emergency rollback triggering `RollbackWorkflow`.
- **Dependencies**: All Phase 1-5 modules.
- **Acceptance Criteria**: 100% test pass rate; zero state corruption; 100% audit log compliance.

### Task 6.2: AST DAG & Architecture Audit (`tests/unit/workflow/test_part2_architecture.py`)
- [ ] Extend AST static analyzer to verify 0 circular imports across all new Part 2 packages.
- [ ] Verify 100% type hint coverage.
- [ ] Verify 0 raw calls to `uuid4()` or `datetime.utcnow()`.
- **Dependencies**: All Part 2 packages.
- **Acceptance Criteria**: Clean AST audit with 0 violations.

### Task 6.3: Documentation & Certification Sign-Off
- [ ] Update `docs/CURRENT_PHASE.md`, `docs/SPRINT.md`, `docs/CHANGELOG.md`.
- [ ] Synchronize Git repository with `origin/main`.
- **Acceptance Criteria**: Working tree clean; HEAD aligned with origin/main.
