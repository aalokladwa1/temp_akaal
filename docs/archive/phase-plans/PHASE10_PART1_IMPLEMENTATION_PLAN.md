# AKAAL Phase 10 – Enterprise Workflow & Orchestration Platform
## Part 1: Platform Foundation & Architecture Plan
**Document Version:** 1.3.0 (Final Architecture Freeze)  
**Status:** Architecture Plan & Blueprint (Permanently Frozen & Approved by Enterprise Architecture Review Board - ARB)

---

## Executive Summary & ARB Architectural Rationale

This document presents the finalized architectural blueprint for **AKAAL Phase 10 - Part 1: Platform Foundation**. Following the final pass review by the Enterprise Architecture Review Board (ARB), this document incorporates three final architectural optimizations to permanently freeze the platform design before implementation.

### Summary of Final ARB Architectural Refinements

1. **Encapsulated `StepFactory` Inside `WorkflowStepRegistry`**:
   - *Rationale*: Exposing `StepFactory` to `WorkflowEngine` leaks internal instantiation details across subsystem boundaries. `WorkflowEngine` now interacts exclusively with `WorkflowStepRegistry`, which privately delegates step instantiation to an internal factory. This enforces zero leak of implementation details and minimizes coupling.

2. **Extended `ExecutionPipeline` Lifecycle with `on_success()` & `on_failure()` Hooks**:
   - *Rationale*: Mission-critical enterprise workflows require explicit, deterministic hooks following step execution for audit logging, metrics emission, alert notifications, resource cleanup, and compensation triggers. The pipeline now provides dedicated success (`on_success`) and failure (`on_failure`) branches before finalizing step execution or initiating rollbacks.

3. **Structured `WorkflowContext` Composition (Replacing Generic `state_data`)**:
   - *Rationale*: A single flat `state_data` mapping inevitably degrades into a unmaintainable, untyped property bag. `WorkflowContext` is now defined as a strongly-typed composition root containing three sub-contexts: `ExecutionContext`, `RuntimeContext`, and `UserContext`.

---

## 1. Platform Position & Boundary Governance

### Pipeline Sequence
```
Scout
  ↓
Rulebook
  ↓
Decoder
  ↓
Risk
  ↓
Planner
  ↓
Advisor
  ↓
Enterprise Intelligence
  ↓
Enterprise Workflow Platform (NEW)
  ↓
Migration Engine
```

### Boundary Isolation Rules
- **Enterprise Intelligence**: Responsible solely for decision-making, optimization, planning, and policy evaluation.
- **Enterprise Workflow Platform**: Responsible solely for state orchestration, execution coordination, state machine transitions, checkpointing, event dispatching, and crash recovery.
- **Strict Non-Responsibilities**: The Workflow Platform MUST NOT perform database queries/writes directly, run business rules, generate migration logic, execute target schema validations, or synthesize analytical reports.

---

## 2. Package & Subsystem Architecture

The Workflow Platform resides in `akaal/workflow/`. Package ownership is strictly segregated to form a Directed Acyclic Graph (DAG).

```
akaal/workflow/
├── api/                # Public Facade & Workflow Client Entrypoints
├── approval/           # Approval Token & Verification Contracts (Part 2 placeholder)
├── checkpoint/         # Checkpoint Models, Manager, & ICheckpointStorage
├── contracts/          # Structural Manifest & Step Contract Integrity
├── engine/             # WorkflowEngine Coordinator & State Machine Integration
├── events/             # Domain Event Definitions & IEventDispatcher Interface
├── exceptions/         # Standardized Workflow Exception Hierarchy
├── execution/          # StepExecutor, ExecutionPipeline, Retry & Timeout Policies
├── execution_records/  # Telemetry, Trace, & Execution Metrics Models
├── interfaces/         # Core Structural Interfaces (IStep, IEngine, IStrategy, ILock, IClock, IIdGenerator)
├── locks/              # Concurrency Control & Distributed Locking Contracts
├── models/             # Pure Immutable Frozen Dataclasses & Sub-Context Compositions
├── registry/           # WorkflowStepRegistry (Private StepFactory Encapsulation)
├── security/           # SecurityContext, RBAC & Audit Identity Interfaces
├── state_machine/      # WorkflowState Enum, TransitionGraph, & StateController
├── steps/              # Base Step Contracts & Reference Step Implementations
└── utils/              # Serializer, SHA-256 Hashing, Injected Clock & ID Generators
```

