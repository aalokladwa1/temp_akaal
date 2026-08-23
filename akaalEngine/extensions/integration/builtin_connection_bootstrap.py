"""
akaalEngine.extensions.integration.builtin_connection_bootstrap
===============================================================
Adopts the 28 registered physical database/storage/streaming providers from frozen Connection Authority
into the canonical Extensions registry.
Preserves canonical provider IDs, versions, and existing strategy instances without recreating implementations.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from akaalEngine.connection.catalog.provider_catalog import (
    ProviderCatalog,
    default_provider_catalog,
)
from akaalEngine.extensions.catalog.registry import ExtensionRegistry, default_extension_registry
from akaalEngine.extensions.integration.connection_contract import (
    CONNECTION_AUTHORITY_ID,
    register_connection_contract,
)
from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.compatibility import CompatibilityRange
from akaalEngine.extensions.models.enums import ExtensionLifecycleState, ExtensionOrigin, IsolationMode, ProofLevel, TrustTier
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import (
    AuthorityId,
    ExtensionId,
    ProviderId,
    StrategyId,
)
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.strategy import StrategyContribution
from akaalEngine.extensions.spi.authority_contract import default_contract_registry
from akaalEngine.extensions.spi.strategy_factory import InstanceStrategyFactory

logger = logging.getLogger(__name__)

BUILTIN_CONNECTION_EXTENSION_ID = ExtensionId("builtin-connection-providers")


from akaalEngine.extensions.models.dependency import (
    DependencyGroup,
    DependencyRequirement,
    PythonDependency,
)
from akaalEngine.extensions.models.enums import DependencyMatchMode


def build_connection_provider_dependency(provider_id_str: str) -> Optional[DependencyRequirement]:
    """
    Constructs the truthful dependency requirement for an adopted Connection provider strategy,
    accurately reflecting single-driver and alternative-driver (ANY_OF) physical implementations.
    """
    if provider_id_str == "sqlite":
        return PythonDependency(name="sqlite3", import_module="sqlite3", is_optional=False, remediation_hint="Standard library built-in")

    elif provider_id_str == "postgresql":
        return PythonDependency(name="psycopg2", import_module="psycopg2", is_optional=False, remediation_hint="Run 'pip install psycopg2-binary'")

    elif provider_id_str == "mysql":
        return PythonDependency(name="pymysql", import_module="pymysql", is_optional=False, remediation_hint="Run 'pip install pymysql'")

    elif provider_id_str == "mariadb":
        # Frozen MariaDB strategy accepts pymysql (or mariadb)
        return DependencyGroup(
            name="mariadb_driver",
            match_mode=DependencyMatchMode.ANY_OF,
            is_optional=False,
            dependencies=(
                PythonDependency(name="pymysql", import_module="pymysql", is_optional=False, remediation_hint="Run 'pip install pymysql'"),
                PythonDependency(name="mariadb", import_module="mariadb", is_optional=False, remediation_hint="Run 'pip install mariadb'"),
            ),
            remediation_hint="Install via 'pip install pymysql' or 'pip install mariadb'",
        )

    elif provider_id_str == "oracle":
        return PythonDependency(name="oracledb", import_module="oracledb", is_optional=False, remediation_hint="Run 'pip install oracledb'")

    elif provider_id_str == "mssql":
        return PythonDependency(name="pyodbc", import_module="pyodbc", is_optional=False, remediation_hint="Run 'pip install pyodbc'")

    elif provider_id_str == "ibm_db2":
        return PythonDependency(name="ibm_db", import_module="ibm_db", is_optional=False, remediation_hint="Run 'pip install ibm_db'")

    elif provider_id_str == "snowflake":
        return PythonDependency(name="snowflake-connector-python", import_module="snowflake.connector", is_optional=False, remediation_hint="Run 'pip install snowflake-connector-python'")

    elif provider_id_str == "bigquery":
        return PythonDependency(name="google-cloud-bigquery", import_module="google.cloud.bigquery", is_optional=False, remediation_hint="Run 'pip install google-cloud-bigquery'")

    elif provider_id_str == "redshift":
        # Frozen Redshift strategy accepts psycopg2 or redshift_connector
        return DependencyGroup(
            name="redshift_driver",
            match_mode=DependencyMatchMode.ANY_OF,
            is_optional=False,
            dependencies=(
                PythonDependency(name="psycopg2", import_module="psycopg2", is_optional=False, remediation_hint="Run 'pip install psycopg2-binary'"),
                PythonDependency(name="redshift-connector", import_module="redshift_connector", is_optional=False, remediation_hint="Run 'pip install redshift-connector'"),
            ),
            remediation_hint="Install via 'pip install psycopg2-binary' or 'pip install redshift-connector'",
        )

    elif provider_id_str == "databricks":
        return PythonDependency(name="databricks-sql-connector", import_module="databricks.sql", is_optional=False, remediation_hint="Run 'pip install databricks-sql-connector'")

    elif provider_id_str == "mongodb":
        return PythonDependency(name="pymongo", import_module="pymongo", is_optional=False, remediation_hint="Run 'pip install pymongo'")

    elif provider_id_str == "cassandra":
        return PythonDependency(name="cassandra-driver", import_module="cassandra", is_optional=False, remediation_hint="Run 'pip install cassandra-driver'")

    elif provider_id_str == "scylladb":
        return PythonDependency(name="cassandra-driver", import_module="cassandra", is_optional=False, remediation_hint="Run 'pip install cassandra-driver'")

    elif provider_id_str == "neo4j":
        return PythonDependency(name="neo4j", import_module="neo4j", is_optional=False, remediation_hint="Run 'pip install neo4j'")

    elif provider_id_str == "redis":
        return PythonDependency(name="redis", import_module="redis", is_optional=False, remediation_hint="Run 'pip install redis'")

    elif provider_id_str == "keydb":
        return PythonDependency(name="redis", import_module="redis", is_optional=False, remediation_hint="Run 'pip install redis'")

    elif provider_id_str == "elasticsearch":
        return PythonDependency(name="elasticsearch", import_module="elasticsearch", is_optional=False, remediation_hint="Run 'pip install elasticsearch'")

    elif provider_id_str == "opensearch":
        return PythonDependency(name="opensearch-py", import_module="opensearchpy", is_optional=False, remediation_hint="Run 'pip install opensearch-py'")

    elif provider_id_str == "kafka":
        # Frozen Kafka strategy accepts kafka-python or confluent-kafka
        return DependencyGroup(
            name="kafka_driver",
            match_mode=DependencyMatchMode.ANY_OF,
            is_optional=False,
            dependencies=(
                PythonDependency(name="kafka-python", import_module="kafka", is_optional=False, remediation_hint="Run 'pip install kafka-python'"),
                PythonDependency(name="confluent-kafka", import_module="confluent_kafka", is_optional=False, remediation_hint="Run 'pip install confluent-kafka'"),
            ),
            remediation_hint="Install via 'pip install kafka-python' or 'pip install confluent-kafka'",
        )

    elif provider_id_str == "kinesis":
        return PythonDependency(name="boto3", import_module="boto3", is_optional=False, remediation_hint="Run 'pip install boto3'")

    elif provider_id_str == "eventhubs":
        return PythonDependency(name="azure-eventhub", import_module="azure.eventhub", is_optional=False, remediation_hint="Run 'pip install azure-eventhub'")

    elif provider_id_str == "pubsub":
        return PythonDependency(name="google-cloud-pubsub", import_module="google.cloud.pubsub_v1", is_optional=False, remediation_hint="Run 'pip install google-cloud-pubsub'")

    elif provider_id_str == "s3":
        return PythonDependency(name="boto3", import_module="boto3", is_optional=False, remediation_hint="Run 'pip install boto3'")

    elif provider_id_str == "gcs":
        return PythonDependency(name="google-cloud-storage", import_module="google.cloud.storage", is_optional=False, remediation_hint="Run 'pip install google-cloud-storage'")

    elif provider_id_str == "azure_blob":
        return PythonDependency(name="azure-storage-blob", import_module="azure.storage.blob", is_optional=False, remediation_hint="Run 'pip install azure-storage-blob'")

    elif provider_id_str == "minio":
        # Frozen MinIO strategy accepts minio or boto3
        return DependencyGroup(
            name="minio_driver",
            match_mode=DependencyMatchMode.ANY_OF,
            is_optional=False,
            dependencies=(
                PythonDependency(name="minio", import_module="minio", is_optional=False, remediation_hint="Run 'pip install minio'"),
                PythonDependency(name="boto3", import_module="boto3", is_optional=False, remediation_hint="Run 'pip install boto3'"),
            ),
            remediation_hint="Install via 'pip install minio' or 'pip install boto3'",
        )

    elif provider_id_str == "hdfs":
        # Frozen HDFS strategy accepts hdfs or pyarrow.fs
        return DependencyGroup(
            name="hdfs_driver",
            match_mode=DependencyMatchMode.ANY_OF,
            is_optional=False,
            dependencies=(
                PythonDependency(name="hdfs", import_module="hdfs", is_optional=False, remediation_hint="Run 'pip install hdfs'"),
                PythonDependency(name="pyarrow", import_module="pyarrow.fs", is_optional=False, remediation_hint="Run 'pip install pyarrow'"),
            ),
            remediation_hint="Install via 'pip install hdfs' or 'pip install pyarrow'",
        )

    return None


class BuiltinConnectionBootstrap:
    """
    Bootstraps Extensions Authority by adopting the 28 frozen Connection provider strategies.
    Preserves truthful physical driver dependency requirements including alternative driver paths.
    """

    @classmethod
    def adopt_connection_providers(
        cls,
        connection_catalog: Optional[ProviderCatalog] = None,
        extension_registry: Optional[ExtensionRegistry] = None,
    ) -> ExtensionManifest:
        conn_cat = connection_catalog or default_provider_catalog
        ext_reg = extension_registry or default_extension_registry

        # 1. Ensure Connection contract is registered in contract registry
        register_connection_contract(default_contract_registry)

        # 2. Iterate through all registered Connection providers
        registered_ids = conn_cat.list_providers()
        provider_contributions: List[ProviderContribution] = []

        for prov_id_str in registered_ids:
            try:
                strategy_inst = conn_cat.get_strategy(prov_id_str)
            except Exception:
                strategy_inst = None
            if strategy_inst is None:
                continue

            static_manifest = strategy_inst.get_static_manifest()
            prov_id = ProviderId(strategy_inst.PROVIDER_ID)
            strat_id = StrategyId(f"{strategy_inst.PROVIDER_ID}-connection")

            # Extract declared capabilities from static manifest
            caps: List[CapabilityDeclaration] = []
            for cap_name, cap_status in static_manifest.capabilities.items():
                is_supp = (
                    cap_status.value == "SUPPORTED"
                    if hasattr(cap_status, "value")
                    else str(cap_status) == "SUPPORTED"
                )
                caps.append(
                    CapabilityDeclaration(
                        capability_name=cap_name,
                        is_supported=is_supp,
                        declared_proof_level=ProofLevel(static_manifest.proof_level.value),
                    )
                )

            # Map truthful physical driver dependency for this provider
            dep_req = build_connection_provider_dependency(prov_id.value)
            strat_deps = (dep_req,) if dep_req is not None else ()

            # Build truthful configuration schema for this provider
            from akaalEngine.extensions.integration.builtin_connection_schemas import build_connection_provider_schema
            prov_schema = build_connection_provider_schema(prov_id.value)

            # Create StrategyContribution
            strat_contrib = StrategyContribution(
                strategy_id=strat_id,
                authority_id=CONNECTION_AUTHORITY_ID,
                provider_id=prov_id,
                contract_version_range=CompatibilityRange(">=1.0.0, <2.0.0"),
                strategy_factory=InstanceStrategyFactory(strategy_inst),
                implementation_version=strategy_inst.PROVIDER_VERSION,
                description=f"Adopted Connection Strategy for {strategy_inst.VENDOR_NAME}",
                configuration_schema=prov_schema,
                capabilities=tuple(caps),
                dependencies=strat_deps,
                priority=100,
            )

            # Create ProviderContribution (dependencies placed cleanly on strategy scope)
            prov_contrib = ProviderContribution(
                provider_id=prov_id,
                vendor_name=strategy_inst.VENDOR_NAME,
                display_name=f"{strategy_inst.VENDOR_NAME} ({strategy_inst.FAMILY.title()})",
                family=strategy_inst.FAMILY,
                version=strategy_inst.PROVIDER_VERSION,
                description=f"Built-in {strategy_inst.VENDOR_NAME} provider adopted from Connection Authority",
                strategies=(strat_contrib,),
                shared_dependencies=(),
                capabilities=tuple(caps),
            )
            provider_contributions.append(prov_contrib)

        # 3. Create ExtensionManifest
        manifest = ExtensionManifest(
            extension_id=BUILTIN_CONNECTION_EXTENSION_ID,
            version="1.0.0",
            display_name="Adopted Built-in Connection Providers",
            engine_version_range=CompatibilityRange(">=1.0.0, <2.0.0"),
            origin=ExtensionOrigin.BUILTIN,
            trust_tier=TrustTier.CORE_TRUSTED,
            isolation_mode=IsolationMode.IN_PROCESS,
            description="28 Canonical built-in physical database/storage/streaming providers adopted from Authority #1 Connection",
            authors=("AKAAL Core Engineering Team",),
            provider_contributions=tuple(provider_contributions),
        )

        # 4. Register into Extensions registry
        ext_reg.register_extension(manifest, allow_replace=True)
        logger.info("Successfully adopted %d Connection providers into Extensions Authority.", len(provider_contributions))

        return manifest
