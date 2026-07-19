"""
Akaal — Advisory Version Info
==============================
Immutable versioning dataclass for Advisor Platform metadata tracking.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvisoryVersion:
    """Immutable version metadata for Advisory Models and Outputs."""
    schema_version: str = "1.0.0"
    model_version: str = "1.0.0"
    generator_version: str = "advisor-1.0.0"
    model_signature: str = "AKAAL-ADVISOR-SIG-V1"

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "generator_version": self.generator_version,
            "model_signature": self.model_signature,
        }
