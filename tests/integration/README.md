# Akaal Live Database Integration Smoke Tests

This directory contains integration smoke tests verifying that the Akaal migration engine executes successfully against real MySQL 8 and PostgreSQL 16 databases.

---

## 1. Prerequisites

Before running the smoke tests, ensure you have the following installed on your machine:
* **Docker Desktop**: Must be started and running.
* **Python 3.8+**
* **psycopg2-binary** (pip install psycopg2-binary)
* **PyMySQL** (pip install PyMySQL)

---

## 2. Docker Startup

Start the Docker containers hosting MySQL 8 and PostgreSQL 16:
```bash
docker-compose -f tests/integration/docker-compose.yml up -d
```
Verify that both containers are running and healthy:
```bash
docker ps
```
The MySQL container exposes port `3306` and PostgreSQL container exposes port `5432` on localhost.

---

## 3. Database Initialization

The databases, users, and schemas are initialized automatically by the containers. The integration tests themselves handle schema drops, DDL schema loading (`sample_schema.sql`), and seed data population (`sample_data.sql`) on the source database before each test run.

---

## 4. Running Integration Tests

Run the MySQL to PostgreSQL integration test:
```bash
py -m unittest tests.integration.test_real_mysql_to_postgres
```

Run the PostgreSQL to MySQL integration test:
```bash
py -m unittest tests.integration.test_real_postgres_to_mysql
```

---

## 5. Cleaning Up

To stop the containers and purge the data volumes, run:
```bash
docker-compose -f tests/integration/docker-compose.yml down -v
```
This guarantees a clean environment for subsequent runs.
