"""
tests/unit/engine_cdc/test_positions_and_prerequisites.py
==========================================================
Unit tests for typed CDCSourcePositions, cross-provider comparison rejection, prerequisite preflight checks, and MSSQL CDC vs Change Tracking distinction.
"""

import pytest

from akaalEngine.cdc import (
    CDCPermissionError,
    MariaDBGTIDPosition,
    MongoDBOpLogPosition,
    MSSQLCDCSourceAdapter,
    MSSQLChangePosition,
    MSSQLChangeTrackingAdapter,
    MySQLCDCSourceAdapter,
    MySQLGTIDPosition,
    OracleCDCSourceAdapter,
    OracleSCNPosition,
    PostgreSQLCDCSourceAdapter,
    PostgresLSNPosition,
)


def test_postgres_lsn_monotonic_ordering():
    """Proves PostgresLSNPosition compares LSNs strictly by integer value."""
    lsn1 = PostgresLSNPosition("0/16B3748")
    lsn2 = PostgresLSNPosition("0/16B3749")
    lsn3 = PostgresLSNPosition("1/0000000")

    assert lsn2 > lsn1
    assert lsn3 > lsn2
    assert lsn1.to_string() == "0/16B3748"


def test_oracle_scn_monotonic_ordering():
    """Proves OracleSCNPosition compares SCNs and sequences strictly."""
    scn1 = OracleSCNPosition(1000, sequence_number=1)
    scn2 = OracleSCNPosition(1000, sequence_number=2)
    scn3 = OracleSCNPosition(1001, sequence_number=1)

    assert scn2 > scn1
    assert scn3 > scn2


def test_mysql_gtid_subset_inclusion():
    """Proves MySQLGTIDPosition compares binlog positions."""
    pos1 = MySQLGTIDPosition("binlog.000001", 120)
    pos2 = MySQLGTIDPosition("binlog.000001", 200)
    pos3 = MySQLGTIDPosition("binlog.000002", 100)

    assert pos2 > pos1
    assert pos3 > pos2


def test_mariadb_gtid_domain_server_sequence():
    """Proves MariaDBGTIDPosition compares sequence numbers."""
    pos1 = MariaDBGTIDPosition(0, 1, 10)
    pos2 = MariaDBGTIDPosition(0, 1, 12)

    assert pos2 > pos1


def test_mssql_lsn_hex_comparison():
    """Proves MSSQLChangePosition compares LSN hex strings."""
    pos1 = MSSQLChangePosition("00000001", "00000001")
    pos2 = MSSQLChangePosition("00000001", "00000002")

    assert pos2 > pos1


def test_mongodb_oplog_timestamp_comparison():
    """Proves MongoDBOpLogPosition compares BSON timestamp & inc."""
    pos1 = MongoDBOpLogPosition(1700000000, 1)
    pos2 = MongoDBOpLogPosition(1700000000, 2)

    assert pos2 > pos1


def test_cross_provider_position_comparison_rejection():
    """Proves comparing positions across different providers fails closed with TypeError."""
    pg_pos = PostgresLSNPosition("0/16B3748")
    ora_pos = OracleSCNPosition(1000)

    with pytest.raises(TypeError):
        _ = pg_pos > ora_pos


def test_prerequisite_validation_failures():
    """Proves preflight checks fail loudly when critical system settings are missing."""
    pg_adapter = PostgreSQLCDCSourceAdapter({})
    with pytest.raises(CDCPermissionError):
        pg_adapter.validate_prerequisites({"wal_level": "replica"})

    ora_adapter = OracleCDCSourceAdapter({})
    with pytest.raises(CDCPermissionError):
        ora_adapter.validate_prerequisites({"archivelog": False})

    mysql_adapter = MySQLCDCSourceAdapter({})
    with pytest.raises(CDCPermissionError):
        mysql_adapter.validate_prerequisites({"binlog_format": "STATEMENT"})


def test_sqlserver_cdc_vs_change_tracking_distinct_capabilities():
    """Proves SQLSERVER_CDC and SQLSERVER_CHANGE_TRACKING have distinct capability descriptors."""
    cdc = MSSQLCDCSourceAdapter({}).capabilities
    ct = MSSQLChangeTrackingAdapter({}).capabilities

    assert cdc.supports_transactions is True
    assert cdc.supports_before_images is True

    assert ct.supports_transactions is False
    assert ct.supports_before_images is False
