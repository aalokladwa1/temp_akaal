"""
akaalEngine.evidence.verification
=================================
EvidenceVerificationEngine for Authority #12.
Performs deterministic mechanical verification of artifact digest integrity, identity binding,
CDC boundary freshness, manifest consistency, and context-sensitive proof completeness.
"""

import logging
from typing import List, Optional, Set, Tuple, Union

from akaalEngine.evidence.canonical import EvidenceDigestCalculator
from akaalEngine.evidence.models.artifact import (
    EvidenceArtifact,
    EvidenceCompleteness,
    EvidenceManifest,
    EvidenceVerificationResult,
)

logger = logging.getLogger("akaalEngine.evidence.verification")


class EvidenceVerificationEngine:
    """
    Evaluates evidence artifact & manifest integrity without rerunning migration work.
    Supports context-sensitive verification where requested verification contexts specify
    mandatory machine-proof categories (e.g. 'execution', 'validation', 'cdc', 'durability', 'transport').
    """

    @classmethod
    def verify_artifact(
        cls,
        artifact: EvidenceArtifact,
        expected_migration_id: Optional[str] = None,
        expected_run_id: Optional[str] = None,
        required_cdc_boundary_position: Optional[str] = None,
        required_proof_categories: Optional[Union[List[str], Set[str]]] = None,
    ) -> EvidenceVerificationResult:
        """
        Verifies a single EvidenceArtifact.
        Checks digest integrity, identity binding, CDC boundary freshness, and required proof categories.
        """
        reasons: List[str] = []
        tamper_detected = False
        boundary_fresh = True

        req_categories = set(required_proof_categories) if required_proof_categories else set()

        # 1. Identity Binding Check
        if expected_migration_id and artifact.migration_id != expected_migration_id:
            reasons.append(f"Migration identity mismatch: expected '{expected_migration_id}', got '{artifact.migration_id}'")

        if expected_run_id and artifact.run_id != expected_run_id:
            reasons.append(f"Run identity mismatch: expected '{expected_run_id}', got '{artifact.run_id}'")

        # 2. Cryptographic Digest Integrity Check
        if not artifact.digest or not artifact.digest.digest_hex:
            reasons.append("Evidence artifact lacks cryptographic digest!")
            tamper_detected = True
        else:
            recalculated = EvidenceDigestCalculator.compute_digest(artifact)
            if recalculated.digest_hex != artifact.digest.digest_hex:
                reasons.append(f"Digest integrity mismatch! Recorded '{artifact.digest.digest_hex}', recalculated '{recalculated.digest_hex}'")
                tamper_detected = True

        # 3. CDC Boundary Freshness Check
        if required_cdc_boundary_position:
            if not artifact.cdc_boundary_position:
                reasons.append(f"Artifact lacks CDC boundary position; cannot satisfy required boundary '{required_cdc_boundary_position}'!")
                boundary_fresh = False
            elif artifact.cdc_boundary_position < required_cdc_boundary_position:
                reasons.append(f"Stale CDC boundary evidence: artifact boundary '{artifact.cdc_boundary_position}' is behind required boundary '{required_cdc_boundary_position}'!")
                boundary_fresh = False

        # 4. Mandatory Proof Context Checks
        if "validation" in req_categories:
            if artifact.artifact_type != "VALIDATION_EVIDENCE" and not any(f.originating_authority == "Authority #11 Validation" for f in artifact.facts):
                reasons.append("Mandatory validation evidence proof absent for requested verification context!")

        if "cdc" in req_categories:
            if artifact.artifact_type != "CDC_EVIDENCE" and not any(f.originating_authority == "Authority #10 CDC" for f in artifact.facts):
                reasons.append("Mandatory CDC evidence proof absent for requested verification context!")

        if "execution" in req_categories:
            if artifact.artifact_type != "EXECUTION_EVIDENCE" and not any(f.originating_authority == "Authority #6 Runtime" for f in artifact.facts):
                reasons.append("Mandatory execution evidence proof absent for requested verification context!")

        # 5. Determine Validity & Truthful Effective Completeness
        is_valid = (len(reasons) == 0) and (artifact.completeness == EvidenceCompleteness.COMPLETE)

        if is_valid:
            effective_completeness = EvidenceCompleteness.COMPLETE
        elif artifact.completeness == EvidenceCompleteness.CANCELLED:
            effective_completeness = EvidenceCompleteness.CANCELLED
        elif artifact.completeness == EvidenceCompleteness.PARTIAL:
            effective_completeness = EvidenceCompleteness.PARTIAL
        elif not boundary_fresh or any("Mandatory" in r for r in reasons):
            effective_completeness = EvidenceCompleteness.UNPROVEN
        else:
            effective_completeness = EvidenceCompleteness.FAILED

        if not is_valid:
            logger.warning(f"Evidence Artifact Verification FAILED: {reasons}")

        return EvidenceVerificationResult(
            is_valid=is_valid,
            migration_id=artifact.migration_id,
            run_id=artifact.run_id,
            completeness=effective_completeness,
            verified_artifact_count=1 if is_valid else 0,
            tamper_detected=tamper_detected,
            boundary_fresh=boundary_fresh,
            reasons=reasons,
        )

    @classmethod
    def verify_manifest(
        cls,
        manifest: EvidenceManifest,
        expected_migration_id: Optional[str] = None,
        expected_run_id: Optional[str] = None,
        required_cdc_boundary_position: Optional[str] = None,
        required_proof_categories: Optional[Union[List[str], Set[str]]] = None,
    ) -> EvidenceVerificationResult:
        """
        Verifies an EvidenceManifest and all contained EvidenceArtifact objects against requested proof categories.
        Detects missing mandatory proof categories, extra/substituted artifacts, digest mismatches, and boundary staleness.
        """
        reasons: List[str] = []
        tamper_detected = False
        boundary_fresh = True
        verified_count = 0

        req_categories = set(required_proof_categories) if required_proof_categories else set()

        # 1. Identity Binding Check
        if expected_migration_id and manifest.migration_id != expected_migration_id:
            reasons.append(f"Manifest migration identity mismatch: expected '{expected_migration_id}', got '{manifest.migration_id}'")

        if expected_run_id and manifest.run_id != expected_run_id:
            reasons.append(f"Manifest run identity mismatch: expected '{expected_run_id}', got '{manifest.run_id}'")

        # 2. Manifest Cryptographic Digest Check
        if not manifest.manifest_digest or not manifest.manifest_digest.digest_hex:
            reasons.append("Evidence manifest lacks cryptographic digest!")
            tamper_detected = True
        else:
            recalculated = EvidenceDigestCalculator.compute_digest(manifest)
            if recalculated.digest_hex != manifest.manifest_digest.digest_hex:
                reasons.append(f"Manifest digest integrity mismatch! Recorded '{manifest.manifest_digest.digest_hex}', recalculated '{recalculated.digest_hex}'")
                tamper_detected = True

        # 3. Mandatory Proof Categories Presence Check across Manifest Bundle
        contained_types = {art.artifact_type for art in manifest.artifacts}
        contained_authorities = {f.originating_authority for art in manifest.artifacts for f in art.facts}

        if "validation" in req_categories:
            if "VALIDATION_EVIDENCE" not in contained_types and "Authority #11 Validation" not in contained_authorities:
                reasons.append("Mandatory validation evidence artifact missing from manifest bundle!")

        if "cdc" in req_categories:
            if "CDC_EVIDENCE" not in contained_types and "Authority #10 CDC" not in contained_authorities:
                reasons.append("Mandatory CDC evidence artifact missing from manifest bundle!")

        if "execution" in req_categories:
            if "EXECUTION_EVIDENCE" not in contained_types and "Authority #6 Runtime" not in contained_authorities:
                reasons.append("Mandatory execution evidence artifact missing from manifest bundle!")

        # 4. Contained Artifacts Verification & Duplicate Identity Detection
        seen_artifact_ids = set()
        for art in manifest.artifacts:
            if art.artifact_id in seen_artifact_ids:
                reasons.append(f"Duplicate artifact identity '{art.artifact_id}' detected in manifest!")
                tamper_detected = True
            seen_artifact_ids.add(art.artifact_id)

            art_res = cls.verify_artifact(
                artifact=art,
                expected_migration_id=manifest.migration_id,
                expected_run_id=manifest.run_id,
                required_cdc_boundary_position=required_cdc_boundary_position,
            )
            if not art_res.is_valid:
                reasons.extend([f"Artifact '{art.artifact_id}': {r}" for r in art_res.reasons])
                if art_res.tamper_detected:
                    tamper_detected = True
                if not art_res.boundary_fresh:
                    boundary_fresh = False
            else:
                verified_count += 1

        is_valid = (len(reasons) == 0) and (manifest.completeness == EvidenceCompleteness.COMPLETE)

        if is_valid:
            effective_completeness = EvidenceCompleteness.COMPLETE
        elif manifest.completeness == EvidenceCompleteness.CANCELLED:
            effective_completeness = EvidenceCompleteness.CANCELLED
        elif manifest.completeness == EvidenceCompleteness.PARTIAL:
            effective_completeness = EvidenceCompleteness.PARTIAL
        elif not boundary_fresh or any("Mandatory" in r for r in reasons):
            effective_completeness = EvidenceCompleteness.UNPROVEN
        else:
            effective_completeness = EvidenceCompleteness.FAILED

        return EvidenceVerificationResult(
            is_valid=is_valid,
            migration_id=manifest.migration_id,
            run_id=manifest.run_id,
            completeness=effective_completeness,
            verified_artifact_count=verified_count,
            tamper_detected=tamper_detected,
            boundary_fresh=boundary_fresh,
            reasons=reasons,
        )
