Phase 7 — Production Engine (v1 Foundation)

Focus: Make migrations reliable under production workloads.

Adaptive batch sizing
Checkpointing & resume
Parallel migration
Connection pooling optimization
Retry with exponential backoff
Performance benchmarking
Large database testing
Memory optimization
Structured logging
Detailed migration reports

Goal:
Production-ready migration engine.

Phase 8 — Enterprise Migration Features

Focus: Match enterprise migration tools.

A. Schema & Object Migration (13)
Schema comparison
Automatic schema synchronization
Type conversion engine
Constraint migration
Trigger migration
Stored procedure migration
Function migration
View migration
Sequence migration
Identity column handling
Partition migration
Synonym migration
Materialized view migration
B. Data Migration Engine (10)
LOB/BLOB streaming
Incremental migration
Change Data Capture (CDC)
Continuous synchronization
Selective migration
Column mapping
Table mapping
Data transformation rules
Data masking
Custom SQL before/after migration
C. Validation & Reliability (8)
Migration diff engine
Object validation
Data quality validation
Pre-migration health checks
Post-migration certification
Drift detection
Dry-run simulation
Rollback engine
D. Enterprise Execution (7)
Parallel object scheduler
Dependency graph engine
Conflict resolution engine
Online/Offline migration modes
Adaptive chunk optimizer
Cross-version compatibility
Object versioning
E. Advanced Enterprise (7)
Migration replay
Storage optimization recommendations
Compression-aware migration
Encryption-aware migration
Cross-region/cloud migration
Zero-downtime cutover support
Plugin/extension framework for custom migration logic

Goal:
Enterprise-grade migration capabilities.

Phase 9 — Migration Intelligence Platform (≈50 Features)

Goal: Akaal stops being "just a migration engine" and starts thinking before migrating.

Scout Platform
Intelligent source discovery
Database fingerprinting
Engine/version detection
Instance discovery
Cluster discovery
Schema inventory
Storage inventory
Object inventory
Network discovery
Dependency discovery
Rulebook Platform
Vendor rule engine
Naming rules
Conversion rules
Compliance rules
Constraint rules
Transformation rules
Security rules
Policy inheritance
Decoder Platform
Universal migration model
SQL dialect normalization
Metadata normalization
Vendor abstraction layer
Canonical schema model
Canonical DDL model
Risk Platform
Compatibility scoring
Downtime estimation
Performance prediction
Data loss prediction
Resource estimation
Cutover readiness
Migration complexity scoring
Planner Platform
Intelligent migration planning
Parallel execution planner
Dependency planner
Rollback planner
Cutover planner
Batch planner
Worker planner
Storage planner
Advisor Platform
Migration recommendations
Batch recommendations
Worker recommendations
Hardware recommendations
Cost estimation
ETA prediction
Best-practice suggestions
New Enterprise Features
Agent coordination
Decision graph
Recommendation engine
Strategy selection
Migration simulation
Readiness scoring

Phase 10 — Distributed Execution Platform (≈45 Features)

Goal: Build the world's fastest migration runtime.

Distributed Runtime
Distributed execution
Multi-node workers
Cluster scheduling
Agent coordination
Leader election
Task distribution
Worker discovery
Heartbeats
Streaming Engine
Zero-copy pipeline
Apache Arrow pipeline
Event-time processing
Window processing
Stream joins
Pipeline fusion
Adaptive streaming
Memory pooling
Schema Evolution
Online DDL propagation
Live schema evolution
Dynamic metadata refresh
DDL replay
Live schema compatibility
CDC Platform
Distributed CDC
Remote CDC
Multi-source CDC
Multi-target CDC
CDC routing
CDC replay
CDC buffering
Performance
SIMD optimization
Hardware acceleration
NUMA awareness
Adaptive scheduling
Vectorized execution
Pipeline optimization

Phase 11 — Reliability & Validation Platform (≈45 Features)

Goal: Enterprise-grade correctness.

Validation
Merkle Tree validation
Parallel validation
Streaming validation
Referential validation
Business rule validation
Constraint validation
Statistical validation
Sampling validation
Self-Healing
Auto repair
Drift correction
Missing row repair
Checksum repair
Constraint repair
Metadata repair
Replication
Active-active replication
Conflict detection
Conflict resolution
Reverse replication
Loop prevention
Reliability
Intelligent retries
Failure prediction
Health scoring
Automatic recovery
Disaster recovery
Chaos testing
Recovery simulation
Governance
Approval workflows
Human checkpoints
Enterprise policies
Phase 12 — Enterprise Security & Operations Platform (≈50 Features)

Goal: Production deployment in Fortune 500 environments.

Zero Trust
mTLS
SPIFFE/SPIRE identities
Certificate rotation
Identity federation
Secure tunnels
Security
Inline masking
Tokenization
Encryption-aware migration
Hardware enclaves
Secret rotation
Key management
Vault integration
Operations
RBAC
Organizations
Teams
Multi-tenancy
Licensing
Scheduling
Notifications
Email
Slack
Teams
Monitoring
Live metrics
Prometheus
Grafana
OpenTelemetry
Tracing
Alerting
Dashboards
Mission Control
Cluster monitoring
Migration monitoring
Fleet management
Health center

Phase 13 — Enterprise Platform & Ecosystem (≈50 Features)

Goal: Make Akaal extensible.

Plugin Platform
WASM runtime
Plugin lifecycle
Plugin registry
Plugin marketplace
Sandboxed execution
Version compatibility
Connector SDK
Language SDKs
Connector framework
API framework
Testing SDK
Certification SDK
Data Connectors
SaaS APIs
REST
GraphQL
Kafka
Pulsar
RabbitMQ
Salesforce
SAP
ServiceNow
Data Formats
CSV
Excel
JSON
XML
Avro
Parquet
ORC
Governance
OpenLineage
Data lineage
Metadata export
Data catalog integration
Phase 14 — Cloud & Data Fabric Platform (≈45 Features)

Goal: Akaal becomes cloud-native.

Kubernetes
Operators
Helm
Auto scaling
Rolling upgrades
Self-healing clusters
Cloud
AWS
Azure
GCP
OCI
Multi-cloud
Hybrid cloud
Data Fabric
Multi-region mesh
Global routing
Data locality
Sovereign routing
Geo-aware scheduling
Infrastructure
Infrastructure as Code
GitOps
Terraform
Pulumi
Kubernetes CRDs
Enterprise
Multi-region failover
Global replication
Cloud storage integration
Object storage pipelines
Phase 15 — AI-Native Migration Platform (≈55 Features)

Goal: Akaal becomes an intelligent data platform.

AI Planner
Migration planning
Strategy generation
Cutover optimization
Dependency optimization
Capacity planning
AI Conversion
SQL translation assistant
Procedure conversion
Trigger conversion
Function conversion
Schema optimization
AI Operations
Root cause analysis
Failure diagnosis
Performance tuning
Bottleneck detection
Automatic optimization
AI Governance
Compliance recommendations
Security recommendations
Cost optimization
Architecture reviews
AI Assistant
Conversational migration assistant
Natural language planning
Report generation
Documentation generation
Executive summaries
Autonomous Platform
Self-tuning
Self-healing recommendations
Predictive scaling
Predictive maintenance
Intelligent scheduling
Final Product Vision

By the end of Phase 15, Akaal is no longer a database migration tool. It is a complete enterprise platform consisting of:

Discovery Platform (Scout)
Intelligence Platform (Rulebook, Decoder, Risk, Planner, Advisor)
Migration Platform
Synchronization Platform
Validation Platform
Reliability Platform
Governance Platform
Security Platform
Operations Platform (Mission Control)
Observability Platform
Developer Platform (SDKs & Plugins)
Cloud & Data Fabric Platform
AI Platform

