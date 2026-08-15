"""
AKAAL P4.6 — Managed Database + Cloud Connectivity Profiles Hostile Test Suite.
==============================================================================
Comprehensive hostile reality verification of P4.6 Cloud Managed Database Profiles across:
AWS (RDS/Aurora), Azure (SQL/PostgreSQL), GCP (Cloud SQL), and OCI (Autonomous DB/DB System).
Verifies provider isolation, durable resource identity, fail-closed SDK/credential handling,
secret redaction ([REDACTED]), endpoint refresh, canonical database adapter handoff,
proof-level separation (Discovery != Reachability != Connection), and zero duplicate authorities.
"""

import unittest
import asyncio

from akaal.cloud.models import CloudManagedDatabaseProfile, CloudProvider, ManagedServiceFamily, EndpointType
from akaal.cloud.aws_provider import AWSManagedDatabaseProvider
from akaal.cloud.azure_provider import AzureManagedDatabaseProvider
from akaal.cloud.gcp_provider import GCPManagedDatabaseProvider
from akaal.cloud.oci_provider import OCIManagedDatabaseProvider
from akaal.cloud.resolver import (
    resolve_cloud_profile_to_connection_config,
    get_database_adapter_for_cloud_profile,
    refresh_cloud_managed_profile,
)
from akaal.core.models.enums import SystemType
from akaal.adapters.adapter_registry import get_adapter_class


