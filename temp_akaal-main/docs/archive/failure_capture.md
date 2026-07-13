# Failure Capture & Diagnostics Template

Use this document to register diagnostics, logs, and tracebacks if any phase of the Stage 1 database migration fails or throws an exception.

---

## 1. Environment
* **Operating System**: `[ e.g. Windows 11 Enterprise ]`
* **Python Version**: `[ e.g. 3.11.4 ]`
* **Akaal Version/Git Commit Hash**: `[ e.g. commit a8b3cd12 ]`

---

## 2. Database Versions
* **MySQL Server Version**: `[ e.g. 8.0.33 ]`
* **PostgreSQL Server Version**: `[ e.g. 16.1 ]`

---

## 3. Connection Strings (Masked)
* **Source Connection (MySQL)**: `mysql://[user]:[password]@[host]:3306/akaal_validation`
* **Target Connection (PostgreSQL)**: `postgresql://[user]:[password]@[host]:5432/akaal_validation_target`

---

## 4. Migration Configuration
* **Configured Batch Size**: `[ e.g. 2000 ]`
* **Worker Count (max_workers)**: `[ e.g. 4 ]`
* **Parallel Migration Enabled**: `[ True / False ]`
* **Retry Limit**: `[ e.g. 3 ]`
* **Timeout Limit**: `[ e.g. 30s ]`

---

## 5. Checkpoint Status
* **Checkpoint Database Path**: `[ e.g. a:\temp_akaal\checkpoints.db ]`
* **Last Written Checkpoint ID**: `[ e.g. c8b742aa-5942-491e-ac14 ]`
* **Last Logged Checkpoint Details (Table/Batch)**:
  ```sql
  -- Query: SELECT project_id, migration_id, table_name, batch_number, workflow_state FROM checkpoints;
  [ Insert rows here ]
  ```

---

## 6. Metrics Summary
* **Migration Duration before crash (seconds)**: `[                     ]`
* **Total rows successfully copied**: `[                     ]`
* **Throughput before crash (rows/sec)**: `[                     ]`
* **Peak Memory usage (MB)**: `[                     ]`
* **Average CPU usage (%)**: `[                     ]`

---

## 7. Last Successful Stage
* **Discovery Stage**: `[ Pass / Fail ]`
* **GB Import Stage**: `[ Pass / Fail ]`
* **GB Validation Stage**: `[ Pass / Fail ]`
* **Human Approval Stage**: `[ Pass / Fail ]`
* **Production Migration (Active Table)**: `[ e.g. order_items ]`

---

## 8. Exception Stack Trace
```python
[ Paste traceback here ]
```

---

## 9. SQL Statement Causing Failure
```sql
[ INSERT FAILED QUERY HERE ]
```

---

## 10. Resolution
* **Diagnostic Findings**:
  ```markdown
  [ Describe findings and hypotheses here ]
  ```
* **Workarounds / Fixes Applied**:
  ```markdown
  [ Describe steps taken to fix the issue ]
  ```

---

## 11. Retest Result
* **Retest Date**: `[ 2026-07-05 ]`
* **Retest Status**: `[ Pass / Fail ]`
* **Retest Notes**:
  ```markdown
  [ Add retest observation here ]
  ```
