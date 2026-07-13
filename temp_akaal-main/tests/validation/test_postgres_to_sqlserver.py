# -*- coding: utf-8 -*-
import unittest
import os
import time
from tests.validation.fixtures import (
    get_connection,
    reset_source_database,
    reset_target_database,
    apply_schema,
    apply_seed_data,
    validate_table_counts,
    validate_row_counts,
    validate_constraints,
    validate_indexes,
    validate_foreign_keys,
    validate_json_columns,
    validate_blob_columns,
    validate_data_integrity,
    POSTGRES_CONFIG,
    SQLSERVER_CONFIG
)
from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.enums import SystemType, MigrationStrategy
from akaal.core.models.project import ConnectionConfig

class TestPostgresToSqlserver(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        try:
            self.conn_src = get_connection("postgres")
            self.conn_tgt = get_connection("sqlserver")
        except Exception as e:
            raise unittest.SkipTest(f"Database engines not available locally: {e}")

    async def asyncTearDown(self):
        if hasattr(self, "conn_src"):
            self.conn_src.close()
        if hasattr(self, "conn_tgt"):
            self.conn_tgt.close()

    async def test_postgres_to_sqlserver_migration(self):
        # 1. Reset both databases
        reset_source_database("postgres")
        reset_target_database("sqlserver")
        
        # 2. Apply schema and seed to source
        apply_schema("postgres")
        apply_seed_data("postgres")
        
        # 3. Apply schema to target
        apply_schema("sqlserver")
        
        # 4. Configure ConnectionConfigs
        src_conn = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            database_name=POSTGRES_CONFIG["database"],
            credentials_ref="pg_creds",
            read_only=True
        )
        src_conn.username = POSTGRES_CONFIG["user"]
        src_conn.password = POSTGRES_CONFIG["password"]
        
        tgt_conn = ConnectionConfig(
            system_type=SystemType.MSSQL,
            host=SQLSERVER_CONFIG["server"],
            port=1433,
            database_name=SQLSERVER_CONFIG["database"],
            credentials_ref="mssql_creds",
            read_only=False
        )
        tgt_conn.username = SQLSERVER_CONFIG["user"]
        tgt_conn.password = SQLSERVER_CONFIG["password"]
        tgt_conn.trusted_connection = SQLSERVER_CONFIG["trusted_connection"]
        
        # 5. Configure migration pipeline
        config = MigrationConfig(
            source_config=src_conn,
            target_config=tgt_conn,
            strategy=MigrationStrategy.BIG_BANG,
            workspace_dir="./validation_workspace",
            project_name="PostgreSQL to SQL Server Validation",
            auto_approve=True,
            use_adaptive_batch=True,
            minimum_batch_size=10,
            initial_batch_size=500,
            maximum_batch_size=2000,
            enable_connection_pooling=True,
            pool_size=4,
            enable_parallel_migration=True,
            log_format="text",
            log_level="INFO"
        )
        
        pipeline = AkaalPipeline()
        
        start_time = time.perf_counter()
        result = await pipeline.run(config)
        duration = time.perf_counter() - start_time
        
        # Assert success
        self.assertEqual(result.get("status"), "completed")
        
        # 6. Verify target counts and integrity
        validate_table_counts(self.conn_tgt, "sqlserver", 5)
        
        tables = ["users", "products", "orders", "order_items", "audit_logs"]
        expected_counts = {
            "users": 100,
            "products": 200,
            "orders": 1000,
            "order_items": 3000,
            "audit_logs": 500
        }
        
        for table in tables:
            validate_row_counts(self.conn_tgt, "sqlserver", table, expected_counts[table])
            validate_constraints(self.conn_src, self.conn_tgt, ("postgres", "sqlserver"), table)
            validate_indexes(self.conn_src, self.conn_tgt, ("postgres", "sqlserver"), table)
            validate_foreign_keys(self.conn_tgt, "sqlserver", table)
            validate_data_integrity(self.conn_src, self.conn_tgt, ("postgres", "sqlserver"), table)
            
        validate_json_columns(self.conn_src, self.conn_tgt, ("postgres", "sqlserver"), "products", "attributes")
        validate_json_columns(self.conn_src, self.conn_tgt, ("postgres", "sqlserver"), "audit_logs", "new_value")
        validate_blob_columns(self.conn_src, self.conn_tgt, ("postgres", "sqlserver"), "audit_logs", "raw_payload")
        
        session = pipeline.get_session()
        summary = session.metrics_summary
        
        # Print performance summary benchmarks
        print("\n" + "="*50)
        print("MIGRATION SMOKE TEST RESULT: PostgreSQL -> SQL Server")
        print("="*50)
        print(f"Status             : {result.get('status').upper()}")
        print(f"Duration           : {duration:.3f} s")
        print(f"Total Rows Migrated: {summary.rows_migrated}")
        print(f"Total Tables       : {summary.tables_migrated}")
        print(f"Throughput         : {summary.rows_per_sec:.2f} rows/sec")
        print(f"Data Transferred   : {summary.bytes_migrated / 1024:.2f} KB")
        print(f"Batch Size         : {config.initial_batch_size}")
        print("="*50 + "\n")

if __name__ == "__main__":
    unittest.main()
