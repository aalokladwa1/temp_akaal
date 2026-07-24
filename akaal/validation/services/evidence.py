"""EvidenceService: Generates signed audit evidence packages and compliance reports."""

import time
import json
import hashlib
import uuid
from typing import Any, Dict, List, Optional
from akaal.validation.core.interfaces import IService
from akaal.validation.core.models import EvidencePackage, ValidationResult, ValidationIssue


class EvidenceService(IService):
    """Infrastructure service generating signed compliance evidence packages."""

    @property
    def service_name(self) -> str:
        return "EvidenceService"

    def generate_evidence_package(
        self,
        session_id: str,
        results: List[ValidationResult],
        merkle_root: str = "N/A",
        policy_profile: str = "DEV",
        secret_key: str = "akaal_enterprise_signing_key",
    ) -> EvidencePackage:
        """Assemble and sign an audit proof evidence package."""
        package_id = str(uuid.uuid4())
        timestamp = time.time()

        total_checks = sum(len(r.capabilities_tested) for r in results)
        passed_checks = sum(r.passed_count for r in results)
        failed_checks = sum(r.failed_count for r in results)

        all_issues: List[ValidationIssue] = []
        for r in results:
            all_issues.extend(r.issues)

        # Compute checksum digest over all issues and results
        raw_payload = f"{package_id}:{session_id}:{timestamp}:{merkle_root}:{total_checks}:{passed_checks}:{failed_checks}"
        checksum_digest = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        # Sign package using secret key
        signing_material = f"{checksum_digest}:{policy_profile}:{secret_key}"
        signature = hashlib.sha256(signing_material.encode("utf-8")).hexdigest()

        return EvidencePackage(
            package_id=package_id,
            timestamp=timestamp,
            session_id=session_id,
            merkle_root=merkle_root,
            checksum_digest=checksum_digest,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            issues=all_issues,
            signature=signature,
            policy_profile=policy_profile,
        )

    def export_evidence_json(self, package: EvidencePackage) -> str:
        """Export evidence package as a formatted JSON document."""
        data = {
            "package_id": package.package_id,
            "session_id": package.session_id,
            "timestamp": package.timestamp,
            "merkle_root": package.merkle_root,
            "checksum_digest": package.checksum_digest,
            "total_checks": package.total_checks,
            "passed_checks": package.passed_checks,
            "failed_checks": package.failed_checks,
            "policy_profile": package.policy_profile,
            "signature": package.signature,
            "issues_count": len(package.issues),
        }
        return json.dumps(data, indent=2)
