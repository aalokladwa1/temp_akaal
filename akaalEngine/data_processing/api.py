"""
akaalEngine.data_processing.api
================================
Single Canonical Entrypoint and Façade for Authority #8 — Data Processing (`DataProcessingAuthority`).
"""

import logging
from threading import RLock
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.data_processing.adapters.arrow import ArrowBatchAdapter
from akaalEngine.data_processing.batching.sizer import AdaptiveBatchSizer
from akaalEngine.data_processing.dedup.deduplicator import RowDeduplicator
from akaalEngine.data_processing.engine.compiler import ProcessingPlanCompiler
from akaalEngine.data_processing.engine.lookup_resolver import LookupResolver
from akaalEngine.data_processing.engine.processing_engine import ProcessingEngine
from akaalEngine.data_processing.models import (
    ASTNode,
    ChangeImageResult,
    LookupDefinition,
    ProcessingPlan,
    ProcessingResult,
    TransformationRule,
)

logger = logging.getLogger("akaalEngine.data_processing.api")


class DataProcessingAuthority:
    """
    Single Canonical Façade for Authority #8 — Data Processing.
    Owns in-memory data transformation, expression evaluation, column mapping,
    type coercions, privacy masking, lookup resolution, cleansing, deduplication,
    adaptive batch sizing, PyArrow columnar adapters, and change-image transformations.
    """

    def __init__(
        self,
        telemetry_authority: Optional[Any] = None,
        runtime_authority: Optional[Any] = None,
        secret_resolver: Optional[Callable[[str], bytes]] = None,
        durable_spill_checker: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.telemetry_authority = telemetry_authority
        self.runtime_authority = runtime_authority
        self.secret_resolver = secret_resolver

        self._lock = RLock()
        self.lookup_resolver = LookupResolver()
        self.deduplicator = RowDeduplicator(durable_spill_checker=durable_spill_checker)
        self.processing_engine = ProcessingEngine(
            lookup_resolver=self.lookup_resolver,
            deduplicator=self.deduplicator,
            secret_resolver=self.secret_resolver,
        )

    def compile_plan(
        self,
        object_name: str,
        rules: Sequence[TransformationRule],
        filter_predicate: Optional[ASTNode] = None,
        dedup_key_columns: Sequence[str] = (),
    ) -> ProcessingPlan:
        """Compiles transformation rules into an immutable ProcessingPlan with cycle detection and SHA-256 fingerprinting."""
        return ProcessingPlanCompiler.compile_plan(
            object_name=object_name,
            rules=rules,
            filter_predicate=filter_predicate,
            dedup_key_columns=dedup_key_columns,
        )

    def register_lookup(self, lookup_def: LookupDefinition) -> None:
        self.lookup_resolver.register_lookup(lookup_def)

    def transform_row(self, row: Mapping[str, Any], plan: ProcessingPlan) -> ProcessingResult:
        """Transforms a single row dictionary."""
        return self.processing_engine.transform_row(row, plan)

    def transform_batch(
        self, batch: Sequence[Mapping[str, Any]], plan: ProcessingPlan
    ) -> Tuple[List[Dict[str, Any]], List[ProcessingResult]]:
        """Transforms a batch of row dictionaries deterministically."""
        transformed, results = self.processing_engine.transform_batch(batch, plan)

        # Record Telemetry aggregate metrics if telemetry_authority is present
        if self.telemetry_authority and hasattr(self.telemetry_authority, "record_counter"):
            try:
                self.telemetry_authority.record_counter("rows_processed_total", increment=float(len(transformed)))
                rejected = sum(1 for r in results if r.status in ("REJECTED", "QUARANTINED"))
                if rejected > 0:
                    self.telemetry_authority.record_counter("rows_rejected_total", increment=float(rejected))
            except Exception as exc:
                logger.warning(f"[DataProcessingAuthority] Failed to record Telemetry: {exc}")

        return transformed, results

    def transform_change_image(self, change_payload: Dict[str, Any], plan: ProcessingPlan) -> ChangeImageResult:
        """Transforms CDC row change image (after_image / before_image) while preserving key identity."""
        return self.processing_engine.transform_change_image(change_payload, plan)

    def transform_record_batch(self, record_batch: Any, plan: ProcessingPlan) -> Tuple[Any, str]:
        """
        Transforms PyArrow RecordBatch.
        Returns (transformed_batch, copy_classification).
        Truthful copy classifications: ZERO_COPY, LOW_COPY, MATERIALIZED_COPY, UNSUPPORTED.
        """
        def _row_fn(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            res = self.transform_row(row, plan)
            return res.transformed_row if res.status == "SUCCESS" else None

        return ArrowBatchAdapter.transform_record_batch(record_batch, _row_fn)

    def calculate_optimal_batch_size(
        self,
        sample_rows: Sequence[Mapping[str, Any]],
        target_memory_envelope_bytes: int = 16 * 1024 * 1024,
    ) -> int:
        """Computes optimal data processing batch size based on row width and RAM envelope."""
        return AdaptiveBatchSizer.calculate_optimal_batch_size(sample_rows, target_memory_envelope_bytes)

    def clear_dedup_cache(self) -> None:
        self.deduplicator.clear()
