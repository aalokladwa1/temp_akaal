# Changelog

All notable changes to the Akaal Enterprise Orchestration Platform are documented in this file.

## [1.6.1] - Post Stage 3 Enterprise Foundation Freeze (2026-07-24)

### Certified Baseline
- **Enterprise Foundation Freeze**: Certified Stage 3 completion and frozen foundation baseline (`v0.10-stage3-certified`).
- **Hygiene & Verification Audit**: Audited repository hygiene, verified package boundaries, configuration integrity, and dependency security.
- **Evidence & Performance Baseline**: Preserved Stage 3 Flagship 10M+ row migration evidence (100% Merkle match, 0 delta) and published `PHASE10_BASELINE.md`.
- **Documentation & Manifest Freeze**: Created `REPOSITORY_HYGIENE.md`, `ARCHITECTURE_REVIEW.md`, `CONFIGURATION_AUDIT.md`, `DEPENDENCY_AUDIT.md`, `TECHNICAL_DEBT.md`, `RELEASE_NOTES.md`, and `FOUNDATION_FREEZE_MANIFEST.md`.

## [1.6.0] - Phase 10 Enterprise Cross-Platform Integration (2026-07-22)

### Added
- **Enterprise Composition Root (`akaal/integration/composition_root.py`)**:
  - `EnterpriseLifecycleManager`: Central lifecycle coordinator managing registration, startup validation, topological initialization, and graceful shutdown across all 9 AKAAL platforms.
  - `PlatformRegistry`: Thread-safe, read-only registry tracking platform metadata, public facades, versions, health, capabilities, and dependencies.
  - `DependencyGraph`: Topological ordering engine detecting circular dependencies and computing safe platform startup order.
  - `HealthRegistry`: Unified health aggregator checking facade responsiveness and status across all platforms.
  - `CrossPlatformContext`: Application runtime context exposing active public facade instances.
  - `execute_e2e_smoke_test`: End-to-end integration smoke test executing unified lifecycles across Platforms 1 through 9 strictly using public facade contracts.
- **Tests**: `tests/integration/composition/test_enterprise_composition_root.py` validating registration, dependency graph, cycle detection, health aggregation, and smoke test execution.
- **Documentation**: `AKAAL_ENTERPRISE_INTEGRATION_WALKTHROUGH.md`, `AKAAL_PLATFORM_COMPOSITION_REPORT.md`, `AKAAL_CROSS_PLATFORM_VERIFICATION_REPORT.md`.

### Fixed
- **Human Approval Request ID Consistency (`akaal/workflow/approval/`)**:
  - Resolved identifier lookup mismatch where `ApprovalGateStep` reconstructed request IDs (`req_<wf>_gate_<num>`) while `ApprovalEngine` generated UUIDs.
  - Implemented `ApprovalEngine.get_request_for_gate(workflow_id, gate_number)` and `self._gate_requests` index ensuring single canonical approval request identity and 100% duplicate request prevention.
  - Added unit test `tests/unit/workflow/test_approval_request_id_consistency.py`.

## [1.5.0] - Phase 10 Platform 9 Enterprise Operations Platform (2026-07-22)

### Added
- **Operations Package (`akaal/operations/`)**:
  - `facade/platform9.py`: Central Public Entry Point (`DefaultOperationsPlatformV9`).
  - `capability_registry/`: Operations Capability Registry dynamically discovering advertised platform capabilities via public facade contracts.
  - `digital_twin/`: Real-time operational model tracking nodes, workers, active jobs, dependencies, health, and incidents.
  - `topology/`: Enterprise Topology Engine mapping parent-child system hierarchies (AKAAL -> Cluster -> Node -> Worker -> Platform -> Job).
  - `discovery/`: Cluster Discovery Service populating the Digital Twin and Capability Registry.
  - `session/`: Operations Session Manager tracking administrative activities in immutable session records.
  - `workflow/`: Operational Workflow Engine executing runbook procedures with step validation and automatic rollback.
  - `approvals/`: Enterprise Approval Manager enforcing single/multi-person approvals, emergency overrides, and timeouts.
  - `health/`: Operations Health Engine computing weighted system health scores across platforms.
  - `observability/`: Unified Observability Collector aggregating OpenTelemetry traces, Prometheus metrics, logs, and correlation IDs.
  - `monitoring/`: Operations Center providing real-time dashboard overviews.
  - `alerts/`: Alert Engine with threshold, predictive, failure, SLA warnings, deduplication, suppression, and grouping.
  - `plugins/`: Notification Framework with Email, Slack, Teams, PagerDuty, and Webhook providers.
  - `incidents/`: Incident Lifecycle Manager enforcing strict state machine transitions (`Detected` -> `Classified` -> `Assigned` -> `Investigating` -> `Mitigating` -> `Recovering` -> `Verifying` -> `Resolved` -> `Closed`).
  - `diagnostics/`: Diagnostics & Root Cause Analysis Engine correlating timeline events and dependency blast radii.
  - `recommendations/`: Operational Recommendation Engine generating explainable advisory guidance (never auto-executing).
  - `control/`: Operations Control Plane delegating `pause`, `drain`, `emergency_stop` actions to public platform facades.
  - `policy/`: Operations Policy Engine governing maintenance windows and action restrictions.
  - `versioning/`: Configuration Version Manager version-controlling policies, rules, and alert thresholds with rollback.
  - `scheduler/`: Operations Scheduler executing periodic internal housekeeping tasks.
  - `replay/`: Operations Replay Engine providing read-only playback of operational timelines and incident histories.
  - `timeline/`: Chronological Operational Timeline recording events with correlation IDs and timestamps.
  - `governance/`: Governance & Audit Center creating immutable, tamper-evident SHA-256 hash-chained audit logs.
  - `forecasting/`: SLA, Capacity & Forecasting Engine predicting resource exhaustion and SLA breach risks.
  - `security/`: Operational Security Engine enforcing RBAC permissions (`SuperAdmin`, `Operator`, `Auditor`, `Viewer`), signature verification, and action signing.
  - `verification/`: Architecture Boundary Verifier ensuring Platform 9 never imports internal modules of Platforms 1–8.
