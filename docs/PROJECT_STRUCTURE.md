# Akaal Repository Structure & Architecture Handbook

This document serves as the developer handbook for understanding the repository layout, architectural boundaries, component dependencies, and historical phase alignments of the Akaal platform.

---

## 🏛️ Overall Architectural Flow

Akaal is structured as a layered enterprise migration engine. The pipeline processes migrations through the following sequence:
1. **Schema Discovery / Advisory (akaal/advisory/)**: Parses source database DDl and schemas to assess risks and suggest migration strategies.
2. **Orchestration / Session Setup (akaal/core/pipeline.py)**: Spawns the central pipeline execution context, resolves adapters, and spins up the agent fleet.
3. **Agent Coordination (akaal/agents/)**: Operates a distributed fleet of actors (Scout, Golden Gate/GB, Validator, CDC, Checkpoint, and Manager) executing parallel writes and validation.
4. **Adapter Layer (akaal/adapters/)**: Abstracted dialect-specific drivers handling transactional reads, bulk writes, LOB transfers, and transaction controls.
5. **Observability (akaal/metrics/ & akaal/core/logging_manager.py)**: Tracks resource health, pool sizes, event logs, and latency measurements.

---

## 📂 Directory Layout

### 1. `akaal/` (Core Namespace Package)
The primary namespace containing all library modules, adapters, rules, and core agent models.

* **`akaal/adapters/`**
  * **Purpose**: Abstracted database interfaces separating engine logic from specific database drivers.
  * **Responsibility**: Translates standard platform requests into dialect-specific queries, bulk-copiers, or cloud object requests.
  * **Important Files**:
    * `rdbms/oracle_adapter.py`: Oracle-specific transaction, bulk-copy, and identity controls (Phase 7).
    * `rdbms/mysql_adapter.py`, `rdbms/postgres_adapter.py`, `rdbms/sqlserver_adapter.py`: Core transactional adapters.
  * **Interactions**: Utilizes models from `akaal/core/models/` and connection pools from `akaal/core/connection_pool/`. Called directly by the Agent Fleet.
  * **Phase**: Core adapters introduced in Phases 1–4, Oracle adapter certified in Phase 7.

* **`akaal/advisory/`**
  * **Purpose**: Migration planning and pre-flight assessments.
  * **Responsibility**: Inspects schemas, identifies cross-dialect incompatibilities (e.g. Oracle datatype maps), evaluates key structures, and generates migration strategies.
  * **Important Files**:
    * `rulebook/resolver.py`: Resolves dialect conversion rules.
    * `risk_scorer/risk_scorer.py`: Scores migrations based on schema size, constraint complexity, and data volume.
  * **Interactions**: Executed prior to agent fleet startup. Reads DDL definitions and produces a `MigrationConfig`.
  * **Phase**: Introduced in Phase 5.

* **`akaal/agents/`**
  * **Purpose**: Distributed execution fleet (Agent Fleet).
  * **Responsibility**: Performs parallel chunking, row transfers, real-time checksum checks, and ongoing replication.
  * **Important Files**:
    * `manager/manager_agent.py`: Orchestrates agent health, states, and lifecycles.
    * `gb/gb_agent.py`: Golden Gate replication / bulk transfer agent.
    * `validator/validator_agent.py`: Normalizes row data and performs checksum validations.
    * `cdc/cdc_agent.py`: Continuous Change Data Capture daemon.
  * **Interactions**: Emits telemetry to `akaal/metrics/`, reports to `akaal/core/message_bus/`, and writes status records to `akaal/core/checkpoint/`.
  * **Phase**: Spawned during Phase 5/6 parallel execution phases.

* **`akaal/core/`**
  * **Purpose**: Platform infrastructure, connection pools, event routers, and state machines.
  * **Responsibility**: Houses core execution primitives, thread-safe connection pooling, rate limiters, and the main pipeline orchestrator.
  * **Important Files**:
    * `pipeline.py`: Main E2E orchestrator executing schema analysis, planning, data transfer, and final validation.
    * `logging_manager.py`: Implements structured contextual JSON/text logging.
    * `connection_pool/`: Dynamic, thread-safe connection pooling engine.
    * `checkpoint/`: Storage layers tracking migration progress to support failure resumption.
  * **Interactions**: The foundation imported by all agents, adapters, and CLI entry points.
  * **Phase**: Reorganized into core namespaces during repository cleanup (Phase 8).

* **`akaal/metrics/`**
  * **Purpose**: Telemetry and latency registry.
  * **Responsibility**: Monitors connection allocation times, execution durations, memory footprints, and retry triggers.
  * **Important Files**:
    * `registry.py`: Holds session-scoped metric collectors.
  * **Interactions**: Injected into agents and core components via `ObservabilityContext`.

---

### 2. `tests/` (Verification Suites)
Reorganized under Phase 8 cleanup to cleanly segregate testing types.

* **`tests/unit/`**
  * **Purpose**: Core functional testing.
  * **Responsibility**: Tests checkpoint formats, normalizer functions, log structures, and metric registries in isolation.
* **`tests/validation/`**
  * **Purpose**: Cross-dialect integration validation.
  * **Responsibility**: Runs actual end-to-end data migrations across all 12 supported source-target dialect pairs.
* **`tests/benchmark/`**
  * **Purpose**: Performance validation.
  * **Responsibility**: Tests memory footprints, adaptive batch sizes, and data transfer rates.
* **`tests/stress/`**
  * **Purpose**: Resiliency and load limits.
  * **Responsibility**: Tests pool lock contention and parallel wave limits.
* **`tests/recovery/`**
  * **Purpose**: Failure validation.
  * **Responsibility**: Induces connection drop-outs at checkpoints and validates exact resume matches.
* **`tests/fixtures/`**
  * **Purpose**: Active schemas and settings.
  * **Responsibility**: Stores the ecommerce SQL definition and credentials JSON mapping.
* **`tests/archive/`**
  * **Purpose**: Legacy stage runners.
  * **Responsibility**: Preserves old raw phase runner scripts for historical context.

---

### 3. `docs/` & `benchmarks/`
* **`docs/`**: Holds architecture design records, metrics certifications, and execution walkthroughs. `docs/archive/` keeps old setup guides.
* **`benchmarks/`**: Contains core benchmarking scripts and historical performance reports.

---

## 📌 Root-Level Files (Why They Remain)

Only two non-configuration python files remain directly in the repository root:

1. **`main.py`**
   * **Why it remains**: This is the CLI runner. It must stay in the root to provide an immediate entry point for developers and deployment scripts executing `python main.py --config config.json`. It is not part of the library packaging, but rather the main command CLI console layer.
2. **`__init__.py` (Root is not a package, but `akaal/` is)**
   * **Why it remains inside `akaal/`**: The `akaal/__init__.py` file initializes the package namespace, exposes versioning, and re-exports core classes (`AkaalPipeline`, `MigrationConfig`, `configure_logging`, `migration_context`) to provide a clean API interface.
