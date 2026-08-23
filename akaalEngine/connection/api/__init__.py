"""
akaalEngine.connection.api
==========================
Connection Authority API and canonical public façade.
"""

from akaalEngine.connection.api.authority import (
    ConnectionAuthority,
    default_connection_authority,
)

__all__ = [
    "ConnectionAuthority",
    "default_connection_authority",
]
