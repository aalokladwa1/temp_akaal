"""
Akaal — Cloud Managed Database Profile Resolver & Database Adapter Handoff (P4.6)
===================================================================================
Resolves CloudManagedDatabaseProfile objects into canonical ConnectionConfig descriptors,
handoffs seamlessly to AKAAL's existing relational database adapters (PostgreSQL, MySQL, Oracle, MSSQL, MariaDB),
and performs fail-closed endpoint refresh and cross-account/cross-region resource identity validation.
"""

import datetime
import logging
from typing import Any, Dict, Optional

from akaal.cloud.models import CloudManagedDatabaseProfile, CloudProvider
from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.adapter_registry import get_adapter_class
from akaal.adapters.base_adapter import BaseAdapter

logger = logging.getLogger("akaal.cloud.resolver")


def map_engine_family_to_system_type(engine_family: str) -> SystemType:
    """Maps engine_family string to canonical AKAAL SystemType."""
    eng = engine_family.upper()
    if "POSTGRES" in eng:
        return SystemType.POSTGRESQL
    elif "MYSQL" in eng:
        return SystemType.MYSQL
    elif "ORACLE" in eng:
        return SystemType.ORACLE
    elif "SQLSERVER" in eng or "MSSQL" in eng:
        return SystemType.MSSQL
    elif "MARIADB" in eng:
        return SystemType.MARIADB
    else:
        raise ValueError(f"Unsupported engine family for cloud managed database: {engine_family}")


def resolve_cloud_profile_to_connection_config(cloud_profile: CloudManagedDatabaseProfile) -> ConnectionConfig:
    """
    Converts CloudManagedDatabaseProfile into canonical ConnectionConfig descriptor
    used by AKAAL's existing database adapters.
    """
    system_type = map_engine_family_to_system_type(cloud_profile.engine_family)

    extra_opts = dict(cloud_profile.extra_metadata or {})
    extra_opts["cloud_provider"] = cloud_profile.provider.value
    extra_opts["cloud_profile_id"] = cloud_profile.profile_id
    extra_opts["resource_id"] = cloud_profile.resource_id
    extra_opts["service_family"] = cloud_profile.service_family.value
    extra_opts["auth_mode"] = cloud_profile.auth_mode
    extra_opts["tls_required"] = cloud_profile.tls_required
    if cloud_profile.service_name:
        extra_opts["service_name"] = cloud_profile.service_name
    if cloud_profile.wallet_ref:
        extra_opts["wallet_ref"] = cloud_profile.wallet_ref
    username = cloud_profile.get_effective_secret("username")
    if username:
        extra_opts["username"] = username

    return ConnectionConfig(
        system_type=system_type,
        host=cloud_profile.hostname,
        port=cloud_profile.port,
        database_name=cloud_profile.database_name,
        credentials_ref=cloud_profile.credentials_ref,
        extra=extra_opts,
    )


def get_database_adapter_for_cloud_profile(cloud_profile: CloudManagedDatabaseProfile) -> BaseAdapter:
    """
    Handoffs CloudManagedDatabaseProfile directly to AKAAL's canonical relational database adapter.
    Ensures zero duplication of database migration engines.
    """
    config = resolve_cloud_profile_to_connection_config(cloud_profile)
    adapter_cls = get_adapter_class(config.system_type)
    if not adapter_cls:
        raise RuntimeError(f"No database adapter registered for SystemType {config.system_type}")

    adapter = adapter_cls(config)
    secret_pwd = cloud_profile.get_effective_secret("password")
    if secret_pwd:
        adapter.config.extra["password"] = secret_pwd

    return adapter


async def refresh_cloud_managed_profile(
    cloud_profile: CloudManagedDatabaseProfile,
    refreshed_profile: CloudManagedDatabaseProfile,
) -> CloudManagedDatabaseProfile:
    """
    Refreshes endpoint topology for stored profile using newly discovered control-plane metadata.
    Enforces strict durable resource identity validation: cross-account, cross-region,
    or provider identity mismatches FAIL CLOSED with RuntimeError.
    """
    # 1. Provider Identity Check
    if cloud_profile.provider != refreshed_profile.provider:
        raise RuntimeError(
            f"Provider identity mismatch during endpoint refresh: expected {cloud_profile.provider}, got {refreshed_profile.provider}"
        )

    # 2. Account / Subscription / Project / Tenancy Identity Check
    if cloud_profile.account_id and refreshed_profile.account_id and cloud_profile.account_id != refreshed_profile.account_id:
        raise RuntimeError(
            f"Account ID mismatch during endpoint refresh: expected {cloud_profile.account_id}, got {refreshed_profile.account_id}"
        )
    if cloud_profile.subscription_id and refreshed_profile.subscription_id and cloud_profile.subscription_id != refreshed_profile.subscription_id:
        raise RuntimeError(
            f"Subscription ID mismatch during endpoint refresh: expected {cloud_profile.subscription_id}, got {refreshed_profile.subscription_id}"
        )
    if cloud_profile.project_id and refreshed_profile.project_id and cloud_profile.project_id != refreshed_profile.project_id:
        raise RuntimeError(
            f"Project ID mismatch during endpoint refresh: expected {cloud_profile.project_id}, got {refreshed_profile.project_id}"
        )
    if cloud_profile.tenancy_id and refreshed_profile.tenancy_id and cloud_profile.tenancy_id != refreshed_profile.tenancy_id:
        raise RuntimeError(
            f"Tenancy ID mismatch during endpoint refresh: expected {cloud_profile.tenancy_id}, got {refreshed_profile.tenancy_id}"
        )

    # 3. Resource Identity Check
    if cloud_profile.resource_id != refreshed_profile.resource_id:
        raise RuntimeError(
            f"Durable resource ID mismatch during endpoint refresh: expected {cloud_profile.resource_id}, got {refreshed_profile.resource_id}"
        )

    # Update endpoints and refresh timestamp
    cloud_profile.hostname = refreshed_profile.hostname
    cloud_profile.port = refreshed_profile.port
    cloud_profile.writer_endpoint = refreshed_profile.writer_endpoint
    cloud_profile.reader_endpoint = refreshed_profile.reader_endpoint
    cloud_profile.failover_endpoint = refreshed_profile.failover_endpoint
    cloud_profile.private_endpoint = refreshed_profile.private_endpoint
    cloud_profile.public_endpoint = refreshed_profile.public_endpoint
    cloud_profile.endpoint_refresh_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(f"[CloudResolver] Successfully refreshed endpoint for resource {cloud_profile.resource_id} -> {cloud_profile.hostname}:{cloud_profile.port}")
    return cloud_profile
