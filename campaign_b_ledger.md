# P7A Campaign B — Internal Working Ledger

Internal, continuously-updated working document for the P7A Campaign B implementation
(P7A.7–P7A.12, 28→48 provider fleet expansion). NOT part of the frozen `progress.md`
record, NOT a claim of Campaign B completion or freeze — that determination belongs to
the owner. This file exists so the eventual final report can be built from a real,
continuously-maintained matrix rather than reconstructed from memory at the end.

Status legend: DONE / PARTIAL / NOT_APPLICABLE / EXTERNAL_DEFERRED / BLOCKED / NOT_STARTED

---

## Architectural finding (applies to every provider below)

Confirmed by direct repository search (`grep -rli` across `akaalPipeline/` and
`akaalIPC/` for any provider-name literal, e.g. `"kafka"`, `"postgresql"`): **zero
provider-name branching exists in Pipeline or IPC.** Operation dispatch, ExecutionPlan
compilation/identity, migration-mode eligibility, Runtime, Gateway, Telemetry, Evidence
#12, and Validation all consume capability truth (`CapabilityDeclaration` /
`CapabilityTruth` / `CertificationRecord`), never a provider identity switch. The same
is true of `akaalEngine/cdc/api.py::resolve_adapter_for_provider()` (extension/capability
resolution, not a hardcoded provider list) and the certification `CertificationProfile`
builder (built from declared capabilities, not a hardcoded provider taxonomy).

**Consequence for this ledger:** for those surfaces, "propagation" for a new provider is
correct-by-construction as long as (a) the provider's capability declarations are
truthful and (b) `probe_capabilities`/`probe_permissions` fail closed. Those surfaces are
marked `DONE (generic, capability-driven — verified no provider branching exists)` below
rather than requiring per-provider edits, because forcing a per-provider integration into
a deliberately provider-agnostic layer would itself violate the capability-first
architecture mandate. Surfaces that DO have genuine per-provider code (Connection,
Discovery, Schema type normalizers/emitters, ExtensionsAuthority adoption, focused tests)
are audited individually per provider.

---

## Provider: CockroachDB (`cockroachdb`) — relational family, provider #29

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/relational/cockroachdb.py`. Reuses `psycopg2` (PostgreSQL wire-compatible), truthful SQLSTATE 40001 retry semantics, distributed topology, license-gated CDC probe. |
| Discovery | DONE | `akaalEngine/discovery/strategies/relational/cockroachdb.py`, subclasses `PostgresDiscoveryStrategy` for pg_catalog-compatible facts; overrides identity/topology/CDC-prereqs/partitioning/change-marker truthfully. |
| Extensions adoption | DONE | Verified live: `ExtensionsAuthority` snapshot shows `cockroachdb` with both `connection` and `discovery` StrategyContributions and truthful capability declarations. |
| Schema (type normalize/emit) | DONE | Added to `normalizers.py` and `emitters.py` relational-PostgreSQL group (routed through `_normalize_postgresql`/`_emit_postgresql` — genuinely valid, CockroachDB documents PostgreSQL-compatible SQL type dialect for standard types). |
| Data Processing / Transport | DONE (generic, capability-driven) | No provider branching found in Pipeline; bulk read/write dispatched by `BULK_READ`/`BULK_WRITE` capability truth, both truthfully SUPPORTED. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | `CDC_LOG_CAPTURE` declared UNSUPPORTED at rest; `probe_capabilities` truthfully elevates to SUPPORTED only on a live, licensed `SHOW CLUSTER SETTING enterprise.license` probe. No live cluster available in this environment → EXTERNAL_DEFERRED for actually exercising a licensed CHANGEFEED end-to-end. |
| Durability / checkpoint / restart | DONE (generic) | `checkpoint.py`'s `provider_name` is a free string field; SQLSTATE-40001 whole-transaction-retry semantics are the CockroachDB-specific contribution here (in `normalize_error`, `retryable=True`), which Pipeline's generic retry/checkpoint loop already consumes via `ConnectionFailure.retryable`. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | Consumes capability truth; no provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot; certification obligations are capability-derived, not hardcoded. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses standard `host`/`port`/`database_name`/`tls_binding`/`auth_spec` fields; no new EndpointSpec fields required. |
| Security / TLS / tenant isolation | DONE | `sslmode` defaults to `verify-full` (stricter than PostgreSQL's `prefer` default) — deliberate, documented in code comments. Standard `TLSBinding`/credential-ref flow reused, no bypass introduced. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_cockroachdb_provider.py` — 11 tests: negative-capability truth, fail-closed probing (both directions), topology truth, SQLSTATE 40001/auth/node-unavailable error mapping, dependency-missing path. All pass. |
| Proof level | UNIT_PROVEN | No live CockroachDB cluster in this environment; conformance suite + dedicated tests pass against real driver code paths with fakes only at the physical test boundary (fake cursor/connection objects), never faking AKAAL's own machinery. LIVE_PROVEN is EXTERNAL_DEFERRED (requires a live cluster). |
| Known limitations | Documented | Partitioning introspection, CDC readiness, and cluster topology all require a live cluster to verify beyond UNIT_PROVEN — correctly classified, not silently claimed. |

