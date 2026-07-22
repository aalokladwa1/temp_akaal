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


@pytest.mark.asyncio
async def test_postgres_wal_adapter():
    adapter = PostgresWALAdapter()
    assert adapter.engine_name == "POSTGRES"
    pos = await adapter.get_current_position()
    assert pos.stream_position == "0/16B3748"

    events = []
    async for evt in adapter.start_capture(pos):
        events.append(evt)
        break
    assert len(events) == 1
    assert events[0].source_engine == "POSTGRES"
    assert events[0].change_type == "INSERT"


@pytest.mark.asyncio
async def test_mysql_binlog_adapter():
    adapter = MySQLBinlogAdapter()
    assert adapter.engine_name == "MYSQL"
    events = []
    async for evt in adapter.start_capture():
        events.append(evt)
        break
    assert len(events) == 1
    assert events[0].source_engine == "MYSQL"


@pytest.mark.asyncio
async def test_oracle_logminer_adapter():
    adapter = OracleLogMinerAdapter()
    assert adapter.engine_name == "ORACLE"
    events = []
    async for evt in adapter.start_capture():
        events.append(evt)
        break
    assert len(events) == 1
    assert events[0].source_table == "EMPLOYEES"


@pytest.mark.asyncio
async def test_sqlserver_cdc_adapter():
    adapter = SQLServerCDCAdapter()
    assert adapter.engine_name == "SQLSERVER"
    events = []
    async for evt in adapter.start_capture():
        events.append(evt)
        break
    assert len(events) == 1
    assert events[0].source_engine == "SQLSERVER"


@pytest.mark.asyncio
async def test_mongodb_change_stream_adapter():
    adapter = MongoDBChangeStreamAdapter()
    assert adapter.engine_name == "MONGODB"
    events = []
    async for evt in adapter.start_capture():
        events.append(evt)
        break
    assert len(events) == 1
    assert events[0].source_engine == "MONGODB"


@pytest.mark.asyncio
async def test_trigger_fallback_adapter():
    adapter = TriggerFallbackAdapter()
    assert adapter.engine_name == "TRIGGER"
    events = []
    async for evt in adapter.start_capture():
        events.append(evt)
        break
    assert len(events) == 1
    assert events[0].source_engine == "TRIGGER"
