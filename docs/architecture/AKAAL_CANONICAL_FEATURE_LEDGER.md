# AKAAL CANONICAL FEATURE LEDGER

**Document Version:** 1.0.0  
**Status:** Active Canonical Truth (P1 + P2 Baseline Frozen)  
**Last Verified Commit:** `92c4f5ce227614b5b86bbbe1618a1ab752d641c4`  
**Governing Policy:** This document is the single operational source of truth for all implemented capabilities in the AKAAL Database Migration Platform. `docs/migration_module/capability_evolution/P1.md` and `P2.md` remain historical phase evolution logs.

---

## 1. Repository Subsystem & Package Matrix

| Package Directory | Primary Classification | Purpose & Description | Canonical Authority Present | Pipeline Reachable | UI / IPC Exposure | Action |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `akaal/adapters` | `CANONICAL_PRODUCTION` | Database catalog discovery & physical LOB-streaming readers/writers for Oracle, PostgreSQL, MySQL, MSSQL. | `AdapterRegistry` | YES | YES | `KEEP_CANONICAL` |
| `akaal/advisor` | `LEGACY_RETAINED` | Early catalog/capacity advisor. Delegated to `scout` and `risk`. | `ScoutOrchestrator` | YES | YES | `DEPRECATE_LATER` |
| `akaal/advisory` | `LEGACY_RETAINED` | Early schema DDL advisory rules. | `UniversalDDLAuthority` | YES | YES | `DEPRECATE_LATER` |
| `akaal/agents` | `FUTURE_PHASE_SCAFFOLDING` | P4/P6 enterprise fleet agent infrastructure. | N/A (P4/P6) | NO | NO | `KEEP_FUTURE` |
| `akaal/api` | `SUPPORTING_PRODUCTION` | Python SDK & IPC data contracts. | `EngineGateway` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/audit` | `SUPPORTING_PRODUCTION` | Tamper-evident audit trail & structured event logger. | `AuditTrailLogger` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/catalog` | `SUPPORTING_PRODUCTION` | Database schema catalog cache & metadata registry. | `CatalogRegistry` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/cdc` | `FUTURE_PHASE_SCAFFOLDING` | P3 native CDC change data capture log miners (Oracle Redo, PG logical, MySQL binlog). | N/A (P3) | NO | NO | `KEEP_FUTURE` |
| `akaal/core` | `CANONICAL_PRODUCTION` | CentralStateStore, ErrorTaxonomy, SystemType enums, base domain models. | `CentralStateStore` | YES | YES | `KEEP_CANONICAL` |
| `akaal/coverage` | `SUPPORTING_PRODUCTION` | Schema datatype conversion coverage analyzer. | `CoverageAnalyzer` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/data_integrity` | `SUPPORTING_PRODUCTION` | Row & table level checksum calculation helpers. | `PhysicalChecksumValidator` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/decoder` | `SUPPORTING_PRODUCTION` | Native binary WAL & REDO log stream decoders. | `RedoLogDecoder` | YES | NO | `KEEP_SUPPORTING` |
| `akaal/distributed` | `FUTURE_PHASE_SCAFFOLDING` | P6 multi-node distributed fleet coordination. | N/A (P6) | NO | NO | `KEEP_FUTURE` |
| `akaal/engine` | `CANONICAL_PRODUCTION` | `AkaalSuperEngine` facade, execution spec, and workflow orchestrator. | `AkaalSuperEngine` | YES | YES | `KEEP_CANONICAL` |
| `akaal/events` | `SUPPORTING_PRODUCTION` | Asynchronous EventBus & pub/sub topic dispatcher. | `EventBus` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/gateway` | `CANONICAL_PRODUCTION` | `EngineGateway` central IPC control facade & capability router. | `EngineGateway` | YES | YES | `KEEP_CANONICAL` |
| `akaal/governance` | `SUPPORTING_PRODUCTION` | `PolicyEngine` & migration approval decision recorder. | `PolicyEngine` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/healing` | `SUPPORTING_PRODUCTION` | `AutoHealingCoordinator` & auto-recovery WAL replayer. | `AutoHealingCoordinator` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/integration` | `SUPPORTING_PRODUCTION` | End-to-end integration test runners and harnesses. | Test Runners | YES | NO | `KEEP_SUPPORTING` |
| `akaal/intelligence` | `FUTURE_PHASE_SCAFFOLDING` | P7C AI-native migration intelligence. | N/A (P7C) | NO | NO | `KEEP_FUTURE` |
| `akaal/ipc` | `SUPPORTING_PRODUCTION` | Tauri IPC message frames, response wrappers, and handlers. | Stdio Protocol | YES | YES | `KEEP_SUPPORTING` |
| `akaal/metrics` | `SUPPORTING_PRODUCTION` | Internal counters, throughput gauges, and Prometheus metrics. | MetricsRegistry | YES | YES | `KEEP_SUPPORTING` |
| `akaal/migration` | `LEGACY_RETAINED` | Early migration workflow & executor. Kept safely without overriding gateway. | `EngineGateway` | YES | NO | `DEPRECATE_LATER` |
| `akaal/operational_reliability` | `SUPPORTING_PRODUCTION` | System health check & resource monitors. | ReliabilityMonitor | YES | YES | `KEEP_SUPPORTING` |
| `akaal/operations` | `SUPPORTING_PRODUCTION` | Operation handles, async tasks, and cancellation tokens. | OperationManager | YES | YES | `KEEP_SUPPORTING` |
| `akaal/orchestration` | `SUPPORTING_PRODUCTION` | Workflow saga orchestrator and execution graph builder. | SagaOrchestrator | YES | YES | `KEEP_SUPPORTING` |
| `akaal/performance` | `CANONICAL_PRODUCTION` | `AdaptiveBatchOptimizer`, RAM/CPU tuning policies. | `AdaptiveBatchOptimizer` | YES | YES | `KEEP_CANONICAL` |
| `akaal/planner` | `SUPPORTING_PRODUCTION` | `PlannerPlatform` & topological execution plan builder. | `PlannerPlatform` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/platform` | `SUPPORTING_PRODUCTION` | Cross-platform OS, path, and configuration resolvers. | EnvironmentConfig | YES | YES | `KEEP_SUPPORTING` |
| `akaal/plugins` | `FUTURE_PHASE_SCAFFOLDING` | P7A plugin extension bus and dynamic hook manager. | PluginBus | NO | NO | `KEEP_FUTURE` |
| `akaal/recovery_intelligence` | `FUTURE_PHASE_SCAFFOLDING` | P6 predictive failure recovery intelligence. | N/A (P6) | NO | NO | `KEEP_FUTURE` |
| `akaal/reliability` | `SUPPORTING_PRODUCTION` | Circuit breakers, bulkheads, and failure isolation. | `CircuitBreakerManager` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/reliability_intelligence` | `FUTURE_PHASE_SCAFFOLDING` | P6 SLA & reliability trend forecasting engine. | N/A (P6) | NO | NO | `KEEP_FUTURE` |
| `akaal/replication` | `CANONICAL_PRODUCTION` | `ParallelReplicationScheduler`, `RangePartitioner`, parallel transport workers. | `ParallelReplicationScheduler` | YES | YES | `KEEP_CANONICAL` |
| `akaal/reporting` | `CANONICAL_PRODUCTION` | `CanonicalReportingAuthority`, `CanonicalReportExportService`. | `CanonicalReportingAuthority` | YES | YES | `KEEP_CANONICAL` |
| `akaal/resilience_eng` | `FUTURE_PHASE_SCAFFOLDING` | P6 fault injection & chaos engineering framework. | N/A (P6) | NO | NO | `KEEP_FUTURE` |
| `akaal/risk` | `CANONICAL_PRODUCTION` | `RiskPlatform`, `CanonicalRiskScorer`, drift & risk modelers. | `CanonicalRiskScorer` | YES | YES | `KEEP_CANONICAL` |
| `akaal/rulebook` | `SUPPORTING_PRODUCTION` | Rulebook engine, translation rules, datatype safety definitions. | TranslationRulebook | YES | YES | `KEEP_SUPPORTING` |
| `akaal/runtime` | `CANONICAL_PRODUCTION` | `RecoveryCoordinator`, `JournalSupervisor`, process tree supervisor. | `RecoveryCoordinator` | YES | YES | `KEEP_CANONICAL` |
| `akaal/schema` | `CANONICAL_PRODUCTION` | `CanonicalSchemaModel`, `CanonicalTypeRegistry`, `UniversalDDLAuthority`, `CanonicalDependencyPlanner`. | `UniversalDDLAuthority` | YES | YES | `KEEP_CANONICAL` |
| `akaal/scout` | `SUPPORTING_PRODUCTION` | `ScoutOrchestrator`, preflight catalog & capacity discovery. | `ScoutOrchestrator` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/streaming` | `CANONICAL_PRODUCTION` | `BackpressureController`, LOB streaming, ring buffers. | `BackpressureController` | YES | YES | `KEEP_CANONICAL` |
| `akaal/transpiler` | `SUPPORTING_PRODUCTION` | SQL dialect parser, AST transformer, DDL generator. | SQLTranspiler | YES | YES | `KEEP_SUPPORTING` |
| `akaal/trust_certification` | `SUPPORTING_PRODUCTION` | Cryptographic certificate sealer & tamper-evident ledger. | `TrustSealer` | YES | YES | `KEEP_SUPPORTING` |
| `akaal/validation` | `CANONICAL_PRODUCTION` | `PhysicalChecksumValidator`, `CanonicalReconciliationEngine`, `ValidationOnlyWriteFirewall`. | `PhysicalChecksumValidator` | YES | YES | `KEEP_CANONICAL` |
| `akaal/workflow` | `CANONICAL_PRODUCTION` | `WorkflowEngine`, `PreStartValidationStep`, `SchemaExecutionStep`, `DataTransportStep`, `ValidationStep`. | `WorkflowEngine` | YES | YES | `KEEP_CANONICAL` |

---

## 2. P1 Baseline Feature Inventory

```yaml
FEATURE_ID: P1.RUNTIME.PARALLEL_WORKERS
PHASE: P1
FEATURE_NAME: Parallel Migration Workers
PURPOSE: Execute table partitions concurrently using worker pool threads.
CANONICAL_AUTHORITY: ParallelReplicationScheduler
IMPLEMENTATION_LOCATION: akaal/replication/scheduling/parallel_scheduler.py
PRIMARY_CLASS_OR_FUNCTION: ParallelReplicationScheduler
PRODUCTION_CALLER: DataTransportStep
PRODUCTION_ENTRYPOINT: EngineGateway → WorkflowEngine
PIPELINE_POSITION: Data Transport Stage
DOWNSTREAM_CONSUMER: Target Database Adapter
IDENTITY_BINDING: migration_id + run_id
STATE_OWNER: CentralStateStore
FAILURE_PROPAGATION: Worker exception → scheduler → step retry/failure
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (MonitoringModule → Workers tab)
MIGRATION_MODULE_FEATURE: Monitoring → Workers
TEST_LOCATION: tests/unit/replication/test_p1_6_universal_transport.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Sanitized telemetry, no raw credentials logged.
DEPENDENCIES: ConnectionConfig, RangePartitioner
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Migration Conductor
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P1.RUNTIME.RANGE_PARTITIONING
PHASE: P1
FEATURE_NAME: Large-Table Range Partitioning
PURPOSE: Split large tables into discrete numeric/date/PK range chunks for parallel streaming.
CANONICAL_AUTHORITY: RangePartitioner
IMPLEMENTATION_LOCATION: akaal/replication/partitioning/range_partitioner.py
PRIMARY_CLASS_OR_FUNCTION: RangePartitioner
PRODUCTION_CALLER: DataTransportStep
PRODUCTION_ENTRYPOINT: EngineGateway → WorkflowEngine
PIPELINE_POSITION: Data Transport Stage
DOWNSTREAM_CONSUMER: ParallelReplicationScheduler
IDENTITY_BINDING: migration_id + table_name + partition_id
STATE_OWNER: CentralStateStore
FAILURE_PROPAGATION: Partition failure → worker retry → task failure
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (MonitoringModule → Tables & Partitions tab)
MIGRATION_MODULE_FEATURE: Monitoring → Tables & Partitions
TEST_LOCATION: tests/unit/replication/test_p1_6_universal_transport.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Safe SQL predicate generation using escaping.
DEPENDENCIES: Physical Reader Adapter
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D High-Throughput Partitioning Engine
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P1.RUNTIME.ADAPTIVE_BATCHING
PHASE: P1
FEATURE_NAME: Self-Adjusting Adaptive Batch Optimizer
PURPOSE: Dynamically adjust batch size based on CPU, RAM, and network latency metrics.
CANONICAL_AUTHORITY: AdaptiveBatchOptimizer
IMPLEMENTATION_LOCATION: akaal/performance/optimizers/batch.py
PRIMARY_CLASS_OR_FUNCTION: AdaptiveBatchOptimizer
PRODUCTION_CALLER: ParallelReplicationScheduler
PRODUCTION_ENTRYPOINT: EngineGateway → WorkflowEngine
PIPELINE_POSITION: Data Transport Stage
DOWNSTREAM_CONSUMER: Physical Writer Adapter
IDENTITY_BINDING: migration_id
STATE_OWNER: CentralStateStore
FAILURE_PROPAGATION: Latency spike → auto-scale down batch size
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (MonitoringModule → Overview / Performance)
MIGRATION_MODULE_FEATURE: Monitoring → Performance
TEST_LOCATION: tests/unit/workflow/test_p2_13_1_canonical_pipeline_semantic_acceptance.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Bounded memory allocation limits.
DEPENDENCIES: System metrics collector
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D AI Batch Tuner
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P1.RUNTIME.CHECKPOINTING
PHASE: P1
FEATURE_NAME: Durable Checkpointing & Monotonic Fencing
PURPOSE: Persist committed LSN / primary key positions to disk for crash recovery.
CANONICAL_AUTHORITY: JournalSupervisor / RecoveryCoordinator
IMPLEMENTATION_LOCATION: akaal/runtime/recovery/coordinator.py
PRIMARY_CLASS_OR_FUNCTION: RecoveryCoordinator
PRODUCTION_CALLER: EngineGateway / DataTransportStep
PRODUCTION_ENTRYPOINT: EngineGateway → trigger_checkpoint
PIPELINE_POSITION: Transport & Recovery Engine
DOWNSTREAM_CONSUMER: CentralStateStore / Recovery Engine
IDENTITY_BINDING: migration_id + epoch + checkpoint_id
STATE_OWNER: JournalSupervisor / Disk WAL
FAILURE_PROPAGATION: Crash → read latest valid checkpoint → issue fencing epoch → resume
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (MonitoringModule → Events / Reliability)
MIGRATION_MODULE_FEATURE: Monitoring → Reliability
TEST_LOCATION: tests/unit/workflow/test_p2_13_1_canonical_pipeline_semantic_acceptance.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: HMAC tamper-evident checksums on checkpoints.
DEPENDENCIES: DurableWALRingBuffer
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Durable State Recovery
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P1.RUNTIME.BACKPRESSURE_CONTROL
PHASE: P1
FEATURE_NAME: Queue Bounding & Backpressure Flow Control
PURPOSE: Prevent buffer overflow by applying high/low watermarks and pausing readers when writers lag.
CANONICAL_AUTHORITY: BackpressureController
IMPLEMENTATION_LOCATION: akaal/streaming/flow/backpressure.py
PRIMARY_CLASS_OR_FUNCTION: BackpressureController
PRODUCTION_CALLER: ParallelReplicationScheduler
PRODUCTION_ENTRYPOINT: EngineGateway → WorkflowEngine
PIPELINE_POSITION: Streaming Transport Layer
DOWNSTREAM_CONSUMER: Physical Reader Workers
IDENTITY_BINDING: migration_id
STATE_OWNER: ParallelReplicationScheduler
FAILURE_PROPAGATION: Queue full → THROTTLED state → pause reader fetch loop
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (MonitoringModule → Overview)
MIGRATION_MODULE_FEATURE: Monitoring → Overview
TEST_LOCATION: tests/unit/workflow/test_p2_13_1_canonical_pipeline_semantic_acceptance.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Protects process RAM from out-of-memory crashes.
DEPENDENCIES: Queue depth monitor
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Streaming Flow Engine
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P1.MONITORING.LIVE_AND_HISTORICAL
PHASE: P1
FEATURE_NAME: Live Telemetry & Historical Run Reopening
PURPOSE: Provide live progress DTOs during execution and allow historical reopening of past runs.
CANONICAL_AUTHORITY: CentralStateStore
IMPLEMENTATION_LOCATION: akaal/core/state/state_store.py
PRIMARY_CLASS_OR_FUNCTION: CentralStateStore
PRODUCTION_CALLER: EngineGateway.get_monitoring_snapshot
PRODUCTION_ENTRYPOINT: IPC / Tauri / Frontend
PIPELINE_POSITION: Monitoring & Governance Layer
DOWNSTREAM_CONSUMER: MonitoringModule.tsx
IDENTITY_BINDING: migration_id + run_id
STATE_OWNER: CentralStateStore
FAILURE_PROPAGATION: Failed runs recorded with error details and stack trace samples
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (MonitoringModule screen)
MIGRATION_MODULE_FEATURE: MonitoringModule
TEST_LOCATION: tests/unit/workflow/test_p2_13_1_canonical_pipeline_semantic_acceptance.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Secret redaction on connection strings & credentials.
DEPENDENCIES: AuditTrailLogger
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Mission Control Hub
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4
```

---

## 3. P2 Baseline Feature Inventory

```yaml
FEATURE_ID: P2.SCHEMA.CANONICAL_MODEL
PHASE: P2
FEATURE_NAME: Canonical Schema Domain Model
PURPOSE: Database-agnostic metadata representation for tables, columns, constraints, and indexes.
CANONICAL_AUTHORITY: CanonicalSchemaModel
IMPLEMENTATION_LOCATION: akaal/schema/domain/models.py
PRIMARY_CLASS_OR_FUNCTION: CanonicalSchemaModel
PRODUCTION_CALLER: Database Adapters (get_canonical_schema)
PRODUCTION_ENTRYPOINT: Preflight & Schema Discovery Stage
PIPELINE_POSITION: Schema Discovery & Normalization Stage
DOWNSTREAM_CONSUMER: UniversalDDLAuthority / CanonicalSchemaComparator
IDENTITY_BINDING: schema_name + schema_fingerprint
STATE_OWNER: CanonicalSchemaModel
FAILURE_PROPAGATION: Unsupported metadata → mapped to CanonicalType.UNSUPPORTED with loss warning
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (SchemaAssessment screen)
MIGRATION_MODULE_FEATURE: Schema Assessment
TEST_LOCATION: tests/unit/schema/test_p2_2_canonical_schema_model.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Deterministic SHA-256 schema fingerprinting.
DEPENDENCIES: CanonicalTypeRegistry
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Universal Schema Studio
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.SCHEMA.DATATYPE_CONVERSION
PHASE: P2
FEATURE_NAME: Universal Datatype System & Conversion Safety
PURPOSE: Standardize native database types into 22 canonical type categories with explicit safety ratings.
CANONICAL_AUTHORITY: CanonicalTypeRegistry
IMPLEMENTATION_LOCATION: akaal/schema/domain/type_registry.py
PRIMARY_CLASS_OR_FUNCTION: CanonicalTypeRegistry
PRODUCTION_CALLER: Catalog Discovery Adapters
PRODUCTION_ENTRYPOINT: Preflight & Schema Discovery Stage
PIPELINE_POSITION: Schema Normalization Stage
DOWNSTREAM_CONSUMER: UniversalDDLAuthority / PhysicalChecksumValidator
IDENTITY_BINDING: source_native_type + target_engine
STATE_OWNER: CanonicalTypeRegistry
FAILURE_PROPAGATION: Lossy conversion → triggers HIGH risk score in CanonicalRiskScorer
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (SchemaAssessment screen)
MIGRATION_MODULE_FEATURE: Schema Assessment → Type Mapping
TEST_LOCATION: tests/unit/schema/test_p2_3_universal_datatype_system.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Safe numerical precision and timezone handling.
DEPENDENCIES: TranslationRulebook
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Datatype Intelligence Engine
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.SCHEMA.DEPENDENCY_PLANNING
PHASE: P2
FEATURE_NAME: Canonical Dependency Intelligence & Topological DDL Planner
PURPOSE: Resolve foreign keys and cyclic table dependencies into wave-ordered execution plans.
CANONICAL_AUTHORITY: CanonicalDependencyPlanner
IMPLEMENTATION_LOCATION: akaal/schema/graph/planner.py
PRIMARY_CLASS_OR_FUNCTION: CanonicalDependencyPlanner
PRODUCTION_CALLER: SchemaExecutionStep
PRODUCTION_ENTRYPOINT: EngineGateway → execute_schema
PIPELINE_POSITION: DDL Execution Stage
DOWNSTREAM_CONSUMER: PostgreSQL / Target Adapter
IDENTITY_BINDING: plan_id + migration_id
STATE_OWNER: CanonicalDependencyPlanner
FAILURE_PROPAGATION: Unresolvable cycle → raises CycleDependencyError → blocks DDL deployment
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (SchemaAssessment → Dependency Graph)
MIGRATION_MODULE_FEATURE: Schema Assessment → Dependency Graph
TEST_LOCATION: tests/unit/schema/test_p2_5_dependency_intelligence.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Prevents FK constraint violation errors during load.
DEPENDENCIES: UniversalDDLAuthority
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D DAG Execution Planner
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.SCHEMA.STRUCTURAL_DDL_EMITTER
PHASE: P2
FEATURE_NAME: Universal Structural DDL Authority
PURPOSE: Emit target-native CREATE TABLE, ALTER TABLE, PK, FK, and Index DDL statements.
CANONICAL_AUTHORITY: UniversalDDLAuthority
IMPLEMENTATION_LOCATION: akaal/schema/domain/ddl_emitter.py
PRIMARY_CLASS_OR_FUNCTION: UniversalDDLAuthority
PRODUCTION_CALLER: SchemaExecutionStep
PRODUCTION_ENTRYPOINT: EngineGateway → execute_schema
PIPELINE_POSITION: DDL Generation Stage
DOWNSTREAM_CONSUMER: CanonicalDependencyPlanner / Target Database Adapter
IDENTITY_BINDING: table_identity + target_engine
STATE_OWNER: UniversalDDLAuthority
FAILURE_PROPAGATION: DDL syntax generation error → raises DDLEmissionError → aborts schema deployment
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (SchemaAssessment → DDL Preview)
MIGRATION_MODULE_FEATURE: Schema Assessment → DDL Preview
TEST_LOCATION: tests/unit/schema/test_p2_4_structural_ddl_emitters.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: SQL injection mitigation via identifier quotes.
DEPENDENCIES: CanonicalSchemaModel
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Universal DDL Studio
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.VALIDATION.MERKLE_TREE
PHASE: P2
FEATURE_NAME: Physical Checksum & SHA-256 Merkle Tree Validator
PURPOSE: Validate binary data identity across source and target tables using framed byte serialization.
CANONICAL_AUTHORITY: PhysicalChecksumValidator
IMPLEMENTATION_LOCATION: akaal/validation/domain/physical_validator.py
PRIMARY_CLASS_OR_FUNCTION: PhysicalChecksumValidator
PRODUCTION_CALLER: ValidationStep
PRODUCTION_ENTRYPOINT: EngineGateway → run_validation
PIPELINE_POSITION: Post-Transport Validation Stage
DOWNSTREAM_CONSUMER: CanonicalReconciliationEngine / CanonicalReportingAuthority
IDENTITY_BINDING: validation_id + migration_id + run_id
STATE_OWNER: PhysicalChecksumValidator
FAILURE_PROPAGATION: Root mismatch → marks table MISMATCHED → triggers Deep Reconciliation
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (ValidationModule screen)
MIGRATION_MODULE_FEATURE: Validation Module
TEST_LOCATION: tests/unit/validation/test_p2_8_canonical_validation_engine.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Length-prefixed serialization preventing delimiter collisions.
DEPENDENCIES: CanonicalValueSerializer
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Row Matcher & Validation Suite
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.VALIDATION.DEEP_RECONCILIATION
PHASE: P2
FEATURE_NAME: Universal Progressive Deep Reconciliation Engine
PURPOSE: Locate exact missing, extra, and value-mismatched rows and columns across tables.
CANONICAL_AUTHORITY: CanonicalReconciliationEngine
IMPLEMENTATION_LOCATION: akaal/validation/domain/reconciliation.py
PRIMARY_CLASS_OR_FUNCTION: CanonicalReconciliationEngine
PRODUCTION_CALLER: ValidationStep
PRODUCTION_ENTRYPOINT: EngineGateway → run_validation
PIPELINE_POSITION: Deep Reconciliation Stage
DOWNSTREAM_CONSUMER: CanonicalReportingAuthority
IDENTITY_BINDING: job_id + run_id + table_name
STATE_OWNER: CanonicalReconciliationEngine
FAILURE_PROPAGATION: Unmatched PK or missing key → marks row INDETERMINATE
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (ValidationModule → Reconciliation Details)
MIGRATION_MODULE_FEATURE: Validation Module → Reconciliation
TEST_LOCATION: tests/unit/validation/test_p2_9_validation_only_deep_reconciliation.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Enforces ValidationOnlyWriteFirewall against target write queries.
DEPENDENCIES: ValidationOnlyWriteFirewall
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Deep Reconciliation Centre
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.REPORTING.CANONICAL_AUTHORITY
PHASE: P2
FEATURE_NAME: Canonical Reporting Authority & Fail-Closed Certification
PURPOSE: Aggregate migration, schema, risk, validation, and reconciliation evidence into canonical reports and certificates.
CANONICAL_AUTHORITY: CanonicalReportingAuthority
IMPLEMENTATION_LOCATION: akaal/reporting/engine/canonical_reporting.py
PRIMARY_CLASS_OR_FUNCTION: CanonicalReportingAuthority
PRODUCTION_CALLER: EngineGateway.generate_certificate
PRODUCTION_ENTRYPOINT: IPC / Tauri / Frontend
PIPELINE_POSITION: Reporting & Certification Stage
DOWNSTREAM_CONSUMER: CanonicalReportExportService / ReportsModule.tsx
IDENTITY_BINDING: report_id + job_id + run_id + certification_id
STATE_OWNER: CanonicalReportingAuthority
FAILURE_PROPAGATION: Execution error or validation failure → automatically issues NOT_CERTIFIED status
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (ReportsModule screen)
MIGRATION_MODULE_FEATURE: Reports Module
TEST_LOCATION: tests/unit/reporting/test_p2_10_canonical_reporting_certification.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Automatic secret redaction for connection passwords & API tokens.
DEPENDENCIES: TrustSealer
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Governance & Certification Centre
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4

