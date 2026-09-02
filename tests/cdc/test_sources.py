"""
Unit tests for Platform 4 CDC Source Adapters.
"""

import pytest
from akaal.cdc.sources.postgres import PostgresWALAdapter
from akaal.cdc.sources.mysql import MySQLBinlogAdapter
from akaal.cdc.sources.oracle import OracleLogMinerAdapter
from akaal.cdc.sources.sqlserver import SQLServerCDCAdapter
from akaal.cdc.sources.mongodb import MongoDBChangeStreamAdapter
from akaal.cdc.sources.trigger import TriggerFallbackAdapter
from tests.conftest import require_postgres, require_mysql, require_oracle, require_mssql, require_mongodb


@pytest.mark.asyncio
async def test_postgres_wal_adapter():
    require_postgres("localhost", 5432)
    adapter = PostgresWALAdapter()
    assert adapter.engine_name in ("POSTGRES", "POSTGRESQL")
    pos = adapter.get_current_position()
    assert pos.stream_position == "0/16B3748"


@pytest.mark.asyncio
async def test_mysql_binlog_adapter():
    require_mysql("localhost", 3306)
    adapter = MySQLBinlogAdapter()
    assert adapter.engine_name == "MYSQL"


@pytest.mark.asyncio
async def test_oracle_logminer_adapter():
    require_oracle("localhost", 1521)
    adapter = OracleLogMinerAdapter()
    assert adapter.engine_name == "ORACLE"


@pytest.mark.asyncio
async def test_sqlserver_cdc_adapter():
    require_mssql("localhost", 1433)
    adapter = SQLServerCDCAdapter()
    assert adapter.engine_name in ("SQLSERVER", "MSSQL")


@pytest.mark.asyncio
async def test_mongodb_change_stream_adapter():
    require_mongodb("localhost", 27017)
    adapter = MongoDBChangeStreamAdapter()
    assert adapter.engine_name == "MONGODB"


@pytest.mark.asyncio
async def test_trigger_fallback_adapter():
    require_postgres("localhost", 5432)
    adapter = TriggerFallbackAdapter()
    assert adapter.engine_name == "TRIGGER"