### Component Dependency Flow (Strict DAG)
```
[api] ──> [engine] ──> [execution] ──> [execution.pipeline] ──> [steps]
            │               │                 │                    │
            ▼               ▼                 ▼                    ▼
     [state_machine]  [checkpoint]    [registry / policies]   [interfaces]
            │               │                 │                    │
            └───────┬───────┴─────────────────┴────────────────────┘
                    ▼
      [models / contracts / security / exceptions / utils / execution_records]
```

---

## 3. Immutable Domain Models & Sub-Context Composition

All models are implemented as `frozen=True` dataclasses with slotted memory optimization, deterministic JSON serialization, and SHA-256 payload checksum protection.

### Sub-Context Composition Architecture (`WorkflowContext`)

Instead of a monolithic `state_data` mapping, `WorkflowContext` aggregates three distinct, strongly-typed sub-contexts:

```
                  ┌────────────────────────┐
                  │    WorkflowContext     │
                  │   (Composition Root)   │
                  └───────────┬────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ExecutionContext│      │ RuntimeContext│      │  UserContext  │
└───────────────┘      └───────────────┘      └───────────────┘
```

1. **`ExecutionContext`**:
   - `workflow_id: str`
   - `run_id: str`
   - `completed_steps: Tuple[str, ...]`
   - `pending_steps: Tuple[str, ...]`
   - `retry_counts: Mapping[str, int]`
   - `checkpoint_reference: Optional[str]`
   - `step_metrics: Mapping[str, float]`

2. **`RuntimeContext`**:
   - `environment_variables: Mapping[str, str]`
   - `transient_parameters: Mapping[str, Any]`
   - `runtime_flags: Mapping[str, bool]`
   - `temporary_state: Mapping[str, Any]`

3. **`UserContext`**:
   - `user_id: str`
   - `tenant_id: str`
   - `security_context: SecurityContext`
   - `granted_permissions: Tuple[str, ...]`
   - `correlation_id: str`
   - `trace_parent: Optional[str]`

4. **`WorkflowContext` (Composition Root)**:
   - `execution_context: ExecutionContext`
   - `runtime_context: RuntimeContext`
   - `user_context: UserContext`
   - `version: int` (Monotonically increasing sequence number)
   - `checksum: str` (SHA-256 hash of aggregated sub-contexts)

---

## 4. Workflow State Machine Architecture

### State Enumeration (`WorkflowState`)
- `CREATED`: Manifest initialized, unvalidated.
- `READY`: Validated DAG, prepared for execution.
- `RUNNING`: Actively processing steps.
- `PAUSING`: Transition state requested prior to pause.
- `PAUSED`: Execution safely suspended at step boundary.
- `WAITING_FOR_APPROVAL`: Halted pending external human approval token.
- `RECOVERING`: Hydrating from checkpoint following crash/restart.
- `COMPLETED`: All terminal steps finished successfully.
- `ROLLING_BACK`: Actively executing compensating rollback actions.
- `ROLLED_BACK`: Successfully completed rollback sequence.
- `FAILED`: Execution terminated with unrecoverable failure.
- `CANCELLED`: Explicitly aborted by user/system command.

### State Transition Graph Matrix
```
CREATED             ──> READY, CANCELLED
READY               ──> RUNNING, CANCELLED
RUNNING             ──> PAUSING, WAITING_FOR_APPROVAL, COMPLETED, ROLLING_BACK, FAILED, CANCELLED
PAUSING             ──> PAUSED, FAILED
PAUSED              ──> RUNNING (via Resume Action), CANCELLED
WAITING_FOR_APPROVAL──> RUNNING (via Resume/Approve Action), ROLLING_BACK, CANCELLED
RECOVERING          ──> READY, RUNNING, FAILED
ROLLING_BACK        ──> ROLLED_BACK, FAILED
COMPLETED           ──> (Terminal)
ROLLED_BACK         ──> (Terminal)
FAILED              ──> ROLLING_BACK, RECOVERING (via Retry Action), (Terminal)
CANCELLED           ──> (Terminal)
```

> **Rule**: Resume is an **ACTION** (invoked via `engine.resume()`), NOT a state. When `resume()` is called on a `PAUSED` or `WAITING_FOR_APPROVAL` workflow, the `StateController` validates and executes the transition back to `RUNNING`.

---

## 5. Extended Generic Step Interface (`IStep`)

Every workflow step MUST implement the extended `IStep` interface contract.

