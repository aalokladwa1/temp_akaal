"""
Akaal — Canonical Connector Capability Contract (P4.8)
=====================================================
Defines the canonical contract declared ONCE per connector family / system type.
Exposes structured Source, Target, CDC, Schema, and Validation capabilities for O(N) compatibility reasoning.
"""

from typing import Dict, Any, Optional, List, Set
from akaal.connectors.taxonomy import ConnectorFamily, SupportState, ImplementationState
from akaal.connectors.datatype_semantics import SemanticDatatypeFamily


class SourceCapabilitySpec:
    def __init__(
        self,
        snapshot_extraction: bool = True,
        deterministic_pagination: bool = True,
        range_extraction: bool = True,
        parallel_reads: bool = True,
        cdc_available: bool = False,
        cdc_mechanism: str = "NONE",  # LOG_BASED, TRIGGER_BASED, TIMESTAMP_BASED, NONE
        cdc_position_type: str = "NONE",  # LSN, SCN, BINLOG_OFFSET, GTID, RESUME_TOKEN, PARTITION_OFFSET, NONE
        before_image_available: bool = False,
        ddl_capture: bool = False,
        delete_capture: bool = False,
        lob_streaming: bool = True,
        nested_structures: bool = False,
        timezone_aware: bool = True,
    ) -> None:
        self.snapshot_extraction = snapshot_extraction
        self.deterministic_pagination = deterministic_pagination
        self.range_extraction = range_extraction
        self.parallel_reads = parallel_reads
        self.cdc_available = cdc_available
        self.cdc_mechanism = cdc_mechanism
        self.cdc_position_type = cdc_position_type
        self.before_image_available = before_image_available
        self.ddl_capture = ddl_capture
        self.delete_capture = delete_capture
        self.lob_streaming = lob_streaming
        self.nested_structures = nested_structures
        self.timezone_aware = timezone_aware

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_extraction": self.snapshot_extraction,
            "deterministic_pagination": self.deterministic_pagination,
            "range_extraction": self.range_extraction,
            "parallel_reads": self.parallel_reads,
            "cdc_available": self.cdc_available,
            "cdc_mechanism": self.cdc_mechanism,
            "cdc_position_type": self.cdc_position_type,
            "before_image_available": self.before_image_available,
            "ddl_capture": self.ddl_capture,
            "delete_capture": self.delete_capture,
            "lob_streaming": self.lob_streaming,
            "nested_structures": self.nested_structures,
            "timezone_aware": self.timezone_aware,
        }


class TargetCapabilitySpec:
    def __init__(
        self,
        bulk_ingestion: bool = True,
        batch_inserts: bool = True,
        native_loaders: bool = False,
        upsert: bool = False,
        merge: bool = False,
        delete_application: bool = True,
        transaction_support: bool = True,
        transactional_ddl: bool = False,
        constraint_creation: bool = True,
        deferred_constraints: bool = False,
        indexes: bool = True,
        partitions: bool = False,
        cdc_event_application: bool = False,
        idempotent_replay: bool = False,
        schema_evolution: bool = True,
        nested_structures: bool = False,
        max_decimal_precision: int = 38,
    ) -> None:
        self.bulk_ingestion = bulk_ingestion
        self.batch_inserts = batch_inserts
        self.native_loaders = native_loaders
        self.upsert = upsert
        self.merge = merge
        self.delete_application = delete_application
        self.transaction_support = transaction_support
        self.transactional_ddl = transactional_ddl
        self.constraint_creation = constraint_creation
        self.deferred_constraints = deferred_constraints
        self.indexes = indexes
        self.partitions = partitions
        self.cdc_event_application = cdc_event_application
        self.idempotent_replay = idempotent_replay
        self.schema_evolution = schema_evolution
        self.nested_structures = nested_structures
        self.max_decimal_precision = max_decimal_precision

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bulk_ingestion": self.bulk_ingestion,
            "batch_inserts": self.batch_inserts,
            "native_loaders": self.native_loaders,
            "upsert": self.upsert,
            "merge": self.merge,
            "delete_application": self.delete_application,
            "transaction_support": self.transaction_support,
            "transactional_ddl": self.transactional_ddl,
            "constraint_creation": self.constraint_creation,
            "deferred_constraints": self.deferred_constraints,
            "indexes": self.indexes,
            "partitions": self.partitions,
            "cdc_event_application": self.cdc_event_application,
            "idempotent_replay": self.idempotent_replay,
            "schema_evolution": self.schema_evolution,
            "nested_structures": self.nested_structures,
            "max_decimal_precision": self.max_decimal_precision,
        }


class ValidationCapabilitySpec:
    def __init__(
        self,
        row_count: bool = True,
        checksum: bool = True,
        hash_comparison: bool = True,
        column_comparison: bool = True,
        sampled_comparison: bool = True,
        cdc_reconciliation: bool = False,
    ) -> None:
        self.row_count = row_count
        self.checksum = checksum
        self.hash_comparison = hash_comparison
        self.column_comparison = column_comparison
        self.sampled_comparison = sampled_comparison
        self.cdc_reconciliation = cdc_reconciliation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_count": self.row_count,
            "checksum": self.checksum,
            "hash_comparison": self.hash_comparison,
            "column_comparison": self.column_comparison,
            "sampled_comparison": self.sampled_comparison,
            "cdc_reconciliation": self.cdc_reconciliation,
        }


class ConnectorCapabilityContract:
    """Canonical Capability Contract declared ONCE per connector system."""

    def __init__(
        self,
        connector_id: str,
        system_type: str,
        family: ConnectorFamily,
        source_spec: Optional[SourceCapabilitySpec] = None,
        target_spec: Optional[TargetCapabilitySpec] = None,
        validation_spec: Optional[ValidationCapabilitySpec] = None,
        supported_semantic_types: Optional[List[SemanticDatatypeFamily]] = None,
        support_state: SupportState = SupportState.SUPPORTED,
        implementation_state: ImplementationState = ImplementationState.IMPLEMENTED,
    ) -> None:
        self.connector_id = connector_id.lower()
        self.system_type = system_type.upper()
        self.family = ConnectorFamily(family)
        self.source_spec = source_spec or SourceCapabilitySpec()
        self.target_spec = target_spec or TargetCapabilitySpec()
        self.validation_spec = validation_spec or ValidationCapabilitySpec()
        self.supported_semantic_types = set(supported_semantic_types or [
            SemanticDatatypeFamily.INTEGER,
            SemanticDatatypeFamily.FIXED_DECIMAL,
            SemanticDatatypeFamily.FLOATING_POINT,
            SemanticDatatypeFamily.VARIABLE_STRING,
            SemanticDatatypeFamily.DATE,
            SemanticDatatypeFamily.TIMESTAMP,
            SemanticDatatypeFamily.BOOLEAN,
        ])
        self.support_state = SupportState(support_state)
        self.implementation_state = ImplementationState(implementation_state)

    def is_type_supported(self, semantic_type: SemanticDatatypeFamily) -> bool:
        return semantic_type in self.supported_semantic_types

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "system_type": self.system_type,
            "family": self.family.value,
            "source_spec": self.source_spec.to_dict(),
            "target_spec": self.target_spec.to_dict(),
            "validation_spec": self.validation_spec.to_dict(),
            "supported_semantic_types": [t.value for t in self.supported_semantic_types],
            "support_state": self.support_state.value,
            "implementation_state": self.implementation_state.value,
        }
