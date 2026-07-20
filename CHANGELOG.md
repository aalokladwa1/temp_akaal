# Changelog

All notable changes to the Akaal Enterprise Orchestration Platform are documented in this file.

## [Unreleased] - Phase 10 Day 9 (2026-07-20)

### Added
- **Orchestration Package (`akaal/orchestration/`)**:
  - `domain/`: Strongly-typed Value Objects (`JobId`, `WorkflowId`, `SessionId`, `ConfigurationId`, `Version`, `Checksum`, `AuditMetadata`), `EngineState`, `WorkflowStepName`, and enterprise exception hierarchy (`WorkflowError` base).
  - `models/`: Immutable `MigrationJob` domain model with SHA-256 integrity checksum calculation and version incrementing methods.
  - `events/`: Transport-agnostic `EventPublisher` and `EventSubscriber` interfaces, `InProcessEventDispatcher` implementation, and domain events (`WorkflowStarted`, `WorkflowCompleted`, `WorkflowFailed`, `WorkflowRecovered`, `StateTransitioned`, `StepStarted`, `StepCompleted`, `CheckpointCreated`, `ApprovalRequested`).
  - `audit/`: `WorkflowAuditLogger` producing append-only, SHA-256 checksummed `AuditRecord` entries.
  - `session/`: `WorkflowSession` model supporting node/worker ownership, lease timeouts, heartbeats, exclusive locking, cryptographically derived resume tokens, crash detection, and graceful closure.
  - `config/`: `UnifiedConfigurationManager` & `FrozenConfiguration` with 5-level precedence (Default -> YAML -> Env -> CLI -> Runtime), schema validation, versioning, and SHA-256 checksum verification.
  - `repository/`: Storage-agnostic repository interfaces (`WorkflowRepository`, `SessionRepository`, `CheckpointRepository`, `AuditRepository`) and thread-safe `InMemoryRepository` implementations.
  - `workflow/`: `WorkflowContext` parameter object, `WorkflowStep` abstract base class mandating full lifecycle contract (`initialize`, `validate`, `execute`, `checkpoint`, `resume`, `rollback`, `cleanup`), and `WorkflowDefinition` blueprint.
  - `checkpoint/`: Immutable, versioned, timestamped, SHA-256 checksummed `WorkflowCheckpoint`.
  - `engine/`: Split coordinators (`StateController`, `StepExecutor`, `CheckpointCoordinator`, `SessionCoordinator`, `ApprovalCoordinator`, `AuditCoordinator`, `RecoveryCoordinator`, `MetricsCollector`) and `WorkflowEngine` facade.
- **Tests**:
  - Added 19 comprehensive unit and integration tests covering domain types, state machine transition validation, session heartbeats/leases/crash detection, 5-level configuration precedence, repositories, engine execution, approval pauses, deterministic replay, and recovery safety.
