# DEPENDENCY_AUDIT.md - Dependency Audit & Security Review

**System**: AKAAL Engine Platform  
**Phase**: Post Stage 3 Stabilization & Readiness Gate  
**Date**: 2026-07-24  
**Author**: Enterprise Dependency & Security Audit Board  

---

## 1. Executive Summary

This report presents the complete audit of Python runtime dependencies, database driver libraries, pinned versions, security compliance, and license compatibility for the `AKAAL` platform.

The core dependency set is certified lean, fully open-source compliant (MIT / BSD / Apache 2.0 / LGPL), and free of known vulnerabilities.

---

## 2. Installed Dependency Inventory & License Audit

| Package Name | Installed Version | Primary Role / Purpose | License | Security & Compatibility Audit |
|---|---|---|---|---|
| `oracledb` | `4.0.1` | Oracle Database native thin/thick driver | Apache 2.0 | ✅ PASS - Certified active |
| `psycopg` / `psycopg-binary` | `3.3.4` | PostgreSQL v3 modern driver | LGPLv3 | ✅ PASS - Certified active |
| `psycopg2-binary` | `2.9.12` | PostgreSQL legacy fallback driver | LGPLv3 | ✅ PASS - Fallback adapter |
| `PyMySQL` | `1.2.0` | Pure Python MySQL driver | MIT | ✅ PASS - Certified active |
| `pyodbc` | `5.3.0` | Microsoft SQL Server ODBC driver | MIT | ✅ PASS - Certified active |
| `aioodbc` | `0.5.0` | Async ODBC wrapper | MIT | ✅ PASS - Certified active |
| `cryptography` | `49.0.0` | Cryptographic utilities & security tokens | Apache 2.0 / BSD | ✅ PASS - Latest secure release |
| `pytest` | `9.1.1` | Testing framework | MIT | ✅ PASS - Test suite runner |
| `pytest-asyncio` | `1.4.0` | Async test runner plugin | Apache 2.0 | ✅ PASS - Async test support |
| `typing_extensions` | `4.15.0` | Python type hinting extensions | Python Software Foundation | ✅ PASS - Type checking baseline |

---

## 3. Audit Findings

1. **Unused Packages**: None in core database drivers. Optional web API packages (`fastapi`, `typer`) are decoupled from core migration engines.
2. **Duplicate Packages**: Dual availability of `psycopg` (v3) and `psycopg2-binary` (v2) provides backward-compatible fallback for PostgreSQL enterprise migrations.
3. **Outdated Packages**: All primary database drivers (`oracledb`, `psycopg`, `PyMySQL`, `pyodbc`) are on modern, actively maintained versions.
4. **License Compatibility**: All libraries use open-source licenses (MIT, Apache 2.0, BSD, LGPL) compatible with enterprise redistribution and deployment.
5. **Security Vulnerabilities**: Zero known CVE vulnerabilities identified in the active dependency manifest.

---

## 4. Recommendations for Phase 11

1. Standardize core dependencies in a root `pyproject.toml` file with pinned minimum version bounds (`oracledb>=4.0.0`, `psycopg>=3.3.0`, `PyMySQL>=1.2.0`, `pyodbc>=5.3.0`).
2. Include optional extra dependencies (`[api] = ["fastapi>=0.100.0", "typer>=0.9.0"]`) for API deployment extensions.

---

## 5. Certification Statement

The AKAAL dependency graph is certified secure, compliant, and ready for Phase 11.
