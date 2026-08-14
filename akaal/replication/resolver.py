"""
AKAAL Replication Engine — Universal Database-Agnostic Transport Resolver
===========================================================================
Resolves canonical physical readers and physical writers for all supported
RDBMS system types (Oracle, PostgreSQL, MySQL, MSSQL).
"""

import logging
from typing import Dict, Any, Type, Optional

from akaal.replication.contracts import IPhysicalReader, IPhysicalWriter
from akaal.replication.readers.oracle_reader import OraclePhysicalReader
from akaal.replication.readers.postgresql_reader import PostgreSQLPhysicalReader
from akaal.replication.readers.mysql_reader import MySQLPhysicalReader
from akaal.replication.readers.mssql_reader import MSSQLPhysicalReader

from akaal.replication.writers.oracle_writer import OraclePhysicalWriter
from akaal.replication.writers.postgresql_writer import PostgreSQLPhysicalWriter
from akaal.replication.writers.mysql_writer import MySQLPhysicalWriter
from akaal.replication.writers.mssql_writer import MSSQLPhysicalWriter

logger = logging.getLogger("akaal.replication.resolver")

_READER_REGISTRY: Dict[str, Type[IPhysicalReader]] = {
    "ORACLE": OraclePhysicalReader,
    "ORACLE_DB": OraclePhysicalReader,
    "POSTGRESQL": PostgreSQLPhysicalReader,
    "POSTGRES": PostgreSQLPhysicalReader,
    "MYSQL": MySQLPhysicalReader,
    "MSSQL": MSSQLPhysicalReader,
    "SQLSERVER": MSSQLPhysicalReader,
}

_WRITER_REGISTRY: Dict[str, Type[IPhysicalWriter]] = {
    "ORACLE": OraclePhysicalWriter,
    "ORACLE_DB": OraclePhysicalWriter,
    "POSTGRESQL": PostgreSQLPhysicalWriter,
    "POSTGRES": PostgreSQLPhysicalWriter,
    "MYSQL": MySQLPhysicalWriter,
    "MSSQL": MSSQLPhysicalWriter,
    "SQLSERVER": MSSQLPhysicalWriter,
}


def register_physical_reader(system_type: str, reader_cls: Type[IPhysicalReader]) -> None:
    """Register a database physical reader class for a system type."""
    _READER_REGISTRY[system_type.upper()] = reader_cls


def register_physical_writer(system_type: str, writer_cls: Type[IPhysicalWriter]) -> None:
    """Register a database physical writer class for a system type."""
    _WRITER_REGISTRY[system_type.upper()] = writer_cls


def resolve_physical_reader(system_type: Any, connection_params: Dict[str, Any]) -> IPhysicalReader:
    """
    Factory: resolve and instantiate the canonical physical reader for a given system type.
    Raises ValueError(UNSUPPORTED_CAPABILITY) if physical reader is not registered for the engine.
    """
    sys_key = str(system_type.value if hasattr(system_type, "value") else system_type).upper()

    reader_cls = _READER_REGISTRY.get(sys_key)
    if not reader_cls:
        raise ValueError(
            f"UNSUPPORTED_CAPABILITY: Physical replication reader is not registered for system type '{sys_key}'."
        )
    logger.info(f"[TransportResolver] Resolved physical reader {reader_cls.__name__} for system type '{sys_key}'")
    return reader_cls(connection_params)


def resolve_physical_writer(system_type: Any, connection_params: Dict[str, Any]) -> IPhysicalWriter:
    """
    Factory: resolve and instantiate the canonical physical writer for a given system type.
    Raises ValueError(UNSUPPORTED_CAPABILITY) if physical writer is not registered for the engine.
    """
    sys_key = str(system_type.value if hasattr(system_type, "value") else system_type).upper()

    writer_cls = _WRITER_REGISTRY.get(sys_key)
    if not writer_cls:
        raise ValueError(
            f"UNSUPPORTED_CAPABILITY: Physical replication writer is not registered for system type '{sys_key}'."
        )
    logger.info(f"[TransportResolver] Resolved physical writer {writer_cls.__name__} for system type '{sys_key}'")
    return writer_cls(connection_params)
