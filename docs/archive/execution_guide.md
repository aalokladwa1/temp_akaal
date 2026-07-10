# Akaal Migration Engine — Stage 1 Validation Guide
This guide provides the complete, step-by-step instructions for executing the Phase 7 database migration validation from MySQL (Source) to PostgreSQL (Target) on local installations.

---

## Prerequisites

Before beginning the migration, ensure your local environment satisfies the following requirements:

* **MySQL Server**: Version 8.0 or newer
* **PostgreSQL Server**: Version 16 or newer
* **Python**: Version 3.10 or newer
* **Required Driver Packages**:
  * `mysql-connector-python` or `pymysql` (MySQL adapter)
  * `psycopg2-binary` or `pg8000` (PostgreSQL adapter)
* **Expected Folder Structure**:
  ```
  a:\temp_akaal\
  ├── akaal\                       # Akaal Core packages
  │   ├── adapters\                # DB adapters (mysql, postgresql, etc.)
  │   ├── agents\                  # Manager, Validator, Scout agents
  │   └── core\                    # Checkpoint and state managers
  ├── tests\                       # Integration & smoke test suites
  ├── generate_validation_seed.py  # Seed generation script
  ├── sample_schema.sql            # MySQL source schema definitions
  ├── validation_queries.sql       # Verification SQL commands
  ├── expected_results.md          # Verification Checklist
  ├── failure_capture.md           # Debug templates
  ├── benchmark_capture.md         # Benchmarking results sheet
  ├── validation_report_template.md # Reusable report template
  ├── validation_checklist.md      # Detailed actionable readiness checklist
  └── walkthrough.md               # Summary description
  ```

---

## PostgreSQL Hashing & Fallback Design

> [!NOTE]
> The validation SQL script dynamically evaluates if the `pgcrypto` extension is installed on the target PostgreSQL database. 
> * **With `pgcrypto`**: The script runs the standard SHA-256 binary hash check using `digest()`.
> * **Without `pgcrypto`**: The script automatically falls back to comparing `md5()` hex checksum strings of the BLOB values, ensuring compatibility out of the box without requiring superuser extensions.

---

## Execution Flow

### Step 1: Generate dataset
Run the seed generator script to write the local DML dump file.
* **Command**: `python generate_validation_seed.py`
* **Estimated Completion Time**: **5 seconds**

---

### Step 2: Import MySQL schema
Initialize the source schema against your local MySQL instance.
* **Commands**:
  * Log into MySQL CLI: `mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS akaal_validation;"`
  * Import schema: `mysql -u root -p akaal_validation < sample_schema.sql`
* **Estimated Completion Time**: **2 seconds**

---

### Step 3: Import seed data
Load the generated seed DML statements into your local MySQL source database.
* **Command**: `mysql -u root -p akaal_validation < sample_data.sql`
* **Estimated Completion Time**: **2 - 4 minutes** (depending on SSD and disk throughput)

---

### Step 4: Run Akaal migration
Configure the target PostgreSQL connection string parameters in the MigrationConfig and trigger the migration pipeline execution.
* **Command**: `python -m akaal.core.pipeline --config config.json`
* **Estimated Completion Time**: **5 - 8 minutes** (465,000 records parallel transfer and checkpointing)

---

### Step 5: Execute validation SQL
Run queries in `validation_queries.sql` on MySQL and PostgreSQL to collect metrics and check structural parity.
* **Estimated Completion Time**: **30 seconds**

---

### Step 6: Compare outputs
Compare query results (row counts, checksums, datatype descriptions, auto-increment sequences) against the sign-off sheet.
* **Estimated Completion Time**: **15 minutes**

---

### Step 7: Record benchmark numbers
Fill in the metrics and capture performance statistics (e.g. CPU, memory, rows/sec throughput) inside `benchmark_capture.md`.
* **Estimated Completion Time**: **5 minutes**

---

### Step 8: Record failures (if any)
If the run fails or encounters errors, copy logs, traceback details, and active checkpoint states into the `failure_capture.md` template.
* **Estimated Completion Time**: **10 minutes**

---

## Performance Capture

Record the following statistics after every migration run for comparison and profiling:

* **Total migration duration (seconds)**: `[                     ]`
* **Total rows migrated**: `[                     ]` (Expected: 465,000)
* **Average migration throughput (rows/sec)**: `[                     ]`
* **Total tables migrated**: `[                     ]` (Expected: 5)
* **Average table duration (seconds)**: `[                     ]`
* **Largest table duration (seconds)**: `[                     ]` (Table name: `[             ]`)
* **Batch size evolution (Initial vs. Final)**: `[                     ]`
* **Retry count (times)**: `[                     ]`
* **Checkpoint count generated**: `[                     ]`
* **Peak memory usage (MB)**: `[                     ]`
* **Average CPU usage (%)**: `[                     ]`