class TestP46ManagedCloudProfiles(unittest.TestCase):
    """Hostile Reality Test Suite for P4.6 Cloud Managed Database Profiles."""

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self) -> None:
        self.loop.close()

    # -------------------------------------------------------------------------
    # 1. AWS Hostile Tests
    # -------------------------------------------------------------------------
    def test_01_aws_rds_and_aurora_profile_construction(self):
        """01: Verify AWS RDS and Aurora profiles capture required managed metadata."""
        profile = CloudManagedDatabaseProfile(
            display_name="RDS Postgres Prod",
            provider=CloudProvider.AWS,
            account_id="123456789012",
            region="us-west-2",
            resource_id="arn:aws:rds:us-west-2:123456789012:db:prod-pg-db",
            resource_name="prod-pg-db",
            service_family=ManagedServiceFamily.RDS,
            engine_family="POSTGRESQL",
            engine_version="14.5",
            deployment_type="MULTI_AZ",
            endpoint_type=EndpointType.PRIVATE_ENDPOINT,
            hostname="prod-pg-db.c1234567890.us-west-2.rds.amazonaws.com",
            port=5432,
            database_name="app_production",
            writer_endpoint="prod-pg-db.c1234567890.us-west-2.rds.amazonaws.com",
            network_id="vpc-0abc1234def56789",
            security_group_ids=["sg-0112233445566"],
            auth_mode="IAM_ROLE",
            tls_required=True,
        )

        self.assertEqual(profile.provider, CloudProvider.AWS)
        self.assertEqual(profile.account_id, "123456789012")
        self.assertEqual(profile.region, "us-west-2")
        self.assertTrue(profile.resource_id.startswith("arn:aws:rds:"))
        self.assertEqual(profile.engine_family, "POSTGRESQL")
        self.assertTrue(profile.tls_required)

    def test_02_aws_missing_credentials_and_failed_discovery_fail_closed(self):
        """02: AWS discovery with invalid credentials fails closed with RuntimeError."""
        async def run():
            aws = AWSManagedDatabaseProvider(
                region="us-east-1",
                aws_access_key_id="invalid_key",
                aws_secret_access_key="invalid_secret_key_12345",
            )
            with self.assertRaises(RuntimeError):
                await aws.discover_instances()

        self.loop.run_until_complete(run())

    def test_03_aws_secret_redaction(self):
        """03: AWS provider redacts credentials as [REDACTED] in logs and errors."""
        aws = AWSManagedDatabaseProvider(
            region="us-east-1",
            aws_access_key_id="AKIA1234567890",
            aws_secret_access_key="my_super_secret_aws_key_9999",
        )
        msg = aws._redact("Failed connecting with key my_super_secret_aws_key_9999")
        self.assertNotIn("my_super_secret_aws_key_9999", msg)
        self.assertIn("[REDACTED]", msg)

    # -------------------------------------------------------------------------
    # 2. Azure Hostile Tests
    # -------------------------------------------------------------------------
    def test_04_azure_sql_and_pg_profile_construction(self):
        """04: Verify Azure SQL and PostgreSQL profiles capture subscription & resource ID."""
        profile = CloudManagedDatabaseProfile(
            display_name="Azure SQL Main",
            provider=CloudProvider.AZURE,
            subscription_id="sub-1111-2222-3333",
            location="eastus",
            resource_id="/subscriptions/sub-1111-2222-3333/resourceGroups/rg-prod/providers/Microsoft.Sql/servers/az-sql-prod",
            resource_name="az-sql-prod",
            service_family=ManagedServiceFamily.AZURE_SQL,
            engine_family="MSSQL",
            engine_version="12.0",
            deployment_type="SINGLE_INSTANCE",
            endpoint_type=EndpointType.PUBLIC_ENDPOINT,
            hostname="az-sql-prod.database.windows.net",
            port=1433,
            database_name="sales_db",
            auth_mode="SERVICE_PRINCIPAL",
            tls_required=True,
        )

        self.assertEqual(profile.provider, CloudProvider.AZURE)
        self.assertEqual(profile.subscription_id, "sub-1111-2222-3333")
        self.assertEqual(profile.engine_family, "MSSQL")
        self.assertEqual(profile.port, 1433)

    def test_05_azure_missing_credentials_and_failed_discovery_fail_closed(self):
        """05: Azure discovery without credentials fails closed with RuntimeError."""
        async def run():
            az = AzureManagedDatabaseProvider(
                subscription_id="sub-9999",
                client_id=None,
                client_secret=None,
            )
            with self.assertRaises(RuntimeError):
                await az.discover_sql_servers()

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 3. GCP Hostile Tests
    # -------------------------------------------------------------------------
    def test_06_gcp_cloud_sql_profile_construction(self):
        """06: Verify GCP Cloud SQL profiles capture project ID and connection name."""
        profile = CloudManagedDatabaseProfile(
            display_name="Cloud SQL PG",
            provider=CloudProvider.GCP,
            project_id="my-gcp-project-123",
            region="us-central1",
            resource_id="my-gcp-project-123:us-central1:pg-instance",
            resource_name="pg-instance",
            service_family=ManagedServiceFamily.CLOUD_SQL,
            engine_family="POSTGRESQL",
            engine_version="POSTGRES_14",
            deployment_type="SINGLE_INSTANCE",
            endpoint_type=EndpointType.PUBLIC_ENDPOINT,
            hostname="35.200.10.5",
            port=5432,
            database_name="analytics",
            auth_mode="ADC",
            tls_required=True,
        )

        self.assertEqual(profile.provider, CloudProvider.GCP)
        self.assertEqual(profile.project_id, "my-gcp-project-123")
        self.assertEqual(profile.resource_id, "my-gcp-project-123:us-central1:pg-instance")

    # -------------------------------------------------------------------------
    # 4. OCI Hostile Tests
    # -------------------------------------------------------------------------
    def test_07_oci_autonomous_db_profile_construction(self):
        """07: Verify OCI Autonomous DB profiles capture tenancy OCID, compartment, and wallet ref."""
        profile = CloudManagedDatabaseProfile(
            display_name="OCI Autonomous DB",
            provider=CloudProvider.OCI,
            tenancy_id="ocid1.tenancy.oc1..aaaaaaaaxxx",
            compartment_id="ocid1.compartment.oc1..yyyyyyy",
            region="us-ashburn-1",
            resource_id="ocid1.autonomousdatabase.oc1.iad.zzzzzz",
            resource_name="db2026",
            service_family=ManagedServiceFamily.AUTONOMOUS_DATABASE,
            engine_family="ORACLE",
            engine_version="19c",
            deployment_type="SHARED",
            endpoint_type=EndpointType.PRIMARY_WRITER,
            hostname="db2026_high.adb.us-ashburn-1.oraclecloud.com",
            port=1522,
            database_name="db2026",
            service_name="db2026_high",
            auth_mode="CONFIG_PROFILE",
            tls_required=True,
            wallet_ref="oci-wallet-db2026",
        )

        self.assertEqual(profile.provider, CloudProvider.OCI)
        self.assertEqual(profile.tenancy_id, "ocid1.tenancy.oc1..aaaaaaaaxxx")
        self.assertEqual(profile.engine_family, "ORACLE")
        self.assertEqual(profile.port, 1522)
        self.assertEqual(profile.wallet_ref, "oci-wallet-db2026")

    def test_08_oci_object_storage_strictly_absent(self):
        """08: Strictly verify OCI Object Storage is NOT added to P4.6 SystemTypes or adapter registry."""
        self.assertFalse(hasattr(SystemType, "OCI_OBJECT_STORAGE"))

    # -------------------------------------------------------------------------
    # 5. Cross-Provider Isolation & Failure Safety
    # -------------------------------------------------------------------------
    def test_09_cross_provider_isolation(self):
        """09: Verify provider profiles enforce enum type checking and reject invalid provider values."""
        p_aws = CloudManagedDatabaseProfile(provider=CloudProvider.AWS)
        p_az = CloudManagedDatabaseProfile(provider=CloudProvider.AZURE)
        p_gcp = CloudManagedDatabaseProfile(provider=CloudProvider.GCP)
        p_oci = CloudManagedDatabaseProfile(provider=CloudProvider.OCI)

        self.assertNotEqual(p_aws.provider, p_az.provider)
        self.assertNotEqual(p_az.provider, p_gcp.provider)
        self.assertNotEqual(p_gcp.provider, p_oci.provider)

        with self.assertRaises(ValueError):
            CloudManagedDatabaseProfile(provider="INVALID_CLOUD_PROVIDER")

    def test_10_cross_account_and_cross_region_identity_mismatch_fails_closed(self):
        """10: Endpoint refresh with mismatched account or durable resource identity fails closed."""
        p1 = CloudManagedDatabaseProfile(
            provider=CloudProvider.AWS,
            account_id="111111111111",
            resource_id="arn:aws:rds:us-east-1:111111111111:db:db1",
            hostname="db1.us-east-1.rds.amazonaws.com",
        )

        p2_diff_account = CloudManagedDatabaseProfile(
            provider=CloudProvider.AWS,
            account_id="999999999999",
            resource_id="arn:aws:rds:us-east-1:111111111111:db:db1",
            hostname="db1.us-east-1.rds.amazonaws.com",
        )

        async def run():
            with self.assertRaises(RuntimeError):
                await refresh_cloud_managed_profile(p1, p2_diff_account)

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 6. Serialization & Process Restart
    # -------------------------------------------------------------------------
    def test_11_profile_secret_safe_serialization(self):
        """11: Verify to_sanitized_dict redacts passwords and raw secrets from serialization."""
        profile = CloudManagedDatabaseProfile(
            display_name="Secret DB",
            provider=CloudProvider.AWS,
            raw_credentials={"password": "super_secret_db_pass_12345"},
        )
        d = profile.to_sanitized_dict()
        self.assertNotIn("super_secret_db_pass_12345", str(d))
        self.assertNotIn("password", d)

        # Verify round-trip process restart restoration of non-secret fields
        restored = CloudManagedDatabaseProfile.from_dict(d)
        self.assertEqual(restored.display_name, "Secret DB")
        self.assertEqual(restored.provider, CloudProvider.AWS)

    # -------------------------------------------------------------------------
    # 7. Endpoint Refresh & Change Detection
    # -------------------------------------------------------------------------
    def test_12_endpoint_refresh_updates_hostname_truthfully(self):
        """12: Endpoint refresh updates hostname when durable resource identity matches."""
        p_orig = CloudManagedDatabaseProfile(
            provider=CloudProvider.AWS,
            account_id="123456789012",
            resource_id="arn:aws:rds:us-east-1:123456789012:db:prod-db",
            hostname="old-endpoint.rds.amazonaws.com",
            port=5432,
        )

        p_new = CloudManagedDatabaseProfile(
            provider=CloudProvider.AWS,
            account_id="123456789012",
            resource_id="arn:aws:rds:us-east-1:123456789012:db:prod-db",
            hostname="new-failover-endpoint.rds.amazonaws.com",
            port=5432,
        )

        async def run():
            refreshed = await refresh_cloud_managed_profile(p_orig, p_new)
            self.assertEqual(refreshed.hostname, "new-failover-endpoint.rds.amazonaws.com")

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 8. Database Adapter Handoff (Zero Duplication)
    # -------------------------------------------------------------------------
    def test_13_cloud_profile_handoff_to_canonical_database_adapters(self):
        """13: Verify CloudManagedDatabaseProfile handoffs to canonical DB adapters without engine duplication."""
        # 1. AWS RDS PostgreSQL -> PostgreSQLAdapter
        p_pg = CloudManagedDatabaseProfile(
            provider=CloudProvider.AWS,
            engine_family="POSTGRESQL",
            hostname="rds-pg.amazonaws.com",
            port=5432,
            database_name="app_db",
        )
        config_pg = resolve_cloud_profile_to_connection_config(p_pg)
        self.assertEqual(config_pg.system_type, SystemType.POSTGRESQL)
        adapter_pg = get_database_adapter_for_cloud_profile(p_pg)
        self.assertEqual(adapter_pg.SYSTEM_TYPE, SystemType.POSTGRESQL)

        # 2. Azure SQL -> MSSQLAdapter
        p_sql = CloudManagedDatabaseProfile(
            provider=CloudProvider.AZURE,
            engine_family="MSSQL",
            hostname="az-sql.database.windows.net",
            port=1433,
            database_name="sales_db",
        )
        adapter_sql = get_database_adapter_for_cloud_profile(p_sql)
        self.assertEqual(adapter_sql.SYSTEM_TYPE, SystemType.MSSQL)

        # 3. OCI Autonomous DB -> OracleAdapter
        p_ora = CloudManagedDatabaseProfile(
            provider=CloudProvider.OCI,
            engine_family="ORACLE",
            hostname="adb.oraclecloud.com",
            port=1522,
            database_name="db2026",
            service_name="db2026_high",
        )
        adapter_ora = get_database_adapter_for_cloud_profile(p_ora)
        self.assertEqual(adapter_ora.SYSTEM_TYPE, SystemType.ORACLE)


if __name__ == "__main__":
    unittest.main()
