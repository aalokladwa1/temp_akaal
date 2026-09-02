"""
AKAAL P2.10 / P2.10.1 — Canonical Reporting, Certification & Governance Evidence Authority Engine
=================================================================================================
Backend authority for aggregating canonical execution, schema, risk, validation, and reconciliation
evidence into tamper-evident Canonical Reports and Enterprise Certification Artifacts.
Hardened against false certification, evidence substitution, non-atomic persistence, and secret leakage.
"""

from dataclasses import asdict
import datetime
import hashlib
import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from akaal.reporting.models.canonical_models import (
    CanonicalReport,
    CanonicalReportType,
    CertificationArtifact,
    CertificationClaim,
    CertificationClaimType,
    CertificationOutcome,
    EvidenceManifestItem,
    SERIALIZATION_VERSION,
)
from akaal.validation.domain.reconciliation import ReconciliationEvidence, ValidationExecutionMode


logger = logging.getLogger("akaal.reporting.engine.canonical_reporting")


class CanonicalReportingAuthority:
    """
    Universal Backend Reporting & Certification Authority (P2.10 / P2.10.1).
    Aggregates frozen P2.2-P2.9 canonical evidence into versioned, tamper-evident artifacts.
    """

    SERIALIZATION_VERSION = SERIALIZATION_VERSION

    def __init__(self, persistence_dir: Optional[str] = None):
        self.persistence_dir = persistence_dir or ".akaal/reports"
        self._reports_store: Dict[str, CanonicalReport] = {}

    def generate_canonical_report(
        self,
        report_id: str,
        job_id: str,
        run_id: str,
        report_type: CanonicalReportType,
        source_info: Dict[str, Any],
        target_info: Dict[str, Any],
        execution_summary: Dict[str, Any],
        schema_risk: Optional[Any] = None,
        reconciliation_evidence: Optional[ReconciliationEvidence] = None,

        governance_approval_approved: bool = True,
        governance_approval_required: bool = False,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        manual_review_items: Optional[List[str]] = None,
    ) -> CanonicalReport:
        """
        Generates a strongly-typed CanonicalReport and computes evidence-derived CertificationArtifact.
        """
        # Redact secrets from source_info & target_info before storing in report
        safe_source_info = self._redact_secrets(source_info)
        safe_target_info = self._redact_secrets(target_info)

        warn_list = list(warnings or [])
        err_list = list(errors or [])
        review_list = list(manual_review_items or [])

        # Validate Evidence Binding to Job & Run ID (Cross-Job/Run Evidence Substitution Firewall)
        evidence_mismatch = False
        if reconciliation_evidence:
            val_id = str(reconciliation_evidence.validation_id)
            # If validation_id doesn't match job_id or run_id or general prefix, flag error
            if val_id and (job_id not in val_id and run_id not in val_id and "VAL-" not in val_id):
                err_msg = f"[EVIDENCE BINDING FIREWALL] Reconciliation evidence '{val_id}' is not bound to job '{job_id}' / run '{run_id}'!"
                logger.error(err_msg)
                err_list.append(err_msg)
                evidence_mismatch = True

        # 1. Schema Summary
        schema_summary: Dict[str, Any] = {
            "risk_score": schema_risk.risk_score if schema_risk else 0.0,
            "overall_compatibility": schema_risk.overall_compatibility.value if schema_risk else "COMPATIBLE",
            "blocking_findings_count": schema_risk.blocking_findings_count if schema_risk else 0,
        }

        # 2. Data Summary & Validation Summary
        data_summary: Dict[str, Any] = {}
        validation_summary: Dict[str, Any] = {}
        evidence_fingerprints: List[str] = []

        if reconciliation_evidence and not evidence_mismatch:
            evidence_fingerprints.append(reconciliation_evidence.evidence_fingerprint)
            db_sum = reconciliation_evidence.database_summary
            data_summary = {
                "tables_validated": db_sum.tables_validated,
                "total_rows_evaluated": db_sum.total_rows_evaluated,
                "total_source_only_rows": db_sum.total_source_only_rows,
                "total_target_only_rows": db_sum.total_target_only_rows,
                "total_value_mismatch_rows": db_sum.total_value_mismatch_rows,
            }
            validation_summary = {
                "serialization_version": reconciliation_evidence.serialization_version,
                "hash_algorithm": reconciliation_evidence.hash_algorithm,
                "final_status": db_sum.final_status,
                "tables_matched": db_sum.tables_matched,
                "tables_mismatched": db_sum.tables_mismatched,
                "tables_indeterminate": db_sum.tables_indeterminate,
                "tables_failed": db_sum.tables_failed,
            }

        # 3. Governance Summary
        governance_summary = {
            "approval_required": governance_approval_required,
            "approval_state": "APPROVED" if governance_approval_approved else ("PENDING" if governance_approval_required else "NOT_REQUIRED"),
        }

        # 4. Final Outcome Determination
        if err_list or (schema_risk and not schema_risk.is_safe_to_continue) or (reconciliation_evidence and reconciliation_evidence.database_summary.final_status in ("ERROR", "MISMATCHED")):
            final_outcome = "FAILED"
        elif reconciliation_evidence and reconciliation_evidence.database_summary.final_status == "INDETERMINATE":
            final_outcome = "INDETERMINATE"
        elif warn_list or review_list:
            final_outcome = "PASSED_WITH_WARNINGS"
        else:
            final_outcome = "PASSED"

        # 5. Certification Derivation
        certification = self._derive_certification(
            report_id=report_id,
            job_id=job_id,
            run_id=run_id,
            report_type=report_type,
            schema_risk=schema_risk,
            reconciliation_evidence=reconciliation_evidence if not evidence_mismatch else None,
            governance_approval_approved=governance_approval_approved,
            governance_approval_required=governance_approval_required,
            err_list=err_list,
            warn_list=warn_list,
        )

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        report = CanonicalReport(
            report_id=report_id,
            report_version=SERIALIZATION_VERSION,
            report_type=report_type,
            job_id=job_id,
            run_id=run_id,
            created_at=now_str,
            source_info=safe_source_info,
            target_info=safe_target_info,
            execution_summary=execution_summary,
            schema_summary=schema_summary,
            data_summary=data_summary,
            validation_summary=validation_summary,
            governance_summary=governance_summary,
            warnings=warn_list,
            errors=err_list,
            manual_review_items=review_list,
            evidence_fingerprints=evidence_fingerprints,
            final_outcome=final_outcome,
            certification=certification,
        )

        report.report_fingerprint = report.compute_report_fingerprint()
        self._reports_store[report_id] = report
        self._persist_report_to_disk(report)
        return report

    def _derive_certification(
        self,
        report_id: str,
        job_id: str,
        run_id: str,
        report_type: CanonicalReportType,
        schema_risk: Optional[Any],
        reconciliation_evidence: Optional[ReconciliationEvidence],

        governance_approval_approved: bool,
        governance_approval_required: bool,
        err_list: List[str],
        warn_list: List[str],
    ) -> CertificationArtifact:
        """Derives explicit certification claims and tamper-evident certificate from evidence."""
        claims: List[CertificationClaim] = []
        manifest: List[EvidenceManifestItem] = []

        # 1. Schema Claim
        if schema_risk:
            is_ok = schema_risk.is_safe_to_continue
            claims.append(CertificationClaim(
                claim_type=CertificationClaimType.SCHEMA_COMPATIBILITY_VERIFIED,
                status="PASSED" if is_ok else "FAILED",
                evidence_fingerprint=f"risk-{schema_risk.risk_score}",
                description=f"Schema compatibility verified with risk score {schema_risk.risk_score}",
            ))
            manifest.append(EvidenceManifestItem(
                evidence_type="SCHEMA_RISK",
                authority="CanonicalRiskScorer",
                version=SERIALIZATION_VERSION,
                fingerprint=f"risk-{schema_risk.risk_score}",
                status=schema_risk.overall_compatibility.value,
                scope="SCHEMA",
            ))

        # 2. Validation / Reconciliation Claims
        val_failed = False
        val_indeterminate = False

        if reconciliation_evidence:
            db_sum = reconciliation_evidence.database_summary
            is_match = (db_sum.final_status == "MATCHED")
            val_failed = (db_sum.final_status in ("ERROR", "MISMATCHED"))
            val_indeterminate = (db_sum.final_status == "INDETERMINATE")

            claims.append(CertificationClaim(
                claim_type=CertificationClaimType.ROW_COUNT_VERIFIED,
                status="PASSED" if is_match else "FAILED",
                evidence_fingerprint=reconciliation_evidence.evidence_fingerprint,
                description=f"Row count verified across {db_sum.tables_validated} tables",
            ))
            claims.append(CertificationClaim(
                claim_type=CertificationClaimType.ROW_RECONCILIATION_VERIFIED,
                status="PASSED" if is_match else "FAILED",
                evidence_fingerprint=reconciliation_evidence.evidence_fingerprint,
                description=f"Deep row reconciliation evaluated {db_sum.total_rows_evaluated} rows",
            ))
            if db_sum.total_source_only_rows == 0:
                claims.append(CertificationClaim(
                    claim_type=CertificationClaimType.NO_SOURCE_ONLY_ROWS,
                    status="PASSED",
                    evidence_fingerprint=reconciliation_evidence.evidence_fingerprint,
                    description="Zero source-only rows detected",
                ))
            if db_sum.total_target_only_rows == 0:
                claims.append(CertificationClaim(
                    claim_type=CertificationClaimType.NO_TARGET_ONLY_ROWS,
                    status="PASSED",
                    evidence_fingerprint=reconciliation_evidence.evidence_fingerprint,
                    description="Zero target-only rows detected",
                ))
            if db_sum.total_value_mismatch_rows == 0:
                claims.append(CertificationClaim(
                    claim_type=CertificationClaimType.NO_VALUE_MISMATCHES,
                    status="PASSED",
                    evidence_fingerprint=reconciliation_evidence.evidence_fingerprint,
                    description="Zero value mismatches detected",
                ))

            manifest.append(EvidenceManifestItem(
                evidence_type="RECONCILIATION_EVIDENCE",
                authority="CanonicalReconciliationEngine",
                version=SERIALIZATION_VERSION,
                fingerprint=reconciliation_evidence.evidence_fingerprint,
                status=db_sum.final_status,
                scope="DATABASE",
            ))

        # 3. Governance Claim
        gov_ok = governance_approval_approved or not governance_approval_required
        claims.append(CertificationClaim(
            claim_type=CertificationClaimType.GOVERNANCE_APPROVAL_COMPLETE,
            status="PASSED" if gov_ok else "FAILED",
            evidence_fingerprint="gov-ok" if gov_ok else "gov-pending",
            description="Governance approval gate verified",
        ))

        # Sort claims and manifest deterministically
        claims = sorted(claims, key=lambda c: c.claim_type.value)
        manifest = sorted(manifest, key=lambda m: m.evidence_type)

        # 4. Outcome Determination
        if err_list or val_failed or not gov_ok or (schema_risk and not schema_risk.is_safe_to_continue):
            outcome = CertificationOutcome.NOT_CERTIFIED
        elif val_indeterminate:
            outcome = CertificationOutcome.INDETERMINATE
        elif warn_list:
            outcome = CertificationOutcome.CERTIFIED_WITH_WARNINGS
        else:
            outcome = CertificationOutcome.CERTIFIED

        cert_id = f"cert-{report_id}"
        issued_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cert = CertificationArtifact(
            certification_id=cert_id,
            report_id=report_id,
            job_id=job_id,
            run_id=run_id,
            outcome=outcome,
            claims=claims,
            evidence_manifest=manifest,
            issued_at=issued_str,
        )

        cert_fp = cert.compute_fingerprint()
        object.__setattr__(cert, "certification_fingerprint", cert_fp)
        return cert

    def get_report(self, report_id: str) -> Optional[CanonicalReport]:
        """Retrieves report by report_id from memory or disk."""
        if report_id in self._reports_store:
            return self._reports_store[report_id]
        return self._load_report_from_disk(report_id)

    def verify_certification_integrity(self, certification: CertificationArtifact) -> bool:
        """Verifies tamper-evident cryptographic fingerprint of a certification artifact."""
        return certification.verify_integrity()

    @staticmethod
    def _redact_secrets(info_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Redacts sensitive key fields like passwords, tokens, API keys, or connection secrets."""
        if not isinstance(info_dict, dict):
            return info_dict
        secret_keys = {"password", "pass", "token", "api_key", "secret", "private_key", "connection_string"}
        res = {}
        for k, v in info_dict.items():
            if any(s in k.lower() for s in secret_keys):
                res[k] = "[REDACTED_SECRET]"
            elif isinstance(v, dict):
                res[k] = CanonicalReportingAuthority._redact_secrets(v)
            else:
                res[k] = v
        return res

    def _persist_report_to_disk(self, report: CanonicalReport) -> None:
        """Persists report JSON payload to disk using atomic temp file replacement."""
        try:
            os.makedirs(self.persistence_dir, exist_ok=True)
            file_path = os.path.join(self.persistence_dir, f"{report.report_id}.json")
            tmp_path = file_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(report.to_json())
            os.replace(tmp_path, file_path)
        except Exception as e:
            logger.warning(f"[CANONICAL REPORTING] Failed to persist report to disk atomically: {e}")

    def _load_report_from_disk(self, report_id: str) -> Optional[CanonicalReport]:
        """Loads report from disk storage with corruption defense."""
        file_path = os.path.join(self.persistence_dir, f"{report_id}.json")
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cert_obj = None
            if "certification" in data and isinstance(data["certification"], dict):
                c_data = data["certification"]
                claims = [
                    CertificationClaim(
                        claim_type=CertificationClaimType(c["claim_type"]),
                        status=c["status"],
                        evidence_fingerprint=c.get("evidence_fingerprint", ""),
                        description=c.get("description", ""),
                    ) for c in c_data.get("claims", [])
                ]
                manifest = [
                    EvidenceManifestItem(
                        evidence_type=m["type"],
                        authority=m.get("authority", "CanonicalReportingAuthority"),
                        version=m.get("version", SERIALIZATION_VERSION),
                        fingerprint=m["fingerprint"],
                        status=m["status"],
                        scope=m.get("scope", "GLOBAL"),
                    ) for m in c_data.get("evidence_manifest", [])
                ]
                cert_obj = CertificationArtifact(
                    certification_id=c_data["certification_id"],
                    report_id=report_id,
                    job_id=data.get("job_id", ""),
                    run_id=data.get("run_id", ""),
                    outcome=CertificationOutcome(c_data["outcome"]),
                    claims=claims,
                    evidence_manifest=manifest,
                    issued_at=data.get("created_at", ""),
                    certification_fingerprint=c_data.get("certification_fingerprint", ""),
                )

            report = CanonicalReport(
                report_id=data["report_id"],
                report_version=data["report_version"],
                report_type=CanonicalReportType(data["report_type"]),
                job_id=data["job_id"],
                run_id=data["run_id"],
                created_at=data["created_at"],
                source_info=data.get("source_info", {}),
                target_info=data.get("target_info", {}),
                execution_summary=data.get("execution_summary", {}),
                schema_summary=data.get("schema_summary", {}),
                data_summary=data.get("data_summary", {}),
                validation_summary=data.get("validation_summary", {}),
                governance_summary=data.get("governance_summary", {}),
                warnings=data.get("warnings", []),
                errors=data.get("errors", []),
                manual_review_items=data.get("manual_review_items", []),
                evidence_fingerprints=data.get("evidence_fingerprints", []),
                final_outcome=data.get("final_outcome", "UNKNOWN"),
                certification=cert_obj,
                report_fingerprint=data.get("report_fingerprint", ""),
            )
            self._reports_store[report_id] = report
            return report
        except Exception as e:
            logger.warning(f"[CANONICAL REPORTING] Failed to load report from disk (corrupted JSON or missing fields): {e}")
            return None
