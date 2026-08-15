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
        source_manifest: Optional[UniversalCapabilityManifest],
        target_manifest: Optional[UniversalCapabilityManifest],
    ) -> Dict[str, Any]:
        """
        Evaluates source-to-target semantic compatibility.
        Returns compatibility status, limitations, required mappings, and risk items.
        Fails closed on missing or malformed manifests.
        """
        if not source_manifest or not isinstance(source_manifest, UniversalCapabilityManifest):
            return {
                "compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason": "Invalid or missing Source capability manifest.",
                "limitations": ["Source manifest missing or invalid"],
                "required_mappings": [],
                "risk_items": ["INVALID_SOURCE_MANIFEST"],
            }

        if not target_manifest or not isinstance(target_manifest, UniversalCapabilityManifest):
            return {
                "compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason": "Invalid or missing Target capability manifest.",
                "limitations": ["Target manifest missing or invalid"],
                "required_mappings": [],
                "risk_items": ["INVALID_TARGET_MANIFEST"],
            }

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

        # 2. Same-Family Homogeneous vs Heterogeneous Relational
        if src_family == ConnectorFamily.RELATIONAL_DATABASE and tgt_family == ConnectorFamily.RELATIONAL_DATABASE:
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

        # 3. Relational -> Cloud Data Warehouse / Lakehouse
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

        # 4. Warehouse -> Relational (Reverse ETL / Analytical to OLTP)
        if src_family in (ConnectorFamily.CLOUD_DATA_WAREHOUSE, ConnectorFamily.LAKEHOUSE_ANALYTICS) and tgt_family == ConnectorFamily.RELATIONAL_DATABASE:
            required_mappings.append("ANALYTIC_TO_RELATIONAL_SCHEMA_MAPPING")
            limitations.append("Data warehouse tables may lack primary keys required for operational OLTP constraints.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value,
                "is_viable": True,
                "reason": f"Warehouse to Relational migration ({source_manifest.connector_id} -> {target_manifest.connector_id}).",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["MISSING_OLTP_PRIMARY_KEYS"],
            }

        # 4b. Warehouse <-> Warehouse & Warehouse <-> Lakehouse
        if src_family in (ConnectorFamily.CLOUD_DATA_WAREHOUSE, ConnectorFamily.LAKEHOUSE_ANALYTICS) and tgt_family in (ConnectorFamily.CLOUD_DATA_WAREHOUSE, ConnectorFamily.LAKEHOUSE_ANALYTICS):
            if source_manifest.system_type == target_manifest.system_type:
                return {
                    "compatibility": SemanticCompatibility.SUPPORTED.value,
                    "is_viable": True,
                    "reason": f"Homogeneous analytical migration ({source_manifest.system_type} -> {target_manifest.system_type}).",
                    "limitations": [],
                    "required_mappings": [],
                    "risk_items": [],
                }
            required_mappings.append("ANALYTICAL_DIALECT_AND_STAGING_CONVERSION")
            limitations.append("Requires cloud object staging coordination (e.g. S3/GCS/ADLS) for bulk transfer.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_MAPPING.value,
                "is_viable": True,
                "reason": f"Cross-warehouse/lakehouse migration ({source_manifest.connector_id} -> {target_manifest.connector_id}).",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["STAGED_TRANSFER_REQUIRED"],
            }

        # 5. Relational -> Document (e.g. Oracle/Postgres -> MongoDB)
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

        # 6. Document -> Relational (e.g. MongoDB -> Postgres)
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

        # 7. Relational -> Graph (e.g. Postgres -> Neo4j)
        if src_family == ConnectorFamily.RELATIONAL_DATABASE and tgt_family == ConnectorFamily.GRAPH_DATABASE:
            required_mappings.append("RELATIONAL_FOREIGN_KEYS_TO_GRAPH_EDGES_MAPPING")
            limitations.append("Requires entity-relationship mapping to graph node labels and edge types.")
            return {
                "compatibility": SemanticCompatibility.LOSSY_REQUIRES_APPROVAL.value,
                "is_viable": True,
                "reason": "Relational to Graph migration requires graph topology approval.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["GRAPH_MODEL_TRANSFORMATION"],
            }

        # 8. Graph -> Relational (e.g. Neo4j -> Postgres)
        if src_family == ConnectorFamily.GRAPH_DATABASE and tgt_family == ConnectorFamily.RELATIONAL_DATABASE:
            required_mappings.append("GRAPH_NODES_AND_EDGES_TO_RELATIONAL_TABLES")
            limitations.append("Graph relationships mapped to adjacency foreign key junction tables.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_MAPPING.value,
                "is_viable": True,
                "reason": "Graph to Relational migration supported via tabular normalization.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["GRAPH_TABULAR_NORMALIZATION"],
            }

        # 9. Stream -> Relational / Warehouse (e.g. Kafka -> Postgres/Snowflake)
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

        # 10. Relational / Warehouse -> Stream (e.g. Postgres -> Kafka)
        if src_family in (ConnectorFamily.RELATIONAL_DATABASE, ConnectorFamily.CLOUD_DATA_WAREHOUSE) and tgt_family == ConnectorFamily.STREAM_EVENT_PLATFORM:
            required_mappings.append("TABLE_ROW_TO_EVENT_ENVELOPE_MAPPING")
            limitations.append("Relational table rows published as individual change events or JSON/Avro payloads.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value,
                "is_viable": True,
                "reason": "Table data publication to event stream destination.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["TABLE_TO_EVENT_CONVERSION"],
            }

        # 11. Object Storage -> Relational / Warehouse (e.g. S3 / GCS / Azure Blob -> Postgres/Snowflake)
        if src_family in (ConnectorFamily.OBJECT_STORAGE, ConnectorFamily.DISTRIBUTED_FILESYSTEM, ConnectorFamily.FILE_DATASET) and tgt_family in (ConnectorFamily.RELATIONAL_DATABASE, ConnectorFamily.CLOUD_DATA_WAREHOUSE):
            required_mappings.append("FILE_FORMAT_PARSER_CSV_PARQUET_JSON")
            limitations.append("Object store files require schema extraction and format parsing.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value,
                "is_viable": True,
                "reason": "Object storage dataset ingestion into database/warehouse.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["FILE_PARSING_SCHEMA_DRIFT"],
            }

        # 12. Relational -> Wide-Column (e.g. Postgres -> Cassandra)
        if src_family == ConnectorFamily.RELATIONAL_DATABASE and tgt_family == ConnectorFamily.WIDE_COLUMN_DATABASE:
            required_mappings.append("RELATIONAL_TO_WIDE_COLUMN_PARTITION_KEY_MAPPING")
            limitations.append("Cassandra/ScyllaDB requires explicit partition and clustering keys for query performance.")
            return {
                "compatibility": SemanticCompatibility.LOSSY_REQUIRES_APPROVAL.value,
                "is_viable": True,
                "reason": "Relational to Wide-Column migration requires partition key design approval.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["WIDE_COLUMN_DATA_MODELING"],
            }

        # 13. Wide-Column -> Relational (e.g. Cassandra -> Postgres)
        if src_family == ConnectorFamily.WIDE_COLUMN_DATABASE and tgt_family == ConnectorFamily.RELATIONAL_DATABASE:
            required_mappings.append("WIDE_COLUMN_TABLE_TO_RELATIONAL_SCHEMA")
            limitations.append("Wide-column types and collection types require normalized column mapping.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_MAPPING.value,
                "is_viable": True,
                "reason": "Wide-Column to Relational migration supported via table mapping.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["COLLECTION_COLUMN_EXPANSION"],
            }

        # 14. Key-Value -> Relational (e.g. Redis -> Postgres)
        if src_family == ConnectorFamily.KEY_VALUE_STORE and tgt_family == ConnectorFamily.RELATIONAL_DATABASE:
            required_mappings.append("KEY_VALUE_PAIRS_TO_STRUCTURED_COLUMNS")
            limitations.append("Key-value entries must be parsed into typed relational columns.")
            return {
                "compatibility": SemanticCompatibility.SUPPORTED_WITH_MAPPING.value,
                "is_viable": True,
                "reason": "Key-Value store to Relational migration.",
                "limitations": limitations,
                "required_mappings": required_mappings,
                "risk_items": ["KEY_VALUE_PARSING"],
            }

        # Default fallback for unproven combinations: STRICT FAIL-CLOSED
        return {
            "compatibility": SemanticCompatibility.NOT_YET_PROVEN.value,
            "is_viable": False,
            "reason": f"Migration path from '{src_family.value}' to '{tgt_family.value}' is not yet proven.",
            "limitations": [f"Unproven cross-family migration: {src_family.value} -> {tgt_family.value}"],
            "required_mappings": ["CUSTOM_ADAPTER_OR_MANUAL_PIPELINE"],
            "risk_items": ["UNPROVEN_CROSS_FAMILY_PATH"],
        }