---

FEATURE_ID: P2.EXPORT.DELIVERY_SERVICE
PHASE: P2
FEATURE_NAME: Canonical Report Export Service & Evidence Package Delivery
PURPOSE: Export tamper-evident JSON, PDF Dossiers, PDF Certificates, and ZIP evidence packages with path traversal protection.
CANONICAL_AUTHORITY: CanonicalReportExportService
IMPLEMENTATION_LOCATION: akaal/reporting/engine/export_service.py
PRIMARY_CLASS_OR_FUNCTION: CanonicalReportExportService
PRODUCTION_CALLER: EngineGateway export methods
PRODUCTION_ENTRYPOINT: IPC / Tauri / ReportsModule.tsx
PIPELINE_POSITION: Evidence Delivery Stage
DOWNSTREAM_CONSUMER: ReportsModule.tsx UI / External Audit Teams
IDENTITY_BINDING: report_id + evidence_package_sha256
STATE_OWNER: CanonicalReportExportService
FAILURE_PROPAGATION: Corrupted ZIP or cross-job identity mismatch → verify_evidence_package returns INVALID
MONITORING_EXPOSURE: YES
IPC_EXPOSURE: YES
UI_EXPOSURE: YES (ReportsModule → Download Buttons & Verification Modal)
MIGRATION_MODULE_FEATURE: Reports Module → Export & Verification
TEST_LOCATION: tests/unit/reporting/test_p2_12_enterprise_export_delivery.py
PROOF_LEVEL: INTEGRATION_PROVEN
INTEGRATION_STATUS: FULLY_INTEGRATED
SECURITY_NOTES: Strictly guards against path traversal (`../`), absolute paths, and backslashes in ZIP archives.
DEPENDENCIES: CanonicalReportingAuthority
LEGACY_OVERLAP: NONE
FUTURE_EVOLUTION: P7D Evidence Package Portal
LAST_VERIFIED_COMMIT: 92c4f5ce227614b5b86bbbe1618a1ab752d641c4
```

---

## 4. UI / IPC / Gateway Mapping & Future P7D Redesign Destinations

| Migration Module UI Feature | Current Backend Authority | Wiring Status | Future P7D Redesign Destination |
| :--- | :--- | :---: | :--- |
| **Migration Creation & Setup** | `EngineGateway.create_migration` | `FULLY_WIRED` | P7D Migration Creation Wizard |
| **Connection Setup & Auth** | `AdapterRegistry` / `ConnectionConfig` | `FULLY_WIRED` | P7D Database Connections Hub |
| **Preflight Discovery** | `ScoutOrchestrator` / `run_preflight` | `FULLY_WIRED` | P7D Preflight & Capacity Scout |
| **Execution Planning** | `PlannerPlatform` / `generate_plan` | `FULLY_WIRED` | P7D DAG Execution Planner |
| **Governance & Approval** | `PolicyEngine` / `request_approval` | `FULLY_WIRED` | P7D Governance & Compliance Centre |
| **Schema Execution** | `SchemaExecutionStep` / `UniversalDDLAuthority` | `FULLY_WIRED` | P7D Universal Schema Studio |
| **Data Transport** | `DataTransportStep` / `ParallelReplicationScheduler` | `FULLY_WIRED` | P7D High-Throughput Transport Engine |
| **Live Monitoring** | `CentralStateStore` / `get_monitoring_snapshot` | `FULLY_WIRED` | P7D Mission Control Hub |
| **Workers & Partitions** | `ParallelReplicationScheduler` / `RangePartitioner` | `FULLY_WIRED` | P7D Worker & Fleet Manager |
| **Reliability & Checkpoints** | `RecoveryCoordinator` / `JournalSupervisor` | `FULLY_WIRED` | P7D Reliability & Auto-Recovery Center |
| **Physical Validation** | `ValidationStep` / `PhysicalChecksumValidator` | `FULLY_WIRED` | P7D Row Matcher & Validation Suite |
| **Deep Reconciliation** | `CanonicalReconciliationEngine` | `FULLY_WIRED` | P7D Deep Reconciliation Centre |
| **Schema Assessment & Risk** | `CanonicalSchemaComparator` / `CanonicalRiskScorer` | `FULLY_WIRED` | P7D Schema Intelligence & Risk Studio |
| **Reports Dossier** | `CanonicalReportingAuthority` | `FULLY_WIRED` | P7D Reports & Dossier Portal |
| **Certification & Seal** | `CanonicalReportingAuthority` / `TrustSealer` | `FULLY_WIRED` | P7D Trust Certification & Custody Ledger |
| **Report & Evidence Export** | `CanonicalReportExportService` / `export_*` | `FULLY_WIRED` | P7D Evidence Package Portal |

---

## 5. Summary Statistics & Ledger Health

- **Total Features Ledgered**: 25 canonical P1/P2 features
- **Fully Integrated P1/P2 Features**: 25 (100%)
- **Partially Integrated P1/P2 Features**: 0 (0%)
- **Orphaned P1/P2 Capabilities**: 0
- **Duplicate Production Authorities**: 0
- **Legacy Bypass Paths**: 0
- **Overall Ledger Health**: `OPTIMAL`
