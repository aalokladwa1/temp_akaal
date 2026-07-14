"""
Akaal — Confidence Scoring Engine
=================================
Calculates explainable, multi-dimensional confidence scores for type mapping results.
"""

from dataclasses import dataclass
from akaal.core.conversion.api.models import DataType, ConversionContext

@dataclass(frozen=True)
class ConfidenceBreakdown:
    category_alignment: float        # (0.0 - 1.0)
    precision_preservation: float    # (0.0 - 1.0)
    metadata_preservation: float     # (0.0 - 1.0)
    storage_adequacy: float          # (0.0 - 1.0)
    overall_score: float             # (0.0 - 1.0)


class ConfidenceScoringEngine:
    """Computes multi-dimensional and overall mapping quality confidence metrics."""

    def calculate(self, source: DataType, target: DataType, context: ConversionContext) -> ConfidenceBreakdown:
        # 1. Category Alignment
        if source.category == target.category:
            category_score = 1.0
        elif {source.category, target.category}.intersection({"LOB", "CLOB", "BLOB", "STRING", "BINARY"}):
            # Safe LOB/String/Binary cross-category conversions
            category_score = 0.8
        else:
            category_score = 0.2

        # 2. Precision and Scale Preservation
        precision_score = 1.0
        
        # Check precision
        if source.precision is not None:
            if target.precision is not None:
                if target.precision < source.precision:
                    # Deduct score based on ratio of precision loss
                    precision_score -= 0.5 * (1.0 - (target.precision / source.precision))
            # If target precision is None, it could be unbounded (e.g. Oracle NUMBER), which is safe.
            
        # Check scale
        if source.scale is not None:
            if target.scale is not None:
                if target.scale < source.scale:
                    precision_score -= 0.5 * (1.0 - (target.scale / source.scale))
            elif target.precision is not None:
                # Target has precision but no scale (effectively scale = 0), which is lossy if source scale > 0
                if source.scale > 0:
                    precision_score -= 0.6
                    
        precision_score = max(0.0, min(1.0, precision_score))

        # 3. Metadata Preservation
        metadata_score = 1.0
        
        # Timezone loss check
        if source.timezone and not target.timezone:
            metadata_score -= 0.3
            
        # Unsigned mismatch
        if source.unsigned and not target.unsigned:
            metadata_score -= 0.1
            
        # Charset / Collation loss
        if source.charset and not target.charset:
            metadata_score -= 0.05
            
        metadata_score = max(0.0, min(1.0, metadata_score))

        # 4. Storage Adequacy
        storage_score = 1.0
        
        if source.length is not None:
            if target.length is not None:
                if target.length == -1:
                    # NVARCHAR(MAX) or TEXT type
                    storage_score = 1.0
                elif target.length < source.length:
                    storage_score = max(0.0, target.length / source.length)
            # If target has no length limit, it's unbounded (e.g. TEXT, CLOB), which is safe.

        # 5. Overall Weighted Score
        overall = (
            (0.4 * category_score) +
            (0.3 * precision_score) +
            (0.1 * metadata_score) +
            (0.2 * storage_score)
        )
        
        # Deduct if emulated (check constraints or transform hooks exist in vendor_metadata)
        if "check_constraints" in target.vendor_metadata or "transform_hooks" in target.vendor_metadata:
            overall -= 0.1
            
        overall = max(0.0, min(1.0, round(overall, 3)))

        return ConfidenceBreakdown(
            category_alignment=round(category_score, 2),
            precision_preservation=round(precision_score, 2),
            metadata_preservation=round(metadata_score, 2),
            storage_adequacy=round(storage_score, 2),
            overall_score=overall
        )
