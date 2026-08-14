import unittest
from akaal.replication.contracts import IPhysicalReader, IPhysicalWriter, ConnectorCapability
from akaal.replication.resolver import (
    resolve_physical_reader,
    resolve_physical_writer,
    register_physical_reader,
    register_physical_writer,
    _READER_REGISTRY,
    _WRITER_REGISTRY,
)
from akaal.replication.readers.oracle_reader import OraclePhysicalReader
from akaal.replication.readers.postgresql_reader import PostgreSQLPhysicalReader
from akaal.replication.readers.mysql_reader import MySQLPhysicalReader
from akaal.replication.readers.mssql_reader import MSSQLPhysicalReader

from akaal.replication.writers.oracle_writer import OraclePhysicalWriter
from akaal.replication.writers.postgresql_writer import PostgreSQLPhysicalWriter
from akaal.replication.writers.mysql_writer import MySQLPhysicalWriter
from akaal.replication.writers.mssql_writer import MSSQLPhysicalWriter

from akaal.engine.spec import TransportPartition, PartitionStrategy, BatchMetadata


class TestP16UniversalTransportFoundation(unittest.TestCase):
    """
    P1.6 Universal Physical Transport Foundation Unit & Contract Test Suite.
    """

    def test_01_all_four_readers_and_writers_registered(self):
        """Verify Oracle, PostgreSQL, MySQL, MSSQL readers & writers are registered in resolver."""
        engines = ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]
        for eng in engines:
            self.assertIn(eng, _READER_REGISTRY)
            self.assertIn(eng, _WRITER_REGISTRY)

    def test_02_resolve_physical_readers_for_all_four_engines(self):
        """Verify resolver instantiates correct physical reader class per engine."""
        dummy_params = {"mock_mode": True, "username": "user", "password": "pass", "host": "127.0.0.1", "database": "db"}
        
        ora_reader = resolve_physical_reader("ORACLE", dummy_params)
        self.assertIsInstance(ora_reader, OraclePhysicalReader)
        self.assertIsInstance(ora_reader, IPhysicalReader)

        pg_reader = resolve_physical_reader("POSTGRESQL", dummy_params)
        self.assertIsInstance(pg_reader, PostgreSQLPhysicalReader)
        self.assertIsInstance(pg_reader, IPhysicalReader)

        my_reader = resolve_physical_reader("MYSQL", dummy_params)
        self.assertIsInstance(my_reader, MySQLPhysicalReader)
        self.assertIsInstance(my_reader, IPhysicalReader)

        ms_reader = resolve_physical_reader("MSSQL", dummy_params)
        self.assertIsInstance(ms_reader, MSSQLPhysicalReader)
        self.assertIsInstance(ms_reader, IPhysicalReader)

    def test_03_resolve_physical_writers_for_all_four_engines(self):
        """Verify resolver instantiates correct physical writer class per engine."""
        dummy_params = {"mock_mode": True, "username": "user", "password": "pass", "host": "127.0.0.1", "database": "db"}

        ora_writer = resolve_physical_writer("ORACLE", dummy_params)
        self.assertIsInstance(ora_writer, OraclePhysicalWriter)
        self.assertIsInstance(ora_writer, IPhysicalWriter)

        pg_writer = resolve_physical_writer("POSTGRESQL", dummy_params)
        self.assertIsInstance(pg_writer, PostgreSQLPhysicalWriter)
        self.assertIsInstance(pg_writer, IPhysicalWriter)

        my_writer = resolve_physical_writer("MYSQL", dummy_params)
        self.assertIsInstance(my_writer, MySQLPhysicalWriter)
        self.assertIsInstance(my_writer, IPhysicalWriter)

        ms_writer = resolve_physical_writer("MSSQL", dummy_params)
        self.assertIsInstance(ms_writer, MSSQLPhysicalWriter)
        self.assertIsInstance(ms_writer, IPhysicalWriter)

    def test_04_reader_contract_compliance_all_four_engines(self):
        """Verify all four readers fulfill open_partition, read_batch, and close contracts."""
        dummy_params = {"mock_mode": True, "username": "user", "password": "pass", "host": "127.0.0.1", "database": "db"}
        partition = TransportPartition(
            partition_id="part-101",
            table_name="CUSTOMERS",
            schema_name="DATA_SCH",
            target_schema="public",
            strategy=PartitionStrategy.SINGLE_STREAM,
        )

        for sys_key in ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]:
            reader = resolve_physical_reader(sys_key, dummy_params)
            reader.open_partition(partition)
            rows, meta = reader.read_batch(10)
            self.assertIsInstance(meta, BatchMetadata)
            reader.close()

    def test_05_writer_contract_compliance_all_four_engines(self):
        """Verify all four writers fulfill write_batch, commit, rollback, and close contracts."""
        dummy_params = {"mock_mode": True, "username": "user", "password": "pass", "host": "127.0.0.1", "database": "db"}
        batch_meta = BatchMetadata(batch_id="b-1", partition_id="p-1", table_name="CUSTOMERS", sequence=1, row_count=2)
        sample_data = [(1, "Alice", 100.0), (2, "Bob", 200.0)]

        for sys_key in ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]:
            writer = resolve_physical_writer(sys_key, dummy_params)
            written = writer.write_batch(
                table_name="CUSTOMERS",
                columns=["id", "name", "balance"],
                data=sample_data,
                batch_meta=batch_meta,
                pk_columns=["id"],
                target_schema="public",
            )
            self.assertEqual(written, 2)
            writer.commit()
            writer.rollback()
            writer.close()

    def test_06_unsupported_engine_fails_closed(self):
        """Verify requesting an unregistered engine raises ValueError UNSUPPORTED_CAPABILITY."""
        with self.assertRaises(ValueError) as ctx:
            resolve_physical_reader("MONGODB", {})
        self.assertIn("UNSUPPORTED_CAPABILITY", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            resolve_physical_writer("MONGODB", {})
        self.assertIn("UNSUPPORTED_CAPABILITY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
