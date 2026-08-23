"""
akaalEngine.data_processing.adapters.arrow
===========================================
PyArrow RecordBatch transformation adapter with truthful copy-classification.
"""

from typing import Any, Dict, List, Mapping, Optional, Tuple

try:
    import pyarrow as pa
    _HAS_PYARROW = True
except ImportError:
    pa = None
    _HAS_PYARROW = False


class ArrowBatchAdapter:
    """
    Adapter for PyArrow RecordBatch transformations.
    Truthfully classifies copy types and handles optional PyArrow environments.
    """

    @classmethod
    def is_available(cls) -> bool:
        return _HAS_PYARROW

    @classmethod
    def transform_record_batch(
        cls,
        record_batch: Any,
        row_transform_fn: Any,
    ) -> Tuple[Any, str]:
        """
        Transforms PyArrow RecordBatch.
        Returns (transformed_batch, copy_classification).
        Copy classifications: ZERO_COPY, LOW_COPY, MATERIALIZED_COPY, UNSUPPORTED
        """
        if not _HAS_PYARROW or not isinstance(record_batch, pa.RecordBatch):
            return None, "UNSUPPORTED"

        # PyArrow RecordBatch -> pydict conversion materializes python objects
        pydict = record_batch.to_pydict()
        num_rows = record_batch.num_rows

        # Materialized row conversion
        rows = [{col: pydict[col][i] for col in pydict} for i in range(num_rows)]
        transformed_rows = [row_transform_fn(r) for r in rows if r is not None]

        if not transformed_rows:
            empty_dict = {col: [] for col in pydict}
            return pa.RecordBatch.from_pydict(empty_dict), "MATERIALIZED_COPY"

        res_dict = {col: [r.get(col) for r in transformed_rows] for col in transformed_rows[0].keys()}
        new_batch = pa.RecordBatch.from_pydict(res_dict)

        return new_batch, "MATERIALIZED_COPY"
