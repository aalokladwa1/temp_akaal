"""
Akaal — Fingerprint Generation Stage
====================================
Stage 9: Generate deterministic cryptographic fingerprint of structural metadata.
"""

import hashlib
import json
from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import DiscoveryFingerprint, StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class FingerprintGenerationStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "FingerprintGeneration"

    @property
    def dependencies(self) -> list:
        return ["ObjectDiscovery", "StorageDiscovery"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        
        # Build normalized structural dict (strictly excluding operational metrics)
        structural_data = {
            "engine": ctx.engine_info.system_type,
            "version": ctx.version_info.get("version_string", ""),
            "schema_inventory": ctx.schema_inventory.to_dict(),
            "object_inventory": ctx.object_inventory.to_dict(),
            "capability_inventory": ctx.capability_inventory.to_dict(),
        }

        # Compute SHA256 of canonical JSON
        canonical_str = json.dumps(structural_data, sort_keys=True)
        sha_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        sch_str = json.dumps(ctx.schema_inventory.to_dict(), sort_keys=True)
        sch_hash = hashlib.sha256(sch_str.encode("utf-8")).hexdigest()

        obj_str = json.dumps(ctx.object_inventory.to_dict(), sort_keys=True)
        obj_hash = hashlib.sha256(obj_str.encode("utf-8")).hexdigest()

        ctx.fingerprint = DiscoveryFingerprint(
            sha256_hash=sha_hash,
            component_hashes={
                "schema": sch_hash,
                "objects": obj_hash,
            },
        )

        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
