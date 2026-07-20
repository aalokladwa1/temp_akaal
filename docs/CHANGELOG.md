# CHANGELOG - AKAAL Platform

## [Unreleased] - Phase 10 Part 1

### Added
- **AKAAL Workflow Platform Foundation (`akaal/workflow/`)**:
  - `api`: `WorkflowClient` public facade.
  - `checkpoint`: `CheckpointManager`, `ICheckpointStorage` repository interface, `InMemoryCheckpointStorage`, `FileBasedCheckpointStorage`.
  - `contracts`: `ManifestValidator` with DAG acyclicity cycle detection and `StepDefinitionValidator`.
  - `engine`: `WorkflowEngine` coordinator facade supporting execute, pause, resume, cancel, and rollback.
  - `events`: `WorkflowEvent`, `WorkflowStateChangedEvent`, `StepExecutedEvent`, `IEventDispatcher`, and `InMemoryEventDispatcher`.
  - `exceptions`: Complete `WorkflowException` hierarchy.
  - `execution`: `StepExecutor`, `ExecutionPipeline` with `on_success()` & `on_failure()` branching, `IRetryPolicy` (Exponential, Fixed, NoRetry), and `ITimeoutPolicy` (Fixed, NoTimeout).
  - `execution_records`: `WorkflowExecutionTrace`, `WorkflowMetrics`, `StateTransitionRecord`.
  - `interfaces`: `IStep`, `IEngine`, `IExecutionStrategy`, `IWorkflowLock`, `IClock`, `IIdGenerator`.
  - `locks`: `InMemoryLock` lease lock.
  - `models`: `ExecutionContext`, `RuntimeContext`, `UserContext`, `WorkflowContext` (composition root), `WorkflowMetadata`, `StepDefinition`, `WorkflowManifest`, `WorkflowCheckpoint`, `WorkflowStepResult`.
  - `registry`: `WorkflowStepRegistry` with private `_StepFactory` encapsulation.
  - `security`: `SecurityContext` model for tenant isolation and RBAC.
  - `state_machine`: `WorkflowState` enum (12 explicit states), `TransitionGraph`, `StateController`.
  - `steps`: `AbstractStep`, `ReferencePassStep`, `ReferenceFailStep`, `ReferencePreconditionFailStep`.
  - `utils`: `SystemClock`, `FixedClock`, `UUIDIdGenerator`, `DeterministicIdGenerator`, canonical JSON serialization & SHA-256 hash calculation.
- **Verification Suites**:
  - `tests/unit/workflow/`: Test coverage for models, state machine, pipeline, registry, checkpoints, determinism, engine facade, and AST DAG import verification.