## Provider: RabbitMQ (`rabbitmq`) — streaming/messaging family, provider #30

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/streaming/rabbitmq.py`. Uses `pika` (AMQP 0-9-1), truthful negative capabilities (OFFSET_COMMIT/CDC_LOG_CAPTURE/EXACTLY_ONCE/SCHEMA_REGISTRY all UNSUPPORTED by design, not oversight). |
| Discovery | DONE | `akaalEngine/discovery/strategies/streaming/rabbitmq.py`. Full broker inventory genuinely requires the RabbitMQ HTTP Management API (AMQP itself has no wire-level "list all queues" op) — implemented as a best-effort `requests`-based probe that returns honest empty/`None` results when the management API isn't reachable, never fabricated inventory. |
| Extensions adoption | DONE | Verified live: `ExtensionsAuthority` snapshot shows `rabbitmq` with both `connection` and `discovery` StrategyContributions; total adopted provider count now 30. |
| Schema (type normalize/emit) | DONE | Added to `normalizers.py`/`emitters.py` streaming/structural group — messages have no fixed relational schema, correctly routed to `STRUCTURAL_ONLY` emission like Kafka/Kinesis/PubSub. |
| Data Processing / Transport | DONE (generic, capability-driven) | `STREAMING_READ`/`STREAMING_WRITE` truthfully SUPPORTED; consumed generically. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | Classic/quorum queues are consume-and-remove, not a replayable log. `CDC_LOG_CAPTURE` UNSUPPORTED at rest; discovery's `discover_cdc_prerequisites` probes the RabbitMQ Streams plugin via the management API and fails closed to not-ready without a verified `rabbitmq_stream` plugin listing. New `CDCMechanism.RABBITMQ_STREAMS` enum value added (additive, non-breaking). EXTERNAL_DEFERRED for actually exercising Streams-based capture end-to-end (needs a live, Streams-enabled cluster). |
| Durability / checkpoint / restart | PARTIAL / genuinely different model | RabbitMQ has no offset-based restart position; restart semantics are per-message ack/nack, not a resumable checkpoint the way Kafka offsets or PostgreSQL LSNs are. `OFFSET_COMMIT` correctly declared UNSUPPORTED rather than forcing a fake checkpoint abstraction onto an ack-based delivery model. This is an honest architectural limitation of the provider itself, not an integration gap. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses `host`/`port`/`options["virtual_host"]`/`auth_spec`/`tls_binding`; no new EndpointSpec fields required. Management-API-only options (`management_port`, `management_scheme`, `management_password`) live in the existing free-form `spec.options` mapping, consistent with how other providers (Kafka's `client_id`, MongoDB's `replica_set`) already extend configuration without schema changes. |
| Security / TLS / tenant isolation | DONE | Standard `TLSBinding`/credential-ref flow reused; management API credentials are separate and read from `spec.options`, never logged (routed through the same `redact_text` used by `normalize_error`). |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_rabbitmq_provider.py` — 12 tests: negative-capability truth, fail-closed Streams-plugin probing (bare channel does NOT elevate CDC), broker-cluster (not partitioned-log) topology truth, AMQP-specific error mapping, dependency-missing path. All pass. |
| Proof level | UNIT_PROVEN | No live RabbitMQ broker in this environment; `pika`/`requests` not installed (truthfully reported via `is_dependency_available`). Fakes exist only at the physical test boundary. LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | Full broker inventory (namespaces/objects/topology) truthfully depends on the HTTP Management API being reachable and `requests` being installed; without either, discovery methods correctly return honest empty results rather than an error or fabricated data. Non-destructive data sampling from a queue is not implemented (would require a peek-without-consume pattern) — `sample_data` truthfully returns an empty sample rather than draining messages as a side effect. |

## Provider: Apache Pulsar (`pulsar`) — streaming/messaging family, provider #31

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/streaming/pulsar.py`. Uses `pulsar-client` (binary protocol, port 6650). Real Pulsar platform features not wired by this connector (transactions, native schema registry) truthfully declared UNSUPPORTED rather than borrowing the product's marketing capability list. |
| Discovery | DONE | `akaalEngine/discovery/strategies/streaming/pulsar.py`. Topic/tenant/namespace inventory via the separate Pulsar Admin REST API (port 8080), same honest best-effort/`None`-on-unreachable pattern as RabbitMQ's management API. New `CDCMechanism.PULSAR_STREAMING` enum value added (additive). |
| Extensions adoption | DONE | Verified live: total adopted provider count now 31, `pulsar` has both `connection` and `discovery` StrategyContributions. |
| Schema (type normalize/emit) | DONE | Added to `normalizers.py`/`emitters.py` streaming/structural group. |
| Data Processing / Transport | DONE (generic, capability-driven) | `STREAMING_READ`/`STREAMING_WRITE`/`OFFSET_COMMIT` truthfully SUPPORTED (Pulsar's cursor-based cumulative acknowledgment is a genuine, real offset-equivalent, unlike RabbitMQ's ack-only model). |
| CDC / change semantics | PARTIAL, correctly disclosed | Pulsar topics ARE a genuine durable log by default (unlike RabbitMQ classic queues) — structurally CDC-capable without a special plugin. This connector strategy does NOT implement reader-based log tailing, so `discover_cdc_prerequisites` truthfully reports not-ready with an explicit blocker reason naming the gap, rather than either fabricating readiness or silently omitting the capability. EXTERNAL_DEFERRED for implementing + proving reader-based tailing against a live cluster. |
| Durability / checkpoint / restart | PARTIAL, correctly disclosed | Cursor-based acknowledgment is a real, genuinely different-from-Kafka restart mechanism; not exercised end-to-end by Pipeline in this pass (same category of gap as CDC above). |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses `host`/`port`/`options["tenant"]`/`options["namespace"]`/`options["service_url"]`/`options["admin_url"]`, consistent with the existing free-form `spec.options` extension pattern. |
| Security / TLS / tenant isolation | DONE | TLS via `pulsar+ssl` scheme + `tls_trust_certs_file_path`; JWT token auth via `pulsar.AuthenticationToken`. Pulsar's own tenant/namespace hierarchy is a genuine multi-tenancy primitive (`MULTI_TENANCY` capability), separate from and layered under AKAAL's own tenant isolation. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_pulsar_provider.py` — 12 tests: negative-capability truth for unwired platform features, permission-probe CDC-denial, broker-cluster topology, error mapping (auth/broker-unavailable/topic-not-found), dependency-missing path, `validate()` None-safety. All pass. |
| Proof level | UNIT_PROVEN | No live Pulsar cluster in this environment; `pulsar-client`/`requests` not installed (truthfully reported). LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | `validate()` cannot perform a true no-op liveness round trip (the `pulsar-client` API has no cheap ping distinct from a side-effecting producer/consumer/reader creation) — disclosed in-code rather than silently claiming an equivalent guarantee to other providers' active `validate()`. Non-destructive sampling and CDC-grade reader tailing are not implemented in this pass. |