This roadmap keeps the progression logical: build intelligence → scale execution → guarantee correctness → secure and operate → extend the ecosystem → become cloud-native → add AI on top. It also aligns with the architecture already present in your repository, rather than replacing it with an unrelated design.


| Part            | Name                                                                    | Primary outcome                                                                                                        | Major functionality / scope                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P0 ✅**        | **Migration Foundation**                                                | **Prove the real migration vertical slice**                                                                            | Real DB connection → discovery → preflight → selection/configuration → planning → approval → schema creation → real bulk transport → validation → result/cutover workflow; canonical **UI → IPC → EngineGateway → AkaalSuperEngine → WorkflowEngine** exposure; no duplicate application logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **P1 ✅ FROZEN** | **Production Migration Engine + Migration Monitoring**                  | **Make the core migration runtime production-capable, recoverable and observable**                                     | Parallel workers; large-table partitioning; adaptive batching; connection pooling; durable checkpoints; deterministic resume; daemon/process restart recovery; worker crash recovery; retry/backoff; backpressure; bandwidth throttling; bounded-memory transport; LOB streaming; worker lifecycle; pause/resume/terminate; canonical live/historical telemetry and monitoring UI. **Canonical pipeline integration verified and frozen.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **P2 ✅ FROZEN** | **Schema Intelligence + Validation + Reporting**                        | **Make complex heterogeneous migrations trustworthy**                                                                  | Canonical schema model; datatype normalization/conversion; PK/FK/indexes/constraints/sequences/identities/partitions/views/procedures/functions/triggers; dependency intelligence; compatibility/conversion/risk/drift analysis; schema reconciliation; checksum/Merkle and deep row/column validation; mismatch localization; validation-only safety; certification; JSON/PDF/ZIP evidence packages and integrity protection. **P1+P2 pipeline integration verified and frozen.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **P3 ✅ FROZEN** | **CDC + Migration Lifecycle Management**                                | **Deliver near-zero-downtime migration with a durable, governed CDC lifecycle**                                        | **CDC foundation & durability:** canonical CDC identities, lifecycle/state machine, native capture, durable persistent buffering, crash-safe checkpoint/ACK/reclamation frontiers, replay/deduplication/idempotency and restart recovery. **Continuous synchronization:** transaction-aware apply, deterministic ordering/causality DAG, partition routing, parallel apply, backlog/backpressure/catch-up, schema-evolution barriers and continuous synchronization. **Advanced CDC:** bidirectional/multi-master topology, provenance/echo suppression, conflict detection/resolution, entity quarantine and governed release. **Monitoring:** authoritative CDC telemetry, lag/backlog/apply/checkpoint/conflict/worker/partition/ordering/schema/recovery/history views integrated into existing Monitoring. **Validation & reconciliation:** consistent validation windows, Levels 1–5 progressive validation, Merkle/row/column reconciliation, privacy-safe evidence and fenced/idempotent repair. **Controlled cutover:** 17-gate readiness engine, governance approvals, source quiescence contract, final boundary capture/drain, final validation, atomic cutover commit, fencing and idempotent replay. **Failback/recovery:** primary-role authority, divergence classification, reverse-sync requirements, split-brain prevention and governed failback. **Lifecycle:** canonical 24-state migration FSM, durable history and restart reconstruction. **Whole-P3 acceptance:** P3.11 verified P3.1–P3.10 pipeline reachability, authority boundaries, identity discipline, crash/restart, fencing, UI/IPC authority, security and integration; **618/618 CDC tests green**. Real-DB CDC certification remains separate from this freeze.                                       |
| **P4 ✅ FROZEN** | **Multi-Database + Universal Connectivity**                             | **Turn AKAAL's frozen P0–P3 engine into a production-grade heterogeneous data migration and synchronization platform** | **Universal connectivity foundation:** connector contract, registry, capability manifests, compatibility/proof/support models, connection profiles and legacy bridges. **Relational:** Oracle, PostgreSQL, MySQL, MariaDB, MSSQL, IBM Db2, SQLite. **Warehouses/lakehouses:** Snowflake, BigQuery, Redshift, Databricks/Delta Lake. **NoSQL/specialized:** MongoDB, Cassandra/ScyllaDB, Neo4j, Redis/KeyDB, Elasticsearch/OpenSearch. **Streaming:** Kafka/Confluent/MSK, Kinesis, Event Hubs, Pub/Sub. **Storage:** HDFS, S3, GCS, Azure Blob, MinIO and common dataset formats. **Managed/cloud connectivity:** AWS, Azure, GCP and OCI profiles; RDS/Aurora, Cloud SQL/AlloyDB, Azure SQL and equivalent managed-service integration; private/on-prem connectivity, SSH/bastion/tunnel foundations. **Connector requirements:** discovery, capability negotiation, source/target operation, schema extraction, bulk read/write, native incremental/CDC interfaces where supported, native positions, validation access, failure handling, restart safety, security/sanitization and truthful support/proof states. **Final integration:** universal source→target compatibility matrix and proof that every connector feeds the existing P0–P3 canonical authorities without duplicate transport, CDC, checkpoint, schema, validation, monitoring, cutover or lifecycle engines. **P4.1–P4.10 completed and frozen; 28 unique physical connectors + 2 managed profiles / 30 registered identities; production mock/stub connectors = 0; source and target executability physically traced; 231/231 P4 acceptance tests green. Final P4 frozen baseline: `c63f96b7ceea849f34af587bf03e34777a428557`. Live external-system certification remains explicitly separate from the P4 freeze.** |
P5 ✅ FROZEN
Enterprise Migration Controls + Governance + Security + Configuration & Recovery
Turn migration intent into an immutable, governed, recoverable and provably enforced execution contract
P5.1–P5.8: planning/configuration authority; selection/filtering/projection; advanced mapping; transformation/cleansing; privacy/masking/tokenization; deduplication/data quality/conflict policy; governed SQL/hooks and related migration controls. P5.9: maximum-assurance enterprise security foundation—identity/session context, authorization, RBAC/ABAC enforcement boundaries, SoD/JIT, governance, approvals, execution authorization, Execution Identity Seal, zero-trust runtime enforcement and fencing. P5.10: governed execution for protected operations with exact approval binding, authorization and engine verification. P5.11: reusable/versioned configuration lifecycle, deterministic canonical serialization/fingerprints, immutable resolved configuration, initialization identity and maximum-assurance exact-execution recovery. P5.12: adversarial Whole-P5 integration/acceptance gate proving intent preservation across IPC → Pipeline → immutable ExecutionPlan → Engine → physical boundaries → checkpoint/recovery → Validation #11 → Evidence #12 → audit/completion. Local closure: 1,679/1,679 Whole-P5 acceptance executions passed; 48/48 flagship P5.12; 4,347/4,347 repository nodes accounted; 0 unexplained; 0 local blockers. Whole P5 locally ACCEPTED & FROZEN. 216 external/live cases remain DEFERRED and NOT LIVE_PROVEN.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
| **P6 ✅ FROZEN** | **Enterprise Operations + Observability + Health + Fleet + Scheduling + Capacity + Incident Management** | **Give operators a complete backend platform-wide production operations and control plane over the frozen P0–P5 authorities** | **Enterprise Operations Control Plane; runtime operational controls; pause/resume/terminate; truthful runtime mutability classification; bandwidth/batch/CDC operational controls where supported; durable operation admission/execution semantics; idempotency; stale-execution fencing; ambiguous-execution reconciliation with no automatic redispatch; Unified Observability + Correlation Fabric; platform-wide migration/execution/node/service correlation; metrics, events and logs; bounded durable subscription/history access; Prometheus-compatible metrics export; Grafana-compatible observability surfaces; OpenTelemetry correlation and trace propagation where supported; Health + Diagnostics + Recovery Operations; explainable health; UNKNOWN ≠ HEALTHY; degradation and dependency causality; sanitized diagnostic snapshots; checkpoint/reconstruction visibility; recovery eligibility and canonical recovery delegation; Fleet + Node + Service Management; stable node identity; liveness; versions/builds/capabilities; workload associations; maintenance; durable drain/undrain where supported; Scheduling + Operational Retention; cron/IANA timezone/DST-aware scheduling; deterministic occurrence identity; schedule revisions; lease/fencing; occurrence-time authorization; misfire/overlap policies; crash/restart-safe scheduling; retention preview/execution; bounded retention; active-migration, Evidence #12, recovery and ambiguous-idempotency protection; Capacity + Storage + Resource Intelligence; measured/derived/estimated/unknown resource truth; authoritative storage accounting; durable capacity history; evidence-gated forecasting; exhaustion/risk intelligence; non-mutating operational recommendations; Alerts + Incidents + Notifications; typed alert rules; deterministic deduplication; alert lifecycle/suppression; policy-driven incident correlation; durable incident timeline; secret-safe notifications; structured-log and webhook delivery; notification idempotency; explicit ambiguous-delivery handling with no blind redispatch; cross-P6 operational flows; tenant isolation and P5 governance enforcement throughout; dynamic Final Operations Gateway providing the unified northbound P6 surface. P1/P3/P5 authorities remain canonical and are consumed rather than rebuilt. Worker-pool resizing remains `UNSUPPORTED_BY_DESIGN`; P7B infrastructure orchestration/autoscaling/GitOps/multi-region fabric remains out of P6. Whole-P6 hostile acceptance completed and locally frozen with **4,440-node test universe, Campaign A 39/39, Campaign B 54/54, 0 known local acceptance blockers**, while external/live verification remains separately and truthfully deferred rather than represented as `LIVE_PROVEN`.** |
                                                                                                                                                                                                                      | **P7 ✅ FROZEN** | **Zero Trust + Enterprise Security + Compliance + Audit** | **Complete and harden the Fortune-500 security boundary across identity, authorization, tenant isolation, cryptographic protection, secure connectivity, governance, audit/evidence, and hostile security acceptance.** | **Zero Trust trust model; TLS/mTLS; PKI and certificate lifecycle; SPIFFE/SPIRE workload identity foundations; enterprise identity federation; OAuth/OIDC; SAML/SSO; LDAP/AD; MFA; SCIM and JIT identity; trusted session reconstruction; centralized authorization; authoritative RBAC; ABAC; JIT privilege; Separation of Duties and maker-checker controls; HIGH-assurance protected operations; caller role/scope injection prevention; Vault-style secret references; secret governance, dynamic credentials and rotation foundations; KMS/HSM foundations; CMK/BYOK and key lifecycle; encryption-aware migration; secure tunnels, bastions, proxies and private-connectivity foundations; canonical tenant/workspace/project/migration resource isolation; tenant-bound sessions; fail-closed resource-scope enforcement; trusted Pipeline→Engine security-context propagation; untrusted-payload isolation; cross-tenant anti-enumeration controls; tenant-aware KMS defense; tamper-evident/hash-chained security audit; authorization and security-decision evidence; secret-safe forensic evidence; governance/JIT authorization controls; GDPR, PCI-DSS, HIPAA, SOC 2 and ISO 27001-oriented technical controls; complete hostile acceptance across authentication, assurance, authorization, tenant boundaries, RBAC/ABAC/JIT/SoD, secrets, cryptography, evidence and Pipeline→Engine trust. Campaigns A–C accepted and frozen for locally proven scope; external infrastructure remains EXTERNAL_DEFERRED where not physically exercised.** |
                                                                                                                                                                                                                                                                                                                                                                                                                                   | **P7A  ✅ FROZEN** | **Enterprise Platform + Universal Connector Ecosystem** | **Make AKAAL securely extensible and expand the canonical physical provider ecosystem without duplicating core authorities** | **Secure extension platform and lifecycle; cryptographic package provenance, signature verification, publisher trust, revocation and quarantine; subprocess sandboxing and permission enforcement; capability-truth and negative-capability enforcement; connector framework/SDK; executable connector certification and compatibility; canonical REST enterprise API through Pipeline authority; extension registry/distribution foundations; streaming, messaging, SaaS and enterprise-application connectivity; universal file/dataset and metadata/lineage interoperability under repository-proven scope; provider-native transport integration through the canonical TransportAuthority/TransportDriverRegistry; 20-provider expansion from 28 → 48 physical providers, including CockroachDB, YugabyteDB, TiDB, SingleStore, ClickHouse, Teradata, Vertica, SAP HANA, SAP ASE, IBM Informix, Couchbase, DynamoDB, Cosmos DB, Cloud Spanner, InfluxDB, Pulsar, RabbitMQ, Salesforce, SAP Application Ecosystem and ServiceNow; whole-ecosystem hostile acceptance and certification. **Final: 48/48 physical providers · 20/20 expansion complete · 230/230 Remaining-10 locally actionable acceptance cells proven · 5,551 passed / 160 skipped / 0 failed · OWNER ACCEPTED & FROZEN · 10/10 locally proven scope.** Live vendor proofs unavailable locally remain `EXTERNAL_DEFERRED`.** |
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **P7B**         | **Cloud + Hybrid + Data Fabric Platform**                               | **Make AKAAL cloud-native, hybrid and topology-aware**                                                                 | AWS/Azure/GCP/OCI environments; managed database integrations; cloud↔cloud, on-prem↔cloud and hybrid migrations; private connectivity; object-storage pipelines; Kubernetes; operators; Helm; autoscaling; rolling upgrades; self-healing clusters; IaC; Terraform; Pulumi; GitOps; CRDs; multi-cloud/multi-region topology; locality/data-sovereignty controls; geo-aware scheduling and failover.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **P7C**         | **AI-Native Migration Intelligence + Optimization**                     | **Intelligently operate and optimize the completed AKAAL platform**                                                    | AI migration planning; strategy generation; dependency and cutover optimization; capacity planning; SQL/procedure/function/trigger conversion assistance; schema optimization; RCA; failure diagnosis; bottleneck detection; performance tuning; self-tuning recommendations; security/compliance/cost recommendations; architecture analysis; conversational migration assistant; natural-language planning; reports/docs/executive summaries; predictive scaling/maintenance and intelligent scheduling.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **P7D**         | **Unified Enterprise Migration Experience + Final Product Integration** | **Turn all completed capabilities into one coherent enterprise migration product before certification**                | Complete workflow: **connection → discovery → assessment → schema intelligence → planning → governance → initial load → CDC → validation → cutover/failback → certification/reporting.** Migration Conductor coordinating existing authorities. Unified enterprise UI including Creation Wizard, Connections Hub, Preflight & Capacity Scout, Schema/Risk Studio, DAG Planner, Governance Centre, Mission Control, Worker/Fleet Manager, Reliability Center, CDC Control Center, Validation/Reconciliation, Reports/Dossier, Trust Certification and Evidence Portal. Consistent identity, navigation, lifecycle, errors/actions, backend truth, role-aware actions, notifications and accessibility. **No duplicate transport/CDC/schema/validation/reporting/security/monitoring authorities.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **P8**          | **Resilience + Scale + Performance Certification**                      | **Prove the final integrated engine and platform at enterprise scale**                                                 | Test the **P7D-integrated product**, not isolated components: 500M–1B+ rows where practical; sustained/peak throughput; very-large-table workloads; concurrency; long-duration soak; memory/storage pressure; process/worker/node failures; crash/restart; checkpoint/CDC recovery; network/source/target/cloud/cluster failures; backpressure stress; performance tuning; resource-envelope determination and final migration-matrix scale certification. **This is where P3/P4 receive real production-scale/live-system evidence rather than reopening their implementation freezes.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **P9**          | **Packaging + Commercial Deployment**                                   | **Turn certified AKAAL into deliverable enterprise software**                                                          | Windows/macOS/Linux packaging; signed installers; desktop + daemon/service deployment; container/cloud packaging; installation/update lifecycle; rollback-safe upgrades; versioning; licensing; deployment profiles; bootstrap/configuration; enterprise installation docs; diagnostics/support bundles; supportability and release engineering.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **P10**         | **Final Enterprise Acceptance**                                         | **Certify the entire AKAAL product together**                                                                          | Complete packaged-product E2E acceptance: migration matrices; schema conversion; bulk transport; CDC/cutover/failback; validation; controls; security; governance; audit; operations; observability; Health Center; fleet/cluster; cloud/hybrid; connectors; AI workflows; P7D unified UX; recovery; scale; soak; packaging; upgrades; installation/deployment and real-customer-style acceptance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |









| Part      | Name                                                        | Primary outcome                                                                                      | Major scope                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P5.1**  | **Enterprise Migration Planning + Configuration Authority** | Establish the canonical planning/control model used by every later P5 capability                     | `MigrationProject → MigrationPlan → PlanVersion → immutable ExecutionPlan`; draft/version/clone/template lifecycle; simple + advanced planning modes; source/target topology; arbitrary source-schema → target-schema routing; 1:1, many:1, controlled 1:many and many:many mappings; object routing; configuration precedence/inheritance; compatibility integration; dependency/impact analysis; risk integration; dry-run compilation; immutable execution snapshots; plan diff/history; restart reconstruction; bulk/CDC policy consistency. **UI:** functional Migration Planning workspace, plan versions, topology/routing editor, review/compile view. |
| **P5.2**  | **Data Selection + Filtering + Projection**                 | Give operators exact control over what data migrates                                                 | Database/catalog/schema/table/collection/object selection where applicable; include/exclude; wildcard/pattern rules; column projection; row predicates; partition/range selection; sampling; dependency-aware selection; FK/dependency warnings; source-side predicate pushdown where safe; estimated selected volume; selection preview; invalid-selection fail-closed validation. **UI:** hierarchical Data Selection Studio with search, selection tree, filters, dependencies and preview.                                                                                                                                                                 |
| **P5.3**  | **Advanced Schema, Object + Column Mapping**                | Allow heterogeneous source structures to be deliberately reshaped onto targets                       | Schema routing; table/object rename and mapping; source object → different target schema/object; column rename/reorder/mapping; target defaults; generated/ignored columns; merge/split mapping foundations; datatype-aware mapping validation; mapping conflicts; naming collisions; dependency preservation; bulk mapping; mapping templates/import/export; mapping preview and deterministic compiled mappings. **UI:** Mapping Studio with source↔target visual mapping and compatibility indicators.                                                                                                                                                      |
| **P5.4**  | **Transformation + Data Cleansing**                         | Transform and normalize data consistently during migration                                           | Type-safe expression/rule model; string/numeric/date/time/boolean operations; trim/case/normalize; NULL/default handling; regex; conditional transformations; derived fields; lookup/reference transformations; malformed-data handling; normalization; cleansing rules; reject/quarantine routes; deterministic execution; transformation ordering/dependencies; preview/test against sample records; identical policy semantics for bulk + CDC. **UI:** Transformation Studio with rule builder, expression editor and before/after preview.                                                                                                                 |
| **P5.5**  | **Privacy, Masking + Tokenization Controls**                | Provide enterprise-grade data privacy controls inside migration plans                                | Static and deterministic masking; redaction; hashing; pseudonymization; tokenization framework; format-preserving transformation where justified; referentially consistent masking; policy-based sensitive-column treatment; reusable privacy rules; safe preview; bulk/CDC consistency; prevention of accidental raw sensitive-data exposure in previews/logs/evidence. **UI:** Privacy Controls Studio.                                                                                                                                                                                                                                                      |
| **P5.6**  | **Deduplication + Data Quality + Conflict Policies**        | Control dirty, duplicate, invalid and conflicting data deterministically                             | Exact/key-based deduplication; composite uniqueness keys; duplicate detection; survivor rules; existing-target collision behaviour; insert/update/delete policies; NULL/overflow/truncation/invalid-value policies; reject/quarantine; thresholds; data-quality gates; configurable failure/warning policies; integration with existing P3 conflict authority rather than recreating conflict resolution. **UI:** Data Quality & Conflict Studio.                                                                                                                                                                                                              |
| **P5.7**  | **Custom SQL, Hooks + Governed Extensibility**              | Allow controlled customer-specific execution logic without compromising runtime safety               | Pre/post migration SQL; pre/post object operations; safe batch/session hooks where justified; source/target session initialization; target preparation/finalization; parameters; ordering/dependencies; transaction semantics; timeout/retry behaviour; allow/deny rules; dangerous-statement detection; approval requirements; rollback/failure behaviour; audit/evidence; secrets sanitization. **UI:** SQL & Hooks Studio with editor, stage/order configuration, safety analysis and approval state.                                                                                                                                                       |
| **P5.8**  | **Execution Modes + Validation-Only Operations**            | Make AKAAL usable for assessment, validation and partial operations without forcing a full migration | Full migration; validation-only; schema-only; data-only; reconciliation-only; initial-load-only; CDC-only where valid; selected-object validation; dry-run; preflight; compare-without-migrate; revalidation; controlled repair eligibility; clone/rerun; execution-mode compatibility checks; evidence through existing P2 validation/reporting authority. **UI:** Execution Mode and Review experience integrated with Migration planning.                                                                                                                                                                                                                   |
| **P5.9**  | **Enterprise Setup + Workspace Administration**             | Establish AKAAL's initial configuration and ongoing administrative model                             | **First-run Enterprise Setup:** installation/node identity, organization/workspace bootstrap, first administrator, environment, storage/runtime defaults, diagnostics and optional initial connections. Ongoing organizations/workspaces; users; teams/groups; memberships; ownership; environments; project ownership; administrative defaults; configuration scopes; reusable templates; connection visibility; quotas/limits foundations. Configuration remains editable post-setup. **UI:** first-run Enterprise Setup + Administration Center. P7 later supplies hardened identity/SSO/Zero-Trust enforcement.                                            |
| **P5.10** | **RBAC Configuration + Policy + Approval Administration**   | Make migration configuration and execution governable                                                | Role/permission model configuration; migration permissions; administrative permissions; policy definitions; approval chains; approver groups; maker-checker/four-eyes; environment-specific policies; privileged-operation policies; plan-change approval; configuration locking; exceptions/waivers; policy simulation; approval evidence/history; integration with existing workflow/governance authorities. **UI:** Governance & Access areas inside Administration. P7 later hardens identity and authorization enforcement.                                                                                                                               |
| **P5.11** | **Reusable Templates + Configuration Lifecycle**            | Make complex enterprise migration configurations reusable and manageable at scale                    | Migration templates; mapping templates; transformation/privacy/data-quality policy templates; organization/environment defaults; inheritance; override rules; template versioning; cloning; import/export; promotion between environments; configuration diff; dependency tracking; deprecation; immutable references from executed migrations; prevent later template edits from altering historical jobs. **UI:** Template & Configuration Library integrated across Migration/Administration/Settings.                                                                                                                                                      |
| **P5.12** | **Whole-P5 Production Acceptance + Immutable Freeze**       | Prove P5 works as one real control plane over frozen P0–P4                                           | Forensic authority audit; every operator-facing UI → IPC → canonical P5 authority → P0–P4 execution trace; simple + advanced plan execution; arbitrary schema/object routing; mapping/transformation/masking/filter/dedup correctness; bulk↔CDC consistency; restart determinism; immutable execution snapshots; validation-only proof; SQL-hook safety attacks; approval/policy bypass attacks; cross-job/org isolation; malformed configuration attacks; concurrency; configuration version/replay testing; mock/stub/dead-path audit; regression/build verification; documentation; capability ledger; final P5 freeze.                                     |