- **Tests**: 15 unit and integration test suites covering all Platform 9 capabilities, state machines, and boundary isolations. 100/100 tests passing cleanly.

## [1.4.0] - Platform 8 Enterprise Reporting Engine (2026-07-22)

### Added
- **Enterprise Reporting Engine (`akaal/reporting/`)**:
  - Implemented all 8 reporting capabilities: Pre-Migration, Migration Progress, GB Validation, Cutover, Post-Migration, Executive Summary, Audit Package Generator, and Report Versioning.
  - **Exporters (`akaal/reporting/exporters/`)**: PDF, HTML, JSON, and CSV exporters implementing abstract `IReportExporter`.
  - **Template Engine (`akaal/reporting/templates/`)**: Structured HTML, JSON, CSV, and Markdown rendering engine.
  - **Digital Signing (`akaal/reporting/signing/`)**: `ISigningProvider` abstraction with `NoSigningProvider`, `HashSigningProvider` (HMAC SHA-256), and `X509SigningProvider` (X.509 PKCS#7/CMS digital signatures).
  - **Metadata & Versioning (`akaal/reporting/metadata/`, `akaal/reporting/versioning/`)**: `MetadataManager` (correlation ID injection & SHA-256 checksums) and `ReportVersionManager` (semantic versioning & history).
  - **Audit Package Builder (`akaal/reporting/audit/`)**: `AuditPackageBuilder` generating multi-report audit packages with hash-chained `manifest.json` signatures.
  - **Public Facades (`akaal/reporting/api/`)**: `ReportingClient`, `IPlatform8Facade`, `Platform8Facade`, and Platform 7 wrapper integration.
  - **Test Suite**: 67 unit, integration, and AST static architecture conformance tests passing cleanly.

## [1.3.0] - Platform 4 Enterprise CDC (2026-07-22)

### Added
- **Enterprise CDC Platform (`akaal/cdc/`)**:
  - Implemented all 9 core CDC capabilities: Distributed CDC, Remote CDC, Multi-Source CDC, Multi-Target CDC, CDC Routing, CDC Replay, CDC Buffering, CDC Checkpoint Synchronization, and Live Failover Synchronization.
  - **Sources Adapters (`akaal/cdc/sources/`)**: PostgreSQL WAL, MySQL Binlog, Oracle LogMiner, SQL Server CDC, MongoDB Change Streams, and Trigger Fallback.
  - **Targets Adapters (`akaal/cdc/targets/`)**: Generic Database Target Adapter applying events idempotently.
  - **Transport Engine (`akaal/cdc/transport/`)**: Transport abstraction `ICDCTransport` with `InMemoryCDCTransport`, `KafkaCDCTransport`, and `RabbitMQCDCTransport`.
  - **Routing & Durable Buffering (`akaal/cdc/routing/`, `akaal/cdc/buffering/`)**: `CDCRoutingEngine` rule-based policy router, `DurableCDCBuffer` with per-table transaction ordering, and `DeadLetterQueue` (DLQ).
  - **Checkpoint Stores (`akaal/cdc/checkpoint/`)**: `ICheckpointStore` abstraction with `MemoryCheckpointStore`, `DatabaseCheckpointStore`, `RedisCheckpointStore`, and `FileCheckpointStore`.
  - **Replay & Failover (`akaal/cdc/replay/`, `akaal/cdc/failover/`)**: `CDCReplayEngine` with `ExactlyOnceController` deduplication and `CDCFailoverCoordinator` worker lease recovery.
  - **Public Facades (`akaal/cdc/api/`)**: `CDCClient`, `IPlatform4Facade`, `Platform4Facade`, and Platform 7 wrapper integration.
  - **Test Suite**: 52 unit, integration, and AST static architecture conformance tests passing cleanly.

## [1.2.0] - Platform 7 Enterprise APIs & Integration (2026-07-22)

### Added
- **Enterprise APIs & Integration (`akaal/api/`)**:
  - Implemented all 8 capabilities of Platform 7 — Enterprise APIs & Integration (REST API, gRPC API, Typer CLI, Python SDK, Config Profiles, YAML Definitions, Transactional Outbox Events, Webhook Engine, Sandboxed Plugin Manager).
<<<<<<< HEAD
=======
>>>>>>> 721b546 (feat(platform4): implement enterprise CDC platform)
>>>>>>> 4388da0

## [1.1.0] - Phase 10 Platform 5 Live Schema Evolution (2026-07-21)

### Added
- **Live Schema Evolution Platform (`akaal/schema/`)**:
  - Implemented all 8 capabilities of Platform 5 — Live Schema Evolution (Metadata Version Control, Dynamic Refresh, Schema Compatibility Analysis, Online Type Evolution, Live Schema Evolution, Online DDL Propagation, Constraint Evolution, DDL Replay) with 12 mandatory enterprise architecture improvements.
  - **Enterprise Schema Transactions** (`akaal/schema/transactions/`): `SchemaTransaction`, `TransactionManager`, `TransactionStore`, nested transactions, atomic rollback plans.
  - **Immutable Operation Journal** (`akaal/schema/replay/`): Append-only `JournalStore` with SHA-256 hash-chaining and tamper detection.
  - **Metadata Version Graph** (`akaal/schema/versioning/`): `MetadataVersionManager`, `SchemaSnapshot` with zlib compression, `VersionDAG` graph, 3-way `VersionMergeEngine`.
  - **Strongly Typed Schema Change Model** (`akaal/schema/domain/changes.py`): 20+ strongly-typed change classes (`AddTable`, `ModifyColumn`, `ChangeForeignKey`, etc.).
  - **Constraint Dependency Graph** (`akaal/schema/graph/`): `ConstraintDependencyGraph` with Tarjan topological cycle-free sorting.
  - **5-Stage Validation Pipeline** (`akaal/schema/validation/`): `ValidationPipeline` (Syntax, Dependency, Compatibility, Execution Pre-Check, Post-Execution) producing `DiagnosticReport`.
  - **Enterprise Concurrency & Recovery** (`akaal/schema/concurrency/`, `akaal/schema/recovery/`): `SchemaLockManager`, OCC, `DeadlockDetector`, `RecoveryManager` 7-class failure recovery.
  - **Enterprise Observability & Telemetry** (`akaal/schema/observability/`): `SchemaTracer` (Correlation/Tx/Replay IDs), `StructuredAuditLogger`, `SchemaMetricsCollector`, and `SchemaEventPublisher`.
  - **Public Platform Facade** (`akaal/schema/facade/platform5.py`): `SchemaEvolutionPlatformV5` high-level public interface.
  - **Test Suite**: 26 unit and integration test suites passing with 100% success rate.

## [1.0.0] - Phase 10 Platforms 1–3 Cross-Platform Integration (2026-07-21)

### Added
- **Cross-Platform Integration Engine (`akaal/integration/`)**:
  - `CrossPlatformIntegrationEngine`: End-to-end integration engine bridging **Platform 1 (Workflow Orchestration Engine)**, **Platform 2 (Distributed Runtime)**, and **Platform 3 (Zero-Copy Streaming Execution Engine)**.
  - End-to-end orchestration flow: Platform 1 job submission -> Platform 2 task scheduling & worker lease negotiation -> Platform 3 zero-copy stream pipeline processing -> Platform 1 audit logging & checkpointing.
- **Cross-Platform Integration Test Suite (`tests/integration/platforms/`)**:
  - `test_cross_platform_happy_path.py`: Scenario 1 — End-to-End Happy Path Validation.
  - `test_cross_platform_concurrency_and_load.py`: Scenario 2 & 7 — Concurrent Jobs & Stress Load Integration.
  - `test_cross_platform_backpressure.py`: Scenario 3 — Backpressure Propagation across Platforms 1–3.
  - `test_cross_platform_failures_and_retry.py`: Scenario 4 — Platform 3 Failure Injection & Platform 2 Retry Integration.
  - `test_cross_platform_cancellation.py`: Scenario 5 — Job Cancellation Propagation.
  - `test_cross_platform_checkpoint_resume.py`: Scenario 6 — Checkpoint Restoration & Resumed Execution.
  - `test_cross_platform_boundaries.py`: Scenario 8 — Architectural Isolation Checks.

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