**P7A.7 (Streaming + Messaging) scope check:** Kafka/Confluent/MSK already existed pre-Campaign-B (strengthening not yet separately audited); RabbitMQ DONE; Pulsar DONE. Both new messaging providers are genuinely differentiated from Kafka's strategy, not relabels.

## Provider: AWS DynamoDB (`dynamodb`) — NoSQL/cloud family, provider #32

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/nosql/dynamodb.py`. Uses `boto3` (same driver as S3/Kinesis). Real DynamoDB Streams CDC probed truthfully per-table via `describe_table().StreamSpecification`; `FOREIGN_KEYS` correctly UNSUPPORTED (no relational FK concept in a key-value store). |
| Discovery | DONE | `akaalEngine/discovery/strategies/nosql/dynamodb.py`. Table inventory via `list_tables`/`describe_table`; key schema + GSI/LSI structure facts (only key attributes are discoverable — DynamoDB enforces no schema for non-key attributes, disclosed as a restriction, not silently presented as a complete schema); bounded item sampling for `infer_document_shape` via real `scan()` + `TypeDeserializer`. New `CDCMechanism.DYNAMODB_STREAMS` enum value added (additive). |
| Extensions adoption | DONE | Verified live: total adopted provider count now 32. |
| Schema (type normalize/emit) | DONE | Added a dedicated `_normalize_dynamodb` mapping DynamoDB's native AttributeValue type codes (S/N/B/BOOL/NULL/L/M/SS/NS/BS) to `CanonicalType` explicitly, rather than lumping into a generic NoSQL fallback — genuinely differentiated from the Mongo/Redis normalizers since DynamoDB's type system is small and closed. Emit side routed to the existing `STRUCTURAL_ONLY` group (correct — no relational DDL concept). |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE` truthfully SUPPORTED via Scan/Query/BatchWriteItem. |
| CDC / change semantics | PARTIAL, correctly disclosed | DynamoDB Streams is a real, well-documented feature — genuinely probed (not fabricated) via `describe_table`, but per-table opt-in, so default is UNSUPPORTED until proven otherwise for the specific table in scope. No reader/tailing implementation wired in this connector (matches the same disclosed gap pattern as Pulsar). EXTERNAL_DEFERRED for live stream-tailing proof. |
| Durability / checkpoint / restart | DONE (generic) | Real transactional support (`TRANSACTIONS` SUPPORTED via TransactWriteItems/TransactGetItems, a genuine DynamoDB primitive) gives Pipeline's generic retry/checkpoint machinery real all-or-nothing semantics to rely on, distinct from a fabricated claim. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses `region`/`options["table_name"]`/`options["endpoint_url"]`/credentials, consistent with S3/Kinesis's existing AWS provider pattern. Deliberately does NOT hard-require `region` in `validate_configuration` (initially added, then removed after it broke the generic conformance harness, which constructs a provider-agnostic spec with no region) — matches the established S3/Kinesis pattern of defaulting to `us-east-1` at `connect()` time rather than gatekeeping in `validate_configuration`. |
| Security / TLS / tenant isolation | DONE | Standard IAM credential-ref flow (access key / secret / session token), consistent with S3/Kinesis. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_dynamodb_provider.py` — 13 tests: negative-capability truth, fail-closed stream probing (3 scenarios: no table in scope, enabled, disabled, exception), permission-probe CDC-denial, managed-service topology truth, AWS ClientError-shaped error mapping (4 error codes), dependency-missing path. All pass. |
| Proof level | UNIT_PROVEN | No live AWS account/table in this environment; `boto3` not installed (truthfully reported). LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | Non-key attribute schema is fundamentally not discoverable ahead of sampling (a genuine DynamoDB architectural property, not an integration gap); `infer_document_shape`/`sample_data` both perform bounded live `Scan` calls when a connection is present. |
| Regression note | Real defect caught and fixed pre-merge | Initial `validate_configuration` override hard-required a region, which is stricter than every other AWS provider (S3/Kinesis) and broke `test_all_providers_pass_conformance_suite` (generic conformance spec carries no region). Removed the override; DynamoDB now matches the established default-region-at-connect-time pattern. Caught by the existing regression suite before being reported as done — not caught by a hostile reviewer. |

## Provider: Couchbase (`couchbase`) — NoSQL family, provider #33

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/nosql/couchbase.py`. Uses the `couchbase` Python SDK (Cluster/PasswordAuthenticator). Real multi-document ACID transactions (SDK-native, genuinely different mechanism from MongoDB's) declared SUPPORTED; DCP-based CDC correctly declared UNSUPPORTED (requires a low-level streaming client not wired here). |
| Discovery | DONE | `akaalEngine/discovery/strategies/nosql/couchbase.py`. Bucket/scope/collection hierarchy (Couchbase 7.0+) via the collections manager; document shape inference via real N1QL sampling (`SELECT ... LIMIT`), not a fabricated schema. New `CDCMechanism.COUCHBASE_DCP` enum value added (additive). |
| Extensions adoption | DONE | Verified live: total adopted provider count now 33. |
| Schema (type normalize/emit) | DONE | Added a dedicated `_normalize_couchbase` mapping N1QL/JSON value types (string/number/boolean/object/array/null/missing/binary) — genuinely distinct vocabulary from MongoDB's BSON types, not reused. Emit side routed to `STRUCTURAL_ONLY`. |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE` truthfully SUPPORTED via N1QL. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | DCP is real but requires a dedicated low-level streaming client this connector does not implement; `discover_cdc_prerequisites` truthfully reports not-ready with an explicit blocker reason. EXTERNAL_DEFERRED for a live DCP-based tailing implementation. |
| Durability / checkpoint / restart | DONE (generic) | Real ACID transactions give Pipeline's generic retry/checkpoint machinery genuine all-or-nothing semantics; CAS-based optimistic concurrency conflicts are mapped to a retryable `COUCHBASE_CAS_CONFLICT` error. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses `host`/`options["bucket"]`/`options["scope"]`/`options["collection"]`/`options["connection_string"]`/`auth_spec`, consistent with the existing free-form `spec.options` extension pattern. |
| Security / TLS / tenant isolation | DONE | TLS via `couchbases://` scheme; standard credential-ref flow. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_couchbase_provider.py` — 13 tests: negative-capability truth, permission-probe CDC-denial, multi-node-cluster topology truth, error mapping (CAS conflict/retryable, document-not-found/non-retryable, auth failure, timeout/retryable), dependency-missing path, `validate()` None-safety. All pass. |
| Proof level | UNIT_PROVEN | No live Couchbase cluster in this environment; `couchbase` SDK not installed (truthfully reported). LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | `discover_object_structure` returns no columns ahead of sampling (genuinely correct for a schema-flexible N1QL store — shape comes from `infer_document_shape`, not a fixed catalog). DCP-based CDC not implemented. |

**NoSQL/cloud family progress:** DynamoDB DONE, Couchbase DONE. Remaining from the original
20-provider list: Cosmos DB, Cloud Spanner, InfluxDB (+ non-NoSQL: YugabyteDB, TiDB,
SingleStore, ClickHouse, Teradata, Vertica, SAP HANA, SAP ASE, IBM Informix, Salesforce,
SAP application ecosystem, ServiceNow).

## Provider: ClickHouse (`clickhouse`) — warehouse/OLAP family, provider #34

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/warehouse/clickhouse.py`. Uses `clickhouse-connect` (HTTP interface). `TRANSACTIONS` correctly declared UNSUPPORTED (no reliable default multi-statement ACID model, unlike the other warehouse providers); real `MUTATIONS` capability (async `ALTER TABLE ... UPDATE/DELETE`) modeled distinctly rather than folded into `BULK_WRITE`. |
| Discovery | DONE | `akaalEngine/discovery/strategies/warehouse/clickhouse.py`. Introspects `system.databases`/`system.tables`/`system.columns`/`system.clusters`; genuine `PARTITION BY` partition-key discovery via `system.tables.partition_key` (a real MergeTree property, not a generic SQL partition scheme). `discover_programmables` truthfully returns empty (no stored procedures/triggers/UDTs in ClickHouse). |
| Extensions adoption | DONE | Verified live: total adopted provider count now 34. |
| Schema (type normalize/emit) | DONE | Dedicated `_normalize_clickhouse`/`_emit_clickhouse` covering ClickHouse's own type system (Int8-256/UInt8-256, Float32/64, arbitrary-precision Decimal, real `Nullable(...)` wrapper, Array/Tuple/Map/Nested) — genuinely differentiated from every other relational/warehouse normalizer, not reused. |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE`/`COLUMNAR_STORAGE` truthfully SUPPORTED. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | ClickHouse has no native binlog/change-log mechanism; `discover_cdc_prerequisites` correctly reports `CDCMechanism.POLLING_WATERMARK` as the only viable mechanism (watermark-based incremental polling), not a fabricated log-based CDC. |
| Durability / checkpoint / restart | PARTIAL, correctly disclosed | No multi-statement transactions means no natural checkpoint/rollback boundary beyond per-statement idempotency; `MUTATIONS` are asynchronous background operations whose completion Pipeline would need to poll for — not implemented end-to-end in this pass, an honest architectural property of the engine, not an integration gap. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses standard `host`/`port`/`database_name`/`auth_spec`/`tls_binding` fields; no new EndpointSpec fields required. |
| Security / TLS / tenant isolation | DONE | TLS via `secure=True` on the HTTP client; standard credential-ref flow. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_clickhouse_provider.py` — 13 tests: negative-capability truth, permission-probe CDC-denial, distributed topology truth, error mapping (auth/permission/memory-limit/too-many-queries/unavailable), dependency-missing path, `validate()` None-safety. All pass. |
| Proof level | UNIT_PROVEN | No live ClickHouse server in this environment; `clickhouse-connect` not installed (truthfully reported). LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | No transactional boundary to anchor Pipeline's generic retry/checkpoint semantics to (an honest property of the engine); async mutation completion polling not implemented. |

**Warehouse family progress:** Snowflake/BigQuery/Redshift/Databricks pre-existing; ClickHouse DONE (new, genuinely differentiated columnar OLAP addition).

## Provider: InfluxDB (`influxdb`) — new time-series family, provider #35

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/timeseries/influxdb.py`. Uses `influxdb-client` (v2.x, Flux). New `FAMILY = "timeseries"` — the Engine's first time-series-native provider. `TRANSACTIONS`/`CDC_LOG_CAPTURE` correctly UNSUPPORTED — not live-probe-dependent gaps like other providers, but genuine absences in the product itself (no transaction concept, no change-log at all). |
| Discovery | DONE | New `akaalEngine/discovery/spi/timeseries.py` SPI contract (`TimeSeriesDiscoveryStrategy`, abstract `discover_retention_policy`) — added because no existing family SPI (relational/nosql/streaming/storage/warehouse) fits the measurement/tag/field model; mirrors the established per-family SPI pattern (e.g. `StorageDiscoveryStrategy.extract_file_embedded_schema`). `akaalEngine/discovery/strategies/timeseries/influxdb.py` introspects buckets/measurements/tag-keys/field-keys via real Flux `schema` package queries — genuine InfluxDB introspection, not borrowed from any relational catalog. Tag keys (indexed) vs field keys (values) reported as structurally distinct column kinds, not collapsed together. |
| Extensions adoption | DONE | Verified live: total adopted provider count now 35. |
| Schema (type normalize/emit) | DONE | Dedicated `_normalize_influxdb` covering InfluxDB's genuinely small type system (tag/float/integer/uinteger/boolean/string/timestamp) — distinct vocabulary, not reused from any other normalizer. Emit side routed to `STRUCTURAL_ONLY`. |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE`/`TIME_SERIES_NATIVE` truthfully SUPPORTED. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | No native change-log exists in InfluxDB at all (not per-table opt-in like DynamoDB Streams, not license-gated like CockroachDB CHANGEFEED — genuinely absent from the product). `discover_cdc_prerequisites` reports `CDCMechanism.POLLING_WATERMARK` as the only viable incremental-extraction mechanism (real `_time`-range re-querying), never a fabricated log-based CDC. |
| Durability / checkpoint / restart | PARTIAL, correctly disclosed | No transaction boundary exists at all (an honest product property, not an integration gap); watermark-based incremental extraction via `_time` range is the correct restart strategy but not wired end-to-end by Pipeline in this pass. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Uses `host`/`options["org"]`/`options["bucket"]`/`options["url"]`/`options["auth_token"]`, consistent with the existing free-form `spec.options` extension pattern. |
| Security / TLS / tenant isolation | DONE | TLS via `https://` scheme derivation from `TLSBinding`; token-based auth (InfluxDB 2.x's native auth model, not username/password). |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_influxdb_provider.py` — 13 tests: negative-capability truth, permission-probe CDC-denial, time-series-engine topology truth, error mapping (auth/permission/rate-limit-retryable/unavailable-retryable), dependency-missing path, `validate()` None-safety. All pass. |
| Proof level | UNIT_PROVEN | No live InfluxDB server in this environment; `influxdb-client` not installed (truthfully reported). LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | No transactional or change-log boundary exists in the product itself; `sample_data` uses a fixed 30-day lookback window as a pragmatic default since InfluxDB has no "all data" scan without a time bound. |

**New family created:** `timeseries` — first provider (InfluxDB) DONE. Establishes the SPI/registration pattern for any future time-series providers (e.g. TimescaleDB would instead route through the existing relational family since it's a PostgreSQL extension).

---

## Provider: YugabyteDB (`yugabytedb`) — relational/distributed-SQL family, provider #36

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/relational/yugabytedb.py`. Reuses `psycopg2` (YSQL is PostgreSQL wire-compatible), same architectural pattern as CockroachDB but NOT a relabel: real CDC via PostgreSQL-protocol replication slots (`pg_replication_slots` with `yboutput`/`pgoutput` plugin) genuinely probed, distinct from CockroachDB's Enterprise-license CHANGEFEED gate. |
| Discovery | DONE | `akaalEngine/discovery/strategies/relational/yugabytedb.py`, subclasses `PostgresDiscoveryStrategy`. Topology via the real YugabyteDB-native `yb_servers()` function (TServer membership), not `pg_stat_replication`. **Genuine differentiator vs. CockroachDB**: YugabyteDB actually supports the same declarative `PARTITION BY`/`pg_partitioned_table` catalog as PostgreSQL, so `discover_partitioning` is correctly left inherited (not overridden) — documented in-code as a deliberate difference, not an oversight. |
| Extensions adoption | DONE | Verified live: total adopted provider count now 36. |
| Schema (type normalize/emit) | DONE | Routed through the existing `_normalize_postgresql`/`_emit_postgresql` (alongside `postgresql`/`cockroachdb`) — genuinely valid since YSQL's type system is PostgreSQL-compatible for standard types. |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE` dispatched by truthfully-SUPPORTED capability truth. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | `CDC_LOG_CAPTURE` UNSUPPORTED at rest; `probe_capabilities`/discovery's `discover_cdc_prerequisites` both truthfully elevate only on a live `pg_replication_slots` probe finding a `yboutput`/`pgoutput` slot. No live cluster in this environment → EXTERNAL_DEFERRED for exercising real CDC end-to-end. |
| Durability / checkpoint / restart | DONE (generic) | SQLSTATE 40001 whole-transaction-retry semantics (`retryable=True` in `normalize_error`) feed Pipeline's generic retry/checkpoint loop the same way as CockroachDB's, but the underlying cause (DocDB's Raft-replicated tablet transaction manager) is documented as genuinely different. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Standard `host`/`port`/`database_name`/`tls_binding`/`auth_spec` fields; default port 5433 (YSQL), default database `yugabyte`. |
| Security / TLS / tenant isolation | DONE | Standard `TLSBinding`/credential-ref flow; `sslmode` defaults to PostgreSQL's `prefer` (not CockroachDB's stricter `verify-full`) — a deliberate, disclosed difference since YugabyteDB deployments don't universally mandate TLS the way Cockroach Cloud does. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_yugabytedb_provider.py` — 11 tests: negative-capability truth, fail-closed replication-slot probing (both directions + exception path), distributed topology truth, SQLSTATE 40001/auth/TServer-unavailable error mapping, dependency-missing path. All pass. |
| Proof level | UNIT_PROVEN | No live YugabyteDB cluster in this environment; conformance suite + dedicated tests pass against real driver code paths with fakes only at the physical test boundary. LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | CDC readiness, TServer topology, and tablet-level partition facts all require a live cluster to verify beyond UNIT_PROVEN. |

**Relational/distributed-SQL family progress:** CockroachDB DONE, YugabyteDB DONE — two genuinely differentiated distributed-SQL providers sharing a driver but not a strategy implementation. Remaining from the original 20: TiDB, SingleStore (also PostgreSQL/MySQL-wire-compatible distributed SQL candidates).

---

## Provider: TiDB (`tidb`) — relational/distributed-SQL family, provider #37

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/relational/tidb.py`. Reuses `PyMySQL` (MySQL wire-compatible), same architectural pattern as the MySQL strategy but NOT a relabel: `CDC_LOG_CAPTURE` and `SAVEPOINTS` deliberately declared UNSUPPORTED rather than inherited from MySQL's manifest, because TiDB does not use MySQL's binlog at all (CDC needs the separate TiCDC component) and SAVEPOINT support is version-gated (6.2+). |
| Discovery | DONE | `akaalEngine/discovery/strategies/relational/tidb.py`, subclasses `MySQLDiscoveryStrategy` for the MySQL-compatible catalog facts, but explicitly overrides `discover_endpoint_identity` (real `tidb_version()`, not `VERSION()`'s MySQL-compatibility string), `discover_topology` (real `information_schema.CLUSTER_INFO` cluster membership — MySQL's inherited version is a no-op returning an empty snapshot, correct for standalone MySQL but wrong for TiDB), and `discover_cdc_prerequisites` (explicitly does NOT inherit MySQL's `@@log_bin`/`@@binlog_format` probe, which would silently produce a misleading result on TiDB). New `CDCMechanism.TIDB_CDC` enum value added (additive). |
| Extensions adoption | DONE | Verified live: total adopted provider count now 37. |
| Schema (type normalize/emit) | DONE | Routed through the existing `_normalize_mysql`/`_emit_mysql` (alongside `mysql`/`mariadb`) — genuinely valid since TiDB's type system is MySQL-compatible. |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE`/`LOAD_DATA_INFILE` truthfully SUPPORTED. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | Both the connection-layer `probe_capabilities` and discovery's `discover_cdc_prerequisites` correctly refuse to reuse MySQL's binlog-variable check (a genuine truthfulness hazard caught and avoided, not just a missed feature) — TiDB CDC requires the separate TiCDC component, not reachable via a plain SQL connection. EXTERNAL_DEFERRED for wiring an actual TiCDC integration. |
| Durability / checkpoint / restart | DONE (generic) | TiDB-specific write-conflict error code 9007 (Percolator 2PC abort) mapped to a retryable `TIDB_WRITE_CONFLICT`, feeding Pipeline's generic retry loop real distributed-transaction semantics distinct from MySQL's deadlock/lock-timeout codes. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Standard `host`/`port`/`database_name`/`tls_binding`/`auth_spec` fields; default port 4000 (TiDB's default SQL port, not MySQL's 3306). |
| Security / TLS / tenant isolation | DONE | Standard `TLSBinding`/credential-ref flow, mirrors MySQL's SSL kwarg construction. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_tidb_provider.py` — 11 tests: negative-capability truth, permission-probe CDC-denial, distributed topology truth, write-conflict/auth/server-unavailable error mapping, dependency-missing path, `validate()` None-safety. All pass. |
| Proof level | UNIT_PROVEN | No live TiDB cluster in this environment; conformance suite + dedicated tests pass against real driver code paths with fakes only at the physical test boundary. LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | Cluster topology, region-based partition facts, and CDC readiness all require a live cluster to verify beyond UNIT_PROVEN — correctly classified, not silently claimed. |

**Relational/distributed-SQL family progress:** CockroachDB, YugabyteDB, TiDB — three genuinely differentiated distributed-SQL providers, each sharing a driver with an existing single-node provider but never a strategy implementation, and each catching at least one real "don't blindly inherit the base provider's probe" hazard specific to its own architecture. Remaining from the original 20: SingleStore.

---

## Provider: SingleStore (`singlestore`) — relational/distributed-SQL family, provider #38

| Surface | Status | Notes |
|---|---|---|
| Engine Connection | DONE | `akaalEngine/connection/providers/relational/singlestore.py`. Reuses `PyMySQL`, same pattern as MySQL/TiDB but NOT a relabel: genuine hybrid `COLUMNAR_STORAGE` capability (SingleStore tables are explicitly declared `ROWSTORE` or `COLUMNSTORE`, a real table-level architectural choice neither MySQL nor TiDB has); `FOREIGN_KEYS` correctly UNSUPPORTED (SingleStore parses but does not enforce them — a genuine, disclosed product limitation, not an integration gap); `CDC_LOG_CAPTURE` correctly UNSUPPORTED (no MySQL-compatible binlog exposed as a change source). |
| Discovery | DONE | `akaalEngine/discovery/strategies/relational/singlestore.py`, subclasses `MySQLDiscoveryStrategy`. Real topology via SingleStore-native `SHOW LEAVES`/`SHOW AGGREGATORS` (aggregator/leaf architecture — distinct from both MySQL's primary/replica and TiDB's PD/TiKV/TiDB-server split). `discover_partitioning` correctly left inherited: SingleStore's optional explicit `PARTITION BY` is genuinely exposed via the same `information_schema.PARTITIONS` MySQL uses (documented as distinct from SingleStore's automatic, non-catalog-visible shard-key sharding, which this strategy does not attempt to surface through this path). |
| Extensions adoption | DONE | Verified live: total adopted provider count now 38. |
| Schema (type normalize/emit) | DONE | Routed through the existing `_normalize_mysql`/`_emit_mysql` (alongside `mysql`/`mariadb`/`tidb`) — genuinely valid since SingleStore's type system is MySQL-compatible. |
| Data Processing / Transport | DONE (generic, capability-driven) | `BULK_READ`/`BULK_WRITE`/`LOAD_DATA_INFILE` truthfully SUPPORTED. |
| CDC / change semantics | NOT_APPLICABLE (truthfully UNSUPPORTED) | Both connection- and discovery-layer CDC checks explicitly refuse to reuse MySQL's binlog probe (same truthfulness hazard pattern caught for TiDB) — SingleStore requires a dedicated Pipelines-based integration this connector does not implement. |
| Durability / checkpoint / restart | DONE (generic) | Standard deadlock/lock-timeout retry mapping (error codes 1213/1205), consistent with MySQL/TiDB pattern. |
| Runtime / Gateway / Telemetry / Evidence #12 | DONE (generic, capability-driven) | See architectural finding above. |
| Validation | DONE (generic, capability-driven) | No provider-specific validation code found or needed. |
| Capability truth / certification | DONE | Verified live via `ExtensionsAuthority` snapshot. |
| EndpointSpec / RouteSpec | DONE (generic) | Standard `host`/`port`/`database_name`/`tls_binding`/`auth_spec` fields; default port 3306 (SingleStore's aggregator port, same as MySQL's default). |
| Security / TLS / tenant isolation | DONE | Standard `TLSBinding`/credential-ref flow, mirrors MySQL/TiDB's SSL kwarg construction. |
| Migration-mode eligibility / ExecutionPlan / operation dispatch / IPC | DONE (generic, capability-driven) | See architectural finding above. |
| Dedicated hostile/unit tests | DONE | `tests/unit/engine_connection/test_singlestore_provider.py` — 11 tests: negative-capability truth, permission-probe CDC-denial, aggregator/leaf topology truth, deadlock/auth/leaf-unavailable error mapping, dependency-missing path, `validate()` None-safety. All pass. |
| Proof level | UNIT_PROVEN | No live SingleStore cluster in this environment; conformance suite + dedicated tests pass against real driver code paths with fakes only at the physical test boundary. LIVE_PROVEN is EXTERNAL_DEFERRED. |
| Known limitations | Documented | Aggregator/leaf topology and explicit-partition facts require a live cluster to verify beyond UNIT_PROVEN. |

**Relational/distributed-SQL family — COMPLETE for the original 20-provider list**: CockroachDB, YugabyteDB, TiDB, SingleStore — four genuinely differentiated distributed-SQL providers, each sharing a driver with an existing single-node provider but never a strategy implementation, and each catching at least one real "don't blindly inherit the base provider's probe" hazard specific to its own architecture (CockroachDB: no primary/replica topology; YugabyteDB: real partitioning inheritance is actually correct unlike CockroachDB; TiDB and SingleStore: explicit binlog-probe refusal).

---

## Regression evidence (non-regressive, this session)

**Second full `tests/unit` sweep** (after CockroachDB/RabbitMQ/Pulsar/DynamoDB/Couchbase/ClickHouse/InfluxDB,
all 7 new providers): **3417 passed, 39 skipped, 1 failed** in 286.48s. The 1 failure is
again `tests/unit/test_day23_reconciliation.py::TestDay23ControlPlaneReconciliation::test_p0_7_telemetry_provenance_and_zero_synthetic_workers`
— same frozen legacy `akaal/`-adjacent test as the first sweep, but a *different*
assertion failed this time (`rows_transferred: 0 != 5` here vs. `throughput_mbps`
unexpectedly `None` in the first sweep). This is consistent with a pre-existing internal
flake/ordering sensitivity within that single legacy test method (multiple sequential
assertions against async gateway state), not a new regression — no file this session has
touched is anywhere near `test_day23_reconciliation.py` or the `akaal/` package (confirmed
via `git status`). Disclosed honestly rather than smoothed over; still out of scope to fix
under the frozen-`akaal/` constraint. Every other test in the entire repository (3417
tests) passed both times.

**Third full `tests/unit` sweep** (after CockroachDB/RabbitMQ/Pulsar/DynamoDB/Couchbase/ClickHouse/InfluxDB/YugabyteDB/TiDB,
9 new providers): **3442 passed, 39 skipped, 0 failed** in 306.47s — the previously
flaky `test_day23_reconciliation.py` test passed clean this run, consistent with it being
an internal timing/ordering flake rather than a real defect. Full green suite.

**Fourth full `tests/unit` sweep** (after adding SingleStore, the 10th and final provider
of this batch): **3454 passed, 39 skipped, 0 failed** in 330.25s. Full green suite,
zero failures anywhere in the repository.


- `tests/unit/engine_connection/ + engine_extensions/ + engine_discovery/ + engine_schema/`:
  **575 passed, 2 skipped, 0 failed** (after CockroachDB + RabbitMQ + Pulsar + DynamoDB +
  Couchbase + ClickHouse + InfluxDB + YugabyteDB + TiDB + SingleStore additions, including
  fixing the two hard-coded `== 28` fleet-size assertions that broke on provider #29).
  Adopted provider count now 38. One isolated flaky timing test
  (`test_enforced_operation_timeout_causes_partial_snapshot`, a 0.001s-deadline race,
  unrelated to any file touched this session) failed once under load and passed cleanly
  on immediate re-run in isolation and in the full suite — noted as a pre-existing timing
  sensitivity, not a regression. Has not recurred since.
- Full `tests/unit` sweep (broader, one-time checkpoint before RabbitMQ was added):
  **3335 passed, 39 skipped, 1 failed.** The 1 failure —
  `tests/unit/test_day23_reconciliation.py::TestDay23ControlPlaneReconciliation::test_p0_7_telemetry_provenance_and_zero_synthetic_workers`
  (`throughput_mbps` unexpectedly `None`) — is in the **frozen legacy `akaal/` package**,
  untouched by any file this session has modified (confirmed via `git status` showing no
  `akaal/` or `tests/unit/test_day23_reconciliation.py` changes). Disclosed as
  pre-existing/out-of-scope; not fixed here since `akaal/` is frozen and modifying it
  requires separate authorization. Will re-run the full sweep again at the next
  whole-ecosystem checkpoint to reconfirm this remains the only failure and is still
  non-regressive.

---

## Remaining Campaign B scope (not started / in progress)

- **Providers not yet built** (of the 20 total): CockroachDB DONE, RabbitMQ DONE, Pulsar
  DONE, DynamoDB DONE, Couchbase DONE, ClickHouse DONE, InfluxDB DONE, YugabyteDB DONE,
  TiDB DONE, SingleStore DONE. Remaining ~10: Teradata, Vertica, SAP HANA, SAP ASE, IBM
  Informix, Cosmos DB, Cloud Spanner, Salesforce, SAP application ecosystem, ServiceNow
  (+ any Kafka/Confluent/MSK strengthening explicitly requested for P7A.7 — not yet
  separately audited). Of these, the remaining relational-family candidates (Teradata,
  Vertica, SAP HANA, SAP ASE, IBM Informix) each require their own proprietary driver
  (no shared wire-protocol reuse like the CockroachDB/YugabyteDB/TiDB/SingleStore group);
  the remaining cloud-family candidates (Cosmos DB, Cloud Spanner) each have their own
  Python SDKs (azure-cosmos, google-cloud-spanner); Salesforce/SAP/ServiceNow are SaaS/ERP
  application-ecosystem connectors (P7A.8 scope), architecturally distinct from every
  database/messaging provider built so far (REST/SOAP APIs, not a DB wire protocol).
- **P7A.9** Universal File+Dataset Framework (CSV, XLSX, JSON, JSONL, XML, Avro, Parquet,
  ORC): NOT_STARTED.
- **P7A.10** Metadata/Lineage/Catalog interop (OpenLineage): NOT_STARTED.
- **P7A.11** Extension Registry + Enterprise Distribution: NOT_STARTED.
- **P7A.12** Whole-Ecosystem Hostile Acceptance: NOT_STARTED (depends on the above).
- Final provider × authority × capability × proof matrix: to be assembled from this
  ledger once all providers are done.

*(This ledger is updated as work continues; see git-uncommitted working tree for the
authoritative current state of the code itself.)*