```python
class IStep(Protocol):
    @property
    def step_id(self) -> str: ...
    
    def initialize(self, context: WorkflowContext) -> None: ...
    
    def validate_preconditions(self, context: WorkflowContext) -> ValidationResult: ...
    
    def execute(self, context: WorkflowContext) -> WorkflowStepResult: ...
    
    def on_success(self, context: WorkflowContext, result: WorkflowStepResult) -> None: ...
    
    def on_failure(self, context: WorkflowContext, error: Exception) -> None: ...
    
    def validate_postconditions(self, context: WorkflowContext, result: WorkflowStepResult) -> ValidationResult: ...
    
    def checkpoint(self, context: WorkflowContext) -> WorkflowCheckpoint: ...
    
    def resume(self, checkpoint: WorkflowCheckpoint, context: WorkflowContext) -> WorkflowStepResult: ...
    
    def rollback(self, context: WorkflowContext) -> WorkflowStepResult: ...
    
    def cleanup(self, context: WorkflowContext) -> None: ...
```

---

## 6. Extended Execution Pipeline & Registry Architecture

### Step Execution Pipeline Lifecycle
Step lifecycle execution is governed by `ExecutionPipeline` inside `StepExecutor`. `WorkflowEngine` never invokes step methods directly.

#### Successful Execution Branch
```
initialize()
  ↓
validate_preconditions()
  ↓
execute()  [Subject to ITimeoutPolicy & IRetryPolicy]
  ↓
on_success()
  ↓
validate_postconditions()
  ↓
checkpoint()
  ↓
cleanup()  [Guaranteed in finally block]
```

#### Failure Execution Branch
```
initialize()
  ↓
validate_preconditions()
  ↓
execute()  [Failed / Retries Exhausted]
  ↓
on_failure()
  ↓
rollback()
  ↓
cleanup()  [Guaranteed in finally block]
```

### Encapsulated Registry & Private Factory Pattern
`WorkflowEngine` communicates ONLY with `WorkflowStepRegistry`. `StepFactory` is an internal private implementation detail of the registry (`_StepFactory`), preventing instantiation mechanics from leaking into the engine.

```
                  ┌─────────────────┐
                  │ WorkflowEngine  │
                  └────────┬────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │ WorkflowStepRegistry  │
               │  • register()         │
               │  • unregister()       │
               │  • resolve()          │
               │  • list_steps()       │
               └───────────┬───────────┘
                           │ (Internal & Private)
                           ▼
                  ┌─────────────────┐
                  │  _StepFactory   │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │      IStep      │
                  └─────────────────┘
```

---

## 7. Decoupled Event Dispatching Architecture

`WorkflowEngine` communicates domain state changes exclusively through the `IEventDispatcher` interface.

```python
class IEventDispatcher(Protocol):
    def dispatch(self, event: WorkflowEvent) -> None: ...
```

### Structural Event Architecture
```
WorkflowEngine ──> IEventDispatcher ──> Enterprise Event Bus ──> Event Handlers / Adapters
```

---

## 8. Deterministic Time & Identity Injection Architecture

To achieve 100% deterministic replayed execution, system calls for time, random values, and UUIDs are strictly banned from direct usage in workflow logic.

### Abstractions
1. **`IClock`**: Interface for time access (`now_utc()`, `monotonic()`).
2. **`IIdGenerator`**: Interface for identity generation (`generate_uuid()`, `generate_idempotency_key()`).

---

## 9. Checkpoint & Crash Recovery Architecture

### Persistence Contract (`ICheckpointStorage`)
- `save_checkpoint(checkpoint: WorkflowCheckpoint) -> None`
- `load_latest_checkpoint(workflow_id: str, run_id: str) -> Optional[WorkflowCheckpoint]`
- `load_checkpoint_by_id(checkpoint_id: str) -> Optional[WorkflowCheckpoint]`
- `list_checkpoints(workflow_id: str) -> Tuple[WorkflowCheckpoint, ...]`

### Concurrency Lease Contract (`IWorkflowLock`)
- `acquire_lock(workflow_id: str, ttl_seconds: int) -> bool`
- `release_lock(workflow_id: str) -> None`

---

## 10. Architectural Governance Rules

