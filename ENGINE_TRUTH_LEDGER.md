# AKAAL ENGINE — AUTHORITY #1 TRUTH LEDGER
*Canonical Architectural Record of Authority #1: Connection*
*Consolidated Correction Pass: Complete & Verified (Freeze Review Verdict: Pass)*

---

## 1. Executive Summary & Status

`akaalEngine/connection/` is Authority #1 of the Canonical 13-Authority AKAAL Engine reconstruction.

This Authority is **fully implemented, strictly conformant, sealed, verified, and frozen** following the final consolidated correction pass.

### Verified Architecture Health
- **Engine Authority**: Authority #1 (Connection)
- **Subsystems Implemented & Hardened**:
  1. `models/` (Immutable endpoint specifications, typed failures, binding fingerprints, capability manifests, health snapshots, session leases, non-weakening SessionRequest restrictions)
  2. `security/` (Fail-closed secret resolution with zero plaintext fallback, bounded in-memory wipe lifecycle, regex redaction, SafeReprMixin, strict TLS/mTLS builder with key wiping)
  3. `identity/` (Deterministic SHA-256 binding fingerprinting incorporating non-secret credential references, role, catalog generation, and TLS/route settings; live physical identity attestation, drift detection with automatic pool invalidation)
  4. `routing/` (RFC 8305 Happy Eyeballs DNS resolution, PrivateLink endpoint routing, HTTP CONNECT proxy tunneling with local forwarder leases, SOCKS5 fail-closed rejection, SSH bastion forwarding with strict host verification by default, physical route resource lifecycle tied to session handles)
  5. `providers/` (BaseProviderStrategy SPI, ProviderConformanceSuite, 28 concrete provider implementations with truthful TLS classification, 4 cloud profile resolvers)
  6. `catalog/` (Thread-safe deterministic ProviderCatalog with generation tracking and pool invalidation, fail-closed CapabilityResolver with full admission validation across all 13 `SessionPurpose` values and non-circular probe bootstrap)
  7. `sessions/` (Purpose-specific SessionInitializer with fail-closed mandatory controls, deterministic transactional SessionResetManager with route cleanup, SessionFactory with route attachment and ephemeral secret wiping, SessionLifecycleManager)
  8. `pooling/` (Bounded process-local ConnectionPool, PID/fork protection, condition variable wait queues, leak detection, asymmetric budgeting, PoolInvalidationCoordinator, PoolManager keyed by fingerprint, purpose, and PID)
  9. `probes/` (ConnectivityProbe, PermissionProbe, CapabilityProbe, HealthProbe, PressureProbe with ephemeral secret wiping)
  10. `api/` (Single canonical public & internal façade `ConnectionAuthority` enforcing admission validation on acquisition)
- **Conformance & Verification**: 50 unit & conformance tests in `tests/unit/engine_connection/` passing with 100% success; repository architectural boundary conformance verified.

---

## 2. Invariants & Guarantees (Post-Correction Pass)

### 1. Ephemeral Secret Resolution & Zero-Leakage Invariant
- **Rule**: Secrets are never persisted, logged, printed in `__repr__`, serialized into public DTOs, embedded in error messages, or included in SHA-256 binding fingerprints. Unresolved secret references fail closed with `SecretResolutionError` (zero plaintext fallback).
- **Enforcement**:
  - `AuthenticationSpec` carries only secret pointers (`secret_ref`, `token_ref`, `key_path`).
  - `SecretConsumer` resolves secrets into `ResolvedSecret` instances that implement explicit `.wipe()` and are wiped in `finally` blocks across all factories, probes, and builders.
  - `InMemorySecretResolver` and `create_testing_consumer()` provide deterministic resolution for tests.
  - `SafeReprMixin` masks all sensitive keys (`password`, `secret`, `token`, `key`, `cert`, `credential`, `auth`).
  - `normalize_error()` strips passwords, tokens, and URIs before surfacing `ConnectionFailure`.

