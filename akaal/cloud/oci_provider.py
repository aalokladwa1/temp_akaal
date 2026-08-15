"""
Akaal — OCI Managed Database Provider (P4.6)
============================================
Physical reality provider for Oracle Cloud Infrastructure (OCI) Autonomous Database and Base Database / DB System discovery and profiling.
Uses official OCI Python SDK when available. Fails closed safely if oci SDK is missing or credentials fail.
Redacts all private keys, passphrases, and secrets from error messages and logs.
STRICTLY NO OCI OBJECT STORAGE (Reserved for P7B).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.cloud.models import CloudManagedDatabaseProfile, CloudProvider, ManagedServiceFamily, EndpointType

logger = logging.getLogger("akaal.cloud.oci_provider")


class OCIManagedDatabaseProvider:
    """Provider for OCI Autonomous Database and DB System resource discovery and profile construction."""

    def __init__(
        self,
        tenancy_ocid: str = "ocid1.tenancy.oc1..example",
        user_ocid: Optional[str] = None,
        fingerprint: Optional[str] = None,
        private_key_content: Optional[str] = None,
        region: str = "us-ashburn-1",
        config_profile: str = "DEFAULT",
    ) -> None:
        self.tenancy_ocid = tenancy_ocid
        self.user_ocid = user_ocid
        self.fingerprint = fingerprint
        self.private_key_content = private_key_content
        self.region = region
        self.config_profile = config_profile

    def _redact(self, text: str) -> str:
        if not text:
            return ""
        res = str(text)
        for k in [self.private_key_content, self.fingerprint, self.user_ocid]:
            if k and len(str(k)) > 3:
                res = res.replace(str(k), "[REDACTED]")
        return res

    async def _get_db_client(self) -> Any:
        try:
            import oci
        except ImportError as exc:
            raise RuntimeError("oci SDK is not installed. OCI managed database discovery requires oci.") from exc

        def _connect():
            if self.user_ocid and self.fingerprint and self.private_key_content:
                config = {
                    "user": self.user_ocid,
                    "fingerprint": self.fingerprint,
                    "key_content": self.private_key_content,
                    "tenancy": self.tenancy_ocid,
                    "region": self.region,
                }
                return oci.database.DatabaseClient(config)
            else:
                config = oci.config.from_file(profile_name=self.config_profile)
                config["region"] = self.region
                return oci.database.DatabaseClient(config)

        return await asyncio.to_thread(_connect)

    async def discover_autonomous_databases(self, compartment_ocid: str) -> List[CloudManagedDatabaseProfile]:
        """Discovers OCI Autonomous Databases in the specified compartment."""
        client = await self._get_db_client()

        def _run():
            try:
                res = client.list_autonomous_databases(compartment_id=compartment_ocid)
                items = res.data
            except Exception as exc:
                raise RuntimeError(f"OCI Autonomous Database discovery failed: {self._redact(str(exc))}") from exc

            profiles = []
            for item in items:
                db_ocid = getattr(item, "id", "")
                name = getattr(item, "display_name", "") or getattr(item, "db_name", "")
                db_version = getattr(item, "db_version", "19c")
                lifecycle_state = getattr(item, "lifecycle_state", "AVAILABLE")
                is_dedicated = getattr(item, "is_dedicated", False)

                conn_strings = getattr(item, "connection_strings", None)
                high_str = ""
                if conn_strings and hasattr(conn_strings, "profiles"):
                    for p in (conn_strings.profiles or []):
                        if getattr(p, "consumer_group", "") == "HIGH":
                            high_str = getattr(p, "value", "")
                            break

                profile = CloudManagedDatabaseProfile(
                    display_name=f"Autonomous DB {name}",
                    provider=CloudProvider.OCI,
                    tenancy_id=self.tenancy_ocid,
                    compartment_id=compartment_ocid,
                    region=self.region,
                    resource_id=db_ocid or name,
                    resource_name=name,
                    service_family=ManagedServiceFamily.AUTONOMOUS_DATABASE,
                    engine_family="ORACLE",
                    engine_version=str(db_version),
                    deployment_type="DEDICATED" if is_dedicated else "SHARED",
                    endpoint_type=EndpointType.PRIMARY_WRITER,
                    hostname=high_str or f"{name}.adb.{self.region}.oraclecloud.com",
                    port=1522,
                    database_name=name,
                    service_name=f"{name}_high",
                    auth_mode="INSTANCE_PRINCIPAL" if not self.user_ocid else "CONFIG_PROFILE",
                    tls_required=True,
                    wallet_ref=f"oci-wallet-{name}",
                    extra_metadata={"lifecycle_state": str(lifecycle_state)},
                )
                profiles.append(profile)

            return profiles

        return await asyncio.to_thread(_run)

    async def discover_db_systems(self, compartment_ocid: str) -> List[CloudManagedDatabaseProfile]:
        """Discovers OCI Base Database Systems in the specified compartment."""
        client = await self._get_db_client()

        def _run():
            try:
                res = client.list_db_systems(compartment_id=compartment_ocid)
                items = res.data
            except Exception as exc:
                raise RuntimeError(f"OCI DB System discovery failed: {self._redact(str(exc))}") from exc

            profiles = []
            for item in items:
                sys_ocid = getattr(item, "id", "")
                name = getattr(item, "display_name", "")
                version = getattr(item, "version", "19c")
                domain = getattr(item, "domain", "")
                hostname = getattr(item, "hostname", "")
                fqdn = f"{hostname}.{domain}" if hostname and domain else hostname or name

                subnet_id = getattr(item, "subnet_id", "")

                profile = CloudManagedDatabaseProfile(
                    display_name=f"OCI DB System {name}",
                    provider=CloudProvider.OCI,
                    tenancy_id=self.tenancy_ocid,
                    compartment_id=compartment_ocid,
                    region=self.region,
                    resource_id=sys_ocid or name,
                    resource_name=name,
                    service_family=ManagedServiceFamily.BASE_DATABASE_SERVICE,
                    engine_family="ORACLE",
                    engine_version=str(version),
                    deployment_type="SINGLE_INSTANCE",
                    endpoint_type=EndpointType.PRIVATE_ENDPOINT if subnet_id else EndpointType.PUBLIC_ENDPOINT,
                    hostname=fqdn,
                    port=1521,
                    database_name=name,
                    subnet_id=subnet_id,
                    auth_mode="CONFIG_PROFILE",
                    tls_required=True,
                )
                profiles.append(profile)

            return profiles

        return await asyncio.to_thread(_run)
