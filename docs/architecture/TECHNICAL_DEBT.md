# TECHNICAL_DEBT.md - AKAAL Technical Debt Register

**System**: AKAAL Engine Platform  
**Phase**: Post Stage 3 Stabilization & Readiness Gate  
**Date**: 2026-07-24  
**Author**: Enterprise Technical Debt Registry Board  

> [!NOTE]
> **POLICY**: Items registered in this document are documented for tracking and future release planning. No production code changes are made to fix these items during the Foundation Freeze.

---

## 1. Summary of Registered Technical Debt

Total Registered Items: 12  
- **Critical**: 0  
- **High**: 2  
- **Medium**: 4  
- **Low**: 3  
- **Future Enhancement**: 3  

---

## 2. Technical Debt Item Catalog

### High Priority

#### TD-HIGH-01: Optional Third-Party Dependency Decoupling (`fastapi`, `typer`)
- **Category**: Dependency & Test Isolation  
- **Description**: `tests/api/test_cli.py` and `tests/api/test_rest.py` raise collection errors if `fastapi` or `typer` packages are not installed in the execution environment.  
- **Impact**: Test runner fails during full suite execution unless optional web dependencies are installed or explicitly ignored.  
- **Recommended Remediation**: Add `@pytest.mark.skipif` or lazy import guards inside API test modules.  

#### TD-HIGH-02: Isolated Standalone Script in Test Folder (`tests/archive/run_advisory_test.py`)
- **Category**: Test Suite Structure  
- **Description**: `run_advisory_test.py` located in `tests/archive/` attempts to load a relative file `test_ddl.sql` during pytest collection.  
- **Impact**: Causes a `FileNotFoundError` during raw `pytest` invocations if working directory lacks `test_ddl.sql`.  
- **Recommended Remediation**: Convert script to standard pytest fixture or move to `scripts/archive/`.  

---

### Medium Priority

#### TD-MED-01: Derived `Rate` Metric Manual Duration Input
- **Category**: Telemetry & Observability  
- **Description**: The `Rate` metric in `akaal.metrics.metrics` requires manual duration parameters during `observe(count, duration)` calls.  
- **Impact**: Callers must calculate delta time explicitly rather than automatic window calculation.  
- **Recommended Remediation**: Implement auto-timestamp delta calculation in `Rate.observe()`.  

#### TD-MED-02: Pytest Collection Warning on `TestingManager`
- **Category**: Test Hygiene  
- **Description**: `akaal/platform/testing/testing_manager.py` defines a class `TestingManager` with an `__init__` method, triggering a `PytestCollectionWarning` from pytest.  
- **Impact**: Cosmetically logs a collection warning during test runs.  
- **Recommended Remediation**: Rename class to `PlatformTestingManager` or set `__test__ = False`.  

#### TD-MED-03: Multiple Postgres Drivers (`psycopg` vs `psycopg2-binary`)
- **Category**: Dependency Architecture  
- **Description**: Workspace retains support for both `psycopg` (v3) and `psycopg2-binary` (v2).  
- **Impact**: Potential confusion regarding driver preference across team members.  
- **Recommended Remediation**: Standardize on `psycopg` v3 for all new database connector modules.  

#### TD-MED-04: Consolidate Database Connection Pooling Logic
- **Category**: Code Duplication  
- **Description**: Slight variation in pool configuration between `akaal/core/` pool managers and database adapters.  
- **Impact**: Redundant connection property validation logic.  
- **Recommended Remediation**: Extract unified `ConnectionPoolFactory` under `akaal/core/connection/pool.py`.  

---

### Low Priority

#### TD-LOW-01: Documentation References in Legacy Archives
- **Category**: Documentation Hygiene  
- **Description**: Sub-folders in `docs/archive/` reference Stage 1/2 milestone naming conventions.  
- **Impact**: Historical naming differences.  
- **Recommended Remediation**: Retain in archive; update cross-links in index.  

#### TD-LOW-02: Logging Output Formatting Consistency
- **Category**: Structured Logging  
- **Description**: Some background worker scripts emit raw string logs alongside JSON structured logs.  
- **Impact**: Log aggregation parsing rules require dual format handling.  
- **Recommended Remediation**: Enforce `StructuredLogger` globally via linting rule.  

#### TD-LOW-03: Temporary Debug Scripts in `scripts/`
- **Category**: Repository Hygiene  
- **Description**: `scripts/debug_customers.py`, `scripts/debug_hashes.py`, `scripts/debug_mysql.py`, `scripts/debug_ora_soi.py` remain in `scripts/`.  
- **Impact**: Minor script clutter.  
- **Recommended Remediation**: Move to `scripts/debug/` directory.  

---

### Future Enhancement Opportunities

#### FE-01: OpenTelemetry Distributed Tracing Integration
- **Category**: Observability  
- **Description**: Integrate trace context propagation across distributed worker nodes using OpenTelemetry baggage context slots.  

#### FE-02: Arrow Flight SQL Network Streaming Connector
- **Category**: Streaming Execution  
- **Description**: Upgrade inter-node streaming transport from gRPC zero-copy to Arrow Flight SQL protocol.  

#### FE-03: Auto-Tuning Dynamic Memory Pool Boundaries
- **Category**: Performance Optimization  
- **Description**: Dynamically adjust memory pool ceiling based on container cgroup limits.  
