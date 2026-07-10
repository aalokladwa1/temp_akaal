# Phase 6 – Microsoft SQL Server Setup & Test Guide

This document outlines the system requirements, Python dependencies, environment variables, and verification steps necessary to execute the Phase 6 live Microsoft SQL Server integration and adversarial tests.

## 1. System Requirements

### Microsoft ODBC Driver
To communicate with SQL Server via Python, you must have the official Microsoft ODBC Driver for SQL Server installed on the host machine.
* **ODBC Driver 18 for SQL Server** (Recommended)
* **ODBC Driver 17 for SQL Server**

#### Installation Links
* **Windows/Linux/macOS:** [Microsoft ODBC Driver for SQL Server installation guide](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### Target SQL Server Version
* **Microsoft SQL Server 2022** (or higher) is recommended.
* You need access to two separate databases (or two separate database instances) to serve as the **Source** and the **Target** for migrations.

---

## 2. Python Dependencies

Ensure the following packages are installed in your Python environment:

```bash
pip install aioodbc pyodbc
```

* **pyodbc**: Provides the baseline DB-API 2.0 driver layer.
* **aioodbc**: Provides the async connection pool wrapper used by `MSSQLAdapter`.

---

## 3. Environment Variables

To run the live integration tests, you must configure the following independent environment variables for your Source and Target SQL Server instances.

```bash
# --- Source Database Configurations ---
export MSSQL_SOURCE_HOST="your-source-host"
export MSSQL_SOURCE_PORT=1433
export MSSQL_SOURCE_DATABASE="your-source-db"
export MSSQL_SOURCE_USERNAME="your-source-user"
export MSSQL_SOURCE_PASSWORD="your-source-password"

# --- Target Database Configurations ---
export MSSQL_TARGET_HOST="your-target-host"
export MSSQL_TARGET_PORT=1433
export MSSQL_TARGET_DATABASE="your-target-db"
export MSSQL_TARGET_USERNAME="your-target-user"
export MSSQL_TARGET_PASSWORD="your-target-password"
```

> [!NOTE]
> If these variables are not supplied or are incomplete, the test script will print a skip message and exit cleanly without failing the build.

---

## 4. Verifying Installation

### A. Verify Installed ODBC Drivers
You can check which ODBC drivers are recognized on your machine by running the following Python command:

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
```

**Expected Output (containing either Driver 18 or 17):**
```python
['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', ...]
```

### B. Verify Connectivity via Python
Use the following snippet to verify that pyodbc can reach your SQL Server:

```python
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=your-host,1433;"
    "DATABASE=your-db;"
    "UID=your-user;"
    "PWD=your-password;"
    "TrustServerCertificate=Yes;"
)
conn = pyodbc.connect(conn_str)
print("Connected successfully!")
conn.close()
```

---

## 5. Execution

To run the Phase 6 test suite:

```bash
python phase6_mssql_test.py
```