### 2. Fail-Closed Capability & Admission Invariant
- **Rule**: `UNKNOWN != SUPPORTED`. If a capability or role is not explicitly proven as `SUPPORTED`, it evaluates to `False`. Workload admission validates role, required capabilities, required privileges, and purpose-specific constraints across all 13 `SessionPurpose` values.
- **Enforcement**:
  - `CapabilityResolver.validate_admission()` validates role suitability, request capability requirements, and privilege requirements.
  - Probe purposes (`HEALTH_PROBE`, `PERMISSION_PROBE`) bootstrap physical sessions non-circularly without requiring unobtained evidence.
  - Read-only purposes (`VALIDATION_READ`, `DISCOVERY`, `METADATA`, `SCHEMA_READ`) cannot be weakened by caller (`read_only=False` is rejected).

### 3. Physical Route & Tunnel Lifetime Invariant
- **Rule**: Drivers connect to active forwarded tunnel sockets rather than bypassing them. Route resources (tunnels, forwarder leases) are owned by the physical session handle and destroyed on connection failure, eviction, or invalidation.
- **Enforcement**:
  - `ProxyTunnel.establish_http_connect_tunnel()` binds a local forwarding socket and pipes bidirectional TCP traffic through HTTP CONNECT.
  - SOCKS5 proxy routing explicitly fails closed with typed `RouteResolutionError`.
  - SSH Bastion tunneling enforces strict host key verification by default (`RejectPolicy()`), requiring explicit `allow_unverified_ssh=True` for permissive development mode.
  - `InternalSessionHandle.route_resource` is cleaned up via `handle.close_route()` in `SessionResetManager.destroy_poisoned_session()`.

### 4. Session Reset & Zero-Contamination Invariant
- **Rule**: No dirty, uncommitted, poisoned, or partially mutated session may ever be returned to an idle connection pool. Mandatory session initialization failures never log-and-continue; they raise typed `SessionInitializationError` and destroy the connection.
- **Enforcement**:
  - Releasing a `SessionLease` triggers `SessionResetManager.reset_and_clean_session()`.
  - The underlying provider strategy executes transactional `ROLLBACK`, restores autocommit, and clears session variables.
  - If `reset_session()` returns `False` or encounters an error, the physical connection is immediately marked poisoned, permanently closed, and destroyed along with its route resource.

### 5. Deterministic Identity & Workload Budget Isolation
- **Rule**: Fingerprints uniquely identify endpoint configurations without collisions across distinct secret references, roles, versions, TLS modes, or routes. High-volume operations must never starve diagnostic probes.
- **Enforcement**:
  - `compute_endpoint_fingerprint()` hashes non-secret credential pointers (`secret_ref`, `token_ref`, `client_key_ref`, `secret_version`), `role`, `provider_version`, `catalog_generation`, TLS settings, and SSH settings into SHA-256.
  - Pools in `PoolManager` are strictly keyed by `(fingerprint_sha256, purpose, process_id)`.
  - Replacing a provider strategy in `ProviderCatalog` increments `catalog_generation` and triggers pool invalidation.

---

## 3. Provider Strategies Matrix

The following 28 concrete provider strategies are fully registered in `ProviderCatalog` and classified with truthful TLS support:

| Category | Provider ID | Supported Roles | Key Proven Capabilities | TLS Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Relational** | `sqlite` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA | Schema Discovery, Bulk Read, Bulk Write, In-Memory DB | In-Process (TLS Disabled / Rejected) |
| | `postgresql` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA, CDC_LOG | Binary COPY, Logical Decoding CDC, Parallel Slicing | Fully Enforced (TLS / mTLS Context) |
| | `mysql` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA, CDC_LOG | Binlog CDC, Load Data Infile, Partition Discovery | Enforced with Driver Verification |
| | `mariadb` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA, CDC_LOG | Binlog CDC, Load Data Infile, Partition Discovery | Enforced with Driver Verification |
| | `oracle` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA, CDC_LOG | LogMiner CDC, Direct-Path Arrays, TNS Resolution | Enforced (TCPS / ssl_context) |
| | `mssql` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA, CDC_LOG | BCP Fast Executemany, MS SQL CDC, Change Tracking | Enforced (ODBC Encrypt / TrustCert) |
| | `ibm_db2` | SOURCE, TARGET, REFERENCE, VALIDATION, METADATA | DB2 Schema Discovery, Bulk Insert, Isolation Config | Enforced (SECURITY=SSL) |
| **Warehouse** | `snowflake` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | Snowflake Stage Copy, Partition Discovery, Bulk Query | Enforced via HTTPS/Driver |
| | `bigquery` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | Storage Read API, BigQuery Load, Partition Expiration | Enforced via HTTPS/gRPC |
| | `redshift` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | S3 COPY / UNLOAD, Enhanced VPC Routing | Enforced via TLS/SSL |
| | `databricks` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | Delta Lake Discovery, Unity Catalog, Cloud Fetch | Enforced via HTTPS/Thrift |
| **NoSQL / KV** | `mongodb` | SOURCE, TARGET, REFERENCE, VALIDATION, CDC_LOG | Change Streams, Aggregation Pipeline, Bulk Write | Enforced (tlsCAFile / ClientKey) |
| | `cassandra` | SOURCE, TARGET, REFERENCE, VALIDATION | Token-Aware Routing, CQL Bulk Paging, Consistency | Enforced (SSL Options) |
| | `scylladb` | SOURCE, TARGET, REFERENCE, VALIDATION, CDC_LOG | Shard-Aware Routing, ScyllaDB CDC, CQL Paging | Enforced (SSL Options) |
| | `neo4j` | SOURCE, TARGET, REFERENCE, VALIDATION | Cypher Querying, Bolt Protocol, Graph Schema Probing | Enforced (bolt+s / bolt+ssc) |
| | `redis` | SOURCE, TARGET, REFERENCE, VALIDATION, CDC_LOG | Key Discovery, Redis Streams CDC, RESP3 Protocol | Enforced (rediss / ssl_cert_reqs) |
| | `keydb` | SOURCE, TARGET, REFERENCE, VALIDATION | Multithreaded Execution, Bulk Read/Write | Enforced (rediss / SSL) |
| | `elasticsearch` | SOURCE, TARGET, REFERENCE, VALIDATION | Index Mapping Discovery, Scroll Search, Bulk Index | Enforced (HTTPS / ca_certs) |
| | `opensearch` | SOURCE, TARGET, REFERENCE, VALIDATION | OpenSearch Schema Discovery, Bulk Indexing | Enforced (HTTPS / ca_certs) |
| **Streaming** | `kafka` | SOURCE, TARGET, CDC_LOG | Topic Discovery, Streaming Read/Write, Offset Commit | Enforced (SSL / SASL_SSL) |
| | `kinesis` | SOURCE, TARGET, CDC_LOG | Shard Management, Record Streaming, PutRecords | Enforced via HTTPS |
| | `eventhubs` | SOURCE, TARGET, CDC_LOG | Event Hubs Consumer Groups, AMQP / Kafka protocol | Enforced via AMQPS / SSL |
| | `pubsub` | SOURCE, TARGET, CDC_LOG | Topic Subscriptions, Streaming Pull/Push, Exactly-Once | Enforced via gRPC / TLS |
| **Storage** | `s3` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | S3 Multipart Parallel Upload, S3 Select, Parquet | Enforced via HTTPS |
| | `gcs` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | Resumable Uploads, Bucket Discovery, Blob Read/Write | Enforced via HTTPS |
| | `azure_blob` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | Block Blob Chunking, Container Discovery | Enforced via HTTPS |
| | `minio` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | S3 API Compliance, Distributed MinIO Profiling | Enforced via HTTPS/HTTP |
| | `hdfs` | SOURCE, TARGET, STAGING, REFERENCE, VALIDATION | WebHDFS REST API, Distributed File Traversal | Enforced via HTTPS/HTTP |

---

## 4. Verification Proof Summary (Authority #1)