| Part      | Scope                                               | What happens with approval barriers                                                                                     |
| --------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **P5.7**  | Custom SQL, Hooks + Governed Extensibility          | Keep essentially as-is. Hooks can *declare* that approval is required, but don't build the general barrier engine here. |
| **P5.8**  | Execution Modes + Validation-Only Operations        | Keep execution-mode applicability and determine which operations/boundaries can legally exist for each mode.            |
| **P5.9**  | Enterprise Setup + Workspace Administration         | Keep as-is.                                                                                                             |
| **P5.10** | **RBAC + Policy + Approval Barrier Administration** | **Build the missing approval-barrier system here.**                                                                     |
| **P5.11** | Reusable Templates + Configuration Lifecycle        | Make barrier configurations/policies reusable/versioned where appropriate.                                              |
| **P5.12** | Whole-P5 Production Acceptance                      | Hostile-test the entire barrier system and Step 6→7→8→9 workflow.                                                       |






| Step  | Wizard step                         | Canonical responsibility                                                                                                                                          |
| ----- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Migration Definition**            | Define migration identity, context, intent, planning mode, execution mode, strategy, window/template/clone                                                        |
| **2** | **Source Instance**                 | Establish source endpoint, connectivity, authentication, network route and capabilities                                                                           |
| **3** | **Target Instance**                 | Establish target endpoint, write authority, capabilities and initial compatibility                                                                                |
| **4** | **Discovery & Advanced Scope**      | Discover topology/metadata and configure exact migration selection/filtering/projection                                                                           |
| **5** | **Mapping & Data Controls Studio**  | Configure routing, mappings, transformations, cleansing, privacy, quality, deduplication, conflict policies and hooks                                             |
| **6** | **Enterprise Configuration Center** | Configure runtime/bulk/CDC/validation/recovery/performance/cutover settings **plus approval/governance policies and approval definitions**                        |
| **7** | **Dynamic Migration Plan**          | Compile the execution DAG, dependencies, schema actions, risks, estimates/blockers and **visualize/add/configure approval barriers at safe execution boundaries** |
| **8** | **Governance & Readiness**          | Evaluate preflight, capacity, permissions, policies, waivers and required approvals against the exact plan/version/fingerprint                                    |
| **9** | **Review, Schedule & Initialize**   | Final review → freeze immutable `ExecutionPlan` → schedule/run → initialize durable execution                                                                     |



