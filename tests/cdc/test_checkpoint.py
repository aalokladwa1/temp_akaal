"""
Unit tests for Checkpoint Stores (Memory, DB, Redis, File).
"""

import pytest
import os
import shutil
from akaal.cdc.checkpoint.db import DatabaseCheckpointStore
from akaal.cdc.checkpoint.file import FileCheckpointStore
from akaal.cdc.checkpoint.memory import MemoryCheckpointStore
from akaal.cdc.checkpoint.redis import RedisCheckpointStore
from akaal.cdc.contracts.checkpoint import Checkpoint, Position


@pytest.mark.asyncio
async def test_memory_checkpoint_store():
    store = MemoryCheckpointStore()
    pos = Position(engine="POSTGRES", stream_position="0/100")
    chk = Checkpoint(checkpoint_id="c1", stream_id="stream-1", source_db="db1", position=pos)

    await store.save_checkpoint(chk)
    loaded = await store.load_checkpoint("stream-1")
    assert loaded is not None
    assert loaded.position.stream_position == "0/100"


@pytest.mark.asyncio
async def test_db_and_redis_checkpoint_stores():
    db_store = DatabaseCheckpointStore()
    redis_store = RedisCheckpointStore()

    pos = Position(engine="MYSQL", stream_position="gtid-100")
    chk = Checkpoint(checkpoint_id="c2", stream_id="stream-2", source_db="db2", position=pos)

    await db_store.save_checkpoint(chk)
    loaded_db = await db_store.load_checkpoint("stream-2")
    assert loaded_db.position.stream_position == "gtid-100"

    await redis_store.save_checkpoint(chk)
    loaded_redis = await redis_store.load_checkpoint("stream-2")
    assert loaded_redis.position.stream_position == "gtid-100"


@pytest.mark.asyncio
async def test_file_checkpoint_store(tmp_path):
    test_dir = str(tmp_path / ".checkpoints")
    store = FileCheckpointStore(directory=test_dir)

    pos = Position(engine="ORACLE", stream_position="scn-999")
    chk = Checkpoint(checkpoint_id="c3", stream_id="stream-3", source_db="db3", position=pos)

    await store.save_checkpoint(chk)
    loaded_file = await store.load_checkpoint("stream-3")
    assert loaded_file is not None
    assert loaded_file.position.stream_position == "scn-999"
