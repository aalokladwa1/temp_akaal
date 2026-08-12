"""
AKAAL Replication Engine — Database-Agnostic Physical Transport Resolver
==========================================================================
Resolves database-specific physical readers and writers for any supported system type.
Enables generic multi-engine and bidirectional transport without hardcoding vendor
types inside WorkflowEngine or DataTransportStep.
"""

import logging
from typing import Dict, Any, Type, Optional

from akaal.replication.readers.oracle_reader import IPhysicalReader, OraclePhysicalReader
from akaal.replication.writers.postgresql_writer import IPhysicalWriter, PostgreSQLPhysicalWriter

logger = logging.getLogger("akaal.replication.resolver")

_READER_REGISTRY: Dict[str, Type[IPhysicalReader]] = {
    "ORACLE": OraclePhysicalReader,
    "ORACLE_DB": OraclePhysicalReader,
}

_WRITER_REGISTRY: Dict[str, Type[IPhysicalWriter]] = {
    "POSTGRESQL": PostgreSQLPhysicalWriter,
    "POSTGRES": PostgreSQLPhysicalWriter,
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
