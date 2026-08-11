# AKAAL Engine (`akaal/engine`) Deep Logical Analysis & Gap Specification

**Document Version:** 1.0  
**Classification:** Architectural Audit & Integration Gap Specification  
**Target Component:** `akaal/engine` ([akaal/engine](file:///a:/temp_akaal/akaal/engine))  

---

## 1. Executive Summary

A deep-code audit of the [`akaal/engine`](file:///a:/temp_akaal/akaal/engine) directory reveals that it represents a **simplified, standalone subset pipeline** rather than the full enterprise-grade AKAAL engine. While `akaal/engine` provides a functional, fast-path Oracle-to-PostgreSQL bulk data transport script with SQLite WAL state logging, **it connects to less than 5% of the total AKAAL enterprise codebase**.

`akaal/engine` bypasses the master 20-stage workflow engine (`WorkflowEngine`), all 3 enterprise governance approval gates (**GATE 1**, **GATE 2**, **GATE 3**), SQL dialect transpilation (`TranspilerFacade`), AST schema evolution (`SchemaEvolutionPlatformV5`), log-based Change Data Capture (`CoordinatorFacade`), automated self-healing (`EnterpriseSelfHealingPlatformV2`), PII data masking (`EnterpriseGovernancePlatformV6`), and cryptographic trust certification (`EnterpriseTrustCertificationPlatformV11`).

---

## 2. Connectivity & Integration Scope Analysis

### To Whom is `akaal/engine` Connected?
An inspection of all 11 files inside `akaal/engine` reveals direct imports to only **2 external subpackages** within the 44-folder AKAAL codebase:

1. **`akaal.adapters.rdbms`**:
   - [`OracleAdapter`](file:///a:/temp_akaal/akaal/adapters/rdbms/oracle_adapter.py) (Connection testing & metadata verification)
   - [`PostgreSQLAdapter`](file:///a:/temp_akaal/akaal/adapters/rdbms/postgresql_adapter.py) (Target verification)
2. **`akaal.core` & `akaal.events`**:
   - `CentralStateStore` ([`akaal.core.state.state_store`](file:///a:/temp_akaal/akaal/core/state/state_store.py)) (Progress telemetry)
   - `EnterpriseEventBus` ([`akaal.events.bus`](file:///a:/temp_akaal/akaal/events/bus.py)) (Asynchronous progress event publishing)

### Connectivity Percentage Calculation
- **Total AKAAL Core Subpackages:** 44 platform folders (`adapters`, `advisor`, `advisory`, `agents`, `api`, `audit`, `catalog`, `cdc`, `core`, `coverage`, `data_integrity`, `decoder`, `distributed`, `events`, `gateway`, `governance`, `healing`, `integration`, `intelligence`, `metrics`, `migration`, `operational_reliability`, `operations`, `performance`, `orchestration`, `planner`, `platform`, `plugins`, `recovery_intelligence`, `reliability`, `reliability_intelligence`, `replication`, `reporting`, `resilience_eng`, `risk`, `rulebook`, `runtime`, `schema`, `scout`, `streaming`, `transpiler`, `trust_certification`, `validation`, `workflow`).
- **Directly Connected Subpackages:** 2 (`adapters`, `core`/`events`).
- **Integration Ratio:**  
  $$\text{Connectivity \%} = \frac{2}{44} \times 100\% = \mathbf{4.55\%}$$

**Conclusion:** `akaal/engine` is disconnected from **95.45%** of the AKAAL platform infrastructure.

---

## 3. Creation of Independent Custom Logic

**Does `akaal/engine` create its own independent logic?**  
**YES.** Instead of delegating to the 11 enterprise platform facades wired inside [`CompositionRoot`](file:///a:/temp_akaal/akaal/integration/composition_root.py), `akaal/engine` implements its own custom, isolated sub-systems:

| Component | Custom Logic Created in `akaal/engine` | Official Enterprise Subsystem Bypassed |
| :--- | :--- | :--- |
| **State Repository** | Custom `EngineStateRepository` in `artifacts/state.db` | Central `WorkflowEngine` State Machine & `CentralStateStore` |
| **Checkpointing** | Custom `CheckpointStore` in `artifacts/checkpoints.db` | `akaal.orchestration.checkpoint` & `akaal.core.checkpoint` |
| **Partitioner** | Custom `TransportPartitioner` (basic min/max PK split) | `akaal.migration.dependency` & `akaal.migration.planner` |
| **Source Reader** | Hardcoded `OracleSourceReader` using `oracledb` cursor | `akaal.adapters` Driver Abstraction & `akaal.streaming.lob` |
| **Target Writer** | Hardcoded `PostgreSQLTargetWriter` using `psycopg2` | `akaal.replication` & `akaal.streaming.transport` |
| **Validator** | Custom `EngineValidator` (simple count & SHA-256) | `EnterpriseDataIntegrityPlatformV8` & `EnterpriseValidationPlatformV1` |
| **Scheduler** | Basic `MigrationScheduler` using `ProcessPoolExecutor` | `DefaultDistributedRuntimeV1` & `akaal.workflow.workers` |

---

## 4. Real Engine vs. Half-Built Prototype Evaluation

### Is `akaal/engine` Exposing the Real AKAAL Engine?
**NO.** `akaal/engine` exposes a **half-built, prototype-grade standalone bulk copy pipeline**. It does not expose the true enterprise AKAAL architecture specified in [`AKAAL_Enterprise_Migration_Workflow_v1.0.md`](file:///a:/temp_akaal/docs/architecture/AKAAL_Enterprise_Migration_Workflow_v1.0.md).

### Crucial Implementation Gaps in `akaal/engine`:

1. **Dummy Schema DDL Generation:**
   - In [`akaal/engine/api.py`](file:///a:/temp_akaal/akaal/engine/api.py#L174), table creation uses fallback DDL:  
     `CREATE TABLE IF NOT EXISTS "schema"."table" (id TEXT);`
   - In [`akaal/engine/writer.py`](file:///a:/temp_akaal/akaal/engine/writer.py#L134), columns are dynamically created by forcing **every data type to `TEXT`**:  
     `cols_ddl = ", ".join([f'"{c.lower()}" TEXT' for c in columns])`
   - Real SQL data type conversion, precision scaling, and constraint remapping are completely absent.
2. **Missing Transpilation & AST Generation:**
   - Completely bypasses [`TranspilerFacade`](file:///a:/temp_akaal/akaal/transpiler/facade.py) and [`SchemaEvolutionPlatformV5`](file:///a:/temp_akaal/akaal/schema/facade/platform5.py).
3. **Hardcoded Database Engines:**
   - Supports **only** Oracle sources and PostgreSQL targets. All other engines (MySQL, SQL Server, DB2, Snowflake, NoSQL, Cloud Warehouses) are unsupported.
4. **Bypasses Governance Approval Gates:**
   - Executes migrations directly without checking **GATE 1** (Discovery/Risk), **GATE 2** (4-Eyes Plan Sign-off), or **GATE 3** (Cutover Authorization).
5. **No Continuous Synchronization or CDC:**
   - Lacks Change Data Capture log parsing (`WF-015`, `WF-016`), streaming LSN tracking, or reverse CDC failback (`WF-018`).
6. **No Closed-Loop Self-Healing:**
   - Lacks connection to [`EnterpriseSelfHealingPlatformV2`](file:///a:/temp_akaal/akaal/healing). When a batch fails, it simply logs an error and aborts.
7. **No Cryptographic Trust Seals or PDF Reporting:**
   - Ignores [`EnterpriseTrustCertificationPlatformV11`](file:///a:/temp_akaal/akaal/trust_certification) and [`Platform8Facade`](file:///a:/temp_akaal/akaal/reporting/api/facade.py) (PDF compilation/SHA-256 signing).

---

## 5. Comprehensive Feature Comparison Matrix

| Feature / Domain | Actual Enterprise AKAAL Platform | `akaal/engine` Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Workflow Stages** | Full 20-Stage Lifecycle (`WF-001` to `WF-020`) | Simple 4-step linear loop (Prepare, Partition, Run, Check) | **Missing 80%** |
| **Governance Gates** | 3 Multi-Custody Gates (**GATE 1**, **GATE 2**, **GATE 3**) | None | **Missing** |
| **Schema Transpilation** | Full AST Dialect Parsing & DDL Generation | Forged DDL with hardcoded `TEXT` column types | **Fake/Prototype** |
| **Database Engines** | Oracle, PostgreSQL, MySQL, SQL Server, DB2, Snowflake, MongoDB | Oracle (Source) + PostgreSQL (Target) only | **Partial (2/7)** |
| **Change Data Capture** | Continuous Log Reader, LSN Tracking, Zero-Loss Sync | None (Bulk Load Only) | **Missing** |
| **Self-Healing** | Automatic Anomaly Detection, Lock Resolution, Recipe Retries | Basic try/except with ProcessPool failover | **Primitive** |
| **Data Masking** | PII/PHI Classification & Anonymization Streams | None (Raw Unmasked Transport) | **Missing** |
| **Validation** | 3-Tier Physical Verification + Merkle Tree Hashing | Simulated row count & fallback Merkle hash | **Simplified** |
| **Audit & Certification** | SHA-256 Signed Audit Ledger & Legal PDF Bundle | Basic SQLite attempt log (`state.db`) | **Primitive** |
| **Cluster Scaling** | Multi-node `DefaultDistributedRuntimeV1` | Single-node Python `ProcessPoolExecutor` | **Single-Host Only** |

---

## 6. Architectural Recommendations

To transform `akaal/engine` from a half-built prototype into a production-grade facade that exposes the real enterprise AKAAL platform:

1. **Wire `AkaalMigrationEngine` to `CompositionRoot`:**  
   Replace custom state repositories and readers inside `akaal/engine/api.py` with facade calls to `CompositionRoot.get_platform("orchestration")` and `CompositionRoot.get_platform("streaming")`.
2. **Integrate Transpiler & Schema Evolution:**  
   Replace `writer.py` string concatenation with `TranspilerFacade.transpile_sql()` to ensure exact data types, constraints, and indexes are created on the target database.
3. **Connect to Governance Platform:**  
   Enforce `EnterpriseGovernancePlatformV6.evaluate_gate()` before allowing `start_migration()` to trigger bulk data transport.
4. **Delegate Validation to Platform 1 & 8:**  
   Replace `EngineValidator` with calls to `EnterpriseDataIntegrityPlatformV8.verify_integrity()`.

---
**END OF ANALYSIS REPORT**
