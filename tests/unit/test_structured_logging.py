import asyncio
import io
import json
import logging
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from akaal.core.logging_manager import (
    configure_logging,
    get_current_context,
    migration_context,
)
from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.enums import SystemType, MigrationStrategy
from akaal.core.models.project import ConnectionConfig, MigrationProject
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager


class TestStructuredLogging(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.test_dir, "logs")

        # Clear root logger handlers before configuring
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)

    def tearDown(self):
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
            h.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # 1. Text format formatter test
    def test_text_formatter_output(self):
        log_capture = io.StringIO()
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        
        configure_logging(
            log_format="text",
            log_level="INFO",
            log_to_console=True,
            log_to_file=False,
            project_name="Test Text Migration"
        )
        
        # Override the StreamHandler destination to capture stdout
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.stream = log_capture

        test_logger = logging.getLogger("nexusforge.test_text")
        test_logger.info("This is a plain text log message")

        output = log_capture.getvalue()
        self.assertIn("[INFO]", output)
        self.assertIn("[nexusforge.test_text]", output)
        self.assertIn("This is a plain text log message", output)
        # Ensure it is NOT formatted as JSON
        self.assertFalse(output.strip().startswith("{"))

    # 2. JSON format formatter test
    def test_json_formatter_output(self):
        log_capture = io.StringIO()
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        
        configure_logging(
            log_format="json",
            log_level="INFO",
            log_to_console=True,
            log_to_file=False,
            project_name="Test JSON Migration"
        )
        
        # Override the StreamHandler destination to capture stdout
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.stream = log_capture

        test_logger = logging.getLogger("nexusforge.test_json")
        
        with migration_context(migration_id="mig-12345", correlation_id="corr-67890"):
            test_logger.info("This is a JSON log message", extra={"table_name": "users", "event": "migration_started"})

        output = log_capture.getvalue().strip()
        self.assertTrue(output.startswith("{"))
        self.assertTrue(output.endswith("}"))

        parsed = json.loads(output)
        self.assertEqual(parsed["log_level"], "INFO")
        self.assertEqual(parsed["component"], "nexusforge.test_json")
        self.assertEqual(parsed["message"], "This is a JSON log message")
        self.assertEqual(parsed["project_name"], "Test JSON Migration")
        self.assertEqual(parsed["migration_id"], "mig-12345")
        self.assertEqual(parsed["correlation_id"], "corr-67890")
        self.assertEqual(parsed["table_name"], "users")
        self.assertEqual(parsed["event"], "migration_started")
        self.assertIn("timestamp", parsed)

    # 3. Dynamic Future-Proof Extra fields test
    def test_dynamic_extra_field_support(self):
        log_capture = io.StringIO()
        root = logging.getLogger()
        
        configure_logging(
            log_format="json",
            log_level="INFO",
            log_to_console=True,
            log_to_file=False
        )
        
        # Override the StreamHandler destination to capture stdout
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.stream = log_capture

        test_logger = logging.getLogger("akaal.dynamic_test")
        
        # Test standard reserved field overwrite protection raises KeyError
        with self.assertRaises(KeyError):
            test_logger.info("Logging arbitrary fields", extra={"created": "attempted_override"})

        # Test other dynamic extra fields are successfully logged
        test_logger.info(
            "Logging arbitrary fields",
            extra={
                "lsn": "0/19F5C50",
                "snapshot": "snap_001",
                "validation_score": 98.7,
            }
        )

        output = log_capture.getvalue().strip()
        parsed = json.loads(output)
        self.assertEqual(parsed["lsn"], "0/19F5C50")
        self.assertEqual(parsed["snapshot"], "snap_001")
        self.assertEqual(parsed["validation_score"], 98.7)

    # 4. Contextvar Propagation across threads/tasks
    async def test_correlation_id_context_propagation(self):
        configure_logging(log_format="json", log_level="INFO", log_to_console=False, log_to_file=False)

        with migration_context(correlation_id="corr-abc", migration_id="mig-xyz"):
            ctx = get_current_context()
            self.assertEqual(ctx["correlation_id"], "corr-abc")
            self.assertEqual(ctx["migration_id"], "mig-xyz")

            # Asynchronous Task Boundary Propagation Check
            async def subtask():
                sub_ctx = get_current_context()
                return sub_ctx.get("correlation_id"), sub_ctx.get("migration_id")

            corr_id, mig_id = await asyncio.create_task(subtask())
            self.assertEqual(corr_id, "corr-abc")
            self.assertEqual(mig_id, "mig-xyz")

    # 5. File creation & Log Rotation
    def test_file_handler_creation_and_rotation(self):
        # Configure logging to write to file
        configure_logging(
            log_format="text",
            log_level="INFO",
            log_to_console=False,
            log_to_file=True,
            log_directory=self.log_dir,
            log_file_name="test_rotation.log",
            log_rotation_size_mb=1,  # Large size to verify rotation explicitly
            log_backup_count=3
        )

        log_file_path = os.path.join(self.log_dir, "test_rotation.log")
        self.assertTrue(os.path.exists(log_file_path))

        test_logger = logging.getLogger("nexusforge.rotation")
        test_logger.info("Initial log entry.")

        with open(log_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Initial log entry.", content)

    # 6. Granularity: Check that debug log events remain silent at INFO level
    def test_log_granularity_and_levels(self):
        log_capture = io.StringIO()
        root = logging.getLogger()
        
        configure_logging(
            log_format="json",
            log_level="INFO",  # Set to INFO: DEBUG messages must be filtered out
            log_to_console=True,
            log_to_file=False
        )
        
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.stream = log_capture

        test_logger = logging.getLogger("nexusforge.granularity")
        
        # DEBUG event: should be filtered out at INFO level
        test_logger.debug("Connection acquired", extra={"event": "connection_acquired"})
        # INFO event: should be kept
        test_logger.info("Migration completed", extra={"event": "migration_completed"})

        output = log_capture.getvalue().strip()
        self.assertNotIn("connection_acquired", output)
        self.assertIn("migration_completed", output)

    # 7. Backward Compatibility: Fallback check on Project configuration
    def test_backward_compatibility(self):
        project = MigrationProject(
            name="Backward Compatibility Proj",
            source_config=ConnectionConfig(SystemType.SQLITE, "localhost", 0, ":memory:", "sec", True),
            target_config=ConnectionConfig(SystemType.SQLITE, "localhost", 0, ":memory:", "sec", False),
            strategy=MigrationStrategy.BIG_BANG
        )
        self.assertEqual(project.log_format, "text")
        self.assertEqual(project.log_level, "INFO")
        self.assertTrue(project.log_to_console)
        self.assertTrue(project.log_to_file)
        self.assertEqual(project.log_directory, "logs")

        # Serialized project to dict compatibility
        d = project.to_dict()
        self.assertEqual(d["log_format"], "text")
        self.assertEqual(d["log_level"], "INFO")
        self.assertEqual(d["log_directory"], "logs")
