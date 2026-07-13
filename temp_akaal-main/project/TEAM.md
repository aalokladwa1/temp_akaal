# Team Profile & Responsibilities

This document defines team roles, system ownership boundaries, and task focus areas for project coordination.

---

## 👥 Members

### 👨‍💻 Aalok (Principal Engineer)
* **Current Responsibilities**:
  * Core architecture reorganization and namespaces.
  * DB connection pooling and transactional adapters (Oracle & SQL Server).
  * Checkpoint resumption and transaction reliability engines.
* **Ownership**: `akaal/core/`, `akaal/adapters/rdbms/`, and `tests/`.
* **Current Focus**: Phase 8 production preparation and scale validations.
* **Availability**: Full-time.

### 👨‍💻 Pratham (Observability & Systems Engineer)
* **Current Responsibilities**:
  * Logging managers, Structured JSON log formatters, and ContextVars.
  * Performance metrics registry, latency aggregators, and Telemetry.
  * Advisory planning validations and risk scoring schemas.
* **Ownership**: `akaal/metrics/`, `akaal/advisory/`, and observability context managers.
* **Current Focus**: OpenTelemetry context propagation design.
* **Availability**: Full-time.

---

## 📂 Subsystem Ownership Matrix

| System Component | Primary Owner | Secondary Owner |
| :--- | :--- | :--- |
| **Akaal Pipeline (`akaal/core/pipeline.py`)** | Aalok | Pratham |
| **Database Adapters (`akaal/adapters/`)** | Aalok | Aalok |
| **Agent Fleet Core (`akaal/agents/`)** | Aalok | Pratham |
| **Structured Logging & Metrics** | Pratham | Aalok |
| **Migration Risk Advisory** | Pratham | Aalok |
| **E2E & Integration Validation** | Aalok | Pratham |

---

## 📝 Coordination Notes
* Synchronize daily via the `project/SPRINT.md` log.
* Any changes to core database schemas or dialect fixtures require review from both owners.