| Report section                    | Contents                                                                                                                                                                                                             |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Identity**                   | Migration ID, name, description, project/workspace, environment, priority, owner, creator, creation time, strategy/execution mode.                                                                                   |
| **2. Plan Identity**              | Plan ID, PlanVersion, revision, parent version, planning mode, compile timestamp, immutable ExecutionPlan ID and SHA-256 fingerprint.                                                                                |
| **3. Source**                     | Connector/engine/version, instance identity, endpoint/profile reference, discovered databases/catalogs and relevant capability information. **Never credentials/secrets.**                                           |
| **4. Target**                     | Target connector/engine/version, instance identity, endpoint/profile, target capabilities and compatibility result.                                                                                                  |
| **5. Discovery**                  | Discovery mode/time, databases, schemas/namespaces, objects, approximate rows/volume and discovery warnings.                                                                                                         |
| **6. Selected Scope**             | Exactly what is included/excluded, selection rules, filters, predicates, projections, partitions/ranges and resulting estimated migration volume.                                                                    |
| **7. Routing & Mapping**          | Every DB/schema/object/column route, rename, 1:1/many:1/1:many/etc. topology, mapping conflicts/warnings and resolved targets.                                                                                       |
| **8. Transformation & Cleansing** | Transformation rules, normalization/cleansing rules, derived/default fields, ordering and reject/quarantine behaviour.                                                                                               |
| **9. Privacy Controls**           | Masking/tokenization/pseudonymization policies and affected fields—policy descriptions/references, **not sensitive source values**.                                                                                  |
| **10. Data Quality**              | Dedup keys/rules, survivor policies, collision behaviour, invalid-value policies, thresholds and quarantine/failure rules.                                                                                           |
| **11. SQL & Hooks**               | Configured pre/post operations, stages, ordering, safety analysis and approval requirements. Secrets and unsafe evidence remain sanitized.                                                                           |
| **12. Execution Configuration**   | Workers, partitions, batching, queues, bandwidth, retries, checkpointing, CDC, validation, recovery, cutover/failback and other resolved settings, including provenance of inherited/overridden values where useful. |
| **13. Dynamic Execution Plan**    | Stage-1 logical plan summary, dependency graph/DAG, stages, Stage-2/runtime handoff information, blockers/warnings and plan fingerprint.                                                                             |
| **14. Compatibility & Risk**      | Connector compatibility, unsupported/degraded capabilities, dependency impact, preflight findings, risks, warnings, blockers and accepted exceptions.                                                                |
| **15. Governance**                | Required policies, approval chain, approvers/roles, approval status/timestamps, waivers/exceptions and fingerprint against which approval was granted.                                                               |
| **16. Schedule**                  | Run-now/scheduled, scheduled window, timezone, scheduling policy and immutable ExecutionPlan reference.                                                                                                              |
| **17. Validation Contract**       | Validation level/method, reconciliation requirements, thresholds, validation-only settings where applicable and cutover gating requirements.                                                                         |
| **18. Change / Version History**  | Draft/version history, who changed what/when, plan diffs, fingerprint changes, approval invalidations and reason for revisions.                                                                                      |
| **19. Initialization Record**     | Initialization timestamp, final readiness result, frozen snapshot ID, scheduler/job reference and launch status.                                                                                                     |
| **20. Evidence & Integrity**      | Report/artifact ID, generated timestamp, schema/version, SHA-256/integrity evidence and links/references to related certification/audit artifacts.                                                                   |




Rebuild AKAAL's migration workflow from first principles. Define all legitimate execution modes and lifecycle paths without being constrained by the current implementation.


Derive the required root component/authority model. Determine what an elite migration platform actually needs and assign exactly one canonical responsibility to each authority.


Define authority contracts. Inputs/outputs, state ownership, persistence, side effects, failures, checkpoints, restart semantics, idempotency, security/governance, evidence, events, etc.


Forensically inspect the existing repository by responsibility. For every required authority, find every candidate implementation and classify it strictly as KEEP / RECTIFY / MERGE / REPLACE / REMOVE / BUILD based on actual code—not names, tests, phase claims, or assumptions.


Make selected implementations genuinely production-grade. Remove production semantic mocks, false success, no-ops, unjustified hardcoding, swallowed failures, machine-specific behavior, and other fake/static behavior. Preserve legitimate test mocks.


Build the new canonical wiring. One production entry path, capability contract, application boundary, orchestration authority, explicit domain authorities, state/evidence flow, and clean UI → Tauri → IPC integration. Then retire old execution paths only after their required functionality has been absorbed and verified.


Reverify the entire P0 → P5.6 roadmap against the reconstructed runtime. Every claimed capability gets implementation, reachability, real-side-effect, durability/restart, failure-semantics, authority, integration, and appropriate real-system evidence. Only after that do we declare those phases frozen again.


