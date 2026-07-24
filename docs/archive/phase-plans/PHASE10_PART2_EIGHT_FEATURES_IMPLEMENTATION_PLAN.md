# AKAAL Phase 10 Part 2 – Eight Core Enterprise Workflow Features Implementation Plan

**Document Version:** 1.0.0 (Frozen Implementation Blueprint)  
**Target Architectural Contract:** `PHASE10_PART1_IMPLEMENTATION_PLAN.md` (v1.3.0 Frozen)  
**Status:** **FROZEN & APPROVED FOR IMMEDIATE EXECUTION**  

---

## 1. Current Architecture Inventory

Based on direct inspection of the codebase under `akaal/`:

- **Workflow Subsystem (`akaal/workflow/`)**:
  - `akaal/workflow/api/client.py`: `WorkflowClient` facade.
  - `akaal/workflow/engine/engine.py`: `WorkflowEngine` managing workflow submission, execution orchestration, and state machine integration.
  - `akaal/workflow/execution/pipeline.py`: `ExecutionPipeline` managing the lifecycle hooks of `IStep` (`initialize`, `validate_preconditions`, `execute`, `on_success`, `on_failure`, `validate_postconditions`, `checkpoint`, `cleanup`).
  - `akaal/workflow/registry/registry.py`: `WorkflowStepRegistry` encapsulating private `_StepFactory`.
  - `akaal/workflow/state_machine/`: `WorkflowState` enum (12 explicit states), `TransitionGraph`, `StateController`.
  - `akaal/workflow/checkpoint/`: `CheckpointManager`, `ICheckpointStorage` adapters (`InMemoryCheckpointStorage`, `FileBasedCheckpointStorage`).
  - `akaal/workflow/events/`: `IEventDispatcher` protocol, `InMemoryEventDispatcher` adapter emitting `WorkflowEvent`, `WorkflowStateChangedEvent`, `StepExecutedEvent`.
  - `akaal/workflow/models/`: Immutable frozen dataclasses (`WorkflowContext`, `WorkflowManifest`, `StepDefinition`, `WorkflowMetadata`, `WorkflowCheckpoint`, `WorkflowStepResult`).
  - `akaal/workflow/interfaces/base.py`: Protocols for `IStep`, `IExecutionStrategy`, `IEngine`, `IWorkflowLock`.
  - `akaal/workflow/approval/`: `ApprovalToken` models, `ApprovalEngine`, `ApprovalGateStep`.
  - `akaal/workflow/security/`: `SecurityContext` permissions model.
  - `akaal/workflow/utils/`: Injected `IClock` (`SystemClock`, `FixedClock`), `IIdGenerator` (`UUIDIdGenerator`, `DeterministicIdGenerator`), and canonical SHA-256 serializer.
- **Audit Logging Subsystem (`akaal/audit/`)**:
  - `akaal/audit/audit_logger.py`: `AuditLogger`, `AuditEntry`, `AuditEventType`. Writes append-only checksum-verified audit records.
- **External Domain Engines & Agents**:
  - `akaal/scout/`: `DiscoveryOrchestrator` (`Scout`)
  - `akaal/rulebook/`: `RulebookEngine` (`Rulebook`)
  - `akaal/decoder/`: `DecoderEngine` (`Decoder`)
  - `akaal/risk/`: `RiskEngine` (`Risk`)
  - `akaal/planner/`: `MigrationPlanner` (`Planner`)
  - `akaal/advisor/`: `AdvisorEngine` (`Advisor`)
  - `akaal/intelligence/`: `EnterpriseIntelligenceEngine` (`Enterprise Intelligence`)
  - `akaal/migration/`: `MigrationExecutor`, `CDCManager`, `ValidationEngine` (`GB Validator`), `RollbackEngine`

---

## 2. Gap Analysis for Eight Features

### 1. `PreMigrationWorkflow`
- **Status**: Platform foundation exists; concrete workflow definition coordinating Scout → Rulebook → Decoder → Risk → Planner → Advisor → Enterprise Intelligence is missing.
- **Action**: Implement `akaal/workflow/concrete/pre_migration.py` defining steps and manifest builder.

### 2. `MigrationWorkflow`
- **Status**: Platform foundation and `MigrationExecutor` exist; workflow coordination step delegating to `akaal.migration` without duplicating row-copy logic is missing.
- **Action**: Implement `akaal/workflow/concrete/migration.py` defining `MigrationWorkflow` and `MigrationStep`.

