"""
akaalEngine.connection.sessions.initialization
==============================================
Purpose-specific session initialization and parameter enforcement.
Applies read-only constraints, statement timeouts, schema search paths, and isolation levels.
"""

from __future__ import annotations

import logging
from typing import Any

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    SessionInitializationError,
)
from akaalEngine.connection.models.session import (
    InternalSessionHandle,
    IsolationLevel,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.sessions.initialization")


class SessionInitializer:
    """
    Initializes physical database / endpoint sessions according to SessionRequest purposes.
    Enforces mandatory safety controls (read-only mode, statement timeouts, isolation levels).
    Fails closed if a required safety control cannot be established.
    """

    @classmethod
    def initialize_session(
        cls,
        handle: InternalSessionHandle,
        request: SessionRequest,
    ) -> None:
        """
        Applies purpose-specific flags, timeout settings, and isolation levels.
        Raises SessionInitializationError if a mandatory safety command fails.
        """
        handle.purpose = request.purpose
        conn = handle.physical_connection
        if conn is None:
            return

        # 1. Store session variables
        is_ro = request.is_effective_read_only()
        handle.session_variables["purpose"] = request.purpose.value
        handle.session_variables["is_read_only"] = is_ro
        handle.session_variables["isolation_level"] = request.isolation_level.value
        handle.session_variables["statement_timeout_ms"] = request.statement_timeout_ms

        # 2. Database-specific statement / isolation setup where supported
        provider_id = handle.provider_id.lower()
        if provider_id in ("postgresql", "postgres"):
            try:
                cur = conn.cursor()
                if is_ro:
                    cur.execute("SET default_transaction_read_only = on;")
                else:
                    cur.execute("SET default_transaction_read_only = off;")

                if request.statement_timeout_ms > 0:
                    cur.execute(f"SET statement_timeout = {int(request.statement_timeout_ms)};")

                if request.lock_timeout_ms > 0:
                    cur.execute(f"SET lock_timeout = {int(request.lock_timeout_ms)};")

                schema = getattr(request.endpoint_spec, "schema_name", None)
                if schema:
                    cur.execute(f"SET search_path = {schema}, public;")
                cur.close()
            except Exception as exc:
                msg = f"Failed to apply mandatory session initialization parameters for PostgreSQL: {redact_text(str(exc))}"
                failure = ConnectionFailure(
                    error_code="POSTGRES_SESSION_INIT_FAILED",
                    category=FailureCategory.PROVIDER_INTERNAL_ERROR,
                    message=msg,
                    retryable=False,
                    provider_id=handle.provider_id,
                )
                raise SessionInitializationError(failure) from exc

        elif provider_id in ("mysql", "mariadb"):
            try:
                cur = conn.cursor()
                if is_ro:
                    cur.execute("SET SESSION TRANSACTION READ ONLY;")
                else:
                    cur.execute("SET SESSION TRANSACTION READ WRITE;")

                if request.statement_timeout_ms > 0:
                    cur.execute(f"SET max_execution_time = {int(request.statement_timeout_ms)};")
                cur.close()
            except Exception as exc:
                msg = f"Failed to apply mandatory session initialization parameters for MySQL/MariaDB: {redact_text(str(exc))}"
                failure = ConnectionFailure(
                    error_code="MYSQL_SESSION_INIT_FAILED",
                    category=FailureCategory.PROVIDER_INTERNAL_ERROR,
                    message=msg,
                    retryable=False,
                    provider_id=handle.provider_id,
                )
                raise SessionInitializationError(failure) from exc
