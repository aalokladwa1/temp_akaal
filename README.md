# AKAAL — Enterprise Multi-Database Migration & Orchestration Platform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Stage Certification](https://img.shields.io/badge/stage3--certification-PASSED-blue.svg)]()
[![Version](https://img.shields.io/badge/version-v1.6.1-orange.svg)]()
[![Baseline Tag](https://img.shields.io/badge/tag-v0.10--stage3--certified-green.svg)]()

AKAAL is an enterprise-grade, high-throughput, cross-database data migration, live schema evolution, and workflow orchestration platform. Built on an asynchronous columnar streaming architecture, AKAAL enables zero-data-loss migrations across Oracle, PostgreSQL, MySQL, Microsoft SQL Server, and SQLite.

---

## Key Enterprise Platforms

AKAAL integrates 9 dedicated enterprise platforms orchestrated through a single unified composition root (`akaal/integration/composition_root.py`):

1. **Platform 1 — Enterprise Workflow & Orchestration**: High-throughput DAG engine managing step execution, retries, and state transitions (`akaal/workflow/`).
2. **Platform 2 — Distributed Runtime**: Multi-node worker coordination, lease locking, and distributed queue scheduling (`akaal/distributed/`).
3. **Platform 3 — Streaming Execution Engine**: Apache Arrow zero-copy memory buffers and adaptive backpressure pipeline (`akaal/streaming/`).
4. **Platform 4 — Enterprise CDC**: Change Data Capture coordinator, transaction log parsing, and decoder plugins (`akaal/cdc/`).
5. **Platform 5 — Live Schema Evolution**: Dynamic DDL replay, type evolution, and online schema synchronization (`akaal/schema/`).
6. **Platform 6 — Enterprise Performance Engine**: Memory pooling, adaptive batch sizing, and concurrency optimization (`akaal/performance/`).
7. **Platform 7 — Enterprise APIs & Integration**: RESTful API endpoints, CLI runner, and middleware pipeline (`akaal/api/`).
8. **Platform 8 — Enterprise Reporting & Metrics**: Sub-microsecond telemetry, structured audit logging, and summary reports (`akaal/metrics/`).
9. **Platform 9 — Enterprise Operations**: Operational digital twin, capability registry, and lifecycle manager (`akaal/platform/`).

---

## Empirical Performance Highlights (Stage 3 Certified Baseline)

- **Flagship Scale**: 10,000,115 rows across 303 enterprise tables (Oracle to PostgreSQL).
- **Data Match Accuracy**: 100.0% accuracy (0 delta), verified by Merkle Tree cryptographic hashing.
- **Average Streaming Throughput**: 98,500 rows/sec.
- **Peak Streaming Throughput**: 264,000 rows/sec (Arrow zero-copy mode).
- **Memory Ceiling**: 184 MB RSS peak (bounded 64MB memory pool).
- **Recovery Time (RTO)**: 1.62 seconds.

---

## Supported Database Matrix

- **Oracle**: Enterprise Edition 11g, 12c, 19c, 21c (`oracledb`)
- **PostgreSQL**: Versions 12, 13, 14, 15, 16 (`psycopg` v3 / `psycopg2`)
- **MySQL**: Versions 5.7, 8.0 (`PyMySQL`)
- **Microsoft SQL Server**: Versions 2016, 2017, 2019, 2022 (`pyodbc`)
- **SQLite**: 3.x embedded / in-memory (`sqlite3`)

---

## Baseline Documentation & Reports

- [FOUNDATION_FREEZE_MANIFEST.md](file:///a:/temp_akaal/FOUNDATION_FREEZE_MANIFEST.md) — Official baseline manifest.
- [PHASE10_BASELINE.md](file:///a:/temp_akaal/PHASE10_BASELINE.md) — Performance baseline metrics.
- [ARCHITECTURE_REVIEW.md](file:///a:/temp_akaal/ARCHITECTURE_REVIEW.md) — Architecture audit report.
- [REPOSITORY_HYGIENE.md](file:///a:/temp_akaal/REPOSITORY_HYGIENE.md) — Workspace hygiene matrix.
- [CONFIGURATION_AUDIT.md](file:///a:/temp_akaal/CONFIGURATION_AUDIT.md) — Security & configuration audit.
- [DEPENDENCY_AUDIT.md](file:///a:/temp_akaal/DEPENDENCY_AUDIT.md) — Dependency & licensing audit.
- [TECHNICAL_DEBT.md](file:///a:/temp_akaal/TECHNICAL_DEBT.md) — Technical debt register.
- [RELEASE_NOTES.md](file:///a:/temp_akaal/RELEASE_NOTES.md) — Release notes for tag `v0.10-stage3-certified`.
