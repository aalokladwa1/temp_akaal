"""
CDC Sources package initialization.
"""

from akaal.cdc.sources.base import ICDCSourceAdapter
from akaal.cdc.sources.postgres import PostgresWALAdapter
from akaal.cdc.sources.mysql import MySQLBinlogAdapter
from akaal.cdc.sources.oracle import OracleLogMinerAdapter
from akaal.cdc.sources.sqlserver import SQLServerCDCAdapter
from akaal.cdc.sources.mongodb import MongoDBChangeStreamAdapter
from akaal.cdc.sources.trigger import TriggerFallbackAdapter

__all__ = [
    "ICDCSourceAdapter",
    "PostgresWALAdapter",
    "MySQLBinlogAdapter",
    "OracleLogMinerAdapter",
    "SQLServerCDCAdapter",
    "MongoDBChangeStreamAdapter",
    "TriggerFallbackAdapter",
]
