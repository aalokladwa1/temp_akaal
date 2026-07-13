"""Compatibility shim — redirects old postgres_adapter imports to new path."""
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter as PostgresAdapter
__all__ = ["PostgresAdapter"]
