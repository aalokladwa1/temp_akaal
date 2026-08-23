"""
Unit tests for 3-state permission evaluation and CDC prerequisite assertions.
"""

from unittest.mock import MagicMock
from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.strategies.relational.postgresql import PostgresDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.oracle import OracleDiscoveryStrategy


def test_postgres_cdc_prerequisites_check():
    strat = PostgresDiscoveryStrategy()
    spec = EndpointSpec(
        provider_id="postgresql",
        host="localhost",
        database_name="postgres",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )
    ctx = DiscoveryContext()

    # Mock connection with wal_level = 'logical' and 10 replication slots
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Query sequences for discover_cdc_prerequisites:
    # 1. SHOW wal_level -> ('logical',)
    # 2. SHOW max_replication_slots -> (10,)
    # 3. SELECT count(*) FROM pg_replication_slots -> (2,)
    # 4. SELECT pg_current_wal_lsn() -> ('0/16B3748',)
    mock_cursor.fetchone.side_effect = [
        ('logical',),
        (10,),
        (2,),
        ('0/16B3748',),
    ]

    cdc_facts = strat.discover_cdc_prerequisites(mock_conn, spec, ctx)
    assert cdc_facts.is_cdc_ready is True
    assert cdc_facts.is_wal_level_logical is True
    assert cdc_facts.available_replication_slots == 8
    assert cdc_facts.starting_position is not None
    assert cdc_facts.starting_position.lsn == '0/16B3748'
    assert len(cdc_facts.blocker_reasons) == 0


def test_oracle_cdc_prerequisites_check():
    strat = OracleDiscoveryStrategy()
    spec = EndpointSpec(
        provider_id="oracle",
        host="localhost",
        database_name="ORCLCDB",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )
    ctx = DiscoveryContext()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # 1. SELECT log_mode, supplemental_log_data_min, current_scn -> ('ARCHIVELOG', 'YES', 12345678)
    mock_cursor.fetchone.side_effect = [
        ('ARCHIVELOG', 'YES', 12345678),
    ]

    cdc_facts = strat.discover_cdc_prerequisites(mock_conn, spec, ctx)
    assert cdc_facts.is_cdc_ready is True
    assert cdc_facts.is_archivelog_enabled is True
    assert cdc_facts.is_supplemental_logging_enabled is True
    assert cdc_facts.starting_position is not None
    assert cdc_facts.starting_position.scn == 12345678
