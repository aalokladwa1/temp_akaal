# Platform Requirements Spec

This document tracks functional, performance, reliability, scalability, and security standards for the Akaal database migration engine.

---

## 🛠️ Functional Requirements

### 1. Cross-Dialect Migration
* **Support Matrix**: Direct migration between MySQL, PostgreSQL, SQL Server, and Oracle.
* **Auto-Conversion**: Automated conversion of table structures, primary keys, foreign keys, indexes, and null constraints.
* **Data Typings**: Handle text, boolean, exact numeric, approximate numeric, JSON, CLOB, and BLOB datatypes.

### 2. Failure Recovery & Resumption
* **Granular Checkpointing**: Save progress after every write batch (watermark offsets).
* **Crash Resumption**: Re-running the pipeline on a failed project must resume exactly from the last saved checkpoint.
* **Idempotency**: All writes must use idempotent keys or MERGE blocks to prevent double-insertions on resume.

### 3. Change Data Capture (CDC)
* **Live Sync**: Tailing binlogs or transaction logs to capture changes during active migration waves.
* **Consistency**: Replay changes in the exact order they occurred on the source (transaction serialization).

---

## ⚡ Performance Requirements

* **Throughput**: Support row transfer rates exceeding 1,000 rows/second for standard RDBMS connections.
* **Memory Limits**: Max memory footprint per migration run must not exceed 256MB under standard configurations (guaranteed by adaptive batch sizing).
* **Connection Reuse**: The adapter pool must reuse connections with a target reuse rate of **80%** or higher to minimize handshake latency.

---

## 🛡️ Security & Reliability Requirements

* **Isolation**: Database passwords must be read from environment variables or secure credentials stores, never hardcoded in configurations.
* **Transaction Safety**: Any batch write failure must execute a clean database rollback on the target connection.
* **Fault Tolerant Backoff**: Auto-reconnect with exponential backoff on transient network drops.

---

## 📈 Scalability & Future Requirements

* **Scalability**: Support scaling to 10M+ rows per table using parallel chunk partitions.
* **Future Dialects**: Maintain abstract base classes for adapters so adding cloud warehouses (e.g. Snowflake, BigQuery) requires only driver implementation without core engine modifications.
* **OpenTelemetry Tracing**: Implement trace context propagation across all agents for enterprise monitoring.
