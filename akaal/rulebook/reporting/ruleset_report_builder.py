"""
Akaal — RuleSet Report Builder
==============================
Assembles canonical MigrationRuleSet artifacts from evaluated pipeline results.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List
from akaal.rulebook.models.rule_evaluation_context import RuleEvaluationContext
from akaal.rulebook.models.migration_ruleset import MigrationRuleSet
from akaal.rulebook.models.rule_result import RuleEvaluationResult
from akaal.rulebook.models.rule_diagnostic import RuleDiagnostic
from akaal.rulebook.models.rule_audit import RuleAudit, RuleAuditEntry
from akaal.rulebook.models.rule_manifest import RuleManifest
from akaal.rulebook.models.rule_execution_trace import RuleExecutionTrace


class RuleSetReportBuilder:
    """Assembles final immutable MigrationRuleSet."""

    @staticmethod
    def build_ruleset(
        ctx: RuleEvaluationContext,
        results: List[RuleEvaluationResult],
        inheritance_summary: Dict[str, Any],
        diagnostics: List[RuleDiagnostic],
        trace: RuleExecutionTrace,
    ) -> MigrationRuleSet:
        vendor_rules: List[Dict[str, Any]] = []
        naming_rules: List[Dict[str, Any]] = []
        conversion_rules: List[Dict[str, Any]] = []
        compliance_rules: List[Dict[str, Any]] = []
        constraint_rules: List[Dict[str, Any]] = []
        transformation_rules: List[Dict[str, Any]] = []
        security_rules: List[Dict[str, Any]] = []

        audit = RuleAudit(correlation_id=ctx.correlation_id)

        for res in results:
            d = res.to_dict()
            cat = res.category.upper()

            audit.add_entry(RuleAuditEntry(
                rule_id=res.rule_id,
                decision=res.status,
                scope=res.scope,
                provenance=res.provenance,
                rationale=res.rationale,
                override_rule_id=res.override_rule_id or "",
            ))

            if res.status == "APPLIED":
                if cat == "VENDOR":
                    vendor_rules.append(d)
                elif cat == "NAMING":
                    naming_rules.append(d)
                elif cat == "CONVERSION":
                    conversion_rules.append(d)
                elif cat == "COMPLIANCE":
                    compliance_rules.append(d)
                elif cat == "CONSTRAINT":
                    constraint_rules.append(d)
                elif cat == "TRANSFORMATION":
                    transformation_rules.append(d)
                elif cat == "SECURITY":
                    security_rules.append(d)

        manifest = RuleManifest(
            rulebook_version=ctx.rulebook_version,
            pack_versions=ctx.rule_pack_registry_ref.manifest() if ctx.rule_pack_registry_ref else {},
            applied_rule_ids=[r.rule_id for r in results if r.status == "APPLIED"],
        )

        metadata = {
            "target_engine": ctx.target_engine,
            "correlation_id": ctx.correlation_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_engine": ctx.discovery_report.engine_info.system_type,
            "source_fingerprint": ctx.discovery_report.fingerprint.sha256_hash if ctx.discovery_report.fingerprint else "",
        }

        diag_dicts = [diag.to_dict() for diag in diagnostics]

        def _clean_rule(r_dict: Dict[str, Any]) -> Dict[str, Any]:
            c = dict(r_dict)
            c.pop("timestamp", None)
            return c

        temp_dict = {
            "target_engine": ctx.target_engine,
            "source_engine": ctx.discovery_report.engine_info.system_type,
            "vendor_rules": [_clean_rule(r) for r in vendor_rules],
            "naming_rules": [_clean_rule(r) for r in naming_rules],
            "conversion_rules": [_clean_rule(r) for r in conversion_rules],
            "compliance_rules": [_clean_rule(r) for r in compliance_rules],
            "constraint_rules": [_clean_rule(r) for r in constraint_rules],
            "transformation_rules": [_clean_rule(r) for r in transformation_rules],
            "security_rules": [_clean_rule(r) for r in security_rules],
            "inheritance_summary": inheritance_summary,
            "applied_rule_ids": manifest.applied_rule_ids,
        }
        checksum_val = hashlib.sha256(json.dumps(temp_dict, default=str, sort_keys=True).encode("utf-8")).hexdigest()

        return MigrationRuleSet(
            sha256_checksum=checksum_val,
            metadata=metadata,
            vendor_rules=vendor_rules,
            naming_rules=naming_rules,
            conversion_rules=conversion_rules,
            compliance_rules=compliance_rules,
            constraint_rules=constraint_rules,
            transformation_rules=transformation_rules,
            security_rules=security_rules,
            inheritance_summary=inheritance_summary,
            rule_manifest=manifest.to_dict(),
            rule_metrics={"total_rules_evaluated": len(results), "applied_rules": len(manifest.applied_rule_ids)},
            audit_trail=audit.to_dict(),
            execution_trace_summary=trace.to_dict(),
            diagnostics=diag_dicts,
        )
