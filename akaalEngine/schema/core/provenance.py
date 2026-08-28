import datetime
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Optional

from akaalEngine.schema.ddl.emitter import StagedDDLPackage
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.schema import CanonicalSchemaModel


def _canonical_normalize(val: Any) -> Any:
    """Strict canonical object normalizer ensuring cross-platform reproducible serialization."""
    if val is None or isinstance(val, (bool, int, str)):
        return val
    elif isinstance(val, float):
        return round(val, 8)
    elif isinstance(val, Enum):
        return val.value
    elif isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    elif hasattr(val, "to_dict") and callable(val.to_dict):
        return _canonical_normalize(val.to_dict())
    elif isinstance(val, (dict, MappingProxyType, Mapping)):
        return {str(k): _canonical_normalize(v) for k, v in sorted(val.items(), key=lambda x: str(x[0]))}
    elif isinstance(val, (list, tuple)):
        return [_canonical_normalize(item) for item in val]
    elif isinstance(val, (set, frozenset)):
        try:
            sorted_items = sorted(val)
        except TypeError:
            sorted_items = sorted(val, key=lambda x: str(x))
        return [_canonical_normalize(item) for item in sorted_items]
    elif hasattr(val, "__dict__"):
        return {str(k): _canonical_normalize(v) for k, v in sorted(val.__dict__.items(), key=lambda x: str(x[0])) if not k.startswith("_")}
    raise TypeError(f"Cannot deterministically serialize type '{type(val).__name__}' to canonical JSON.")


import inspect


def get_rule_implementation_version() -> str:
    """Computes deterministic mechanical hash of loaded schema rule engine bytecodes and constants."""
    from akaalEngine.schema.types.normalizers import ProviderTypeNormalizers
    from akaalEngine.schema.types.emitters import ProviderTypeEmitters
    from akaalEngine.schema.dialect.datetime import DateTimeDialectTranslator
    from akaalEngine.schema.dialect.sequences import SequenceDialectTranslator
    from akaalEngine.schema.dialect.functions import FunctionDialectTranslator

    rule_hashes = []
    classes = (
        ProviderTypeNormalizers,
        ProviderTypeEmitters,
        DateTimeDialectTranslator,
        SequenceDialectTranslator,
        FunctionDialectTranslator,
    )
    for cls in classes:
        for name, member in inspect.getmembers(cls, predicate=callable):
            func = getattr(member, "__func__", member)
            if hasattr(func, "__code__"):
                co = func.__code__
                code_bytes = co.co_code
                consts_repr = repr(co.co_consts).encode("utf-8")
                member_hash = hashlib.sha256(code_bytes + consts_repr).hexdigest()
                rule_hashes.append(f"{cls.__name__}.{name}:{member_hash}")

    combined = ";".join(sorted(rule_hashes))
    return f"v4.0.0-{hashlib.sha256(combined.encode('utf-8')).hexdigest()[:12]}"


class DeterministicSchemaProvenanceHasher:
    """Computes reproducible SHA-256 fingerprints across canonical schema artifacts."""

    @classmethod
    def hash_dict(cls, data: Mapping[str, Any]) -> str:
        """Serializes dictionary to strict sorted canonical JSON and computes SHA-256."""
        normalized = _canonical_normalize(data)
        raw = json.dumps(normalized, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def compute_model_fingerprint(cls, model: CanonicalSchemaModel) -> str:
        """Computes deterministic fingerprint for CanonicalSchemaModel."""
        return cls.hash_dict(model.to_dict())

    @classmethod
    def compute_mapping_fingerprint(cls, mapping: CompiledSchemaMapping) -> str:
        """Computes deterministic fingerprint for CompiledSchemaMapping."""
        return cls.hash_dict(mapping.to_dict())

    @classmethod
    def compute_ddl_fingerprint(cls, package: StagedDDLPackage) -> str:
        """Computes deterministic fingerprint for generated StagedDDLPackage."""
        return cls.hash_dict(package.to_dict())

    @classmethod
    def compute_compilation_provenance(
        cls,
        source_model_hash: str,
        mapping_hash: str,
        ddl_package_hash: str,
        target_engine: str,
        target_version: str = "default",
        rule_set_version: str = "1.0.0",
        procedural_hash: str = "",
        readiness_hash: str = "",
        compatibility_breakdown_hash: str = "",
        compat_pack_hash: str = "",
        risk_hash: str = "",
        capacity_hash: str = "",
        options_hash: str = "",
        rule_impl_version: Optional[str] = None,
    ) -> str:
        """Computes composite provenance signature across all 18 compilation decisions and artifacts."""
        impl_ver = rule_impl_version or get_rule_implementation_version()
        combined = (
            f"{source_model_hash}:{mapping_hash}:{ddl_package_hash}:"
            f"{target_engine.upper()}:{target_version}:{rule_set_version}:{impl_ver}:"
            f"{procedural_hash}:{readiness_hash}:{compatibility_breakdown_hash}:"
            f"{compat_pack_hash}:{risk_hash}:{capacity_hash}:{options_hash}"
        )
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
