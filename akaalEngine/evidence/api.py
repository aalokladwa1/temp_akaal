"""
akaalEngine.evidence.api
========================
Single Canonical Public Façade for Authority #12 — Evidence / Provenance / Execution-Truth Artifacts (`EvidenceAuthority`).
Physically integrates with Authorities #1, #4, #5, #6, #7, #8, #9, #10, #11 to package physical execution and validation truth.
"""

import logging
from threading import RLock
import time
from typing import Any, Dict, List, Optional, Union

from akaalEngine.evidence.canonical import CanonicalEvidenceSerializer, EvidenceDigestCalculator
from akaalEngine.evidence.models.artifact import (
    EvidenceArtifact,
    EvidenceCompleteness,
    EvidenceDigest,
    EvidenceFact,
    EvidenceManifest,
    EvidenceProvenance,
    EvidenceVerificationResult,
    ProofClassification,
)
from akaalEngine.evidence.models.errors import (
    EvidenceFencingError,
    EvidenceIdentityError,
    EvidenceIntegrityError,
    EvidenceVerificationError,
)
from akaalEngine.evidence.security import EvidenceSecuritySanitizer
from akaalEngine.evidence.verification import EvidenceVerificationEngine

logger = logging.getLogger("akaalEngine.evidence.api")


class EvidenceAuthority:
    """
    Single Canonical Public Façade for Authority #12 — Evidence / Provenance / Execution-Truth Artifacts.
    Consumes authoritative facts from Authorities #1–#11 and packages them into deterministic,
    tamper-detectable, identity-bound evidence artifacts and manifests.
    """

    def __init__(
        self,
        connection_authority: Optional[Any] = None,
        schema_authority: Optional[Any] = None,
        durability_authority: Optional[Any] = None,
        runtime_authority: Optional[Any] = None,
        telemetry_authority: Optional[Any] = None,
        data_processing_authority: Optional[Any] = None,
        transport_authority: Optional[Any] = None,
        cdc_authority: Optional[Any] = None,
        validation_authority: Optional[Any] = None,
    ) -> None:
        self.connection_authority = connection_authority
        self.schema_authority = schema_authority
        self.durability_authority = durability_authority
        self.runtime_authority = runtime_authority
        self.telemetry_authority = telemetry_authority
        self.data_processing_authority = data_processing_authority
        self.transport_authority = transport_authority
        self.cdc_authority = cdc_authority
        self.validation_authority = validation_authority

        self._lock = RLock()
        self.evidence_artifacts_created_total = 0
        self.evidence_verification_failures_total = 0
        self.evidence_persistence_failures_total = 0

    def record_telemetry_metrics(self) -> None:
        """Physical integration with Authority #7 Telemetry metrics registry."""
        if self.telemetry_authority and hasattr(self.telemetry_authority, "record_counter"):
            self.telemetry_authority.record_counter("evidence_artifacts_created_total", self.evidence_artifacts_created_total)
            self.telemetry_authority.record_counter("evidence_verification_failures_total", self.evidence_verification_failures_total)
            self.telemetry_authority.record_counter("evidence_persistence_failures_total", self.evidence_persistence_failures_total)

    def create_evidence_artifact(
        self,
        migration_id: str,
        run_id: str,
        artifact_type: str,
        facts: List[EvidenceFact],
        provenance_list: List[EvidenceProvenance],
        artifact_id: Optional[str] = None,
        job_id: Optional[str] = None,
        source_identity: Optional[str] = None,
        target_identity: Optional[str] = None,
        provider_identity: Optional[str] = None,
        plan_identity: Optional[str] = None,
        validation_identity: Optional[str] = None,
        cdc_boundary_position: Optional[str] = None,
        fencing_epoch: Optional[int] = None,
        completeness: EvidenceCompleteness = EvidenceCompleteness.COMPLETE,
    ) -> EvidenceArtifact:
        """
        Creates, sanitizes, and digests a new EvidenceArtifact bound to migration identity.
        """
        art_id = artifact_id or f"evd-art-{time.time_ns()}"

        # Scrub secrets from fact keys/values and metadata
        sanitized_facts: List[EvidenceFact] = []
        for f in facts:
            clean_val = EvidenceSecuritySanitizer.sanitize_mapping({f.fact_key: f.fact_value})[f.fact_key]
            sanitized_facts.append(
                EvidenceFact(
                    fact_key=f.fact_key,
                    fact_value=clean_val,
                    originating_authority=f.originating_authority,
                    fact_type=f.fact_type,
                    observed_at=f.observed_at or time.time(),
                    proof_classification=f.proof_classification,
                    scope=f.scope,
                    resource_id=f.resource_id,
                )
            )

        sanitized_source = EvidenceSecuritySanitizer.sanitize(source_identity)
        sanitized_target = EvidenceSecuritySanitizer.sanitize(target_identity)

        artifact = EvidenceArtifact(
            artifact_id=art_id,
            artifact_type=artifact_type,
            migration_id=migration_id,
            run_id=run_id,
            job_id=job_id,
            source_identity=sanitized_source,
            target_identity=sanitized_target,
            provider_identity=provider_identity,
            plan_identity=plan_identity,
            validation_identity=validation_identity,
            cdc_boundary_position=cdc_boundary_position,
            fencing_epoch=fencing_epoch,
            created_at=time.time(),
            provenance_list=provenance_list,
            facts=sanitized_facts,
            completeness=completeness,
        )

        # Compute SHA-256 cryptographic digest over canonical payload
        artifact.digest = EvidenceDigestCalculator.compute_digest(artifact)

        with self._lock:
            self.evidence_artifacts_created_total += 1
            self.record_telemetry_metrics()

        return artifact

    def package_validation_evidence(
        self,
        migration_id: str,
        run_id: str,
        validation_result: Any,
        cdc_snapshot: Optional[Dict[str, Any]] = None,
        artifact_id: Optional[str] = None,
    ) -> EvidenceArtifact:
        """
        Packages physical truth from Authority #11 ValidationResult into an EvidenceArtifact.
        """
        now = time.time()
        prov = EvidenceProvenance(
            authority_name="Authority #11 Validation",
            component_id="ValidationAuthority",
            boundary_position=getattr(validation_result, "cdc_boundary_position", None),
            recorded_at=now,
        )

        val_dict = validation_result.to_dict() if hasattr(validation_result, "to_dict") else {}

        facts = [
            EvidenceFact("proof_scope", val_dict.get("proof_scope", "UNPROVEN"), "Authority #11 Validation", "METADATA", now),
            EvidenceFact("validation_gate", str(val_dict.get("validation_gate")), "Authority #11 Validation", "STATUS", now),
            EvidenceFact("rows_expected", val_dict.get("rows_expected", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("rows_validated", val_dict.get("rows_validated", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("rows_matched", val_dict.get("rows_matched", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("rows_mismatched", val_dict.get("rows_mismatched", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("rows_missing", val_dict.get("rows_missing", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("rows_extra", val_dict.get("rows_extra", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("duplicates", val_dict.get("duplicates", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("partitions_total", val_dict.get("partitions_total", 0), "Authority #11 Validation", "QUANTITATIVE", now),
            EvidenceFact("partitions_matched", val_dict.get("partitions_matched", 0), "Authority #11 Validation", "QUANTITATIVE", now),
        ]

        if cdc_snapshot:
            facts.append(EvidenceFact("cdc_open_transactions", cdc_snapshot.get("open_transactions", 0), "Authority #10 CDC", "QUANTITATIVE", now))
            facts.append(EvidenceFact("cdc_ambiguous_commits", cdc_snapshot.get("ambiguous_commit_count", 0), "Authority #10 CDC", "QUANTITATIVE", now))
            facts.append(EvidenceFact("cdc_backlog_events", cdc_snapshot.get("backlog_events", 0), "Authority #10 CDC", "QUANTITATIVE", now))

        # Evaluate completeness derived strictly from ValidationResult facts
        gate_str = str(val_dict.get("validation_gate"))
        status_str = str(val_dict.get("status"))
        scope_str = str(val_dict.get("proof_scope"))

        if status_str == "CANCELLED":
            completeness = EvidenceCompleteness.CANCELLED
        elif status_str == "FAILED" or gate_str in ("FAILED", "ValidationGateStatus.FAILED"):
            completeness = EvidenceCompleteness.FAILED
        elif scope_str in ("UNPROVEN", "SAMPLED", "STRUCTURE_ONLY", "COUNT_ONLY") or gate_str in ("WITHHELD", "ValidationGateStatus.WITHHELD"):
            completeness = EvidenceCompleteness.PARTIAL if scope_str == "SAMPLED" else EvidenceCompleteness.UNPROVEN
        elif gate_str in ("PASSED", "ValidationGateStatus.PASSED"):
            completeness = EvidenceCompleteness.COMPLETE
        else:
            completeness = EvidenceCompleteness.UNPROVEN

        return self.create_evidence_artifact(
            migration_id=migration_id,
            run_id=run_id,
            artifact_type="VALIDATION_EVIDENCE",
            facts=facts,
            provenance_list=[prov],
            artifact_id=artifact_id,
            plan_identity=getattr(validation_result, "validation_run_id", None),
            validation_identity=getattr(validation_result, "validation_run_id", None),
            cdc_boundary_position=getattr(validation_result, "cdc_boundary_position", None),
            completeness=completeness,
        )

    def package_cdc_evidence(
        self,
        migration_id: str,
        run_id: str,
        cdc_snapshot: Dict[str, Any],
        artifact_id: Optional[str] = None,
    ) -> EvidenceArtifact:
        """
        Packages physical truth from Authority #10 CDC snapshot into an EvidenceArtifact.
        """
        now = time.time()
        prov = EvidenceProvenance(
            authority_name="Authority #10 CDC",
            component_id="CDCBoundaryReconciler",
            boundary_position=cdc_snapshot.get("target_applied_position"),
            recorded_at=now,
        )

        facts = [
            EvidenceFact("target_applied_position", cdc_snapshot.get("target_applied_position"), "Authority #10 CDC", "POSITION", now),
            EvidenceFact("required_boundary_position", cdc_snapshot.get("required_boundary_position"), "Authority #10 CDC", "POSITION", now),
            EvidenceFact("open_transactions", cdc_snapshot.get("open_transactions", 0), "Authority #10 CDC", "QUANTITATIVE", now),
            EvidenceFact("ambiguous_commit_count", cdc_snapshot.get("ambiguous_commit_count", 0), "Authority #10 CDC", "QUANTITATIVE", now),
            EvidenceFact("backlog_events", cdc_snapshot.get("backlog_events", 0), "Authority #10 CDC", "QUANTITATIVE", now),
            EvidenceFact("synchronization_barrier_reached", cdc_snapshot.get("synchronization_barrier_reached", True), "Authority #10 CDC", "STATUS", now),
        ]

        completeness = EvidenceCompleteness.COMPLETE if (
            cdc_snapshot.get("open_transactions", 0) == 0 and
            cdc_snapshot.get("ambiguous_commit_count", 0) == 0 and
            cdc_snapshot.get("backlog_events", 0) == 0 and
            cdc_snapshot.get("synchronization_barrier_reached", True)
        ) else EvidenceCompleteness.FAILED

        return self.create_evidence_artifact(
            migration_id=migration_id,
            run_id=run_id,
            artifact_type="CDC_EVIDENCE",
            facts=facts,
            provenance_list=[prov],
            artifact_id=artifact_id,
            cdc_boundary_position=cdc_snapshot.get("target_applied_position"),
            completeness=completeness,
        )

    def package_execution_evidence(
        self,
        migration_id: str,
        run_id: str,
        execution_state: str,
        telemetry_snapshot: Optional[Dict[str, Any]] = None,
        artifact_id: Optional[str] = None,
        cdc_boundary_position: Optional[str] = None,
    ) -> EvidenceArtifact:
        """
        Packages physical runtime execution state & Authority #7 telemetry facts into an EvidenceArtifact.
        """
        now = time.time()
        prov = EvidenceProvenance(
            authority_name="Authority #6 Runtime",
            component_id="RuntimeAuthority",
            recorded_at=now,
        )

        facts = [
            EvidenceFact("execution_state", execution_state, "Authority #6 Runtime", "STATUS", now),
        ]

        if telemetry_snapshot:
            for k, v in telemetry_snapshot.items():
                facts.append(EvidenceFact(k, v, "Authority #7 Telemetry", "METRIC", now))

        completeness = EvidenceCompleteness.COMPLETE if execution_state in ("COMPLETED", "SUCCESS") else (
            EvidenceCompleteness.CANCELLED if execution_state == "CANCELLED" else EvidenceCompleteness.FAILED
        )

        return self.create_evidence_artifact(
            migration_id=migration_id,
            run_id=run_id,
            artifact_type="EXECUTION_EVIDENCE",
            facts=facts,
            provenance_list=[prov],
            artifact_id=artifact_id,
            cdc_boundary_position=cdc_boundary_position,
            completeness=completeness,
        )

    def create_manifest(
        self,
        migration_id: str,
        run_id: str,
        artifacts: List[EvidenceArtifact],
        manifest_id: Optional[str] = None,
    ) -> EvidenceManifest:
        """
        Binds related EvidenceArtifacts into a single deterministic EvidenceManifest bundle.
        Sorts contained artifacts deterministically by artifact_id for non-semantic manifest equality.
        """
        man_id = manifest_id or f"evd-man-{time.time_ns()}"

        # Verify identity matching across all contained artifacts
        for art in artifacts:
            if art.migration_id != migration_id or art.run_id != run_id:
                raise EvidenceIdentityError(f"Artifact '{art.artifact_id}' identity mismatch: artifact ({art.migration_id}/{art.run_id}) vs manifest ({migration_id}/{run_id})!")

        sorted_artifacts = sorted(artifacts, key=lambda a: a.artifact_id)

        all_complete = len(sorted_artifacts) > 0 and all(a.completeness == EvidenceCompleteness.COMPLETE for a in sorted_artifacts)
        any_failed = any(a.completeness == EvidenceCompleteness.FAILED for a in sorted_artifacts)
        any_cancelled = any(a.completeness == EvidenceCompleteness.CANCELLED for a in sorted_artifacts)

        if any_failed:
            overall = EvidenceCompleteness.FAILED
        elif any_cancelled:
            overall = EvidenceCompleteness.CANCELLED
        elif all_complete:
            overall = EvidenceCompleteness.COMPLETE
        else:
            overall = EvidenceCompleteness.UNPROVEN

        manifest = EvidenceManifest(
            manifest_id=man_id,
            migration_id=migration_id,
            run_id=run_id,
            created_at=time.time(),
            artifacts=sorted_artifacts,
            completeness=overall,
        )

        manifest.manifest_digest = EvidenceDigestCalculator.compute_digest(manifest)
        return manifest

    def verify_artifact(
        self,
        artifact: EvidenceArtifact,
        expected_migration_id: Optional[str] = None,
        expected_run_id: Optional[str] = None,
        required_cdc_boundary_position: Optional[str] = None,
        required_proof_categories: Optional[Union[List[str], Any]] = None,
    ) -> EvidenceVerificationResult:
        """Verifies digest integrity, identity, and CDC boundary freshness of an EvidenceArtifact."""
        res = EvidenceVerificationEngine.verify_artifact(
            artifact=artifact,
            expected_migration_id=expected_migration_id,
            expected_run_id=expected_run_id,
            required_cdc_boundary_position=required_cdc_boundary_position,
            required_proof_categories=required_proof_categories,
        )
        if not res.is_valid:
            with self._lock:
                self.evidence_verification_failures_total += 1
                self.record_telemetry_metrics()
        return res

    def verify_manifest(
        self,
        manifest: EvidenceManifest,
        expected_migration_id: Optional[str] = None,
        expected_run_id: Optional[str] = None,
        required_cdc_boundary_position: Optional[str] = None,
        required_proof_categories: Optional[Union[List[str], Any]] = None,
    ) -> EvidenceVerificationResult:
        """Verifies digest integrity, artifact binding, and completeness of an EvidenceManifest."""
        res = EvidenceVerificationEngine.verify_manifest(
            manifest=manifest,
            expected_migration_id=expected_migration_id,
            expected_run_id=expected_run_id,
            required_cdc_boundary_position=required_cdc_boundary_position,
            required_proof_categories=required_proof_categories,
        )
        if not res.is_valid:
            with self._lock:
                self.evidence_verification_failures_total += 1
                self.record_telemetry_metrics()
        return res

    def persist_evidence(
        self,
        evidence_obj: Union[EvidenceArtifact, EvidenceManifest],
        fencing_token: Optional[Any] = None,
    ) -> str:
        """
        Durably persists an EvidenceArtifact or EvidenceManifest through Authority #5 Durability SPI.
        """
        if self.durability_authority and hasattr(self.durability_authority, "verify_fencing_token"):
            if fencing_token and not self.durability_authority.verify_fencing_token(fencing_token):
                with self._lock:
                    self.evidence_persistence_failures_total += 1
                    self.record_telemetry_metrics()
                raise EvidenceFencingError("Stale fencing token rejected during evidence persistence by Authority #5!")

        if isinstance(evidence_obj, EvidenceArtifact):
            key = f"evd_art_{evidence_obj.artifact_id}_{evidence_obj.migration_id}"
            payload = evidence_obj.to_dict(include_digest=True)
        elif isinstance(evidence_obj, EvidenceManifest):
            key = f"evd_man_{evidence_obj.manifest_id}_{evidence_obj.migration_id}"
            payload = evidence_obj.to_dict(include_digest=True)
        else:
            raise EvidenceVerificationError("Unsupported evidence object type for persistence!")

        if self.durability_authority and hasattr(self.durability_authority, "save_spill_frame"):
            self.durability_authority.save_spill_frame("evidence", key, payload)

        return key

    def reload_evidence(
        self,
        evidence_key: str,
        expected_migration_id: Optional[str] = None,
    ) -> Union[EvidenceArtifact, EvidenceManifest]:
        """
        Reloads and verifies a previously persisted evidence frame from Authority #5 Durability SPI.
        """
        if not self.durability_authority or not hasattr(self.durability_authority, "load_spill_frame"):
            raise EvidenceVerificationError("Durability Authority (#5) unavailable for evidence reload!")

        payload = self.durability_authority.load_spill_frame("evidence", evidence_key)
        if not payload:
            raise EvidenceVerificationError(f"Evidence key '{evidence_key}' not found in durability store!")

        if "artifact_id" in payload:
            art = EvidenceArtifact(
                artifact_id=payload["artifact_id"],
                artifact_type=payload.get("artifact_type", "UNKNOWN"),
                migration_id=payload.get("migration_id", ""),
                run_id=payload.get("run_id", ""),
                artifact_version=payload.get("artifact_version", "1.0"),
                job_id=payload.get("job_id"),
                source_identity=payload.get("source_identity"),
                target_identity=payload.get("target_identity"),
                provider_identity=payload.get("provider_identity"),
                plan_identity=payload.get("plan_identity"),
                validation_identity=payload.get("validation_identity"),
                cdc_boundary_position=payload.get("cdc_boundary_position"),
                fencing_epoch=payload.get("fencing_epoch"),
                created_at=payload.get("created_at", 0.0),
                completeness=EvidenceCompleteness(payload.get("completeness", "UNPROVEN")),
            )
            for p in payload.get("provenance_list", []):
                art.provenance_list.append(
                    EvidenceProvenance(
                        authority_name=p.get("authority_name", ""),
                        component_id=p.get("component_id", ""),
                        boundary_position=p.get("boundary_position"),
                        fencing_epoch=p.get("fencing_epoch"),
                        recorded_at=p.get("recorded_at", 0.0),
                    )
                )
            for f in payload.get("facts", []):
                art.facts.append(
                    EvidenceFact(
                        fact_key=f.get("fact_key", ""),
                        fact_value=f.get("fact_value"),
                        originating_authority=f.get("originating_authority", ""),
                        fact_type=f.get("fact_type", ""),
                        observed_at=f.get("observed_at", 0.0),
                        proof_classification=ProofClassification(f.get("proof_classification", "UNIT_PROVEN")),
                        scope=f.get("scope"),
                        resource_id=f.get("resource_id"),
                    )
                )

            if "digest" in payload and payload["digest"]:
                d = payload["digest"]
                art.digest = EvidenceDigest(
                    algorithm=d.get("algorithm", "SHA-256"),
                    canonical_bytes_len=d.get("canonical_bytes_len", 0),
                    digest_hex=d.get("digest_hex", ""),
                    digital_signature_supported=d.get("digital_signature_supported", False),
                    digital_signature_status=d.get("digital_signature_status", "DIGEST_INTEGRITY_ONLY"),
                )

            res = self.verify_artifact(art, expected_migration_id=expected_migration_id)
            if not res.is_valid and res.tamper_detected:
                raise EvidenceIntegrityError(f"Reloaded evidence artifact '{art.artifact_id}' failed digest integrity verification!")
            if expected_migration_id and art.migration_id != expected_migration_id:
                raise EvidenceIdentityError(f"Reloaded evidence artifact migration identity '{art.migration_id}' mismatch with expected '{expected_migration_id}'!")
            return art

        elif "manifest_id" in payload:
            artifacts_list = []
            for art_payload in payload.get("artifacts", []):
                art = EvidenceArtifact(
                    artifact_id=art_payload["artifact_id"],
                    artifact_type=art_payload.get("artifact_type", "UNKNOWN"),
                    migration_id=art_payload.get("migration_id", ""),
                    run_id=art_payload.get("run_id", ""),
                    artifact_version=art_payload.get("artifact_version", "1.0"),
                    job_id=art_payload.get("job_id"),
                    source_identity=art_payload.get("source_identity"),
                    target_identity=art_payload.get("target_identity"),
                    provider_identity=art_payload.get("provider_identity"),
                    plan_identity=art_payload.get("plan_identity"),
                    validation_identity=art_payload.get("validation_identity"),
                    cdc_boundary_position=art_payload.get("cdc_boundary_position"),
                    fencing_epoch=art_payload.get("fencing_epoch"),
                    created_at=art_payload.get("created_at", 0.0),
                    completeness=EvidenceCompleteness(art_payload.get("completeness", "UNPROVEN")),
                )
                for p in art_payload.get("provenance_list", []):
                    art.provenance_list.append(
                        EvidenceProvenance(
                            authority_name=p.get("authority_name", ""),
                            component_id=p.get("component_id", ""),
                            boundary_position=p.get("boundary_position"),
                            fencing_epoch=p.get("fencing_epoch"),
                            recorded_at=p.get("recorded_at", 0.0),
                        )
                    )
                for f in art_payload.get("facts", []):
                    art.facts.append(
                        EvidenceFact(
                            fact_key=f.get("fact_key", ""),
                            fact_value=f.get("fact_value"),
                            originating_authority=f.get("originating_authority", ""),
                            fact_type=f.get("fact_type", ""),
                            observed_at=f.get("observed_at", 0.0),
                            proof_classification=ProofClassification(f.get("proof_classification", "UNIT_PROVEN")),
                            scope=f.get("scope"),
                            resource_id=f.get("resource_id"),
                        )
                    )
                if "digest" in art_payload and art_payload["digest"]:
                    d = art_payload["digest"]
                    art.digest = EvidenceDigest(
                        algorithm=d.get("algorithm", "SHA-256"),
                        canonical_bytes_len=d.get("canonical_bytes_len", 0),
                        digest_hex=d.get("digest_hex", ""),
                        digital_signature_supported=d.get("digital_signature_supported", False),
                        digital_signature_status=d.get("digital_signature_status", "DIGEST_INTEGRITY_ONLY"),
                    )
                artifacts_list.append(art)

            man = EvidenceManifest(
                manifest_id=payload["manifest_id"],
                migration_id=payload.get("migration_id", ""),
                run_id=payload.get("run_id", ""),
                created_at=payload.get("created_at", 0.0),
                artifacts=artifacts_list,
                completeness=EvidenceCompleteness(payload.get("completeness", "UNPROVEN")),
            )

            if "manifest_digest" in payload and payload["manifest_digest"]:
                d = payload["manifest_digest"]
                man.manifest_digest = EvidenceDigest(
                    algorithm=d.get("algorithm", "SHA-256"),
                    canonical_bytes_len=d.get("canonical_bytes_len", 0),
                    digest_hex=d.get("digest_hex", ""),
                    digital_signature_supported=d.get("digital_signature_supported", False),
                    digital_signature_status=d.get("digital_signature_status", "DIGEST_INTEGRITY_ONLY"),
                )

            res = self.verify_manifest(man, expected_migration_id=expected_migration_id)
            if not res.is_valid and res.tamper_detected:
                raise EvidenceIntegrityError(f"Reloaded evidence manifest '{man.manifest_id}' failed digest integrity verification!")
            if expected_migration_id and man.migration_id != expected_migration_id:
                raise EvidenceIdentityError(f"Reloaded evidence manifest migration identity '{man.migration_id}' mismatch with expected '{expected_migration_id}'!")
            return man

        else:
            raise EvidenceVerificationError("Unrecognized evidence payload structure in durability store!")
