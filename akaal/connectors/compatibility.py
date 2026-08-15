"""
AKAAL Cross-System Semantic Compatibility & Safety Engine (P4.1).
==================================================================
Evaluates source-to-target migration feasibility, semantic differences,
datatype lossiness, transaction semantics, ordering, and constraints.
Enforces fail-closed protection against invalid cross-system assumptions.
"""

from typing import Dict, Any, List, Optional
import logging

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    SemanticCompatibility,
)
from akaal.connectors.manifest import UniversalCapabilityManifest

logger = logging.getLogger("akaal.connectors.compatibility")


class SemanticCompatibilityMatrix:
    """
    Evaluates cross-system semantic compatibility between Source and Target manifests.
    Ensures safe migration planning without assuming all N x N migrations work out of the box.
    """

    @classmethod
    def evaluate_compatibility(
        cls,
        source_manifest: UniversalCapabilityManifest,
        target_manifest: UniversalCapabilityManifest,
    ) -> Dict[str, Any]:
        """
        Evaluates source-to-target semantic compatibility.
        Returns compatibility status, limitations, required mappings, and risk items.
        """
        src_family = source_manifest.family
        tgt_family = target_manifest.family

        limitations: List[str] = []
        required_mappings: List[str] = []
        risk_items: List[str] = []

        # 1. Check Role Feasibility
        if not source_manifest.is_source_capable():
            return {
                "compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason": f"Source connector '{source_manifest.connector_id}' does not support SOURCE role.",
                "limitations": [f"Source role unsupported for '{source_manifest.connector_id}'"],
                "required_mappings": [],
                "risk_items": ["UNSUPPORTED_ROLE"],
            }

        if not target_manifest.is_target_capable():
            return {
                "compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason": f"Target connector '{target_manifest.connector_id}' does not support TARGET role.",
                "limitations": [f"Target role unsupported for '{target_manifest.connector_id}'"],
                "required_mappings": [],
                "risk_items": ["UNSUPPORTED_ROLE"],
            }

        # 2. Same-Family Compatibility
        if src_family == tgt_family:
            if src_family == ConnectorFamily.RELATIONAL_DATABASE:
                if source_manifest.system_type == target_manifest.system_type:
                    return {
                        "compatibility": SemanticCompatibility.SUPPORTED.value,
                        "is_viable": True,
                        "reason": f"Homogeneous relational migration ({source_manifest.system_type} -> {target_manifest.system_type}).",
                        "limitations": [],
                        "required_mappings": [],
                        "risk_items": [],
                    }
                else:
                    required_mappings.append("SQL_DIALECT_DATATYPE_CONVERSION")
                    limitations.append("Stored procedures, triggers, and sequences require dialect translation.")
                    return {
                        "compatibility": SemanticCompatibility.SUPPORTED_WITH_MAPPING.value,
                        "is_viable": True,
                        "reason": f"Heterogeneous relational migration ({source_manifest.system_type} -> {target_manifest.system_type}).",
                        "limitations": limitations,
                        "required_mappings": required_mappings,
                        "risk_items": ["HETEROGENEOUS_DIALECT_DIFF"],
                    }

        # 3. Relational -> Warehouse (e.g. Postgres -> Snowflake/BigQuery/Redshift)
        if src_family == ConnectorFamily.RELATIONAL_DATABASE and tgt_family in (ConnectorFamily.CLOUD_DATA_WAREHOUSE, ConnectorFamily.LAKEHOUSE_ANALYTICS):
            required_mappings.append("RELATIONAL_TO_ANALYTIC_SCHEMA_MAPPING")
            limitations.append("Target data warehouse does not enforce OLTP foreign key constraints or triggers.")
            limitations.append("Transactions use micro-batch or analytical isolation semantics.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value,
                "is_viable": True,
                "reason": f"Relational to Cloud Warehouse migration ({source_manifest.connector_id} -> {target_manifest.connector_id}).",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["OLTP_TO_OLAP_SEMANTIC_MISMATCH"],
            }

        # 4. Relational -> Document (e.g. Oracle/Postgres -> MongoDB)
        if src_family == ConnectorFamily.RELATIONAL_DATABASE and tgt_family == ConnectorFamily.DOCUMENT_DATABASE:
            required_mappings.append("RELATIONAL_TABLES_TO_DOCUMENT_COLLECTIONS_MAPPING")
            limitations.append("Relational FK joins must be denormalized or converted into embedded subdocuments/references.")
            return {
                "compatibility": SemanticCompatibility.LOSSY_REQUIRES_APPROVAL.value,
                "is_viable": True,
                "reason": "Relational to Document migration requires structural document modeling approval.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["SCHEMA_PARADIGM_CHANGE"],
            }

        # 5. Document -> Relational (e.g. MongoDB -> Postgres)
        if src_family == ConnectorFamily.DOCUMENT_DATABASE and tgt_family == ConnectorFamily.RELATIONAL_DATABASE:
            required_mappings.append("UNSTRUCTURED_DOCUMENT_TO_RELATIONAL_SCHEMA_MAPPING")
            limitations.append("Dynamic document fields and heterogeneous schema types require flattening or JSONB mapping.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_MAPPING.value,
                "is_viable": True,
                "reason": "Document to Relational migration supported via schema normalization/JSONB column mapping.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["DYNAMIC_SCHEMA_FLATTENING"],
            }

        # 6. Stream -> Database/Warehouse (e.g. Kafka -> Postgres/Snowflake)
        if src_family == ConnectorFamily.STREAM_EVENT_PLATFORM and tgt_family in (ConnectorFamily.RELATIONAL_DATABASE, ConnectorFamily.CLOUD_DATA_WAREHOUSE):
            required_mappings.append("EVENT_PAYLOAD_TO_TABLE_SCHEMA_MAPPING")
            limitations.append("Event stream consumer commits provide at-least-once or exactly-once streaming semantics.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value,
                "is_viable": True,
                "reason": "Streaming event ingestion into table destination.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["STREAM_OFFSET_ORDERING"],
            }

        # Default fallback for unproven combinations
        return {
            "compatibility": SemanticCompatibility.NOT_YET_PROVEN.value,
            "is_viable": False,
            "reason": f"Migration path from '{src_family.value}' to '{tgt_family.value}' is not yet proven.",
            "limitations": [f"Unproven cross-family migration: {src_family.value} -> {tgt_family.value}"],
            "required_mappings": ["CUSTOM_ADAPTER_OR_MANUAL_PIPELINE"],
            "risk_items": ["UNPROVEN_CROSS_FAMILY_PATH"],
        }
