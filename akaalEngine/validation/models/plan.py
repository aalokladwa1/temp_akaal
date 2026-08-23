"""
akaalEngine.validation.models.plan
==================================
ValidationPlan and ProofScope models for Authority #11.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProofScope(str, Enum):
    """Truthful Proof Scope classifications for validation runs."""
    FULL = "FULL"
    PARTITIONED_FULL = "PARTITIONED_FULL"
    SAMPLED = "SAMPLED"
    STRUCTURE_ONLY = "STRUCTURE_ONLY"
    COUNT_ONLY = "COUNT_ONLY"
    UNPROVEN = "UNPROVEN"
    FAILED = "FAILED"


class ValidationMode(str, Enum):
    """Policy-driven validation operational modes."""
    FAST_FULL = "FAST_FULL"          # Schema + Cardinality + Partition Fingerprints + Mismatch Drilldown
    EXACT_FULL = "EXACT_FULL"        # Schema + Cardinality + Full Exact Row Comparison
    SAMPLED = "SAMPLED"              # Schema + Cardinality + Deterministic Sample Comparison
    STRUCTURE_ONLY = "STRUCTURE_ONLY"# Schema & Type Metadata Only
    COUNT_ONLY = "COUNT_ONLY"        # Cardinality Only


@dataclass
class SamplingConfig:
    """Configuration for deterministic reproducible sampling."""
    sample_size: int = 1000
    population_size: Optional[int] = None
    seed: int = 42
    strategy: str = "DETERMINISTIC_HASH_MODULO"


@dataclass
class ValidationPlan:
    """
    Immutable/machine-readable plan for validation execution (VAL-002).
    Captures migration identity, source/target tables, schema mapping, validation mode,
    partition bounds, sampling configuration, and CDC boundary anchoring.
    """
    plan_id: str
    migration_id: str
    source_identity: str
    target_identity: str
    table_name: str
    target_table_name: Optional[str] = None
    column_mapping: Dict[str, str] = field(default_factory=dict)  # source_col -> target_col
    mode: ValidationMode = ValidationMode.FAST_FULL
    proof_scope: ProofScope = ProofScope.UNPROVEN
    partition_count: int = 10
    batch_size: int = 5000
    max_concurrency: int = 4
    sampling_config: Optional[SamplingConfig] = None
    cdc_boundary_position: Optional[str] = None
    checkpoint_identity: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.target_table_name:
            self.target_table_name = self.table_name
