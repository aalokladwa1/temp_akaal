"""
tests/conftest.py
=================
Root test configuration and external live infrastructure prerequisite gating.
Provides explicit, truthful gating for tests requiring live database daemons
or external network sockets, classifying them as EXTERNAL_DEFERRED when
prerequisites are unavailable in the execution environment.
"""

from __future__ import annotations

import os
import socket
import pytest
from typing import Optional


def is_service_reachable(host: str, port: int, timeout: float = 0.3) -> bool:
    """Checks if a TCP socket is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.error):
        return False


def require_postgres(
    host: str = "127.0.0.1",
    port: int = 5432,
    user: str = "akaal_admin",
    password: str = "AkaalPass2026",
    database: str = "postgres",
) -> None:
    """Explicit prerequisite gate for live PostgreSQL database."""
    import unittest
    target_host = os.environ.get("AKAAL_TEST_POSTGRES_HOST", host)
    target_port = int(os.environ.get("AKAAL_TEST_POSTGRES_PORT", str(port)))
    if not is_service_reachable(target_host, target_port):
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live PostgreSQL daemon unavailable at {target_host}:{target_port}")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=target_host,
            port=target_port,
            user=os.environ.get("AKAAL_TEST_POSTGRES_USER", user),
            password=os.environ.get("AKAAL_TEST_POSTGRES_PASSWORD", password),
            dbname=os.environ.get("AKAAL_TEST_POSTGRES_DB", database),
            connect_timeout=1,
        )
        conn.close()
    except Exception as exc:
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live PostgreSQL authentication/connection failed at {target_host}:{target_port}: {exc}")


def require_mysql(
    host: str = "127.0.0.1",
    port: int = 3306,
    user: str = "akaal_admin",
    password: str = "AkaalPass2026",
    database: str = "akaal_smoke_test",
) -> None:
    """Explicit prerequisite gate for live MySQL database."""
    import unittest
    target_host = os.environ.get("AKAAL_TEST_MYSQL_HOST", host)
    target_port = int(os.environ.get("AKAAL_TEST_MYSQL_PORT", str(port)))
    if not is_service_reachable(target_host, target_port):
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live MySQL daemon unavailable at {target_host}:{target_port}")
    try:
        import pymysql
        conn = pymysql.connect(
            host=target_host,
            port=target_port,
            user=os.environ.get("AKAAL_TEST_MYSQL_USER", user),
            password=os.environ.get("AKAAL_TEST_MYSQL_PASSWORD", password),
            database=os.environ.get("AKAAL_TEST_MYSQL_DB", database),
            connect_timeout=1,
        )
        conn.close()
    except Exception as exc:
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live MySQL authentication/connection failed at {target_host}:{target_port}: {exc}")


def require_oracle(
    host: str = "127.0.0.1",
    port: int = 1521,
    user: str = "akaal_admin",
    password: str = "AkaalPass2026",
    service_name: str = "FREEPDB1",
) -> None:
    """Explicit prerequisite gate for live Oracle database."""
    import unittest
    target_host = os.environ.get("AKAAL_TEST_ORACLE_HOST", host)
    target_port = int(os.environ.get("AKAAL_TEST_ORACLE_PORT", str(port)))
    if not is_service_reachable(target_host, target_port):
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live Oracle database unavailable at {target_host}:{target_port}")


def require_mssql(host: str = "127.0.0.1", port: int = 1433) -> None:
    """Explicit prerequisite gate for live MSSQL database."""
    import unittest
    target_host = os.environ.get("AKAAL_TEST_MSSQL_HOST", host)
    target_port = int(os.environ.get("AKAAL_TEST_MSSQL_PORT", str(port)))
    if not is_service_reachable(target_host, target_port):
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live MSSQL database unavailable at {target_host}:{target_port}")


def require_mongodb(host: str = "127.0.0.1", port: int = 27017) -> None:
    """Explicit prerequisite gate for live MongoDB daemon."""
    import unittest
    target_host = os.environ.get("AKAAL_TEST_MONGODB_HOST", host)
    target_port = int(os.environ.get("AKAAL_TEST_MONGODB_PORT", str(port)))
    if not is_service_reachable(target_host, target_port):
        raise unittest.SkipTest(f"EXTERNAL_DEFERRED: Live MongoDB daemon unavailable at {target_host}:{target_port}")

