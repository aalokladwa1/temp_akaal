# Phase 7 Production Readiness Validation Checklist

This checklist defines every validation item that must pass before the checkpoint and recovery subsystem is considered production ready.

---

## 1. Pre-Migration
- [ ] **Database Reachability**: Run connection queries from Akaal to ensure local MySQL and PostgreSQL databases are reachable.
- [ ] **Clean Target Setup**: Truncate all tables on target PostgreSQL database (`akaal_validation_target`) and delete any existing local `checkpoints.db` file.
- [ ] **Source Schema Deployment**: Execute `sample_schema.sql` on the source MySQL database and confirm all 5 tables are empty.
- [ ] **Dataset Generation**: Run `generate_validation_seed.py` and confirm that `sample_data.sql` exists and is populated.
- [ ] **Source Seed Load**: Import `sample_data.sql` into the source MySQL database and verify no SQL errors occur.
- [ ] **Source Count Audit**: Verify the source MySQL tables contain exactly 465,000 records total (10k Users, 5k Products, 100k Orders, 300k Items, 50k Logs).

---

## 2. Migration
- [ ] **Pipeline Execution Launch**: Start the migration runner with the configure block.
- [ ] **Table Discovery Verification**: Monitor console logs to confirm that all 5 tables are discovered dynamically by the scout agent.
- [ ] **Active Connection Pool Monitoring**: Check system processes to verify database connection pool objects do not exhaust server limits.
- [ ] **Adaptive Batch Scaling**: Verify that the pipeline adjusts batch block sizes depending on table weight (e.g. smaller sizes on tables with BLOBs/JSONs).
- [ ] **Audit Trail Log Verification**: Ensure console prints clear updates on each table state transition.

---

## 3. Post-Migration
- [ ] **Target Row Count Verification**: Execute the count queries on PostgreSQL and verify matching row counts for all tables.
- [ ] **PK Preservation Check**: Verify that target primary key definitions are preserved on all tables and duplicate checking queries return 0 rows.
- [ ] **FK Integrity Scans**: Confirm target foreign keys enforce relationships and referential integrity checks return 0 orphaned rows.
- [ ] **Unique Constraints Check**: Confirm composite unique constraint `uq_order_product` is active on `order_items`.
- [ ] **Aggregate Precision Check**: Confirm that decimal aggregations on total amounts match source totals exactly.
- [ ] **Timestamp Bounds Parity**: Confirm earliest/latest dates align exactly on target columns.
- [ ] **NULL vs Empty Cell Parity**: Confirm that NULL and empty string counts match source counts exactly.
- [ ] **JSON Format Check**: Confirm that JSON columns parse correctly and key-value extractions match source values.
- [ ] **BLOB Hash Match**: Confirm that MD5/SHA256 byte hash comparisons match source hashes (with pgcrypto fallback).
- [ ] **Unicode & Emoji Integrity**: Check users/products tables for accents, Cyrillic, Kanji, Arabic, and Emoji characters, confirming no encoding losses occurred.

---

## 4. Performance
- [ ] **Duration Profiling**: Record total migration execution time using a stopwatch or log timestamps.
- [ ] **Throughput Calculation**: Calculate rows/sec transfer speed to verify performance metrics.
- [ ] **Peak Memory Consumption**: Verify peak memory usage is below the 500MB threshold.
- [ ] **Peak CPU Load Monitoring**: Track CPU consumption to ensure system load is balanced.

---

## 5. Reliability
- [ ] **Connection Loss Safety**: Simulating source database connection drop should trigger retry loops and succeed once restored.
- [ ] **Lock Contention Check**: Confirm the SQLite checkpoint database does not throw locking errors during concurrent agent accesses.

---

## 6. Recovery
- [ ] **Checkpoint Creation**: Confirm that checkpoint rows are written to the SQLite database.
- [ ] **State Resumption Logic**: Kill the migration pipeline mid-run and restart it. Confirm it reads checkpoints and resumes from the last completed batch without duplicating records.
- [ ] **Loop Governor Safety**: Verify that loop governor aborts execution if failures repeat beyond the max retry threshold.

---

## 7. Documentation
- [ ] **Benchmark Capture Sheet**: Fill in all values in the `benchmark_capture.md` template.
- [ ] **Validation Report**: Compile and save the final report using the `validation_report_template.md`.
- [ ] **Failure Logging**: Fill out the `failure_capture.md` sheet if any step encountered issues.