1. **Rule 1 - Pure Orchestration**: Workflow Platform orchestrates; it never performs business logic.
2. **Rule 2 - Interface Isolation**: Workflow Platform communicates only through abstract interfaces, never concrete implementations.
3. **Rule 3 - Zero Database Code**: No SQL, ORM, or database drivers within the workflow package.
4. **Rule 4 - Zero Migration Code**: Migration logic resides strictly within `akaal/migration/`.
5. **Rule 5 - Zero Validation Code**: Target data/schema validation rules reside in `akaal/decoder/` or `akaal/rulebook/`. Structural contract validation resides in `akaal/workflow/contracts/`.
6. **Rule 6 - Zero Report Generation**: Report building resides in dedicated reporting subsystems.
7. **Rule 7 - Zero Circular Dependencies**: Package hierarchy must form a strict Directed Acyclic Graph (DAG).
8. **Rule 8 - Isolated Testability**: Every step implementation must be testable in complete isolation without running the engine.
9. **Rule 9 - Strict Determinism**: Given the same manifest, seed, and input context, execution order and state transitions must be 100% deterministic. Time and random generators must be injected dependencies (`IClock`, `IIdGenerator`).
10. **Rule 10 - Total Resumability**: Every workflow must be capable of persisting state at step boundaries and resuming without data loss or duplicate execution side-effects.
11. **Rule 11 - Complete Auditability**: Every state transition, step result, error, and metadata change must produce an immutable trace record (`WorkflowExecutionTrace`).
12. **Rule 12 - Mandatory Versioning**: All manifests, contexts, and domain models must carry semantic version attributes.
13. **Rule 13 - Cryptographic Checksums**: All snapshots, manifests, and checkpoints must validate SHA-256 payload integrity before processing.

---

## 11. Comprehensive Architectural Verification Plan

### Test Suite Categories
1. **Package Dependency & DAG Tests**: Automated AST import analysis verifying zero circular dependencies and zero unauthorized cross-package imports.
2. **State Machine Invariant Tests**: Exhaustive permutation tests verifying all valid transitions succeed and all invalid transitions raise `InvalidStateTransitionException`.
3. **Immutability & Integrity Tests**: Verification that domain model modification attempts raise `FrozenInstanceError` and checksum mismatches raise `ChecksumMismatchException`.
4. **Interface Contract Compliance Tests**: Verification that Reference Step Implementations adhering to `IStep` execute seamlessly within `ExecutionPipeline` and `WorkflowEngine`.
5. **Deterministic Replay Tests**: Mock execution runs asserting identical execution traces across repeated runs using controlled `IClock` and `IIdGenerator`.
6. **Checkpoint & Recovery Tests**: Simulated crash injection mid-workflow; verifying recovery resumes from exact checkpoint step with zero duplicated step execution.
7. **Thread & Async Concurrency Tests**: Multi-threaded and `asyncio` concurrent execution tests verifying lock acquisition and thread-safe state changes.

---

## 12. Scope Boundaries & Implementation Restrictions

### Explicitly Excluded (Part 2 Scope)
- `PreMigrationWorkflow`
- `MigrationWorkflow`
- `ValidationWorkflow`
- `CutoverWorkflow`
- `RollbackWorkflow`
- Approval Engine concrete evaluation logic
- Workflow Distributed Event Bus integration (Kafka/RabbitMQ connectors)
- Analytical Report Orchestration rendering

---

## 13. Success Criteria for Part 1 Completion

✓ Directory structure `akaal/workflow/` established with clean subpackages including `contracts/`, `execution_records/`, `registry/`.  
✓ All domain models defined as immutable frozen dataclasses with sub-context composition (`ExecutionContext`, `RuntimeContext`, `UserContext`).  
✓ State machine transition graph implemented with explicit pause/resume/recovery semantics.  
✓ Generic `IStep` interface contract finalized with `on_success()` and `on_failure()` hooks.  
✓ `ExecutionPipeline` implemented to handle both success and failure branching logic.  
✓ `WorkflowStepRegistry` encapsulates factory logic; `_StepFactory` hidden from `WorkflowEngine`.  
✓ `IRetryPolicy` and `ITimeoutPolicy` interfaces defined.  
✓ Deterministic dependencies `IClock` and `IIdGenerator` injected throughout engine and pipeline.  
✓ `ICheckpointStorage` abstraction and local file/memory adapters created.  
✓ Reference Step Implementations provided for architectural contract testing.  
✓ Complete unit and architecture test suites passing with 100% contract compliance.  
✓ Zero architectural violations detected by automated linting and AST dependency checkers.  
✓ Architecture permanently frozen and signed off for Part 2 concrete workflow implementation.