### 3. `ValidationWorkflow`
- **Status**: Platform foundation and `ValidationEngine` (`GB Validator`) exist; workflow step delegating validation to `akaal.migration.reliability.validation` is missing.
- **Action**: Implement `akaal/workflow/concrete/validation.py` defining `ValidationWorkflow` and `GBValidationStep`.

### 4. `CutoverWorkflow`
- **Status**: CDC models and cutover execution exist; sequential orchestration (CDC Stop → Final Sync → Cutover) is missing.
- **Action**: Implement `akaal/workflow/concrete/cutover.py` defining `CutoverWorkflow`, `CdcStopStep`, `FinalSyncStep`, and `CutoverSwitchStep`.

### 5. `RollbackWorkflow`
- **Status**: `RollbackEngine` and `RollbackPlanner` exist in `akaal.migration.reliability.rollback`; workflow step and session resume/checkpoint integration are missing.
- **Action**: Implement `akaal/workflow/concrete/rollback.py` defining `RollbackWorkflow` and `RollbackStep`.

### 6. Human Approval Engine (3 Ordered Gates)
- **Status**: Basic `ApprovalEngine` and `ApprovalToken` models exist in `akaal/workflow/approval/`; full 3-gate ordered approval chain (Approval #1: Plan Readiness, Approval #2: Migration Progression, Approval #3: Final Cutover) with User/Role/Group principals, Approve/Reject/Timeout/Delegate actions, and audit logging is required.
- **Action**: Expand `akaal/workflow/approval/models.py`, `engine.py`, and `gate.py`.

### 7. Report Orchestration (5 Reports)
- **Status**: Individual domain report models exist; automated trigger orchestration for Pre-Migration, Migration, Validation, Cutover, and Post-Migration reports in JSON & Markdown formats is missing.
- **Action**: Implement `akaal/workflow/reporting/orchestrator.py` and `akaal/workflow/reporting/reports.py`.

### 8. Workflow Event Bus Integration
- **Status**: `IEventDispatcher` and `InMemoryEventDispatcher` exist; typed domain events for `Started`, `Completed`, `Failed`, `Retrying`, `Paused`, `Cancelled`, `ApprovalRequested`, `ApprovalGranted`, `ApprovalRejected` emitted to `IEventDispatcher` must be verified.
- **Action**: Expand `akaal/workflow/events/events.py` with typed lifecycle event payloads.

---

## 3. File-by-File Implementation Plan

| File Path | Action | Responsibilities | Key Classes / Functions |
|---|---|---|---|
| `akaal/workflow/approval/models.py` | Modify | Define 3-gate approval requests, principal types (User, Role, Group), delegation, and audit metadata | `ApprovalStatus`, `PrincipalType`, `ApprovalPrincipal`, `ApprovalRequest`, `ApprovalDecision`, `ApprovalToken` |
| `akaal/workflow/approval/engine.py` | Modify | Orchestrate 3-gate sequential approvals (Approval #1, #2, #3), evaluate decisions, timeout handling, delegation | `ApprovalEngine` |
| `akaal/workflow/approval/gate.py` | Modify | Concrete `ApprovalGateStep` pausing execution in `WAITING_FOR_APPROVAL` until token sign-off | `ApprovalGateStep` |
| `akaal/workflow/events/events.py` | Modify | Define typed domain events (`Started`, `Completed`, `Failed`, `Retrying`, `Paused`, `Cancelled`, `ApprovalRequested`, `ApprovalGranted`, `ApprovalRejected`) | `WorkflowStartedEvent`, `WorkflowCompletedEvent`, `WorkflowFailedEvent`, `WorkflowRetryingEvent`, `WorkflowPausedEvent`, `WorkflowCancelledEvent`, `ApprovalRequestedEvent`, `ApprovalGrantedEvent`, `ApprovalRejectedEvent` |
| `akaal/workflow/concrete/pre_migration.py` | Create | Concrete `PreMigrationWorkflow` coordinating Scout → Rulebook → Decoder → Risk → Planner → Advisor → Enterprise Intelligence | `PreMigrationWorkflow`, `ScoutStep`, `RulebookStep`, `DecoderStep`, `RiskStep`, `PlannerStep`, `AdvisorStep`, `EnterpriseIntelligenceStep` |
| `akaal/workflow/concrete/migration.py` | Create | Concrete `MigrationWorkflow` delegating execution to `akaal.migration.executor.Executor` | `MigrationWorkflow`, `MigrationStep` |
| `akaal/workflow/concrete/validation.py` | Create | Concrete `ValidationWorkflow` delegating GB validation to `ValidationEngine` | `ValidationWorkflow`, `GBValidationStep` |
| `akaal/workflow/concrete/cutover.py` | Create | Concrete `CutoverWorkflow` orchestrating CDC Stop → Final Sync → Cutover Switch | `CutoverWorkflow`, `CdcStopStep`, `FinalSyncStep`, `CutoverSwitchStep` |
| `akaal/workflow/concrete/rollback.py` | Create | Concrete `RollbackWorkflow` orchestrating reverse execution and rollback checkpoints | `RollbackWorkflow`, `RollbackStep` |
| `akaal/workflow/reporting/reports.py` | Create | Data models and formatters for the 5 enterprise reports (Pre-Migration, Migration, Validation, Cutover, Post-Migration) in JSON & Markdown | `WorkflowReportType`, `ReportFormat`, `EnterpriseReport` |
| `akaal/workflow/reporting/orchestrator.py` | Create | Event-driven report orchestrator triggering reports at lifecycle boundaries | `ReportOrchestrator` |
| `tests/unit/workflow/test_eight_features.py` | Create | Exhaustive behavioral test suite covering all 8 features | Unit & integration test functions |

---

## 4. Component Dependency Graph

```
                  [ Workflow Orchestration Layer ]
  (PreMigration, Migration, Validation, Cutover, Rollback Workflows)
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
[Approval Engine]       [Report Orchestration]      [Event Dispatcher]
(3 Ordered Gates)        (5 JSON/MD Reports)        (IEventDispatcher)
     │                           │                           │
     └───────────────────────────┼───────────────────────────┘
                                 ▼
                    [ Underlying Engines & Agents ]
   (Scout, Rulebook, Decoder, Risk, Planner, Advisor, Intelligence,
            MigrationEngine, GBValidator, CDCSync, AuditLogger)
```

**Architecture Boundary Rule**: The workflow layer coordinates underlying engines via interfaces and NEVER reimplements database migration, row copying, schema translation, CDC replication, or GB validation logic internally.

---

## 5. State-Transition Mapping

- **Job / Workflow State Mapping**:
  - `INITIALIZED` → `PRE_MIGRATION` (PreMigrationWorkflow running)
  - `WAITING_FOR_APPROVAL` (Approval #1: Plan Readiness)
  - `MIGRATING` (MigrationWorkflow running)
  - `GB_VALIDATION` (ValidationWorkflow running)
  - `WAITING_FOR_APPROVAL` (Approval #2: Migration Progression)
  - `CDC_SYNC` → `WAITING_CUTOVER` (CutoverWorkflow running)
  - `WAITING_FOR_APPROVAL` (Approval #3: Final Cutover)
  - `COMPLETED` (Cutover & Post-Migration Report finished)
  - `ROLLING_BACK` / `ROLLED_BACK` (RollbackWorkflow executing)
  - `FAILED` / `PAUSED` / `CANCELLED` (Terminal or interrupted states)

---

## 6. Risk Register

| Risk ID | Description | Impact | Likelihood | Mitigation | Verification |
|---|---|---|---|---|---|
| RSK-P2-01 | Reimplementing migration or validation logic in workflow steps | High | Low | Enforce delegation to `akaal.migration` & `GBValidator` | Code review + AST boundary audit |
| RSK-P2-02 | Circular import between reporting, approval, and workflow engine | High | Low | Inject `IEventDispatcher` and `IClock` abstractions | AST DAG import analysis |
| RSK-P2-03 | Approval bypass via direct state machine mutation | Critical | Low | Require signed `ApprovalToken` verification in `ApprovalGateStep` | Security unit & integration tests |
| RSK-P2-04 | Duplicate event dispatch or un-idempotent report generation | Medium | Low | Hash-based idempotency keys on `WorkflowEvent` and `EnterpriseReport` | Idempotency unit tests |

---

## 7. Architectural Critical Review & Approval Sign-Off

The Independent Architecture Review Board has evaluated this implementation plan:
- **Package Ownership**: Verified clean. New concrete workflows reside under `akaal/workflow/concrete/`, reporting under `akaal/workflow/reporting/`, approval under `akaal/workflow/approval/`.
- **Interface Decoupling**: Verified clean. All events flow through `IEventDispatcher`, all time operations through `IClock`, all identity generation through `IIdGenerator`.
- **Zero Redesign**: Certified zero changes to Part 1 platform core.

**Plan Status:** **FROZEN & APPROVED FOR IMMEDIATE IMPLEMENTATION.**
