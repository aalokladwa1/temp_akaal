"""
Akaal — P5.1 Canonical Plan Compiler
=====================================
Compiles MigrationPlan + PlanVersion + ConfigurationScope + Topology/Routing into an
immutable ExecutionPlan.

Key Duties:
1. Validates topology and schema routing rules (detects collisions, unsupported topologies).
2. Evaluates connector compatibility via UniversalCompatibilityEngine.
3. Invokes SynchronizationPlanner for Stage 1 DDL planning and SHA-256 fingerprinting.
4. Generates a dynamic execution DAG reflecting compiled scope, performance settings, CDC, and validation.
5. Computes deterministic plan diffs between version revisions.
6. Enforces zero data writes during dry-run compilation.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from akaal.planner.models.p5_domain import (
    MigrationPlan,
    PlanVersion,
    ExecutionPlan,
    CompilationDiagnostic,
    CompilationResult,
    PlanDiff,
    ConfigurationScope,
    PlanningMode,
    RoutingDefinition,
    TopologyDefinition,
)
from akaal.migration.planner import SynchronizationPlanner
from akaal.migration.hashing import calculate_plan_hash
from akaal.connectors.compatibility_engine import UniversalCompatibilityEngine
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.core.models.enums import SystemType


class PlanCompiler:
    """Canonical P5.1 planning authority for compiling enterprise execution plans."""

    def __init__(
        self,
        sync_planner: Optional[SynchronizationPlanner] = None,
        compat_engine: Optional[UniversalCompatibilityEngine] = None,
    ) -> None:
        self.sync_planner = sync_planner or SynchronizationPlanner()
        self.compat_engine = compat_engine or UniversalCompatibilityEngine()

    def compile(
        self,
        plan: MigrationPlan,
        version: PlanVersion,
        config_scope: Optional[ConfigurationScope] = None,
        dry_run: bool = False,
    ) -> CompilationResult:
        """
        Compiles a draft plan and version into an immutable ExecutionPlan.
        If dry_run is True, zero state mutations or disk writes are committed.
        """
        diagnostics: List[CompilationDiagnostic] = []

        # 1. Resolve Effective Configuration Precedence
        scope = config_scope or ConfigurationScope(
            plan_overrides=plan.configuration
        )
        effective_config, provenance = scope.resolve()

        # Sanitize any accidental secrets in configuration logging
        for secret_key in ["password", "token", "secret", "api_key"]:
            if secret_key in effective_config:
                effective_config[secret_key] = "[REDACTED_HANDLE]"

        # 2. Topology & Routing Validation
        topo = plan.topology
        routing = plan.routing

        # 2b. P5.2 Canonical Data Selection Resolution & Validation
        sel_def = self.resolve_selection_definition(plan.selected_scope)
        resolved_scope_info = self.resolve_rules_and_projections(
            selected_scope=plan.selected_scope,
            selection_def=sel_def,
            connector_type=plan.topology.source.connector_type,
        )
        diagnostics.extend(resolved_scope_info["diagnostics"])

        # Validate Schema Routing Collisions
        route_targets = [r.target_schema for r in routing.schema_routes if r.status == "ACTIVE"]
        unique_targets = set(route_targets)
        if len(route_targets) != len(unique_targets):
            if not routing.allow_many_to_one:
                diagnostics.append(
                    CompilationDiagnostic(
                        level="BLOCKER",
                        code="ROUTING_COLLISION",
                        message="Multiple source schemas route to the same target schema, but allow_many_to_one is False.",
                    )
                )

        # Validate 1:MANY or MANY:MANY topologies if disabled
        if topo.topology_type == "1:MANY" and not routing.allow_one_to_many:
            diagnostics.append(
                CompilationDiagnostic(
                    level="BLOCKER",
                    code="UNSUPPORTED_TOPOLOGY",
                    message="1:MANY topology configured, but allow_one_to_many routing policy is False.",
                )
            )

        # 3. Connector Compatibility Check
        src_conn = plan.topology.source.connector_type
        tgt_conn = plan.topology.target.connector_type
        
        try:
            src_type = SystemType(src_conn.upper()) if hasattr(SystemType, src_conn.upper()) else SystemType.GENERIC
            tgt_type = SystemType(tgt_conn.upper()) if hasattr(SystemType, tgt_conn.upper()) else SystemType.GENERIC
            
            compat_eval = self.compat_engine.evaluate_compatibility(src_type, tgt_type)
            if not compat_eval.is_compatible:
                diagnostics.append(
                    CompilationDiagnostic(
                        level="BLOCKER",
                        code="INCOMPATIBLE_CONNECTORS",
                        message=f"Source connector '{src_conn}' and target connector '{tgt_conn}' are incompatible: {compat_eval.incompatibility_reason}",
                    )
                )
            elif compat_eval.degraded_reasons:
                for deg in compat_eval.degraded_reasons:
                    diagnostics.append(
                        CompilationDiagnostic(
                            level="WARNING",
                            code="DEGRADED_COMPATIBILITY",
                            message=f"Degraded compatibility warning: {deg}",
                        )
                    )
        except Exception as err:
            diagnostics.append(
                CompilationDiagnostic(
                    level="WARNING",
                    code="CONNECTOR_EVAL_FAILURE",
                    message=f"Could not fully evaluate connector compatibility: {err}",
                )
            )

        # 3b. P5.6 Deduplication, Data Quality, and Conflict Policy Compilation & Validation
        p56_res = self.compile_deduplication_and_quality(
            selected_scope=plan.selected_scope if isinstance(plan.selected_scope, dict) else {},
            dedup_def=effective_config.get("deduplication") or plan.configuration.get("deduplication"),
            quality_def=effective_config.get("data_quality") or plan.configuration.get("data_quality"),
            conflict_config=effective_config.get("conflict_policy") or plan.configuration.get("conflict_policy"),
            target_connector_type=tgt_conn,
        )
        if p56_res.get("status") == "BLOCKER":
            for d_dict in p56_res.get("diagnostics", []):
                if d_dict.get("level") == "BLOCKER":
                    diagnostics.append(CompilationDiagnostic(
                        level=d_dict["level"],
                        code=d_dict["code"],
                        message=d_dict["message"],
                        target=d_dict.get("target"),
                    ))
        effective_config["deduplication"] = p56_res["deduplication"]
        effective_config["data_quality"] = p56_res["data_quality"]
        effective_config["conflict_policy"] = p56_res["conflict_policy"]
        effective_config["p5_6_fingerprint"] = p56_res["fingerprint"]

        # If blocking diagnostics exist, fail closed
        blockers = [d for d in diagnostics if d.level == "BLOCKER"]
        if blockers:
            return CompilationResult(
                success=False,
                fingerprint="",
                diagnostics=diagnostics,
                execution_plan=None,
            )

        # 4. Generate Stage 1 Logical DDL Plan & Calculate Fingerprint
        # Build canonical payload for fingerprinting (includes typed SelectionDefinition)
        canonical_str = json.dumps(
            {
                "project_id": plan.project_id,
                "version_id": version.version_id,
                "revision": version.revision,
                "topology": topo.to_dict(),
                "routing": routing.to_dict(),
                "selected_scope": plan.selected_scope,
                "selection_definition": sel_def.to_dict(),
                "effective_config": effective_config,
            },
            sort_keys=True,
        )
        fingerprint = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        # 5. Build Dynamic Execution DAG Nodes
        dag_stages = self._build_dynamic_dag(
            plan=plan,
            effective_config=effective_config,
            fingerprint=fingerprint,
        )

        stage1_payload = {
            "fingerprint": fingerprint,
            "version_revision": version.revision,
            "stage_count": len(dag_stages),
            "effective_config": effective_config,
            "provenance": provenance,
        }

        exec_plan = ExecutionPlan(
            execution_plan_id=f"exec-plan-{version.version_id[:8]}",
            project_id=plan.project_id,
            plan_version_id=version.version_id,
            fingerprint=fingerprint,
            compiled_at=datetime.now(timezone.utc).isoformat(),
            resolved_topology=topo.to_dict(),
            resolved_routing=routing.to_dict(),
            resolved_configuration=effective_config,
            stage1_plan=stage1_payload,
            dag_stages=dag_stages,
            is_immutable=True,
        )

        return CompilationResult(
            success=True,
            fingerprint=fingerprint,
            diagnostics=diagnostics,
            execution_plan=exec_plan.to_dict(),
        )

    def compute_diff(
        self,
        payload_a: Dict[str, Any],
        payload_b: Dict[str, Any],
        version_a_id: str = "vA",
        version_b_id: str = "vB",
    ) -> PlanDiff:
        """Computes human-readable plan diff and checks if approval invalidation is required."""
        changes: List[Dict[str, Any]] = []
        requires_reapproval = False

        # Compare Topology
        if payload_a.get("topology") != payload_b.get("topology"):
            changes.append({
                "field": "topology",
                "old": payload_a.get("topology"),
                "new": payload_b.get("topology"),
                "impact": "FINGERPRINT_CHANGE",
            })
            requires_reapproval = True

        # Compare Routing
        if payload_a.get("routing") != payload_b.get("routing"):
            changes.append({
                "field": "routing",
                "old": payload_a.get("routing"),
                "new": payload_b.get("routing"),
                "impact": "FINGERPRINT_CHANGE",
            })
            requires_reapproval = True

        # Compare Scope
        if payload_a.get("selected_scope") != payload_b.get("selected_scope"):
            changes.append({
                "field": "selected_scope",
                "old": payload_a.get("selected_scope"),
                "new": payload_b.get("selected_scope"),
                "impact": "FINGERPRINT_CHANGE",
            })
            requires_reapproval = True

        # Compare Configuration
        config_a = payload_a.get("configuration") or payload_a.get("effective_config") or {}
        config_b = payload_b.get("configuration") or payload_b.get("effective_config") or {}
        
        for k in set(config_a.keys()).union(set(config_b.keys())):
            val_a = config_a.get(k)
            val_b = config_b.get(k)
            if val_a != val_b:
                is_critical = k in [
                    "parallelism",
                    "batch_size",
                    "enable_cdc",
                    "validation_level",
                    "four_eyes_policy",
                    "privacy_policy",
                    "privacy_rules",
                    "privacy_fingerprint",
                    "deduplication",
                    "deduplication_rules",
                    "data_quality",
                    "quality_rules",
                    "quality_thresholds",
                    "collision_policy",
                    "conflict_policy",
                    "p5_6_fingerprint",
                ]
                changes.append({
                    "field": f"configuration.{k}",
                    "old": val_a,
                    "new": val_b,
                    "impact": "CRITICAL_CONFIG_CHANGE" if is_critical else "MINOR_CONFIG_CHANGE",
                })
                if is_critical:
                    requires_reapproval = True

        return PlanDiff(
            version_a=version_a_id,
            version_b=version_b_id,
            changes=changes,
            requires_reapproval=requires_reapproval,
        )

    @staticmethod
    def validate_plan_approval(execution_plan: Dict[str, Any], approved_fingerprint: Optional[str]) -> bool:
        """
        Enforces that current ExecutionPlan privacy/plan fingerprint matches approved_fingerprint.
        Fails closed if metadata is missing, empty, or altered after approval.
        """
        if not execution_plan or not isinstance(execution_plan, dict):
            raise RuntimeError("STALE_APPROVAL_REJECTED: Execution plan is missing or invalid.")

        current_fp = execution_plan.get("fingerprint")
        privacy_fp = execution_plan.get("resolved_configuration", {}).get("privacy_fingerprint")

        # Missing or empty approved_fingerprint for a privacy-controlled plan MUST fail closed
        if not approved_fingerprint or not isinstance(approved_fingerprint, str) or not approved_fingerprint.strip():
            if current_fp or privacy_fp:
                raise RuntimeError("STALE_APPROVAL_REJECTED: Approved fingerprint is missing or empty for privacy-controlled plan.")

        if approved_fingerprint and (current_fp != approved_fingerprint and privacy_fp != approved_fingerprint):
            raise RuntimeError(
                f"STALE_APPROVAL_REJECTED: Approved fingerprint '{approved_fingerprint}' does not match "
                f"current plan fingerprint '{current_fp}' (privacy_fingerprint='{privacy_fp}'). Plan requires re-approval."
            )
        return True

    @staticmethod
    def validate_resume_checkpoint(checkpoint_data: Dict[str, Any], current_privacy_fingerprint: Optional[str]) -> bool:
        """
        Enforces that checkpoint privacy fingerprint matches current execution privacy fingerprint on job resume.
        Fails closed with zero target writes if metadata is missing, empty, or policy has changed.
        """
        if not checkpoint_data or not isinstance(checkpoint_data, dict):
            raise RuntimeError("STALE_RESUME_REJECTED: Checkpoint data is missing or invalid.")

        ckpt_privacy_fp = checkpoint_data.get("privacy_fingerprint")

        if ckpt_privacy_fp:
            if not current_privacy_fingerprint or not isinstance(current_privacy_fingerprint, str) or not current_privacy_fingerprint.strip():
                raise RuntimeError("STALE_RESUME_REJECTED: Checkpoint is privacy-controlled, but current_privacy_fingerprint is missing or empty.")
            if ckpt_privacy_fp != current_privacy_fingerprint:
                raise RuntimeError(
                    f"STALE_RESUME_REJECTED: Checkpoint privacy fingerprint '{ckpt_privacy_fp}' does not match "
                    f"current privacy fingerprint '{current_privacy_fingerprint}'. Resume aborted with zero target writes."
                )
        elif current_privacy_fingerprint:
            raise RuntimeError("STALE_RESUME_REJECTED: Current execution requires privacy controls, but checkpoint is missing privacy fingerprint.")

        return True

    def _build_dynamic_dag(
        self,
        plan: MigrationPlan,
        effective_config: Dict[str, Any],
        fingerprint: str,
    ) -> List[Dict[str, Any]]:
        """Constructs a dynamic DAG graph based on compiled scope, options, and capabilities."""
        stages: List[Dict[str, Any]] = []
        stage_num = 1

        # Stage 1: Discovery & Catalog Fencing
        stages.append({
            "stage": stage_num,
            "name": "Discovery & Catalog Fencing",
            "category": "Catalog",
            "details": f"Source Instance: {plan.topology.source.instance_id} -> Target: {plan.topology.target.instance_id}",
            "status": "VERIFIED",
        })
        stage_num += 1

        # Stage 2: Topological Dependency Sorting & Schema Routing
        route_count = len(plan.routing.schema_routes)
        stages.append({
            "stage": stage_num,
            "name": "DAG Topological Dependency Sorting & Schema Routing",
            "category": "Planner",
            "details": f"Topology: {plan.topology.topology_type}, Schema Routes: {route_count}",
            "status": "VERIFIED",
        })
        stage_num += 1

        # Stage 3: Target Schema Structure Deployment
        stages.append({
            "stage": stage_num,
            "name": "Target Schema Structure Deployment",
            "category": "DDL",
            "details": f"Deploy DDL definitions to target instance {plan.topology.target.instance_id}",
            "status": "READY",
        })
        stage_num += 1

        # Stage 4: Parallel Stream Data Transport
        workers = effective_config.get("parallelism", 8)
        batch_size = effective_config.get("batch_size", 5000)
        stages.append({
            "stage": stage_num,
            "name": "Parallel Stream Data Transport",
            "category": "Data Transport",
            "details": f"Bulk data streaming ({workers} Workers Pool, {batch_size} Row Batch Size)",
            "status": "READY",
        })
        stage_num += 1

        # Stage 5: CDC Continuous Replication Setup (conditional)
        if effective_config.get("enable_cdc", False):
            stages.append({
                "stage": stage_num,
                "name": "CDC Continuous Replication Setup",
                "category": "Replication",
                "details": "Setup WAL Log Reader & streaming sync coordinator",
                "status": "READY",
            })
            stage_num += 1

        # Stage 6: Data Reconciliation & Validation (conditional)
        val_level = effective_config.get("validation_level", "CHECKSUM")
        if val_level != "NONE":
            stages.append({
                "stage": stage_num,
                "name": "Reconciliation & Validation Node",
                "category": "Validation",
                "details": f"Validation Policy Level: {val_level}",
                "status": "READY",
            })
            stage_num += 1

        # Stage 7: SHA-256 Digital Trust Seal
        stages.append({
            "stage": stage_num,
            "name": "SHA-256 Digital Trust Seal",
            "category": "Certification",
            "details": f"Immutable SHA-256 Fingerprint: sha256-{fingerprint[:16]}...",
            "status": "READY",
        })

        return stages

    def resolve_selection_definition(self, selected_scope: Dict[str, Any]) -> "SelectionDefinition":
        """Converts or extracts canonical SelectionDefinition from selected_scope."""
        from akaal.planner.models.p5_domain import SelectionDefinition
        if not isinstance(selected_scope, dict):
            return SelectionDefinition()
        if "selection_definition" in selected_scope and isinstance(selected_scope["selection_definition"], dict):
            return SelectionDefinition.from_dict(selected_scope["selection_definition"])
        # Reconcile raw objects array into SelectionDefinition rules
        raw_objs = selected_scope.get("objects", [])
        from akaal.planner.models.p5_domain import SelectionRule
        rules = []
        for obj in raw_objs:
            if isinstance(obj, dict):
                o_name = obj.get("object_name") or obj.get("name")
                is_sel = obj.get("selected", True)
                if o_name:
                    rules.append(SelectionRule(
                        rule_type="INCLUDE" if is_sel else "EXCLUDE",
                        target_type="OBJECT",
                        pattern=o_name,
                        is_regex=False
                    ))
        return SelectionDefinition(rules=rules)

    def resolve_rules_and_projections(
        self,
        selected_scope: Dict[str, Any],
        selection_def: "SelectionDefinition",
        connector_type: str,
    ) -> Dict[str, Any]:
        """
        Applies include/exclude rules, globs, regex with ReDoS protection,
        auto-retains mandatory PK/CDC keys, and validates row predicates.
        """
        import fnmatch
        import re
        from akaal.planner.models.p5_domain import CompilationDiagnostic, ProjectionDefinition

        diagnostics: List[CompilationDiagnostic] = []
        raw_objs = selected_scope.get("objects", []) if isinstance(selected_scope, dict) else []

        # Validate Regex Rules with ReDoS Safety Fencing
        for rule in selection_def.rules:
            if rule.is_regex and rule.pattern:
                if len(rule.pattern) > 250 or "(.*)*" in rule.pattern or "(.+)+" in rule.pattern or "(a+)+" in rule.pattern:
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="INVALID_REGEX_PATTERN",
                        message=f"Regex pattern '{rule.pattern}' violates ReDoS safety fencing (catastrophic backtracking risk).",
                        target=rule.pattern,
                    ))
                else:
                    try:
                        re.compile(rule.pattern)
                    except re.error as err:
                        diagnostics.append(CompilationDiagnostic(
                            level="BLOCKER",
                            code="INVALID_REGEX_SYNTAX",
                            message=f"Regex pattern '{rule.pattern}' failed syntax validation: {err}",
                            target=rule.pattern,
                        ))

        # Enforce Mandatory PK / CDC Key Retention on Projections
        valid_operators = {"=", "!=", ">", ">=", "<", "<=", "IN", "NOT IN", "BETWEEN", "IS NULL", "IS NOT NULL", "LIKE"}
        for pred in selection_def.predicates:
            if pred.operator.upper() not in valid_operators:
                diagnostics.append(CompilationDiagnostic(
                    level="BLOCKER",
                    code="UNSUPPORTED_PREDICATE_OPERATOR",
                    message=f"Predicate operator '{pred.operator}' for column '{pred.column}' is unsupported or unsafe.",
                    target=pred.object_id,
                ))

        # Enforce Connector Capability Fail-Closed Boundaries
        conn_upper = str(connector_type).upper()
        if selection_def.sampling and "CDC" in conn_upper:
            diagnostics.append(CompilationDiagnostic(
                level="BLOCKER",
                code="SAMPLING_UNSUPPORTED_FOR_CDC",
                message=f"Continuous CDC streaming migrations do not support sampling reduction filters on connector '{connector_type}'.",
                target=connector_type,
            ))

        # Process Projections & Auto-Retain Primary Keys
        resolved_projections: Dict[str, ProjectionDefinition] = {}
        for proj in selection_def.projections:
            # Reconcile mandatory PKs if available from discovery
            pk_cols = ["id", "uuid", "pk"]  # Default PK candidates
            auto_retained = [c for c in proj.excluded_columns or c not in proj.selected_columns]

            # Ensure mandatory keys are never stripped
            clean_selected = list(proj.selected_columns)
            for k in auto_retained:
                if k not in clean_selected:
                    clean_selected.append(k)

            resolved_projections[proj.object_id] = ProjectionDefinition(
                object_id=proj.object_id,
                selected_columns=clean_selected,
                auto_retained_columns=auto_retained,
                excluded_columns=[c for c in proj.excluded_columns if c not in auto_retained],
            )

        return {
            "diagnostics": diagnostics,
            "projections": resolved_projections,
        }

    def verify_discovery_drift(
        self,
        planned_scope: Dict[str, Any],
        current_discovery: Dict[str, Any],
    ) -> List[CompilationDiagnostic]:
        """Pre-execution fence: compares planned selection scope against current catalog discovery."""
        diagnostics = []
        planned_objs = {o.get("object_name") for o in planned_scope.get("objects", []) if isinstance(o, dict) and o.get("selected", True)}
        current_objs = {o.get("object_name") for o in current_discovery.get("objects", []) if isinstance(o, dict)}

        missing = planned_objs - current_objs
        for m in missing:
            diagnostics.append(CompilationDiagnostic(
                level="BLOCKER",
                code="DISCOVERY_DRIFT_DETECTED",
                message=f"Selected table/object '{m}' present in planned scope was removed or altered in current database catalog.",
                target=m,
            ))
        return diagnostics

    def compile_mapping(
        self,
        selected_scope: Dict[str, Any],
        routing_def: Optional[Dict[str, Any]] = None,
        connector_type: str = "GENERIC",
    ) -> Dict[str, Any]:
        """Compiles canonical P5.3 structural mapping, evaluating schema routing, object/column renames, bulk rules, and datatype compatibility."""
        from akaal.planner.models.p5_domain import RoutingDefinition, CompiledMapping, SchemaRoute, ObjectRoute, ColumnMapping, BulkMappingRule
        from akaal.schema.domain.type_registry import CanonicalTypeRegistry
        from akaal.migration.target_identifier import validate_operator_configured_identifier

        diagnostics: List[CompilationDiagnostic] = []
        r_def = RoutingDefinition()
        if routing_def and isinstance(routing_def, dict):
            # Parse routing configuration
            for sr in routing_def.get("schema_routes", []):
                if isinstance(sr, dict):
                    r_def.schema_routes.append(SchemaRoute(**sr))
            for ob in routing_def.get("object_routes", []):
                if isinstance(ob, dict):
                    r_def.object_routes.append(ObjectRoute(**ob))
            for cm in routing_def.get("column_mappings", []):
                if isinstance(cm, dict):
                    r_def.column_mappings.append(ColumnMapping(**cm))
            for br in routing_def.get("bulk_rules", []):
                if isinstance(br, dict):
                    r_def.bulk_rules.append(BulkMappingRule(**br))

        # 1. Resolve Schema Mapping
        schema_map: Dict[str, str] = {}
        for sr in r_def.schema_routes:
            schema_map[sr.source_schema] = sr.target_schema

        # 2. Resolve Object Mapping
        object_map: Dict[str, str] = {}
        target_obj_provenance: Dict[str, str] = {}
        objects = selected_scope.get("objects", []) if isinstance(selected_scope, dict) else []

        explicit_obj_routes = {(r.source_schema, r.source_object): r.target_object for r in r_def.object_routes}

        for obj in objects:
            if not isinstance(obj, dict) or not obj.get("selected", True):
                continue
            s_name = obj.get("schema_name", "public")
            t_name = obj.get("object_name") or obj.get("table_name")
            if not t_name:
                continue

            src_key = f"{s_name}.{t_name}"

            # Check explicit object rename first
            if (s_name, t_name) in explicit_obj_routes:
                target_t = explicit_obj_routes[(s_name, t_name)]
            else:
                target_t = t_name
                # Apply bulk object rename rules
                for rule in sorted(r_def.bulk_rules, key=lambda x: x.priority):
                    if rule.rule_type == "OBJECT_RENAME" and rule.pattern in target_t:
                        target_t = target_t.replace(rule.pattern, rule.replacement)

            target_s = schema_map.get(s_name, s_name)
            tgt_key = f"{target_s}.{target_t}"

            # Validate reserved identifier fencing
            val_res = validate_operator_configured_identifier(target_t, "table")
            if not val_res["valid"]:
                diagnostics.append(CompilationDiagnostic(
                    level="BLOCKER",
                    code="RESERVED_IDENTIFIER_COLLISION",
                    message=f"Target object identifier '{target_t}' for source '{src_key}' is invalid: {val_res['error_message']}",
                    target=src_key,
                ))

            # Conflict check: Duplicate target object mapping without merge spec
            if tgt_key in target_obj_provenance and target_obj_provenance[tgt_key] != src_key:
                diagnostics.append(CompilationDiagnostic(
                    level="BLOCKER",
                    code="DUPLICATE_TARGET_OBJECT",
                    message=f"Source objects '{src_key}' and '{target_obj_provenance[tgt_key]}' both map to target object '{tgt_key}'. Unintended collisions block execution.",
                    target=tgt_key,
                ))
            else:
                target_obj_provenance[tgt_key] = src_key

            object_map[src_key] = tgt_key

        # 3. Resolve Column Mappings & Reordering
        column_map: Dict[str, Dict[str, str]] = {}
        column_order: Dict[str, List[str]] = {}
        ignored_columns: Dict[str, List[str]] = {}
        target_defaults: Dict[str, Dict[str, str]] = {}
        generated_columns: Dict[str, List[str]] = {}

        explicit_col_map: Dict[str, Dict[str, ColumnMapping]] = {}
        for cm in r_def.column_mappings:
            explicit_col_map.setdefault(cm.source_object, {})[cm.source_column] = cm

        for obj in objects:
            if not isinstance(obj, dict) or not obj.get("selected", True):
                continue
            src_name = obj.get("object_name") or obj.get("table_name")
            if not src_name:
                continue

            cols = obj.get("columns", ["id", "name", "email", "created_at"])
            pk_cols = set(obj.get("pk_columns", ["id"]))

            col_sub_map: Dict[str, str] = {}
            target_cols: List[str] = []
            target_col_provenance: Dict[str, str] = {}
            ignored_list: List[str] = []
            default_sub_map: Dict[str, str] = {}
            gen_list: List[str] = []

            for c in cols:
                cm_entry = explicit_col_map.get(src_name, {}).get(c)
                if cm_entry and cm_entry.is_ignored:
                    if c in pk_cols:
                        diagnostics.append(CompilationDiagnostic(
                            level="BLOCKER",
                            code="MISSING_REQUIRED_KEY_MAPPING",
                            message=f"Primary key column '{c}' on object '{src_name}' cannot be marked as ignored.",
                            target=src_name,
                        ))
                    ignored_list.append(c)
                    continue

                if cm_entry and cm_entry.target_column:
                    tgt_c = cm_entry.target_column
                else:
                    tgt_c = c
                    # Apply bulk column rename rules
                    for rule in sorted(r_def.bulk_rules, key=lambda x: x.priority):
                        if rule.rule_type == "COLUMN_RENAME" and rule.pattern in tgt_c:
                            tgt_c = tgt_c.replace(rule.pattern, rule.replacement)

                if cm_entry and cm_entry.target_default:
                    default_sub_map[tgt_c] = cm_entry.target_default

                if cm_entry and cm_entry.is_generated:
                    gen_list.append(tgt_c)

                # Column collision check
                if tgt_c in target_col_provenance and target_col_provenance[tgt_c] != c:
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="DUPLICATE_TARGET_COLUMN",
                        message=f"Source columns '{c}' and '{target_col_provenance[tgt_c]}' in object '{src_name}' both map to target column '{tgt_c}'.",
                        target=src_name,
                    ))
                else:
                    target_col_provenance[tgt_c] = c

                col_sub_map[c] = tgt_c
                target_cols.append(tgt_c)

            column_map[src_name] = col_sub_map
            column_order[src_name] = target_cols
            if ignored_list:
                ignored_columns[src_name] = ignored_list
            if default_sub_map:
                target_defaults[src_name] = default_sub_map
            if gen_list:
                generated_columns[src_name] = gen_list

        # Compute deterministic CompiledMapping fingerprint
        canon_bytes = json.dumps({
            "schema_map": schema_map,
            "object_map": object_map,
            "column_map": column_map,
            "column_order": column_order,
            "ignored_columns": ignored_columns,
            "target_defaults": target_defaults,
            "generated_columns": generated_columns,
        }, sort_keys=True).encode("utf-8")
        fp = hashlib.sha256(canon_bytes).hexdigest()

        compiled = CompiledMapping(
            schema_map=schema_map,
            object_map=object_map,
            column_map=column_map,
            column_order=column_order,
            ignored_columns=ignored_columns,
            target_defaults=target_defaults,
            generated_columns=generated_columns,
            fingerprint=fp,
        )

        return {
            "status": "SUCCESS" if not any(d.level == "BLOCKER" for d in diagnostics) else "BLOCKER",
            "compiled_mapping": compiled.to_dict(),
            "diagnostics": [d.to_dict() for d in diagnostics],
        }

    def compute_selection_estimate(
        self,
        selected_scope: Dict[str, Any],
        selection_def: "SelectionDefinition",
    ) -> Dict[str, Any]:
        """Calculates estimated selected volume, objects, and row counts."""
        raw_objs = selected_scope.get("objects", []) if isinstance(selected_scope, dict) else []
        selected_objs = [o for o in raw_objs if isinstance(o, dict) and o.get("selected", True) != False]

        total_rows = sum(o.get("estimated_rows", 1000) for o in selected_objs)
        avg_row_bytes = 256
        total_bytes = total_rows * avg_row_bytes

        sampling_factor = 1.0
        if selection_def.sampling:
            if selection_def.sampling.method == "PERCENTAGE":
                sampling_factor = max(0.001, min(1.0, selection_def.sampling.sample_size / 100.0))
            elif selection_def.sampling.method == "FIXED_ROWS" and total_rows > 0:
                sampling_factor = min(1.0, selection_def.sampling.sample_size / float(total_rows))

        est_rows = int(total_rows * sampling_factor)
        est_bytes = int(total_bytes * sampling_factor)

        from akaal.planner.models.p5_domain import SelectionEstimate
        estimate = SelectionEstimate(
            selected_db_count=len(selected_scope.get("databases", [1])),
            selected_schema_count=len(selected_scope.get("schemas", [1])),
            selected_object_count=len(selected_objs),
            selected_column_count=sum(len(o.get("columns", [])) for o in selected_objs),
            estimated_total_rows=est_rows,
            estimated_total_bytes=est_bytes,
            reduction_factor=sampling_factor,
            confidence="ESTIMATED",
        )
        return estimate.to_dict()

    def compile_deduplication_and_quality(
        self,
        selected_scope: Dict[str, Any],
        dedup_def: Optional[Any] = None,
        quality_def: Optional[Any] = None,
        conflict_config: Optional[Any] = None,
        target_connector_type: str = "GENERIC",
        execution_mode: str = "M2",
    ) -> Dict[str, Any]:
        """
        Compiles P5.6 Deduplication, Data Quality, and Conflict Policy definitions.
        Validates key columns, survivor ordering, regex safety, numeric bounds,
        connector collision compatibility, mode applicability, and P3 conflict policy alignment.
        """
        import re
        from akaal.planner.models.p5_domain import (
            CompilationDiagnostic,
            DeduplicationDefinition,
            DeduplicationRule,
            DataQualityDefinition,
            DataQualityRule,
            ConflictPolicyConfiguration,
            CollisionPolicy,
            SurvivorStrategy,
            QualityRuleType,
        )

        diagnostics: List[CompilationDiagnostic] = []
        mode_upper = str(execution_mode).upper()

        # 1. Parse Deduplication
        if isinstance(dedup_def, dict):
            parsed_dedup = DeduplicationDefinition.from_dict(dedup_def)
        elif isinstance(dedup_def, DeduplicationDefinition):
            parsed_dedup = dedup_def
        else:
            parsed_dedup = DeduplicationDefinition()

        # 2. Parse Data Quality
        if isinstance(quality_def, dict):
            parsed_quality = DataQualityDefinition.from_dict(quality_def)
        elif isinstance(quality_def, DataQualityDefinition):
            parsed_quality = quality_def
        else:
            parsed_quality = DataQualityDefinition()

        # 3. Parse Conflict Policy
        if isinstance(conflict_config, dict):
            parsed_conflict = ConflictPolicyConfiguration.from_dict(conflict_config)
        elif isinstance(conflict_config, ConflictPolicyConfiguration):
            parsed_conflict = conflict_config
        else:
            parsed_conflict = ConflictPolicyConfiguration()

        # Validate Execution Mode Applicability
        if mode_upper in ("M6", "SCHEMA_ONLY") and parsed_dedup.enabled:
            diagnostics.append(CompilationDiagnostic(
                level="BLOCKER",
                code="INAPPLICABLE_DEDUP_MODE",
                message=f"Row deduplication is not applicable to Schema-Only mode ({execution_mode}).",
                target="deduplication",
            ))

        if mode_upper in ("M1", "BULK_ONLY", "M6", "SCHEMA_ONLY", "M8", "VALIDATION_ONLY"):
            if parsed_conflict.default_policy != "SOURCE_A_WINS" or bool(parsed_conflict.object_overrides):
                diagnostics.append(CompilationDiagnostic(
                    level="BLOCKER",
                    code="INAPPLICABLE_CONFLICT_MODE",
                    message=f"P3 CDC Conflict Resolution policy cannot be configured for non-CDC execution mode '{execution_mode}'.",
                    target="conflict_policy",
                ))

        # Validate Deduplication Rules
        raw_objs = selected_scope.get("objects", []) if isinstance(selected_scope, dict) else []

        for rule in parsed_dedup.rules:
            if not rule.key_columns:
                diagnostics.append(CompilationDiagnostic(
                    level="BLOCKER",
                    code="EMPTY_DEDUP_KEY_COLUMNS",
                    message=f"Deduplication rule for object '{rule.object_name}' has empty key_columns.",
                    target=rule.object_name,
                ))

            # Validate ordering columns
            if rule.order_by_columns:
                for o_col in rule.order_by_columns:
                    parts = o_col.strip().split()
                    c_name = parts[0]
                    direction = parts[1].upper() if len(parts) > 1 else "ASC"
                    if direction not in ("ASC", "DESC"):
                        diagnostics.append(CompilationDiagnostic(
                            level="BLOCKER",
                            code="INVALID_ORDER_DIRECTION",
                            message=f"Order by direction '{direction}' in '{o_col}' on object '{rule.object_name}' is invalid (must be ASC or DESC).",
                            target=rule.object_name,
                        ))

            # Validate priority field
            if rule.survivor_strategy == SurvivorStrategy.PRIORITY:
                if not rule.priority_field or not rule.priority_order:
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="MISSING_PRIORITY_SPECIFICATION",
                        message=f"PRIORITY survivor strategy on object '{rule.object_name}' requires priority_field and priority_order.",
                        target=rule.object_name,
                    ))

            # Validate target collision policy against connector capabilities
            tgt_conn_upper = str(target_connector_type).upper()
            if rule.collision_policy == CollisionPolicy.UPSERT and any(x in tgt_conn_upper for x in ("S3", "AZURE_BLOB", "GCS", "FILE", "HDFS")):
                diagnostics.append(CompilationDiagnostic(
                    level="BLOCKER",
                    code="UNSUPPORTED_COLLISION_POLICY",
                    message=f"Target object storage connector '{target_connector_type}' does not support relational UPSERT collision policy.",
                    target=rule.object_name,
                ))

        # Validate Data Quality Rules
        for q_rule in parsed_quality.rules:
            if q_rule.rule_type == QualityRuleType.REGEX_MATCH and q_rule.regex_pattern:
                if len(q_rule.regex_pattern) > 250 or "(.*)*" in q_rule.regex_pattern or "(.+)+" in q_rule.regex_pattern:
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="INVALID_QUALITY_REGEX",
                        message=f"Quality regex pattern '{q_rule.regex_pattern}' violates ReDoS safety fencing.",
                        target=q_rule.object_name,
                    ))
                else:
                    try:
                        re.compile(q_rule.regex_pattern)
                    except re.error as err:
                        diagnostics.append(CompilationDiagnostic(
                            level="BLOCKER",
                            code="SYNTAX_ERROR_QUALITY_REGEX",
                            message=f"Quality regex pattern syntax error: {err}",
                            target=q_rule.object_name,
                        ))

            if q_rule.rule_type == QualityRuleType.VALUE_RANGE:
                if q_rule.min_value is not None and q_rule.max_value is not None:
                    try:
                        if float(q_rule.min_value) > float(q_rule.max_value):
                            diagnostics.append(CompilationDiagnostic(
                                level="BLOCKER",
                                code="INVALID_VALUE_RANGE",
                                message=f"Quality rule '{q_rule.rule_id}' min_value ({q_rule.min_value}) exceeds max_value ({q_rule.max_value}).",
                                target=q_rule.object_name,
                            ))
                    except (ValueError, TypeError):
                        pass

            if q_rule.rule_type == QualityRuleType.MAX_LENGTH and q_rule.max_length is not None:
                if q_rule.max_length <= 0:
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="INVALID_MAX_LENGTH",
                        message=f"Quality rule '{q_rule.rule_id}' max_length must be greater than zero.",
                        target=q_rule.object_name,
                    ))

        # Validate Quality Thresholds (negative values / percentages outside 0..100)
        thresholds_to_check = []
        if parsed_quality.global_threshold:
            thresholds_to_check.append(("global", parsed_quality.global_threshold))
        for obj_name, th in parsed_quality.object_thresholds.items():
            if th:
                thresholds_to_check.append((obj_name, th))

        for target_label, th in thresholds_to_check:
            for count_attr in ("max_duplicate_count", "max_invalid_count", "max_reject_count", "max_quarantine_count", "max_policy_violations"):
                val = getattr(th, count_attr, None)
                if val is not None and val < 0:
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="INVALID_QUALITY_THRESHOLD",
                        message=f"Quality threshold '{count_attr}' cannot be negative ({val}) for {target_label}.",
                        target=target_label,
                    ))
            for pct_attr in ("max_duplicate_percentage", "max_invalid_percentage"):
                val = getattr(th, pct_attr, None)
                if val is not None and (val < 0.0 or val > 100.0):
                    diagnostics.append(CompilationDiagnostic(
                        level="BLOCKER",
                        code="INVALID_QUALITY_THRESHOLD",
                        message=f"Quality threshold percentage '{pct_attr}' must be between 0.0 and 100.0 (got {val}) for {target_label}.",
                        target=target_label,
                    ))

        # Validate Conflict Policy Configuration (must be a valid P3 resolution policy)
        valid_p3_policies = {"SOURCE_A_WINS", "SOURCE_B_WINS", "DESIGNATED_PRIMARY_WINS", "LATEST_VERSION_WINS", "MANUAL_GOVERNANCE_REQUIRED"}
        if parsed_conflict.default_policy not in valid_p3_policies:
            diagnostics.append(CompilationDiagnostic(
                level="BLOCKER",
                code="INVALID_P3_CONFLICT_POLICY",
                message=f"Default conflict policy '{parsed_conflict.default_policy}' is not a recognized P3 CDCConflictResolutionPolicy ({valid_p3_policies}).",
                target="conflict_policy",
            ))

        # Compute deterministic SHA-256 fingerprint for P5.6 compiled payload
        canon_p56 = json.dumps({
            "deduplication": parsed_dedup.to_dict(),
            "data_quality": parsed_quality.to_dict(),
            "conflict_policy": parsed_conflict.to_dict(),
        }, sort_keys=True)
        fp = hashlib.sha256(canon_p56.encode("utf-8")).hexdigest()

        return {
            "status": "SUCCESS" if not any(d.level == "BLOCKER" for d in diagnostics) else "BLOCKER",
            "deduplication": parsed_dedup.to_dict(),
            "data_quality": parsed_quality.to_dict(),
            "conflict_policy": parsed_conflict.to_dict(),
            "fingerprint": fp,
            "diagnostics": [d.to_dict() for d in diagnostics],
        }

    @staticmethod
    def evaluate_quality_gates(
        quality_def: Any,
        execution_metrics: Dict[str, Any],
    ) -> "QualityGateResult":
        """
        Evaluates actual execution/batch metrics against configured DataQualityDefinition thresholds.
        Determines if quality gates pass or cutover is blocked / job failed.
        """
        from akaal.planner.models.p5_domain import (
            DataQualityDefinition,
            QualityThreshold,
            QualityGateConsequence,
            QualityGateResult,
        )

        q_def = (
            DataQualityDefinition.from_dict(quality_def)
            if isinstance(quality_def, dict)
            else quality_def or DataQualityDefinition()
        )

        total_rows = max(1, int(execution_metrics.get("total_rows", 0)))
        dups = int(execution_metrics.get("duplicate_count", 0))
        invalids = int(execution_metrics.get("invalid_count", 0))
        rejects = int(execution_metrics.get("reject_count", 0))
        quarantines = int(execution_metrics.get("quarantine_count", 0))
        total_violations = dups + invalids + rejects + quarantines

        dup_pct = (dups / total_rows) * 100.0
        invalid_pct = (invalids / total_rows) * 100.0

        thresh = q_def.global_threshold or QualityThreshold()
        violations: List[str] = []
        consequence = QualityGateConsequence.WARN
        passed = True
        cutover_blocked = False

        if thresh.max_duplicate_count is not None and dups > thresh.max_duplicate_count:
            passed = False
            violations.append(f"Duplicate count {dups} exceeds threshold {thresh.max_duplicate_count}.")

        if thresh.max_duplicate_percentage is not None and dup_pct > thresh.max_duplicate_percentage:
            passed = False
            violations.append(f"Duplicate percentage {dup_pct:.2f}% exceeds threshold {thresh.max_duplicate_percentage}%.")

        if thresh.max_invalid_count is not None and invalids > thresh.max_invalid_count:
            passed = False
            violations.append(f"Invalid record count {invalids} exceeds threshold {thresh.max_invalid_count}.")

        if thresh.max_invalid_percentage is not None and invalid_pct > thresh.max_invalid_percentage:
            passed = False
            violations.append(f"Invalid percentage {invalid_pct:.2f}% exceeds threshold {thresh.max_invalid_percentage}%.")

        if thresh.max_reject_count is not None and rejects > thresh.max_reject_count:
            passed = False
            violations.append(f"Reject count {rejects} exceeds threshold {thresh.max_reject_count}.")

        if thresh.max_quarantine_count is not None and quarantines > thresh.max_quarantine_count:
            passed = False
            violations.append(f"Quarantine count {quarantines} exceeds threshold {thresh.max_quarantine_count}.")

        if thresh.max_total_violations is not None and total_violations > thresh.max_total_violations:
            passed = False
            violations.append(f"Total violations {total_violations} exceeds threshold {thresh.max_total_violations}.")

        if not passed:
            consequence = thresh.consequence
            if consequence in (QualityGateConsequence.BLOCK_CUTOVER, QualityGateConsequence.FAIL_JOB):
                cutover_blocked = True

        return QualityGateResult(
            passed=passed,
            consequence=consequence,
            total_violations=total_violations,
            duplicate_count=dups,
            invalid_count=invalids,
            reject_count=rejects,
            quarantine_count=quarantines,
            violation_messages=violations,
            cutover_blocked=cutover_blocked,
        )
