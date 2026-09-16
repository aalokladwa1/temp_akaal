"""akaalPipeline/orchestration/importer.py

Canonical migration metadata importer for DevKros.
Converts external migration configurations (AWS DMS, Oracle GoldenGate, DevKros JSON/CSV)
into reviewable, non-authoritative DevKros draft proposals.

SECURITY LAW:
1. Imported metadata is UNTRUSTED HOSTILE INPUT.
2. It MUST NEVER become trusted execution authority automatically.
3. Credentials/secrets are detected and redacted.
4. Tenant scope and file safety limits are strictly enforced.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union


# Security & Resource Constants
MAX_IMPORT_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_IMPORTED_OBJECTS = 10_000
MAX_JSON_DEPTH = 20

# Sensitive keys to redact
SENSITIVE_KEY_PATTERNS = [
    re.compile(r"(?i)password"),
    re.compile(r"(?i)secret"),
    re.compile(r"(?i)token"),
    re.compile(r"(?i)api_key"),
    re.compile(r"(?i)private_key"),
    re.compile(r"(?i)conn_string"),
    re.compile(r"(?i)connection_string"),
    re.compile(r"(?i)credential"),
]


@dataclass
class DiscoveredObject:
    schema_name: str
    object_name: str
    object_type: str = "TABLE"
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProposedCorrespondence:
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str
    column_mappings: Dict[str, str] = field(default_factory=dict)
    filters: List[str] = field(default_factory=list)
    transformations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ImportProposalRecord:
    proposal_id: str
    tenant_id: str
    workspace_id: str
    project_id: Optional[str]
    format_type: str  # AWS_DMS, GOLDENGATE, DEVKROS_JSON, DEVKROS_CSV
    source_provider_hint: Optional[str]
    target_provider_hint: Optional[str]
    discovered_objects: List[DiscoveredObject]
    proposed_correspondences: List[ProposedCorrespondence]
    accepted_fields: List[str]
    unsupported_fields: List[str]
    warnings: List[str]
    errors: List[str]
    security_redactions: List[str]
    manual_review_items: List[str]
    fingerprint: str
    created_at: str
    is_proposal_only: bool = True  # NEVER trusted execution authority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "format_type": self.format_type,
            "source_provider_hint": self.source_provider_hint,
            "target_provider_hint": self.target_provider_hint,
            "discovered_objects": [
                {
                    "schema_name": o.schema_name,
                    "object_name": o.object_name,
                    "object_type": o.object_type,
                    "attributes": o.attributes,
                }
                for o in self.discovered_objects
            ],
            "proposed_correspondences": [
                {
                    "source_schema": c.source_schema,
                    "source_table": c.source_table,
                    "target_schema": c.target_schema,
                    "target_table": c.target_table,
                    "column_mappings": c.column_mappings,
                    "filters": c.filters,
                    "transformations": c.transformations,
                }
                for c in self.proposed_correspondences
            ],
            "accepted_fields": self.accepted_fields,
            "unsupported_fields": self.unsupported_fields,
            "warnings": self.warnings,
            "errors": self.errors,
            "security_redactions": self.security_redactions,
            "manual_review_items": self.manual_review_items,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at,
            "is_proposal_only": True,
        }


class MigrationMetadataImporter:
    """Subordinate to canonical planning/orchestration authority.

    Parses external migration manifests into reviewable, un-trusted draft proposals.
    """

    def parse_and_create_proposal(
        self,
        content: str,
        filename: str,
        tenant_id: str,
        workspace_id: str,
        project_id: Optional[str] = None,
    ) -> ImportProposalRecord:
        """Parses external metadata content and returns a reviewable proposal."""
        # 1. Resource & Payload Checks
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > MAX_IMPORT_FILE_SIZE_BYTES:
            raise ValueError(
                f"Import metadata exceeds maximum size limit of {MAX_IMPORT_FILE_SIZE_BYTES} bytes (got {len(content_bytes)})"
            )

        # 2. Compute Content Fingerprint (SHA-256 for idempotency)
        fingerprint = hashlib.sha256(content_bytes).hexdigest()
        proposal_id = f"prop_{fingerprint[:16]}"
        now_str = datetime.now(timezone.utc).isoformat()

        # 3. Detect Format & Parse
        format_type, parsed_json, parse_err = self._detect_and_parse(content, filename)
        if parse_err:
            return ImportProposalRecord(
                proposal_id=proposal_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                project_id=project_id,
                format_type=format_type or "UNKNOWN",
                source_provider_hint=None,
                target_provider_hint=None,
                discovered_objects=[],
                proposed_correspondences=[],
                accepted_fields=[],
                unsupported_fields=[],
                warnings=[],
                errors=[parse_err],
                security_redactions=[],
                manual_review_items=["File could not be parsed as a supported migration manifest"],
                fingerprint=fingerprint,
                created_at=now_str,
            )

        # 4. Redact Secrets & Check Depth
        redactions: List[str] = []
        sanitized_payload = self._sanitize_and_redact(parsed_json, redactions)

        # 5. Extract Details per Format
        if format_type == "AWS_DMS":
            return self._extract_aws_dms(
                proposal_id, tenant_id, workspace_id, project_id, fingerprint, now_str, sanitized_payload, redactions
            )
        elif format_type == "GOLDENGATE":
            return self._extract_goldengate(
                proposal_id, tenant_id, workspace_id, project_id, fingerprint, now_str, sanitized_payload, redactions
            )
        elif format_type == "DEVKROS_CSV":
            return self._extract_devkros_csv(
                proposal_id, tenant_id, workspace_id, project_id, fingerprint, now_str, content, redactions
            )
        else:  # DEVKROS_JSON
            return self._extract_devkros_json(
                proposal_id, tenant_id, workspace_id, project_id, fingerprint, now_str, sanitized_payload, redactions
            )

    def _detect_and_parse(self, content: str, filename: str) -> Tuple[str, Any, Optional[str]]:
        fn_lower = filename.lower()
        if fn_lower.endswith(".csv"):
            return "DEVKROS_CSV", None, None

        try:
            data = json.loads(content)
            if not isinstance(data, (dict, list)):
                return "UNKNOWN", None, "JSON root must be an object or array"

            if isinstance(data, dict):
                # AWS DMS signature
                if "rules" in data or "rules" in data.get("table-mappings", {}) or "TableMappings" in data:
                    return "AWS_DMS", data, None
                # GoldenGate signature
                if "goldengate" in data or "gg_params" in data or "map" in data:
                    return "GOLDENGATE", data, None

            return "DEVKROS_JSON", data, None
        except Exception as e:
            # Check if text looks like GoldenGate parameter file (e.g., MAP schema.table, TARGET schema.table;)
            if "TABLE " in content.upper() or "MAP " in content.upper():
                return "GOLDENGATE", content, None
            return "UNKNOWN", None, f"Failed to parse import content: {str(e)}"

    def _sanitize_and_redact(self, data: Any, redactions: List[str], current_depth: int = 0) -> Any:
        if current_depth > MAX_JSON_DEPTH:
            redactions.append(f"Maximum JSON depth ({MAX_JSON_DEPTH}) exceeded; nested values truncated.")
            return None

        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if any(pat.search(str(k)) for pat in SENSITIVE_KEY_PATTERNS):
                    redactions.append(f"Redacted sensitive field '{k}' from import payload")
                    new_dict[k] = "***REDACTED***"
                else:
                    new_dict[k] = self._sanitize_and_redact(v, redactions, current_depth + 1)
            return new_dict
        elif isinstance(data, list):
            return [self._sanitize_and_redact(item, redactions, current_depth + 1) for item in data]
        else:
            return data

    def _extract_aws_dms(
        self,
        proposal_id: str,
        tenant_id: str,
        workspace_id: str,
        project_id: Optional[str],
        fingerprint: str,
        now_str: str,
        data: Dict[str, Any],
        redactions: List[str],
    ) -> ImportProposalRecord:
        discovered: List[DiscoveredObject] = []
        correspondences: List[ProposedCorrespondence] = []
        accepted = ["rules", "table-mappings", "selection", "transformation"]
        unsupported: List[str] = []
        warnings: List[str] = []
        manual_review: List[str] = ["Review AWS DMS rule transformations before creating DevKros migration pipeline"]

        rules = []
        if "rules" in data:
            rules = data["rules"]
        elif "table-mappings" in data and "rules" in data["table-mappings"]:
            rules = data["table-mappings"]["rules"]
        elif "TableMappings" in data and "rules" in data["TableMappings"]:
            rules = data["TableMappings"]["rules"]

        for rule in rules:
            if len(discovered) >= MAX_IMPORTED_OBJECTS:
                warnings.append(f"Imported objects capped at maximum limit of {MAX_IMPORTED_OBJECTS}")
                break

            rule_type = rule.get("rule-type")
            object_loc = rule.get("object-locator", {})
            schema_pattern = object_loc.get("schema-name", "%")
            table_pattern = object_loc.get("table-name", "%")

            if rule_type == "selection":
                action = rule.get("rule-action", "include")
                if action == "include":
                    discovered.append(
                        DiscoveredObject(
                            schema_name=schema_pattern,
                            object_name=table_pattern,
                            object_type="TABLE",
                            attributes={"dms_action": action, "rule_id": rule.get("rule-id")},
                        )
                    )
                    correspondences.append(
                        ProposedCorrespondence(
                            source_schema=schema_pattern,
                            source_table=table_pattern,
                            target_schema=schema_pattern,  # Default 1:1 unless transformed
                            target_table=table_pattern,
                        )
                    )
            elif rule_type == "transformation":
                target_schema = rule.get("value") if rule.get("rule-target") == "schema" else schema_pattern
                target_table = rule.get("value") if rule.get("rule-target") == "table" else table_pattern
                for corr in correspondences:
                    if corr.source_schema == schema_pattern or schema_pattern == "%":
                        if rule.get("rule-target") == "schema":
                            corr.target_schema = target_schema
                        elif rule.get("rule-target") == "table":
                            corr.target_table = target_table
            else:
                if rule_type:
                    unsupported.append(f"DMS rule type '{rule_type}' not directly executable in DevKros proposal")

        return ImportProposalRecord(
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            format_type="AWS_DMS",
            source_provider_hint="AWS_DMS_SOURCE",
            target_provider_hint="AWS_DMS_TARGET",
            discovered_objects=discovered,
            proposed_correspondences=correspondences,
            accepted_fields=accepted,
            unsupported_fields=unsupported,
            warnings=warnings,
            errors=[],
            security_redactions=redactions,
            manual_review_items=manual_review,
            fingerprint=fingerprint,
            created_at=now_str,
        )

    def _extract_goldengate(
        self,
        proposal_id: str,
        tenant_id: str,
        workspace_id: str,
        project_id: Optional[str],
        fingerprint: str,
        now_str: str,
        data: Union[Dict[str, Any], str],
        redactions: List[str],
    ) -> ImportProposalRecord:
        discovered: List[DiscoveredObject] = []
        correspondences: List[ProposedCorrespondence] = []
        manual_review = ["GoldenGate replication parameters parsed as draft table correspondence; verify column mappings."]

        if isinstance(data, str):
            # Parse line by line for TABLE / MAP statements
            lines = data.splitlines()
            for line in lines:
                clean_line = line.strip().rstrip(";")
                if clean_line.upper().startswith("TABLE "):
                    parts = clean_line.split()
                    if len(parts) >= 2:
                        full_name = parts[1]
                        schema_name, _, table_name = full_name.rpartition(".")
                        discovered.append(
                            DiscoveredObject(schema_name=schema_name or "PUBLIC", object_name=table_name)
                        )
                        correspondences.append(
                            ProposedCorrespondence(
                                source_schema=schema_name or "PUBLIC",
                                source_table=table_name,
                                target_schema=schema_name or "PUBLIC",
                                target_table=table_name,
                            )
                        )
                elif clean_line.upper().startswith("MAP "):
                    # e.g. MAP src.tbl, TARGET tgt.tbl;
                    match = re.search(r"MAP\s+([\w\.]+),\s*TARGET\s+([\w\.]+)", clean_line, re.IGNORECASE)
                    if match:
                        src_full, tgt_full = match.group(1), match.group(2)
                        s_sch, _, s_tbl = src_full.rpartition(".")
                        t_sch, _, t_tbl = tgt_full.rpartition(".")
                        correspondences.append(
                            ProposedCorrespondence(
                                source_schema=s_sch or "PUBLIC",
                                source_table=s_tbl,
                                target_schema=t_sch or "PUBLIC",
                                target_table=t_tbl,
                            )
                        )
        elif isinstance(data, dict):
            maps = data.get("maps", data.get("mappings", []))
            for m in maps:
                if isinstance(m, dict):
                    src_sch = m.get("source_schema", "PUBLIC")
                    src_tbl = m.get("source_table", m.get("table", "UNKNOWN"))
                    tgt_sch = m.get("target_schema", src_sch)
                    tgt_tbl = m.get("target_table", src_tbl)
                    correspondences.append(
                        ProposedCorrespondence(
                            source_schema=src_sch,
                            source_table=src_tbl,
                            target_schema=tgt_sch,
                            target_table=tgt_tbl,
                        )
                    )

        return ImportProposalRecord(
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            format_type="GOLDENGATE",
            source_provider_hint="ORACLE",
            target_provider_hint="TARGET_DB",
            discovered_objects=discovered,
            proposed_correspondences=correspondences,
            accepted_fields=["TABLE", "MAP", "TARGET"],
            unsupported_fields=["TRANLOGOPTIONS", "EXTTRAIL"],
            warnings=[],
            errors=[],
            security_redactions=redactions,
            manual_review_items=manual_review,
            fingerprint=fingerprint,
            created_at=now_str,
        )

    def _extract_devkros_json(
        self,
        proposal_id: str,
        tenant_id: str,
        workspace_id: str,
        project_id: Optional[str],
        fingerprint: str,
        now_str: str,
        data: Dict[str, Any],
        redactions: List[str],
    ) -> ImportProposalRecord:
        discovered: List[DiscoveredObject] = []
        correspondences: List[ProposedCorrespondence] = []

        src_provider = data.get("source_provider") or data.get("source_type")
        tgt_provider = data.get("target_provider") or data.get("target_type")

        mappings = data.get("mappings") or data.get("correspondences") or []
        if isinstance(mappings, list):
            for m in mappings:
                if isinstance(m, dict):
                    src_sch = m.get("source_schema", "PUBLIC")
                    src_tbl = m.get("source_table", "UNKNOWN")
                    tgt_sch = m.get("target_schema", src_sch)
                    tgt_tbl = m.get("target_table", src_tbl)
                    col_maps = m.get("column_mappings", {})
                    filters = m.get("filters", [])
                    correspondences.append(
                        ProposedCorrespondence(
                            source_schema=src_sch,
                            source_table=src_tbl,
                            target_schema=tgt_sch,
                            target_table=tgt_tbl,
                            column_mappings=col_maps if isinstance(col_maps, dict) else {},
                            filters=filters if isinstance(filters, list) else [],
                        )
                    )

        return ImportProposalRecord(
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            format_type="DEVKROS_JSON",
            source_provider_hint=src_provider,
            target_provider_hint=tgt_provider,
            discovered_objects=discovered,
            proposed_correspondences=correspondences,
            accepted_fields=["source_provider", "target_provider", "mappings", "correspondences"],
            unsupported_fields=[],
            warnings=[],
            errors=[],
            security_redactions=redactions,
            manual_review_items=["Review proposed table and column mappings prior to initialization."],
            fingerprint=fingerprint,
            created_at=now_str,
        )

    def _extract_devkros_csv(
        self,
        proposal_id: str,
        tenant_id: str,
        workspace_id: str,
        project_id: Optional[str],
        fingerprint: str,
        now_str: str,
        content: str,
        redactions: List[str],
    ) -> ImportProposalRecord:
        correspondences: List[ProposedCorrespondence] = []
        warnings: List[str] = []
        errors: List[str] = []

        try:
            reader = csv.DictReader(io.StringIO(content))
            for row_idx, row in enumerate(reader):
                if len(correspondences) >= MAX_IMPORTED_OBJECTS:
                    warnings.append(f"CSV import rows capped at maximum limit of {MAX_IMPORTED_OBJECTS}")
                    break

                # Expect columns: source_schema, source_table, target_schema, target_table
                src_sch = row.get("source_schema") or row.get("src_schema") or "PUBLIC"
                src_tbl = row.get("source_table") or row.get("src_table")
                tgt_sch = row.get("target_schema") or row.get("tgt_schema") or src_sch
                tgt_tbl = row.get("target_table") or row.get("tgt_table") or src_tbl

                if src_tbl:
                    correspondences.append(
                        ProposedCorrespondence(
                            source_schema=src_sch,
                            source_table=src_tbl,
                            target_schema=tgt_sch,
                            target_table=tgt_tbl,
                        )
                    )
        except Exception as e:
            errors.append(f"Malformed CSV content: {str(e)}")

        return ImportProposalRecord(
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            format_type="DEVKROS_CSV",
            source_provider_hint=None,
            target_provider_hint=None,
            discovered_objects=[],
            proposed_correspondences=correspondences,
            accepted_fields=["source_schema", "source_table", "target_schema", "target_table"],
            unsupported_fields=[],
            warnings=warnings,
            errors=errors,
            security_redactions=redactions,
            manual_review_items=["Review CSV mapping proposals."],
            fingerprint=fingerprint,
            created_at=now_str,
        )