Target UI
AKAAL
│
│
├══════════════════════════════════════════════════════════════
│  1. DASHBOARD
├══════════════════════════════════════════════════════════════
│
├── Enterprise Overview
├── Active Migrations
├── Migration Health
├── Risk / Blockers
├── Pending Approvals
├── Alerts / Incidents
├── Platform Health
├── Capacity Summary
├── Fleet / Cluster Summary
├── Security / Compliance Summary
└── Recent Activity
│
│
│
├══════════════════════════════════════════════════════════════
│  2. MIGRATION
├══════════════════════════════════════════════════════════════
│
├── 2.1 Migration Portfolio
│   ├── All Migrations
│   ├── Active
│   ├── Scheduled
│   ├── Attention Required
│   ├── Completed
│   ├── Failed / Interrupted
│   └── Archived
│
│
├── 2.2 Create Migration
│   │
│   └── 9-Step Creation Wizard
│       │
│       ├── STEP 1 — Migration Definition
│       │   ├── Identity / Description
│       │   ├── Business Context
│       │   ├── Owner
│       │   ├── Environment
│       │   ├── Priority
│       │   ├── Optional Project / Workspace
│       │   ├── Planning Mode
│       │   │   ├── Standard
│       │   │   └── Advanced
│       │   │
│       │   ├── Execution Mode
│       │   │   ├── M1 — Bulk Migration
│       │   │   ├── M2 — Bulk + CDC
│       │   │   ├── M3 — CDC / Continuous Replication
│       │   │   ├── M4 — Incremental Query / Polling
│       │   │   ├── M5 — State-Based Synchronization
│       │   │   ├── M6 — Schema Only
│       │   │   ├── M7 — Data Only
│       │   │   └── M8 — Validation / Reconciliation Only
│       │   │
│       │   ├── Migration Window
│       │   ├── Start from Template
│       │   └── Clone Migration
│       │
│       ├── STEP 2 — Source Instance
│       │   ├── Saved / New Connection
│       │   ├── Authentication
│       │   ├── Network Route
│       │   ├── Connector Properties
│       │   ├── Connectivity Test
│       │   └── Capability Discovery
│       │
│       ├── STEP 3 — Target Instance
│       │   ├── Saved / New Connection
│       │   ├── Authentication
│       │   ├── Network Route
│       │   ├── Connector Properties
│       │   ├── Connectivity Test
│       │   ├── Write Authority
│       │   ├── Capability Discovery
│       │   └── Source ↔ Target Compatibility
│       │
│       ├── STEP 4 — Discovery & Advanced Scope
│       │   │
│       │   ├── Discovery & Assessment
│       │   │   ├── Instance Topology
│       │   │   ├── Database / Catalog Discovery
│       │   │   ├── Schema / Namespace Discovery
│       │   │   ├── Object Discovery
│       │   │   ├── Metadata Inspection
│       │   │   ├── Dependency Analysis
│       │   │   ├── Compatibility Assessment
│       │   │   ├── Impact Assessment
│       │   │   └── Risk Assessment
│       │   │
│       │   └── Selection & Scope
│       │       ├── Database / Catalog Selection
│       │       ├── Schema / Namespace Selection
│       │       ├── Object Selection
│       │       ├── Include / Exclude Rules
│       │       ├── Patterns
│       │       ├── Column Projection
│       │       ├── Row Predicates
│       │       ├── Partition / Range Selection
│       │       ├── Sampling
│       │       ├── Dependency Warnings
│       │       ├── Selection Preview
│       │       └── Volume Estimation
│       │
│       ├── STEP 5 — Mapping & Data Controls Studio
│       │   │
│       │   ├── Mapping
│       │   │   ├── Schema Routing
│       │   │   ├── Object Mapping
│       │   │   ├── Column Mapping
│       │   │   ├── Rename / Reorder
│       │   │   ├── Merge / Split
│       │   │   ├── Defaults / Generated / Ignored
│       │   │   └── Mapping Preview
│       │   │
│       │   ├── Transformation & Cleansing
│       │   │   ├── Transformation Rules
│       │   │   ├── Expression Builder
│       │   │   ├── Normalization
│       │   │   ├── NULL / Default Handling
│       │   │   ├── Derived Fields
│       │   │   ├── Lookups
│       │   │   ├── Malformed Data Handling
│       │   │   ├── Reject / Quarantine
│       │   │   └── Before / After Preview
│       │   │
│       │   ├── Privacy
│       │   │   ├── Masking
│       │   │   ├── Redaction
│       │   │   ├── Hashing
│       │   │   ├── Pseudonymization
│       │   │   ├── Tokenization
│       │   │   ├── Format Preservation
│       │   │   └── Referential Consistency
│       │   │
│       │   ├── Data Quality & Conflict
│       │   │   ├── Deduplication
│       │   │   ├── Duplicate Detection
│       │   │   ├── Composite Uniqueness
│       │   │   ├── Survivor Rules
│       │   │   ├── Invalid Data Policies
│       │   │   ├── Collision Policies
│       │   │   ├── Quarantine
│       │   │   └── Conflict Policies
│       │   │
│       │   └── SQL & Hooks
│       │       ├── Pre / Post Migration SQL
│       │       ├── Object Hooks
│       │       ├── Session Hooks
│       │       ├── Parameters
│       │       ├── Ordering / Dependencies
│       │       ├── Transaction Semantics
│       │       ├── Timeout / Retry
│       │       ├── Safety Analysis
│       │       └── Approval Requirements
│       │
│       ├── STEP 6 — Enterprise Configuration Center
│       │   │
│       │   ├── Standard Mode
│       │   │   ├── Enterprise-Level Controls
│       │   │   ├── AKAAL Recommendations
│       │   │   └── Automatically Derived Low-Level Settings
│       │   │
│       │   ├── Advanced Mode
│       │   │   ├── Runtime / Orchestration
│       │   │   ├── Workers / Parallelism
│       │   │   ├── Partitioning
│       │   │   ├── Batching
│       │   │   ├── Connection Pools
│       │   │   ├── Queues / Buffers
│       │   │   ├── Backpressure
│       │   │   ├── Bandwidth
│       │   │   ├── Bulk Transport
│       │   │   ├── CDC
│       │   │   ├── Incremental / Polling
│       │   │   ├── State Synchronization
│       │   │   ├── Validation
│       │   │   ├── Checkpointing / Durable State
│       │   │   ├── Recovery
│       │   │   ├── Retry / Failure
│       │   │   ├── LOB Handling
│       │   │   ├── Performance
│       │   │   ├── Schema Evolution
│       │   │   ├── Cutover / Failback
│       │   │   ├── Scheduling
│       │   │   ├── Resource Limits
│       │   │   ├── Connector Controls
│       │   │   └── Scoped Dynamic Overrides
│       │   │       ├── Organization
│       │   │       ├── Environment
│       │   │       ├── Migration
│       │   │       ├── Execution Mode
│       │   │       ├── DAG Node
│       │   │       ├── Object
│       │   │       ├── Partition
│       │   │       └── Connector
│       │   │
│       │   └── Approval Barrier Configuration
│       │
│       ├── STEP 7 — Dynamic Migration Plan
│       │   ├── Logical Plan
│       │   ├── Dynamic Execution DAG
│       │   ├── Schema Actions
│       │   ├── Dependencies
│       │   ├── Execution Ordering
│       │   ├── Node Configuration / Overrides
│       │   ├── Approval Barriers
│       │   ├── Compatibility
│       │   ├── Risk
│       │   ├── Work / Resource Estimates
│       │   ├── Warnings / Blockers
│       │   ├── Plan Versions / Diff
│       │   ├── Dry Run
│       │   └── Plan Fingerprint
│       |   |  
│       │   └── Approval Barrier Configuration
│       │
│       ├── STEP 8 — Governance & Readiness
│       │   ├── Preflight
│       │   ├── Environment / Capacity Readiness
│       │   ├── Permissions
│       │   ├── Security / Policy Checks
│       │   ├── Migration Policies
│       │   ├── Approval Barriers
│       │   ├── Approval Chain / Status
│       │   ├── Waivers / Exceptions
│       │   ├── Fingerprint Verification
│       │   └── Execution Authorization
│       │
│       └── STEP 9 — Review, Schedule & Initialize
│           ├── Final Review
│           ├── Compile Immutable ExecutionPlan
│           ├── ExecutionPlan Fingerprint
│           ├── Run Now
│           ├── Schedule
│           └── Initialize Durable Execution
│                    │
│                    ▼
│              MISSION CONTROL
│
│
├── 2.3 Projects & Workspaces
│   ├── Projects
│   ├── Workspaces
│   ├── Overview
│   ├── Assigned Migrations
│   ├── Owners / Members
│   ├── Environment
│   ├── Activity
│   ├── Assign Migration
│   └── Move Migration
│
│   Migration may be:
│   • independent
│   • created inside a project/workspace
│   • assigned later
│   • moved later with authorization
│
├── 2.4 Connections
│   ├── Connections
│   ├── Profiles
│   ├── Capabilities
│   ├── Connectivity Tests
│   ├── Network Routes / Tunnels
│   ├── Health
│   └── Connector Details
│
├── 2.5 Mission Control
│   │
│   ├── Overview
│   │   ├── Migration State
│   │   ├── Progress
│   │   ├── Current / Next Operation
│   │   ├── Execution DAG
│   │   ├── Throughput / ETA
│   │   ├── Warnings / Blockers
│   │   └── Approval Barriers
│   │
│   ├── Runtime
│   │   ├── Workers
│   │   ├── Partitions
│   │   ├── Queues
│   │   ├── Checkpoints
│   │   └── Runtime Events
│   │
│   ├── Controls
│   │   ├── Start
│   │   ├── Pause
│   │   ├── Resume
│   │   ├── Terminate
│   │   └── Recover
│   │
│   └── Capability-Driven Operations
│       │
│       ├── Bulk
│       │
│       ├── CDC
│       │   ├── Capture / Apply
│       │   ├── Lag / Backlog
│       │   ├── Transactions / Ordering
│       │   ├── Parallel Apply
│       │   ├── Schema Evolution
│       │   ├── Conflicts / Quarantine
│       │   ├── Bidirectional
│       │   ├── Catch-Up
│       │   └── Recovery
│       │
│       ├── Incremental / Polling
│       │
│       ├── State Synchronization
│       │
│       ├── Schema Execution
│       │
│       ├── Validation & Reconciliation
│       │   ├── Validation Levels
│       │   ├── Row Counts
│       │   ├── Checksums / Merkle
│       │   ├── Row / Column Comparison
│       │   ├── Mismatch Localization
│       │   ├── Reconciliation
│       │   ├── Governed Repair
│       │   └── Evidence
│       │
│       └── Cutover & Failback
│           ├── Readiness
│           ├── Source Quiescence
│           ├── Final Drain
│           ├── Final Validation
│           ├── Approval
│           ├── Atomic Commit
│           ├── Fencing
│           ├── Failback Evaluation
│           ├── Failback Execution
│           └── Recovery
│
│   NOTE:
│   Only capabilities relevant to the migration's mode,
│   connector capabilities and lifecycle are exposed.
│
├── 2.6 Validation Operations
│   ├── New Validation
│   ├── Active Validations
│   ├── Validation History
│   ├── Source / Target
│   ├── Scope
│   ├── Configuration
│   ├── Validation Levels
│   ├── Row Counts
│   ├── Checksums / Merkle
│   ├── Row / Column Comparison
│   ├── Mismatch Analysis
│   ├── Reconciliation
│   ├── Governed Repair
│   └── Evidence
│
├── 2.7 Migration History
│   ├── Lifecycle / Timeline
│   ├── Execution History
│   ├── Plan / Configuration History
│   ├── Approval History
│   ├── Validation History
│   ├── Cutover / Failback History
│   ├── Recovery History
│   └── Audit Trail
│
└── 2.8 Templates
    └── Available Migration Templates
        (creation/use surface; enterprise template
         ownership remains under Administration)
