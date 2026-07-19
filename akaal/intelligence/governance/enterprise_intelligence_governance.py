"""
AKAAL Enterprise Intelligence Platform — Governance Subsystem
==============================================================
Provides SHA-256 checksum generation, model equivalence verification, and semver governance.
"""

import hashlib
import json
from typing import Any, Dict
from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel


class EnterpriseIntelligenceGovernanceError(Exception):
    """Exception raised for errors in EnterpriseIntelligenceGovernance operations."""
    pass


class EnterpriseIntelligenceGovernance:
    """
    Governance engine providing checksum calculation, equivalence verification, and semver checks.
    """

    @staticmethod
    def compute_model_checksum(model_or_dict: Any) -> str:
        """
        Computes a 100% deterministic SHA-256 checksum of an EnterpriseIntelligenceModel
        or model dictionary payload (excluding any pre-existing checksum field).
        """
        if isinstance(model_or_dict, EnterpriseIntelligenceModel):
            d_dict = model_or_dict.to_dict()
        elif isinstance(model_or_dict, dict):
            d_dict = dict(model_or_dict)
        else:
            raise EnterpriseIntelligenceGovernanceError(
                f"Expected EnterpriseIntelligenceModel or dict, got {type(model_or_dict).__name__}."
            )

        # Exclude existing checksum field from calculation
        payload_copy = dict(d_dict)
        payload_copy.pop("checksum", None)
        # Exclude non-deterministic trace id or timestamps if needed
        trace = payload_copy.get("trace", {})
        if isinstance(trace, dict):
            trace_copy = dict(trace)
            trace_copy.pop("trace_id", None)
            payload_copy["trace"] = trace_copy

        try:
            canonical_json = json.dumps(payload_copy, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        except Exception as ex:
            raise EnterpriseIntelligenceGovernanceError(f"Failed to compute SHA-256 checksum: {ex}") from ex

    @classmethod
    def verify_model_checksum(cls, model: EnterpriseIntelligenceModel) -> bool:
        """
        Verifies that a model's embedded checksum matches its computed SHA-256 checksum.
        """
        if not isinstance(model, EnterpriseIntelligenceModel):
            raise EnterpriseIntelligenceGovernanceError("Expected EnterpriseIntelligenceModel instance.")

        if not model.checksum:
            return False

        computed = cls.compute_model_checksum(model)
        return computed == model.checksum

    @classmethod
    def verify_equivalence(cls, model1: EnterpriseIntelligenceModel, model2: EnterpriseIntelligenceModel) -> bool:
        """
        Verifies 100% deterministic equivalence between two execution runs.
        """
        if not isinstance(model1, EnterpriseIntelligenceModel) or not isinstance(model2, EnterpriseIntelligenceModel):
            raise EnterpriseIntelligenceGovernanceError("Both inputs must be EnterpriseIntelligenceModel instances.")

        checksum1 = cls.compute_model_checksum(model1)
        checksum2 = cls.compute_model_checksum(model2)
        return checksum1 == checksum2

    @staticmethod
    def check_semver_compatibility(schema_version: str, target_version: str = "1.0.0") -> bool:
        """
        Verifies major semver version compatibility between schema version and target platform version.
        """
        if not schema_version or not target_version:
            return False

        try:
            s_major = int(schema_version.split(".")[0])
            t_major = int(target_version.split(".")[0])
            return s_major == t_major
        except Exception:
            return False
