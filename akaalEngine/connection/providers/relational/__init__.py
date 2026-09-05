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
from akaalEngine.connection.providers.relational.cockroachdb import CockroachDBProviderStrategy
from akaalEngine.connection.providers.relational.yugabytedb import YugabyteDBProviderStrategy
from akaalEngine.connection.providers.relational.tidb import TiDBProviderStrategy
from akaalEngine.connection.providers.relational.singlestore import SingleStoreProviderStrategy
from akaalEngine.connection.providers.relational.teradata import TeradataProviderStrategy
from akaalEngine.connection.providers.relational.vertica import VerticaProviderStrategy
from akaalEngine.connection.providers.relational.sap_hana import SAPHANAProviderStrategy
from akaalEngine.connection.providers.relational.sap_ase import SAPASEProviderStrategy
from akaalEngine.connection.providers.relational.informix import InformixProviderStrategy
from akaalEngine.connection.providers.relational.spanner import SpannerProviderStrategy

__all__ = [
    "SQLiteProviderStrategy",
    "PostgreSQLProviderStrategy",
    "MySQLProviderStrategy",
    "MariaDBProviderStrategy",
    "OracleProviderStrategy",
    "MSSQLProviderStrategy",
    "IBMDb2ProviderStrategy",
    "CockroachDBProviderStrategy",
    "YugabyteDBProviderStrategy",
    "TiDBProviderStrategy",
    "SingleStoreProviderStrategy",
    "TeradataProviderStrategy",
    "VerticaProviderStrategy",
    "SAPHANAProviderStrategy",
    "SAPASEProviderStrategy",
    "InformixProviderStrategy",
    "SpannerProviderStrategy",
]