│
│
│
├══════════════════════════════════════════════════════════════
│  3. MONITORING
├══════════════════════════════════════════════════════════════
│
├── 3.1 Overview
│   ├── Platform Status
│   ├── Active Workloads
│   ├── Health
│   ├── Alerts
│   └── Capacity
│
├── 3.2 Migration Monitoring
│   ├── All Running Migrations
│   ├── Bulk
│   ├── CDC
│   ├── Incremental / Polling
│   ├── State Synchronization
│   ├── Schema / Data Operations
│   └── Validation Operations
│
│   NOTE:
│   Capability-driven. A Bulk-only migration does NOT
│   suddenly display meaningless CDC telemetry.
│
├── 3.3 Performance
│   ├── Throughput
│   ├── Latency
│   ├── Worker / Partition Performance
│   ├── Queue / Backpressure
│   ├── Resource Usage
│   ├── Bottlenecks
│   └── Historical Performance
│
├── 3.4 Health Center
│   ├── Platform
│   ├── Runtime / Engine
│   ├── Connectors
│   ├── Databases / Endpoints
│   ├── Queues / Buffers
│   ├── Storage
│   ├── IPC / Services
│   ├── Dependencies
│   └── Diagnostics
│
├── 3.5 Infrastructure & Fleet
│   ├── Fleet
│   │   ├── Nodes / Agents
│   │   ├── Workers
│   │   ├── Health
│   │   ├── Versions
│   │   ├── Assignments
│   │   └── Lifecycle
│   │
│   ├── Clusters
│   │   ├── Clusters / Nodes
│   │   ├── Workload Distribution
│   │   ├── Kubernetes Workloads
│   │   ├── Scaling / Autoscaling
│   │   ├── Failover
│   │   ├── Regions / Locality
│   │   └── Topology
│   │
│   └── Capacity
│       ├── CPU
│       ├── Memory
│       ├── Storage
│       ├── Network
│       ├── Queue Capacity
│       └── Forecasts
│
├── 3.6 Reliability Center
│   ├── Failures
│   ├── Recovery
│   ├── Checkpoints / Resume
│   ├── Restart History
│   ├── Resilience
│   ├── Anomalies
│   ├── RCA
│   └── Reliability History
│
├── 3.7 Alerts & Incidents
│   ├── Active Alerts
│   ├── Alert Rules
│   ├── Incidents
│   ├── Correlation
│   ├── Escalation
│   └── History
│
└── 3.8 Observability
    ├── Metrics
    ├── Logs
    ├── Distributed Traces
    ├── Services
    ├── Migration Correlation
    ├── Runtime Events
    └── OpenTelemetry
│
│
│
├══════════════════════════════════════════════════════════════
│  4. REPORTS
├══════════════════════════════════════════════════════════════
│
├── 4.1 Reports Catalog
│   ├── Migration
│   ├── Schema / Compatibility
│   ├── Validation / Reconciliation
│   ├── Data Quality
│   ├── Performance
│   ├── CDC
│   ├── Cutover / Failback
│   ├── Recovery / Reliability
│   ├── Security
│   ├── Compliance
│   ├── Governance / Approval
│   ├── Audit
│   ├── Infrastructure / Fleet
│   └── Executive
│
├── 4.2 Trust Certification
│   ├── Certification Status
│   ├── Migration Certification
│   ├── Validation Certification
│   └── Verification
│
└── 4.3 Evidence Portal
    ├── Evidence Explorer
    ├── Dossiers
    ├── Certificates
    ├── Evidence Packages
    ├── Integrity Verification
    ├── Export
    └── Archive
