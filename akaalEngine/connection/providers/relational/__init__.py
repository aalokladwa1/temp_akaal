"""
akaalEngine.connection.providers.relational
===========================================
Relational database provider strategies.
"""

from akaalEngine.connection.providers.relational.sqlite import SQLiteProviderStrategy
from akaalEngine.connection.providers.relational.postgresql import PostgreSQLProviderStrategy
from akaalEngine.connection.providers.relational.mysql import MySQLProviderStrategy
from akaalEngine.connection.providers.relational.mariadb import MariaDBProviderStrategy
from akaalEngine.connection.providers.relational.oracle import OracleProviderStrategy
from akaalEngine.connection.providers.relational.mssql import MSSQLProviderStrategy
from akaalEngine.connection.providers.relational.ibm_db2 import IBMDb2ProviderStrategy

__all__ = [
    "SQLiteProviderStrategy",
    "PostgreSQLProviderStrategy",
    "MySQLProviderStrategy",
    "MariaDBProviderStrategy",
    "OracleProviderStrategy",
    "MSSQLProviderStrategy",
    "IBMDb2ProviderStrategy",
]
