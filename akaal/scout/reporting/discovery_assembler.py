"""
Akaal — Discovery Assembler
===========================
Assembles canonical DiscoveryReport from runtime DiscoveryContext with enterprise metadata.
"""

import hashlib
import json
from datetime import datetime, timezone

from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import (
    DiscoveryReport,
    MetadataSection,
    StatisticsSection,
    PerformanceSection,
    HealthSection,
)
from akaal.scout.models.discovery_audit import DiscoveryAudit
from akaal.scout.models.discovery_health import DiscoveryHealth, DiscoveryRecommendation
from akaal.scout.models.discovery_manifest import DiscoveryManifest


class DiscoveryAssembler:
    """Assembles final immutable DiscoveryReport from runtime context."""

    @staticmethod
    def assemble(ctx: DiscoveryContext, cache_hit: bool = False) -> DiscoveryReport:
        schema_dict = ctx.schema_inventory.to_dict()
        object_dict = ctx.object_inventory.to_dict()
        storage_dict = ctx.storage_inventory.to_dict()
        capability_dict = ctx.capability_inventory.to_dict()

        total_schemas = len(schema_dict.get("schemas", []))
        tables = schema_dict.get("tables", [])
        total_tables = len(tables)
        total_columns = sum(len(t.get("columns", [])) for t in tables)
        total_indexes = sum(len(t.get("indexes", [])) for t in tables)
        total_fks = len(schema_dict.get("foreign_keys", []))
        total_views = len(schema_dict.get("views", []))
        total_objects = (
            len(object_dict.get("procedures", []))
            + len(object_dict.get("functions", []))
            + len(object_dict.get("triggers", []))
            + len(object_dict.get("sequences", []))
            + len(object_dict.get("custom_types", []))
        )
        total_rows = sum(storage_dict.get("row_counts", {}).values())
        total_bytes = storage_dict.get("database_size_bytes", 0)

        total_duration_ms = (ctx.end_time - ctx.start_time) * 1000.0 if ctx.end_time > ctx.start_time else 0.0

        stats = StatisticsSection(
            total_schemas=total_schemas,
            total_tables=total_tables,
            total_columns=total_columns,
            total_indexes=total_indexes,
            total_foreign_keys=total_fks,
            total_views=total_views,
            total_objects=total_objects,
            total_rows=total_rows,
            total_bytes=total_bytes,
        )

        schemas_sec = (total_schemas / total_duration_ms * 1000.0) if total_duration_ms > 0 else 0.0
        objects_sec = ((total_tables + total_objects) / total_duration_ms * 1000.0) if total_duration_ms > 0 else 0.0
        avg_latency = (ctx.metadata_query_total_ms / ctx.metadata_query_count) if ctx.metadata_query_count > 0 else 0.0

        perf = PerformanceSection(
            total_discovery_duration_ms=total_duration_ms,
            schemas_per_sec=schemas_sec,
            objects_per_sec=objects_sec,
            metadata_query_count=ctx.metadata_query_count,
            avg_query_latency_ms=avg_latency,
            cache_hit=cache_hit,
        )

        failed_count = sum(1 for d in ctx.stage_diagnostics if d.status == "FAILED")
        status_str = "FAILED" if failed_count == len(ctx.stage_diagnostics) and len(ctx.stage_diagnostics) > 0 else ("PARTIAL" if failed_count > 0 or ctx.errors else "HEALTHY")

        health_sec = HealthSection(
            overall_status=status_str,
            failed_stage_count=failed_count,
            warning_count=len(ctx.warnings),
            error_count=len(ctx.errors),
        )

        metadata = MetadataSection(
            discovered_at=datetime.now(timezone.utc).isoformat(),
            environment=ctx.request.discovery_options.get("environment", "production"),
            read_only_verified=ctx.read_only_verified,
            connection_host=ctx.request.connection_config.host,
        )

        # Update Cost Estimate Actuals
        ctx.cost_estimate.actual_metadata_queries = ctx.metadata_query_count
        ctx.cost_estimate.actual_runtime_sec = total_duration_ms / 1000.0
        ctx.cost_estimate.actual_objects_scanned = total_tables + total_objects

        # Compute Health Score & Recommendations
        comp_score = 100.0 if status_str == "HEALTHY" else (75.0 if status_str == "PARTIAL" else 0.0)
        perm_score = 100.0 if ctx.read_only_verified else 80.0
        conf_score = ctx.capability_inventory.get_average_confidence()
        warn_score = max(0.0, 100.0 - (len(ctx.warnings) * 5.0))

        ctx.health.completeness_score = comp_score
        ctx.health.permission_score = perm_score
        ctx.health.confidence_score = conf_score
        ctx.health.provider_compatibility_score = 100.0
        ctx.health.warning_score = warn_score
        ctx.health.calculate_overall()

        if not ctx.read_only_verified:
            ctx.health.recommendations.append(DiscoveryRecommendation(
                category="PERMISSIONS",
                severity="WARNING",
                observation="Read-only permissions could not be explicitly confirmed.",
                recommendation_text="Verify database user privileges before running migration stages.",
            ))

        if failed_count > 0:
            ctx.health.recommendations.append(DiscoveryRecommendation(
                category="PROVIDER",
                severity="HIGH",
                observation=f"{failed_count} pipeline stage(s) encountered execution errors.",
                recommendation_text="Inspect stage_diagnostics error details and retry discovery with verbose logging.",
            ))

        # Generate Audit Trail
        audit_record = DiscoveryAudit(
            discovery_id=ctx.discovery_id,
            request_id=ctx.request.request_id or ctx.discovery_id,
            authenticated_user=ctx.request.authenticated_user,
            target_endpoint=f"{ctx.request.connection_config.host}:{ctx.request.connection_config.port}",
            database_engine=ctx.engine_info.system_type,
            discovery_profile=ctx.request.profile.value if hasattr(ctx.request.profile, "value") else str(ctx.request.profile),
            discovery_policy_hash=hashlib.sha256(str(ctx.policy).encode("utf-8")).hexdigest(),
            fingerprint=ctx.fingerprint.sha256_hash if ctx.fingerprint else "",
            duration_ms=total_duration_ms,
            result=status_str,
            failure_reason=ctx.errors[0] if ctx.errors else None,
            warning_count=len(ctx.warnings),
            provider_version="1.0.0",
        )

        # Generate Manifest
        manifest_record = DiscoveryManifest(
            report_version="1.0.0",
            fingerprint=ctx.fingerprint.sha256_hash if ctx.fingerprint else "",
            provider_versions={ctx.engine_info.system_type: "1.0.0"},
            engine=ctx.engine_info.system_type,
            discovery_profile=ctx.request.profile.value if hasattr(ctx.request.profile, "value") else str(ctx.request.profile),
            policy_checksum=hashlib.sha256(str(ctx.policy).encode("utf-8")).hexdigest(),
        )

        temp_dict = {
            "engine": ctx.engine_info.system_type,
            "schema_inventory": schema_dict,
            "object_inventory": object_dict,
            "capability_inventory": capability_dict,
            "fingerprint": ctx.fingerprint.sha256_hash if ctx.fingerprint else "",
        }
        checksum_val = hashlib.sha256(json.dumps(temp_dict, default=str, sort_keys=True).encode("utf-8")).hexdigest()

        raw_report = DiscoveryReport(
            sha256_checksum=checksum_val,
            metadata=metadata,
            engine_info=ctx.engine_info,
            version_info=ctx.version_info,
            instance_info=ctx.instance_info,
            cluster_info=ctx.cluster_info,
            capability_inventory=capability_dict,
            schema_inventory=schema_dict,
            object_inventory=object_dict,
            storage_inventory=storage_dict,
            permission_assessment=ctx.permission_assessment.to_dict(),
            health_assessment=ctx.health.to_dict(),
            cost_estimate=ctx.cost_estimate.to_dict(),
            audit_trail=audit_record.to_dict(),
            manifest=manifest_record.to_dict(),
            statistics=stats,
            performance=perf,
            health=health_sec,
            fingerprint=ctx.fingerprint,
            stage_diagnostics=ctx.stage_diagnostics,
            warnings=ctx.warnings,
            errors=ctx.errors,
        )

        manifest_record.compute_checksum(raw_report.to_dict())

        return raw_report
