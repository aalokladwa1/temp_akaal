"""
Akaal — Discovery Report Model
==============================
Canonical, versioned, immutable Discovery Report produced by Scout Platform.
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class StageDiagnostics:
    stage_name: str
    status: str  # "SUCCESS", "FAILED", "SKIPPED"
    start_time: str
    end_time: str
    duration_ms: float
    warnings: List[str] = field(default_factory=list)
    error_details: Optional[str] = None


@dataclass
class DiscoveryFingerprint:
    sha256_hash: str
    component_hashes: Dict[str, str] = field(default_factory=dict)


@dataclass
class EngineInfo:
    system_type: str
    vendor: str
    engine_name: str


@dataclass
class InstanceInfo:
    host: str
    port: int
    database_name: str
    server_version: str
    max_connections: int = 100
    active_connections: int = 1
    uptime_seconds: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterInfo:
    is_clustered: bool = False
    role: str = "PRIMARY"
    node_count: int = 1
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    replication_lag_ms: int = 0


@dataclass
class MetadataSection:
    discovered_at: str
    environment: str = "production"
    read_only_verified: bool = True
    connection_host: str = "localhost"


@dataclass
class StatisticsSection:
    total_schemas: int = 0
    total_tables: int = 0
    total_columns: int = 0
    total_indexes: int = 0
    total_foreign_keys: int = 0
    total_views: int = 0
    total_objects: int = 0
    total_rows: int = 0
    total_bytes: int = 0


@dataclass
class PerformanceSection:
    total_discovery_duration_ms: float = 0.0
    schemas_per_sec: float = 0.0
    objects_per_sec: float = 0.0
    metadata_query_count: int = 0
    avg_query_latency_ms: float = 0.0
    cache_hit: bool = False


@dataclass
class HealthSection:
    overall_status: str = "HEALTHY"  # "HEALTHY", "PARTIAL", "FAILED"
    failed_stage_count: int = 0
    warning_count: int = 0
    error_count: int = 0


@dataclass(frozen=True)
class DiscoveryReport:
    """
    Final immutable, versioned Discovery Report document.
    """
    schema_version: str = "1.0.0"
    report_version: str = "1.0.0"
    generator_version: str = "scout-1.0.0"
    compatibility_version: str = "1.0.0"
    report_signature: str = "AKAAL-SCOUT-SIG-V1"
    sha256_checksum: str = ""

    metadata: MetadataSection = field(default_factory=lambda: MetadataSection(datetime.now(timezone.utc).isoformat()))
    engine_info: EngineInfo = field(default_factory=lambda: EngineInfo("GENERIC", "Generic", "Generic"))
    version_info: Dict[str, Any] = field(default_factory=dict)
    instance_info: InstanceInfo = field(default_factory=lambda: InstanceInfo("localhost", 0, "default", "1.0"))
    cluster_info: ClusterInfo = field(default_factory=ClusterInfo)
    
    capability_inventory: Dict[str, Any] = field(default_factory=dict)
    schema_inventory: Dict[str, Any] = field(default_factory=dict)
    object_inventory: Dict[str, Any] = field(default_factory=dict)
    storage_inventory: Dict[str, Any] = field(default_factory=dict)

    permission_assessment: Dict[str, Any] = field(default_factory=dict)
    health_assessment: Dict[str, Any] = field(default_factory=dict)
    cost_estimate: Dict[str, Any] = field(default_factory=dict)
    audit_trail: Dict[str, Any] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)

    statistics: StatisticsSection = field(default_factory=StatisticsSection)
    performance: PerformanceSection = field(default_factory=PerformanceSection)
    health: HealthSection = field(default_factory=HealthSection)
    
    fingerprint: Optional[DiscoveryFingerprint] = None
    stage_diagnostics: List[StageDiagnostics] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def compute_sha256_checksum(self) -> str:
        d = self.to_dict()
        d.pop("sha256_checksum", None)
        canonical_json = json.dumps(d, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "report_version": self.report_version,
            "generator_version": self.generator_version,
            "compatibility_version": self.compatibility_version,
            "report_signature": self.report_signature,
            "sha256_checksum": self.sha256_checksum,
            "metadata": {
                "discovered_at": self.metadata.discovered_at,
                "environment": self.metadata.environment,
                "read_only_verified": self.metadata.read_only_verified,
                "connection_host": self.metadata.connection_host,
            },
            "engine_info": {
                "system_type": self.engine_info.system_type,
                "vendor": self.engine_info.vendor,
                "engine_name": self.engine_info.engine_name,
            },
            "version_info": self.version_info,
            "instance_info": {
                "host": self.instance_info.host,
                "port": self.instance_info.port,
                "database_name": self.instance_info.database_name,
                "server_version": self.instance_info.server_version,
                "max_connections": self.instance_info.max_connections,
                "active_connections": self.instance_info.active_connections,
                "uptime_seconds": self.instance_info.uptime_seconds,
                "parameters": self.instance_info.parameters,
            },
            "cluster_info": {
                "is_clustered": self.cluster_info.is_clustered,
                "role": self.cluster_info.role,
                "node_count": self.cluster_info.node_count,
                "nodes": self.cluster_info.nodes,
                "replication_lag_ms": self.cluster_info.replication_lag_ms,
            },
            "capability_inventory": self.capability_inventory,
            "schema_inventory": self.schema_inventory,
            "object_inventory": self.object_inventory,
            "storage_inventory": self.storage_inventory,
            "permission_assessment": self.permission_assessment,
            "health_assessment": self.health_assessment,
            "cost_estimate": self.cost_estimate,
            "audit_trail": self.audit_trail,
            "manifest": self.manifest,
            "statistics": {
                "total_schemas": self.statistics.total_schemas,
                "total_tables": self.statistics.total_tables,
                "total_columns": self.statistics.total_columns,
                "total_indexes": self.statistics.total_indexes,
                "total_foreign_keys": self.statistics.total_foreign_keys,
                "total_views": self.statistics.total_views,
                "total_objects": self.statistics.total_objects,
                "total_rows": self.statistics.total_rows,
                "total_bytes": self.statistics.total_bytes,
            },
            "performance": {
                "total_discovery_duration_ms": self.performance.total_discovery_duration_ms,
                "schemas_per_sec": self.performance.schemas_per_sec,
                "objects_per_sec": self.performance.objects_per_sec,
                "metadata_query_count": self.performance.metadata_query_count,
                "avg_query_latency_ms": self.performance.avg_query_latency_ms,
                "cache_hit": self.performance.cache_hit,
            },
            "health": {
                "overall_status": self.health.overall_status,
                "failed_stage_count": self.health.failed_stage_count,
                "warning_count": self.health.warning_count,
                "error_count": self.health.error_count,
            },
            "fingerprint": {
                "sha256_hash": self.fingerprint.sha256_hash if self.fingerprint else "",
                "component_hashes": self.fingerprint.component_hashes if self.fingerprint else {},
            },
            "stage_diagnostics": [
                {
                    "stage_name": d.stage_name,
                    "status": d.status,
                    "start_time": d.start_time,
                    "end_time": d.end_time,
                    "duration_ms": d.duration_ms,
                    "warnings": d.warnings,
                    "error_details": d.error_details,
                }
                for d in self.stage_diagnostics
            ],
            "warnings": self.warnings,
            "errors": self.errors,
        }
        if not res["sha256_checksum"]:
            canonical = json.dumps(res, sort_keys=True)
            res["sha256_checksum"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return res

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
