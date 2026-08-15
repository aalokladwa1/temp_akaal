"""
AKAAL CDC Sources Package Initialization.
========================================
Exports canonical database CDC source miners (PostgresWALMiner, MySQLBinlogMiner, OracleRedoMiner, MSSQLCDCMiner, MongoDBOplogMiner)
and backwards-compatible aliases for legacy scaffolding.
"""

from akaal.cdc.sources.base import ICDCSourceAdapter, CDCCapabilityFlags
from akaal.cdc.sources.postgres import PostgresWALMiner, PostgresWALMiner as PostgresWALAdapter
from akaal.cdc.sources.mysql import MySQLBinlogMiner, MySQLBinlogMiner as MySQLBinlogAdapter
from akaal.cdc.sources.oracle import OracleRedoMiner, OracleRedoMiner as OracleLogMinerAdapter
from akaal.cdc.sources.sqlserver import MSSQLCDCMiner, MSSQLCDCMiner as SQLServerCDCAdapter
from akaal.cdc.sources.mariadb import MariaDBBinlogMiner, MariaDBBinlogMiner as MariaDBBinlogAdapter
from akaal.cdc.sources.mongodb import MongoDBOplogMiner, MongoDBOplogMiner as MongoDBChangeStreamAdapter
from akaal.cdc.sources.reconstruction import TransactionReconstructor
from akaal.cdc.sources.coordinator import CDCCaptureCoordinator

__all__ = [
    "ICDCSourceAdapter",
    "CDCCapabilityFlags",
    "PostgresWALMiner",
    "PostgresWALAdapter",
    "MySQLBinlogMiner",
    "MySQLBinlogAdapter",
    "MariaDBBinlogMiner",
    "MariaDBBinlogAdapter",
    "OracleRedoMiner",
    "OracleLogMinerAdapter",
    "MSSQLCDCMiner",
    "SQLServerCDCAdapter",
    "MongoDBOplogMiner",
    "MongoDBChangeStreamAdapter",
    "TransactionReconstructor",
    "CDCCaptureCoordinator",
]
