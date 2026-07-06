# Akaal Migration Engine — Stage 1 Production Sign-off Checklist

This document acts as the formal production sign-off sheet for certifying the Stage 1 database migration (MySQL Source → PostgreSQL Target) as production ready.

---

## □ Schema Validation
- [ ] Table Count parity (exactly 5 tables exist on target database).
- [ ] Column Count matching (column counts of all tables match).
- [ ] Column Ordinal Order matches source tables.
- [ ] Datatype mappings match target specifications.
- [ ] Nullable settings match source column properties.
- [ ] Default values correctly persist or default to target equivalents.
- [ ] Sequence generation objects created and associated with target tables.

## □ Data Validation
- [ ] Row count matches exactly across all tables (465,000 total rows).
- [ ] Lowest and highest primary key IDs (`id` columns) match exactly.
- [ ] Null values count in columns matches exactly.
- [ ] Empty string cell (`''`) counts are identical on source and target.
- [ ] Duplicate primary key checks return 0 rows on target tables.
- [ ] Integrity check comparisons of random row subsets confirm data matches.

## □ Constraint Validation
- [ ] Primary Keys are correctly set and functioning.
- [ ] Foreign Key counts and definitions (exactly 3 FK constraints) exist on target.
- [ ] Orphan checks on child records (foreign key columns) return 0 rows.
- [ ] Unique constraints and composite keys (e.g. `uq_order_product`) match.
- [ ] Secondary index declarations exist and are correctly initialized.

## □ Unicode Validation
- [ ] Multi-language UTF-8 character strings (Japanese, Cyrillic, Hindi, German, Arabic) copy without character loss.
- [ ] Emojis (e.g. `😊`, `🚀`, `💻`, `☕`, `🇩🇪`, `🇰🇷`, `🌴`) are stored and read correctly on target.
- [ ] Character length constraints are preserved without truncation on multi-byte characters.

## □ JSON Validation
- [ ] Target JSON fields parse successfully as structurally valid JSON.
- [ ] Extracting JSON keys (`category`, `details.rating`) matches source values.
- [ ] Total JSON key counts are identical on source and target.

## □ BLOB Validation
- [ ] Total binary size (`octet_length(raw_payload)`) matches source lengths exactly.
- [ ] Average binary size per column matches.
- [ ] Hex checksum comparison (`portable_sha256()` or `md5()`) matches source hashes.

## □ Metrics Validation
- [ ] Pipeline reports accurate execution duration in log summary.
- [ ] Total count of rows processed matches target database totals.
- [ ] Average throughput metric is correctly logged.

## □ Logging Validation
- [ ] Logging statements categorized by level (`INFO`, `WARNING`, `ERROR`).
- [ ] Phase trace metrics (`WORKFLOW_STARTED`, `TASK_ASSIGNED`, `MIGRATION_COMPLETED`) recorded.
- [ ] Errors, exceptions, or connection retries clearly logged with cause details.

## □ Checkpoint Validation
- [ ] SQLite checkpoint database created successfully.
- [ ] Interrupted execution resumes from last checkpoint row without errors.
- [ ] Checkpoint indices match correctly on resume.

## □ Performance Validation
- [ ] Peak RAM usage remains below the 500MB boundary.
- [ ] CPU utilization is balanced across concurrent workers.
- [ ] Connection pool sizes do not exhaust database limits during execution.

---

## Certification of Completion

* **Overall Status**: `[ Pass / Fail ]`
* **Reviewer**: `[                     ]`
* **Date**: `[ 2026-07-05 ]`