│
│
│
├══════════════════════════════════════════════════════════════
│  5. ADMINISTRATION
├══════════════════════════════════════════════════════════════
│
├── 5.1 Enterprise
│   ├── Enterprise Setup
│   ├── Organizations
│   ├── Workspaces
│   ├── Environments
│   ├── Ownership
│   └── Quotas / Limits
│
├── 5.2 People & Access
│   ├── Users
│   ├── Teams / Groups
│   ├── Roles
│   ├── Permissions
│   ├── RBAC
│   ├── ABAC
│   ├── JIT Access
│   └── Separation of Duties
│
├── 5.3 Governance Centre
│   ├── Policies
│   ├── Approval Chains
│   ├── Approver Groups
│   ├── Maker / Checker
│   ├── Privileged Operations
│   ├── Exceptions / Waivers
│   ├── Policy Simulation
│   └── Governance History
│
├── 5.4 Identity & Security
│   ├── SSO
│   │   ├── OIDC
│   │   └── SAML
│   ├── MFA
│   ├── LDAP / Active Directory
│   ├── SCIM
│   ├── Identity Federation
│   ├── Service / Workload Identity
│   ├── SPIFFE / SPIRE
│   ├── Certificates
│   ├── Secrets / Vault
│   ├── KMS / CMK / BYOK
│   └── Rotation
│
├── 5.5 Template & Configuration Library
│   ├── Migration Templates
│   ├── Mapping Templates
│   ├── Transformation Templates
│   ├── Privacy Policies
│   ├── Data Quality Policies
│   ├── Configuration Profiles
│   ├── Versions
│   ├── Promotion
│   ├── Import / Export
│   └── Deprecation
│
├── 5.6 Connector & Plugin Center
│   ├── Connector Registry
│   ├── Installed Connectors
│   ├── Capabilities
│   ├── Compatibility
│   ├── Certification
│   ├── Plugins
│   ├── Plugin Security / Lifecycle
│   └── SDK / Developer Configuration
│
├── 5.7 Cloud & Infrastructure Configuration
│   ├── Cloud Environments
│   │   ├── AWS
│   │   ├── Azure
│   │   ├── GCP
│   │   └── OCI
│   ├── Kubernetes Configuration
│   ├── Private Connectivity
│   ├── Hybrid Environments
│   ├── Regions
│   ├── Data Sovereignty
│   ├── Infrastructure as Code
│   └── GitOps
│
│   NOTE:
│   Configuration/registration lives here.
│   Live cluster/fleet operation lives in Monitoring.
│
├── 5.8 Compliance
│   ├── Control Frameworks
│   ├── GDPR
│   ├── PCI-DSS
│   ├── HIPAA
│   ├── SOC 2
│   ├── ISO-Oriented Controls
│   └── Compliance Evidence
│
├── 5.9 Audit
│   ├── Audit Policies
│   ├── Audit Trail
│   ├── Evidence Retention
│   └── Tamper Evidence
│
└── 5.10 Platform Administration
    ├── Nodes / Services
    ├── Deployment
    ├── Versions
    ├── Licensing
    ├── Updates
    └── Support / Diagnostics
│
│
│
├══════════════════════════════════════════════════════════════
│  6. SETTINGS
├══════════════════════════════════════════════════════════════
│
├── 6.1 General
├── 6.2 Appearance
│
├── 6.3 Runtime & Migration Defaults
│   ├── Runtime
│   ├── Workers / Parallelism
│   ├── Batching
│   ├── Queues
│   ├── Resource Limits
│   ├── Bulk
│   ├── CDC
│   ├── Incremental / Polling
│   ├── State Synchronization
│   ├── Validation
│   └── Recovery
│
├── 6.4 Connector Defaults
│
├── 6.5 Storage & Retention
│   ├── Checkpoints
│   ├── CDC Buffers
│   ├── Reports / Evidence
│   ├── Logs
│   └── Retention Policies
│
├── 6.6 Notifications
│   ├── Email
│   ├── Slack
│   ├── Microsoft Teams
│   ├── Webhooks
│   └── Escalation Defaults
│
├── 6.7 Integrations
│   ├── Observability Integrations
│   ├── Notification Integrations
│   ├── Catalog / Lineage Integrations
│   └── Installed Enterprise Integrations
│
├── 6.8 AI & Intelligence
│   ├── Assistant Configuration
│   ├── Planning Assistance
│   ├── Optimization
│   ├── RCA / Diagnostics
│   ├── Recommendation Policies
│   └── Predictive Operations
│
├── 6.9 Logging & Diagnostics
│   ├── Log Levels
│   ├── Diagnostics
│   ├── Tracing
│   └── Support Bundles
│
└── 6.10 Advanced
    ├── Capability Controls
    ├── Experimental Capabilities
    ├── Developer Options
    └── Internal Diagnostics


══════════════════════════════════════════════════════════════
 GLOBAL / CROSS-CUTTING EXPERIENCE
══════════════════════════════════════════════════════════════

├── AKAAL Assistant
│   ├── Context-Aware Assistance
│   ├── Migration Planning
│   ├── Schema / SQL Assistance
│   ├── Failure / RCA Assistance
│   ├── Performance Optimization
│   └── Natural-Language Platform Control
│
├── Global Search / Command Palette
│
├── Notification Center
│
├── Approval Inbox
│   ├── Awaiting My Approval
│   ├── Requested by Me
│   ├── Approval Barrier Context
│   ├── Plan Fingerprint / Diff
│   └── Approval History
│
├── Incident Indicator
├── Background Operations
├── User / Organization / Workspace / Environment Switcher
├── Contextual Help
└── Documentation






AKAAL UI REBUILD
│
├── FOUNDATION
│   ├── Application Shell                     100% ✅ FROZEN
│   └── Dashboard                             100% ✅ FROZEN
│
├── GLOBAL EXPERIENCE
│   ├── Search / Command                      FOUNDATION ✅
│   ├── User Menu                             DONE ✅
│   ├── Context Switcher                      DONE ✅
│   │
│   ├── Notification Center                   DEFER → P6
│   ├── Approval Inbox                        DEFER → P5.10/P7D
│   ├── Incident Indicator                    DEFER → P6
│   ├── Background Operations                 DEFER → P6/P7D
│   ├── AKAAL Assistant                       DEFER → P7C
│   ├── Contextual Help                       DEFER → P7D/P9
│   └── Documentation                         DEFER → P7D/P9
│
└── NEXT
    └── MIGRATION
        └── 2.1 Migration Portfolio            ← NOW











                         DESIRED AKAAL UI
                                │
                     declares user INTENT
                                │
                                ▼
                         ┌─────────────┐
                         │     IPC     │
                         │ thin/reliable│
                         └──────┬──────┘
                                │
                                ▼
════════════════════════════════════════════════════════════
                    akaalPipeline/
════════════════════════════════════════════════════════════

                       UNIFIED CALLER
                     "What was requested?"
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
          IDENTITY          STATE           POLICY
        which thing?     what is true?    is it allowed?
              │               │                │
              └───────────────┼────────────────┘
                              ▼
                       INTENT ROUTER
                              │
             ┌────────────────┼─────────────────┐
             │                │                 │
             ▼                ▼                 ▼
          COMMAND          QUERY           EXECUTION
             │                │                 │
             │                │          ORCHESTRATOR
             │                │                 │
             └────────────────┼─────────────────┘
                              ▼
════════════════════════════════════════════════════════════
                     akaalEngine/
════════════════════════════════════════════════════════════

 connectivity │ discovery │ schema │ mapping │ transformation
 privacy │ transport │ CDC │ validation │ integrity │ recovery
 performance │ reporting │ evidence │ etc.

                              │
                              ▼
                       RESULT / EVENT
                              │
                              ▼
                        DURABLE STATE
                              │
                              ▼
                             IPC
                              │
                              ▼
                              UI


