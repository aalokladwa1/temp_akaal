# Native Database Smoke Tests

This directory contains the native Windows database smoke testing framework for validating the Akaal migration engine. It verifies schema parity, data integrity, and constraint correctness across live, locally installed instances of MySQL 8, PostgreSQL 16, and SQL Server 2022.

---

## 1. Directory Structure

```text
tests/
    validation/
        README.md                     # This documentation file
        fixtures.py                   # Reusable connection, schema loading, and verification fixtures
        schemas/
            ecommerce.sql             # Target database schema definitions for MySQL, Postgres, and SQL Server
        datasets/
            ecommerce_seed.sql        # Reproducible e-commerce DML seed statements for all three dialects
        test_mysql_to_postgres.py     # Smoke test: MySQL -> PostgreSQL
        test_postgres_to_mysql.py     # Smoke test: PostgreSQL -> MySQL
        test_mysql_to_sqlserver.py     # Smoke test: MySQL -> SQL Server
        test_sqlserver_to_postgres.py  # Smoke test: SQL Server -> PostgreSQL
        test_postgres_to_sqlserver.py  # Smoke test: PostgreSQL -> SQL Server
        test_sqlserver_to_mysql.py     # Smoke test: SQL Server -> MySQL
```

---

## 2. Configuration & Credentials

Connections can be configured using environment variables. If not defined, the framework uses these defaults:

### PostgreSQL
*   `POSTGRES_HOST`: `127.0.0.1`
*   `POSTGRES_PORT`: `5432`
*   `POSTGRES_USER`: `postgres`
*   `POSTGRES_PASSWORD`: `postgres`
*   `POSTGRES_DATABASE`: `akaal_smoke` (automatically created if it does not exist)

### SQL Server (MSSQL)
*   `SQLSERVER_DRIVER`: `ODBC Driver 17 for SQL Server` or `ODBC Driver 18 for SQL Server`
*   `SQLSERVER_SERVER`: `localhost`
*   `SQLSERVER_DATABASE`: `akaal_smoke` (automatically created if it does not exist)
*   `SQLSERVER_TRUSTED`: `yes` (utilizes Windows Authentication, omitting UID/PWD credentials)
*   `SQLSERVER_USER`: (optional UID)
*   `SQLSERVER_PASSWORD`: (optional PWD)

### MySQL
*   `MYSQL_HOST`: `127.0.0.1`
*   `MYSQL_PORT`: `3306`
*   `MYSQL_USER`: `root`
*   `MYSQL_PASSWORD`: `rootpassword`
*   `MYSQL_DATABASE`: `akaal_smoke`

---

## 3. How to Run the Tests

If a database service is offline or not installed, the corresponding tests will **skip gracefully** using `unittest.SkipTest`, while the accessible database migrations (e.g. Postgres <-> SQL Server) will execute fully.

### Run All Validation Tests
```bash
$env:PYTHONPATH="a:\temp_akaal"; py -m unittest discover -s tests/validation -p "test_*.py"
```

### Run PostgreSQL <-> SQL Server Migrations Only
```bash
$env:PYTHONPATH="a:\temp_akaal"; py -m unittest tests/validation/test_postgres_to_sqlserver.py
$env:PYTHONPATH="a:\temp_akaal"; py -m unittest tests/validation/test_sqlserver_to_postgres.py
```

---

## 4. Diagnostics & Failures
If any validation checks fail (e.g. mismatched row counts, broken constraint references, or altered binary payloads), the assertions will print detailed diagnostics detailing the mismatch to standard output.