- **Test Suite**: `tests/unit/engine_connection/`
- **Total Tests**: 50
- **Passed**: 50 (100%)
- **Failed**: 0
- **Execution Command**: `python -m pytest tests/unit/engine_connection/ -v`
- **Execution Platform**: Windows, Python 3.14.6, pytest-9.1.1
- **Architectural Boundary Conformance**: `tests/test_repository_architecture_conformance.py` (100% Passed)
- **Status**: Authority #1 Connection is complete, conformant, and frozen.

---

# AKAAL ENGINE — AUTHORITY #2 EXTENSIONS TRUTH LEDGER
*Canonical Architectural Record of Authority #2: Extensions*
*Final Consolidated Correction Pass: Complete & Verified (Ready for Final Source-Level Closure Review)*

---

## 1. Executive Summary & Status

`akaalEngine/extensions/` is Authority #2 of the Canonical 13-Authority AKAAL Engine reconstruction.

This Authority serves as the Engine's **single cross-authority provider-extension foundation**, establishing unified provider identity, versioning, strategy registration & resolution, dependency truth, configuration schemas, proof metadata, and drain-safe lifecycle management across all current and future Engine authorities.

### Verified Architecture Health
- **Engine Authority**: Authority #2 (Extensions)
- **Subsystems Implemented & Hardened**:
  1. `models/` (Immutable normalized identity types, enums, extension manifests, provider contributions, strategy contributions, configuration schemas, capability declarations, proof references, lifecycle transitions, events, availability descriptors, and Gateway-safe sanitized DTOs)
  2. `errors/` (Typed exception taxonomy rooted in `ExtensionEngineException`, error sanitization, and external exception normalization)
  3. `spi/` (AuthorityContractDefinition, thread-safe AuthorityContractRegistry with fail-closed unknown authority rejection, StrategyFactory protocols, ProviderBundle aggregation envelope, and Manifest/Strategy structural validators with lazy callable validation)
  4. `compatibility/` (Deterministic SemVer 2.0.0 parser/comparator, SemVer range expressions with caret/tilde/hyphen operators, and CompatibilityEvaluator)
  5. `dependencies/` (Lazy Python package inspection via `importlib.util.find_spec` and `importlib.metadata.version`, native OS library/executable inspector, and consolidated DependencyDiagnosticReport aggregator)
  6. `configuration/` (Declarative ConfigurationSchema validator with condition participation, strict `SECRET_REF` pointer URI enforcement, and Gateway-safe ConfigurationSanitizer redacting sensitive defaults directly on DTO instances)
  7. `truth/` (Authoritative CapabilityTruthResolver enforcing fail-closed `UNKNOWN != SUPPORTED`, ProofResolver rejecting unproven self-awarded live certifications, and runtime AvailabilityResolver)
  8. `lifecycle/` (Strict LifecycleStateMachine, thread-safe HandleLeaseTracker with drain safety preventing destructive unregistration while active leases exist, and isolated internal NotificationDispatcher)
  9. `catalog/` (Immutable O(1)-indexed RegistrySnapshot with MappingProxyType deep immutability, thread-safe ExtensionRegistry, OwnershipManager rejecting cross-owner and strategy ID collisions, and staged atomic RegistrationTransaction with reverse-order rollback for applied mutations)
  10. `resolution/` (Deterministic StrategyResolver, capability/priority StrategySelector with ambiguity rejection, generation-aware ResolutionCache, and internal ResolvedStrategyHandle lease tokens)
  11. `loading/` (Explicit ModuleExtensionSource, EntryPointExtensionSource for `akaal.extensions`, and truthful IsolationManager enforcing IN_PROCESS fail-closed)
  12. `integration/` (Authority #1 Connection contract definition, transactional ConnectionCatalogBridge coordinating catalog generation bumps and pool invalidations with forward/rollback closures, and BuiltinConnectionBootstrap adopting all 28 Connection providers with truthful driver dependency mapping)
  13. `authority.py` (Single canonical internal façade `ExtensionsAuthority` and singleton `default_extensions_authority`)
- **Conformance & Verification**: 48 unit & conformance tests in `tests/unit/engine_extensions/` passing with 100% success; Authority #1 Connection suite passing (50/50); repository architectural boundary conformance verified.

---

## 2. Invariants & Guarantees (Extensions Authority Post-Correction)

### 1. Unified Provider Identity & Multi-Authority Bundle Invariant
- **Rule**: One provider contributes separate authority-specific strategies rather than collapsing into a universal provider superclass. Future authorities (Discovery, Schema, Transport, CDC, Validation, etc.) attach strategies to the same canonical `ProviderId`.
- **Enforcement**:
  - `ProviderBundle` groups distinct `StrategyContribution` instances per target `AuthorityId`.
  - Each authority contract validates its specific strategy instance (e.g. Connection validates against `BaseProviderStrategy`).
  - No competing provider registries exist across authorities.

### 2. Adoption & Transactional Bridge Invariant
- **Rule**: All 28 physical Connection provider strategies are adopted into the Extensions registry at bootstrap with physical driver dependencies declared. Connection strategy updates/replacements execute transactionally through `ConnectionCatalogBridge` with indexed reverse rollback on failure.
- **Enforcement**:
  - `BuiltinConnectionBootstrap` adopts all 28 Connection strategies with declared driver packages (`sqlite3`, `psycopg2`, `oracledb`, `boto3`, etc.).
  - `RegistrationTransaction` executes bridge mutations forward and applies rollback mutations in reverse order for only applied mutations on failure.
  - Active leases prevent destructive unregistration (`ExtensionHandleLeakError`).

### 3. Fail-Closed Capability & Proof Governance Invariant
- **Rule**: `UNKNOWN != SUPPORTED`. If a capability is undeclared, unsupported, or missing mandatory dependencies, it evaluates to `False`. Manifest declarations cannot self-award `LIVE_PROVEN` certification without formal `CertificationReference`.
- **Enforcement**:
  - `CapabilityTruthResolver` fails closed on unknown capabilities or missing dependencies.
  - `ProofResolver` enforces provenance and distinguishes `DECLARED`, `IMPLEMENTED`, `UNIT_PROVEN`, `INTEGRATION_PROVEN`, and `LIVE_PROVEN`.

### 4. Lazy Dependency Inspection & Fault Isolation Invariant
- **Rule**: Extension discovery and dependency inspection must never eagerly import every optional database SDK. Missing dependencies for one provider (e.g. `oracledb`) isolate that provider without impacting unrelated providers or engine stability.
- **Enforcement**:
  - `PythonDependencyInspector` inspects presence lazily using `importlib.util.find_spec` and versions via `importlib.metadata`.
  - Uninstalled packages produce structured `DependencyDiagnostic` records with remediation hints.
  - Resolution of dependency-gated providers fails closed with `DependencyResolutionError` without eager driver import.

### 5. Drain-Safe Handle Leasing & Lifecycle Invariant
- **Rule**: Strategy handles leased for execution are tracked via immutable lease tokens. Deactivating an extension marks it `INACTIVE` (rejecting new resolutions) while allowing active leases to drain cleanly. Destructive unregistration while active leases exist is rejected.
- **Enforcement**:
  - `HandleLeaseTracker` tracks active checked-out handles. Duplicate releases or stale tokens are detected and rejected without corrupting counters.
  - `ExtensionsAuthority.unregister_extension` checks active lease counts and raises `ExtensionHandleLeakError` if leases remain unreleased.
  - `ResolvedStrategyHandle` provides context manager support (`with handle:`) and auto-releases on exit.

### 6. Gateway-Safe Descriptors & Zero Secret Leakage Invariant
- **Rule**: Extensions describes configuration schemas using `ConfigurationField` and `SECRET_REF` pointer types. Secret values, sensitive defaults, internal factory references, Python modules, and private filepaths are stripped from sanitized DTOs.
- **Enforcement**:
  - `SanitizedConfigurationField` redacts sensitive defaults directly upon object construction.
  - `SECRET_REF` enforces strict pointer URI format (`vault://...`, `env:...`, `ref:...`, etc.) and rejects raw plaintext credentials.
  - Conditions participate in field validation and schema sanitization.

---

## 3. Adopted Connection Providers (28 Total)

The following 28 physical database, warehouse, nosql, streaming, and storage providers are adopted as built-in contributions:

| Provider ID | Vendor Name | Family | Implemented Strategies | Driver Dependency (Match Mode) |
| :--- | :--- | :--- | :--- | :--- |
| `sqlite` | SQLite | relational | `sqlite-connection` | `sqlite3` (built-in standard library) |
| `postgresql` | PostgreSQL | relational | `postgresql-connection` | `psycopg2` |
| `mysql` | MySQL | relational | `mysql-connection` | `pymysql` |
| `mariadb` | MariaDB | relational | `mariadb-connection` | `ANY_OF`: `pymysql` \| `mariadb` |
| `oracle` | Oracle | relational | `oracle-connection` | `oracledb` |
| `mssql` | Microsoft SQL Server | relational | `mssql-connection` | `pyodbc` |
| `ibm_db2` | IBM Db2 | relational | `ibm_db2-connection` | `ibm_db` |
| `snowflake` | Snowflake | warehouse | `snowflake-connection` | `snowflake-connector-python` |
| `bigquery` | Google BigQuery | warehouse | `bigquery-connection` | `google-cloud-bigquery` |
| `redshift` | Amazon Redshift | warehouse | `redshift-connection` | `ANY_OF`: `psycopg2` \| `redshift-connector` |
| `databricks` | Databricks / Delta Lake | warehouse | `databricks-connection` | `databricks-sql-connector` |
| `mongodb` | MongoDB | nosql | `mongodb-connection` | `pymongo` |
| `cassandra` | Apache Cassandra | nosql | `cassandra-connection` | `cassandra-driver` |
| `scylladb` | ScyllaDB | nosql | `scylladb-connection` | `cassandra-driver` |
| `neo4j` | Neo4j Graph DB | nosql | `neo4j-connection` | `neo4j` |
| `redis` | Redis | nosql | `redis-connection` | `redis` |
| `keydb` | KeyDB | nosql | `keydb-connection` | `redis` |
| `elasticsearch` | Elasticsearch | nosql | `elasticsearch-connection` | `elasticsearch` |
| `opensearch` | OpenSearch | nosql | `opensearch-connection` | `opensearch-py` |
| `kafka` | Apache Kafka | streaming | `kafka-connection` | `ANY_OF`: `kafka-python` \| `confluent-kafka` |
| `kinesis` | AWS Kinesis | streaming | `kinesis-connection` | `boto3` |
| `eventhubs` | Azure Event Hubs | streaming | `eventhubs-connection` | `azure-eventhub` |
| `pubsub` | Google Cloud Pub/Sub | streaming | `pubsub-connection` | `google-cloud-pubsub` |
| `s3` | Amazon S3 | storage | `s3-connection` | `boto3` |
| `gcs` | Google Cloud Storage | storage | `gcs-connection` | `google-cloud-storage` |
| `azure_blob` | Azure Blob Storage | storage | `azure_blob-connection` | `azure-storage-blob` |
| `minio` | MinIO Storage | storage | `minio-connection` | `ANY_OF`: `minio` \| `boto3` |
| `hdfs` | Apache Hadoop HDFS | storage | `hdfs-connection` | `ANY_OF`: `hdfs` \| `pyarrow` |

---

## 4. Verification Proof Summary (Authority #2)

- **Test Suite**: `tests/unit/engine_extensions/`
- **Total Tests**: 58
- **Passed**: 58 (100%)
- **Failed**: 0
- **Execution Command**: `python -m pytest tests/unit/engine_extensions/ -v`
- **Authority #1 Connection Suite**: `python -m pytest tests/unit/engine_connection/ -v` (50 passed)
- **Repository Boundary Conformance**: `python -m pytest tests/test_repository_architecture_conformance.py -v` (1 passed)
- **Execution Platform**: Windows, Python 3.14.6, pytest-9.1.1
- **Freeze Candidacy**: READY FOR FINAL SOURCE-LEVEL CLOSURE REVIEW.

