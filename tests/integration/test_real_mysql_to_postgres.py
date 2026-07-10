# -*- coding: utf-8 -*-
import unittest
import os
import sys
import time
import pymysql
import psycopg2
import logging

from tests.integration.fixtures import (
    start_containers,
    stop_containers,
    reset_source_database,
    reset_target_database,
    load_schema,
    load_seed_data,
    validate_table_count,
    validate_row_count,
    validate_constraints,
    validate_indexes,
    validate_json_columns,
    validate_blob_columns,
    validate_foreign_keys,
    validate_data_integrity,
    MYSQL_CONFIG,
    POSTGRES_CONFIG
)
from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.enums import SystemType, MigrationStrategy
from akaal.core.models.project import ConnectionConfig

class TestRealMysqlToPostgres(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 1. Start Docker environment and check health
        try:
            start_containers()
        except Exception as e:
            # If docker is not running or fails, fail the suite early with instructions
            raise unittest.SkipTest(
                f"Docker environment check failed. Make sure Docker Desktop is running. Error: {e}"
            )

    @classmethod
    def tearDownClass(cls):
        # Stop and clean docker environment
        stop_containers()

    def test_mysql_to_postgres_migration(self):
        # Reset and load source (MySQL)
        reset_source_database("mysql", MYSQL_CONFIG)
        reset_target_database("postgres", POSTGRES_CONFIG)
        
        schema_path = os.path.join(os.path.dirname(__file__), "sample_schema.sql")
        data_path = os.path.join(os.path.dirname(__file__), "sample_data.sql")
        
        load_schema("mysql", MYSQL_CONFIG, schema_path)
        load_seed_data("mysql", MYSQL_CONFIG, data_path)
        
        # Configure ConnectionConfigs
        src_conn = ConnectionConfig(
            system_type=SystemType.MYSQL,
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            database_name=MYSQL_CONFIG["database"],
            credentials_ref="mysql_env_ref",
            read_only=True
        )
        src_conn.username = MYSQL_CONFIG["user"]
        src_conn.password = MYSQL_CONFIG["password"]
        
        tgt_conn = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            database_name=POSTGRES_CONFIG["database"],
            credentials_ref="postgres_env_ref",
            read_only=False
        )
        tgt_conn.username = POSTGRES_CONFIG["user"]
        tgt_conn.password = POSTGRES_CONFIG["password"]
        
        # Configure migration config with adaptive batching, connection pooling, and structured logging
        config = MigrationConfig(
            source_config=src_conn,
            target_config=tgt_conn,
            strategy=MigrationStrategy.BIG_BANG,
            workspace_dir="./smoke_test_workspace",
            project_name="MySQL to PostgreSQL Smoke Test",
            auto_approve=True,
            use_adaptive_batch=True,
            minimum_batch_size=10,
            initial_batch_size=500,
            maximum_batch_size=2000,
            enable_connection_pooling=True,
            pool_size=4,
            log_format="json",
            log_level="INFO"
        )
        
        # Start migration run
        pipeline = AkaalPipeline(config)
        
        start_time = time.perf_counter()
        result = pipeline.run()
        duration = time.perf_counter() - start_time
        
        # Assert success
        self.assertEqual(result.get("status"), "completed")
        session_id = result.get("migration_id")
        self.assertIsNotNone(session_id)
        
        # 2. Assert and validate target schema and data
        conn_mysql = pymysql.connect(
            host=MYSQL_CONFIG["host"], port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"], password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"], cursorclass=pymysql.cursors.DictCursor
        )
        
        conn_pg = psycopg2.connect(
            host=POSTGRES_CONFIG["host"], port=POSTGRES_CONFIG["port"],
            user=POSTGRES_CONFIG["user"], password=POSTGRES_CONFIG["password"],
            dbname=POSTGRES_CONFIG["database"]
        )
        
        # A. Table count
        validate_table_count(conn_pg, "postgres", 5)
        
        # B. Row counts and constraint checks for each table
        tables = ["users", "products", "orders", "order_items", "audit_logs"]
        expected_counts = {
            "users": 100,
            "products": 200,
            "orders": 1000,
            "order_items": 3000,
            "audit_logs": 500
        }
        
        for table in tables:
            validate_row_count(conn_pg, "postgres", table, expected_counts[table])
            validate_constraints(conn_mysql, conn_pg, ("mysql", "postgres"), table)
            validate_indexes(conn_mysql, conn_pg, ("mysql", "postgres"), table)
            validate_foreign_keys(conn_pg, "postgres", table)
            validate_data_integrity(conn_mysql, conn_pg, ("mysql", "postgres"), table)
            
        # C. Specialized column validation
        validate_json_columns(conn_mysql, conn_pg, ("mysql", "postgres"), "products", "attributes")
        validate_json_columns(conn_mysql, conn_pg, ("mysql", "postgres"), "audit_logs", "new_value")
        validate_blob_columns(conn_mysql, conn_pg, ("mysql", "postgres"), "audit_logs", "raw_payload")
        
        conn_mysql.close()
        conn_pg.close()
        
        # Retrieve session metric snapshot summary
        session = pipeline.get_session()
        self.assertIsNotNone(session)
        self.assertIsNotNone(session.metrics_summary)
        summary = session.metrics_summary
        
        # Verify metric attributes
        self.assertEqual(summary.rows_migrated, 4800)
        self.assertEqual(summary.tables_migrated, 5)
        
        # Print performance summary benchmarks
        print("\n" + "="*50)
        print("PERFORMANCE BENCHMARK SUMMARY (MySQL -> PostgreSQL)")
        print("="*50)
        print(f"Migration Duration : {duration:.3f} s")
        print(f"Total Rows Migrated: {summary.rows_migrated}")
        print(f"Total Tables       : {summary.tables_migrated}")
        print(f"Throughput         : {summary.rows_per_sec} rows/sec")
        print(f"Data Transferred   : {summary.bytes_migrated / 1024:.2f} KB")
        print(f"Avg Batch Size     : {config.initial_batch_size}")
        print("="*50 + "\n")

if __name__ == "__main__":
    unittest.main()
