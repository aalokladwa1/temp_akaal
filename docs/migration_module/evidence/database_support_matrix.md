# Multi-Database Production Capability Matrix

**Phase Baseline:** P1.6 Universal Physical Transport Foundation

---

## 1. Target Four-Engine Directional Matrix

```text
SOURCE ↓ / TARGET →

                 Oracle              PostgreSQL          MySQL               MSSQL
Oracle             —               REAL_DB_PROVEN    INTEGRATION_PROVEN  INTEGRATION_PROVEN
PostgreSQL     INTEGRATION_PROVEN      —            INTEGRATION_PROVEN  INTEGRATION_PROVEN
MySQL          INTEGRATION_PROVEN  INTEGRATION_PROVEN      —            INTEGRATION_PROVEN
MSSQL          INTEGRATION_PROVEN  INTEGRATION_PROVEN  INTEGRATION_PROVEN      —
```

### Classification Legend:
- **`REAL_DB_PROVEN`**: Production physical reader (`OraclePhysicalReader`) → `ParallelReplicationScheduler` → Production physical writer (`PostgreSQLPhysicalWriter`) executed and verified against real Oracle and PostgreSQL database instances.
- **`INTEGRATION_PROVEN`**: Universal physical reader (`Oracle`, `PostgreSQL`, `MySQL`, `MSSQL`) → `ParallelReplicationScheduler` → Universal physical writer (`Oracle`, `PostgreSQL`, `MySQL`, `MSSQL`) verified via canonical contracts, type-safe array bindings, and mock-isolated unit/integration test suites.

---

## 2. Feature-Level Engine Support Matrix

| Engine Feature | Oracle | PostgreSQL | MySQL | MSSQL |
| :--- | :---: | :---: | :---: | :---: |
| **Real Connection & Handshake** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Schema & Table Discovery** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Column Metadata & PK Discovery** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Target Schema DDL Generation** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Physical Bulk Reader** | ✅ REAL (`OraclePhysicalReader`) | ✅ REAL (`PostgreSQLPhysicalReader`) | ✅ REAL (`MySQLPhysicalReader`) | ✅ REAL (`MSSQLPhysicalReader`) |
| **Physical Bulk Writer** | ✅ REAL (`OraclePhysicalWriter`) | ✅ REAL (`PostgreSQLPhysicalWriter`) | ✅ REAL (`MySQLPhysicalWriter`) | ✅ REAL (`MSSQLPhysicalWriter`) |
| **Parallel Partition Transport** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Checkpoint & Resumption** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Native CDC Adapter** | ✅ REAL (`oracle_cdc.py`) | ✅ REAL (`postgres_cdc.py`) | ✅ REAL (`mysql_cdc.py`) | ✅ REAL (`mssql_cdc.py`) |
