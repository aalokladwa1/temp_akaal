# Multi-Database Production Capability Matrix

**Phase Baseline:** P1.5  

---

## 1. Real Directional Support Matrix

```text
SOURCE ↓ / TARGET →

                 Oracle       PostgreSQL       MySQL       MSSQL
Oracle             —         REAL_DB_PROVEN      NOT_SUP     NOT_SUP
PostgreSQL      NOT_SUP           —            NOT_SUP     NOT_SUP
MySQL           NOT_SUP        PARTIAL           —         NOT_SUP
MSSQL           NOT_SUP        PARTIAL         NOT_SUP        —
```

### Classification Legend:
- **`REAL_DB_PROVEN`**: Production physical reader (`OraclePhysicalReader`) → `ParallelReplicationScheduler` → Production physical writer (`PostgreSQLPhysicalWriter`) executed and verified against real Oracle and PostgreSQL database instances.
- **`PARTIAL`**: Schema discovery, catalog extraction, and DDL adapters exist in `akaal/adapters/rdbms/` (`mysql_adapter.py`, `mssql_adapter.py`), but generic physical transport resolver (`resolver.py`) lacks physical streaming readers for MySQL and MSSQL in P1.
- **`NOT_SUPPORTED`**: Physical reader/writer pair not registered in `akaal/replication/resolver.py`.

---

## 2. Feature-Level Engine Support Matrix

| Engine Feature | Oracle | PostgreSQL | MySQL | MSSQL |
| :--- | :---: | :---: | :---: | :---: |
| **Real Connection & Handshake** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Schema & Table Discovery** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Column Metadata & PK Discovery** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Target Schema DDL Generation** | ✅ REAL | ✅ REAL | ✅ REAL | ✅ REAL |
| **Physical Bulk Reader** | ✅ REAL (`OraclePhysicalReader`) | ❌ PARTIAL | ❌ PARTIAL | ❌ PARTIAL |
| **Physical Bulk Writer** | ❌ PARTIAL | ✅ REAL (`PostgreSQLPhysicalWriter`) | ❌ PARTIAL | ❌ PARTIAL |
| **Parallel Partition Transport** | ✅ REAL | ✅ REAL | ❌ PARTIAL | ❌ PARTIAL |
| **Checkpoint & Resumption** | ✅ REAL | ✅ REAL | ❌ PARTIAL | ❌ PARTIAL |
| **Native CDC Adapter** | ✅ REAL (`oracle_cdc.py` in backup) | ✅ REAL (`postgres_cdc.py`) | ✅ REAL (`mysql_cdc.py` in backup) | ✅ REAL (`mssql_cdc.py` in backup) |
