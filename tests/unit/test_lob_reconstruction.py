import asyncio
import hashlib
import unittest
from akaal.core.models.project import MigrationProject
from akaal.core.models.enums import MigrationStrategy
from akaal.core.models.configuration import MigrationConfiguration
from akaal.adapters.base_adapter import BaseAdapter
from akaal.agents.gb.gb_agent import GBAgent

class MockAdapter(BaseAdapter):
    async def connect(self): self.is_connected = True
    async def close(self): self.is_connected = False
    async def check_permissions(self): return True
    async def discover_tables(self): return ["lob_table"]
    async def discover_columns(self, table_name):
        return [{"name": "id", "type": "INTEGER"}, {"name": "blob_col", "type": "BLOB"}]
    async def _primary_key_columns(self, table_name):
        return ["id"]
    async def discover_foreign_keys(self): return []
    async def discover_indexes(self, t): return []
    async def discover_constraints(self, t): return []
    async def discover_triggers(self, t): return []
    async def discover_views(self): return []
    
    async def read_batch(self, table_name, offset, limit, last_processed_primary_key=None, incremental_filter=None):
        if offset > 0:
            return []
        return [{"id": 1, "blob_col": "hello world large LOB content"}]

    async def write_batch(self, table_name, rows):
        self.written_rows = rows
        return len(rows)

    async def read_lob_chunk(self, table_name, pk_value, lob_column, offset, chunk_size):
        data = b"hello world large LOB content"
        return data[offset:offset+chunk_size]

    async def write_lob_chunk(self, table_name, pk_value, lob_column, chunk_data, offset):
        if not hasattr(self, "reconstructed"):
            self.reconstructed = bytearray()
        self.reconstructed[offset:offset+len(chunk_data)] = chunk_data

    async def get_row_count(self, t): return 1
    async def compute_checksum(self, t): return "abc"

class TestLOBReconstruction(unittest.TestCase):
    async def run_lob_streaming_and_reconstruction(self):
        from akaal.core.state.global_state import GlobalState
        from akaal.core.message_bus.bus import MessageBus
        
        state = GlobalState()
        bus = MessageBus()
        agent = GBAgent(state, bus)

        from unittest.mock import AsyncMock
        agent._checkpoint_mgr = AsyncMock()
        agent._checkpoint_mgr.resume.return_value = None
        agent._checkpoint_mgr.save_progress.return_value = True

        # Mock adapter registry creation logic
        src_adapter = MockAdapter(None)
        tgt_adapter = MockAdapter(None)

        def mock_create_adapter(config):
            if config == "src": return src_adapter
            return tgt_adapter

        import akaal.agents.gb.gb_agent
        original_create_adapter = akaal.agents.gb.gb_agent.create_adapter
        akaal.agents.gb.gb_agent.create_adapter = mock_create_adapter

        try:
            # Create project
            from akaal.core.models.project import ConnectionConfig
            from akaal.core.models.enums import SystemType
            c_src = ConnectionConfig(SystemType.POSTGRESQL, "localhost", 5432, "src", "ref")
            c_tgt = ConnectionConfig(SystemType.POSTGRESQL, "localhost", 5432, "tgt", "ref")
            project = MigrationProject("lob_proj", c_src, c_tgt, MigrationStrategy.BIG_BANG)
            project.human_approval_granted = True
            project.configuration.lob_chunk_size = 5 # small chunk size to trigger multi chunk transfers
            await state.register_project(project)

            res = await agent.migrate_table(
                source_config="src",
                target_config="tgt",
                table_name="lob_table",
                batch_size=10,
                project_id=project.project_id,
                migration_id="m1"
            )

            self.assertEqual(res["status"], "SUCCESS")
            # Verify target LOB was reconstructed exactly
            self.assertEqual(bytes(tgt_adapter.reconstructed), b"hello world large LOB content")
            self.assertEqual(
                hashlib.sha256(tgt_adapter.reconstructed).hexdigest(),
                hashlib.sha256(b"hello world large LOB content").hexdigest()
            )
        finally:
            akaal.agents.gb.gb_agent.create_adapter = original_create_adapter

    def test_run_async(self):
        import asyncio
        asyncio.run(self.run_lob_streaming_and_reconstruction())
