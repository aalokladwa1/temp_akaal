# A:\temp_akaal\tests\integration\akaal_intelligence_models.py
from dataclasses import dataclass, field
from typing import Dict, List, Any
import hashlib
import json

@dataclass(frozen=True)
class ScoutModel:
    engine_type: str
    engine_version: str
    schema_name: str
    discovered_tables: List[str]
    column_metadata: Dict[str, List[Dict[str, Any]]]
    discovered_sequences: List[str]
    discovered_constraints: List[str]
    metadata_checksum: str = field(init=False)

    def __post_init__(self):
        # Enforce deterministic metadata hash generation
        raw_payload = {
            "engine": self.engine_type,
            "version": self.engine_version,
            "schema": self.schema_name,
            "tables": sorted(self.discovered_tables),
            "sequences": sorted(self.discovered_sequences),
            "constraints": sorted(self.discovered_constraints)
        }
        serialized = json.dumps(raw_payload, sort_keys=True)
        sha256 = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        object.__setattr__(self, 'metadata_checksum', sha256)


@dataclass(frozen=True)
class RulebookModel:
    source_engine: str
    target_engine: str
    type_mappings: Dict[str, str]
    transformation_policies: Dict[str, Any]
    rule_priority: int
    rule_checksum: str = field(init=False)

    def __post_init__(self):
        raw_payload = {
            "src": self.source_engine,
            "tgt": self.target_engine,
            "mappings": self.type_mappings,
            "policies": self.transformation_policies,
            "priority": self.rule_priority
        }
        serialized = json.dumps(raw_payload, sort_keys=True)
        sha256 = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        object.__setattr__(self, 'rule_checksum', sha256)


@dataclass(frozen=True)
class DecodedMigrationModel:
    scout_checksum: str
    rulebook_checksum: str
    canonical_schema_name: str
    target_ddl_matrix: Dict[str, str]
    decoded_manifest_hash: str = field(init=False)

    def __post_init__(self):
        raw_payload = {
            "scout": self.scout_checksum,
            "rulebook": self.rulebook_checksum,
            "schema": self.canonical_schema_name,
            "ddl": self.target_ddl_matrix
        }
        serialized = json.dumps(raw_payload, sort_keys=True)
        sha256 = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        object.__setattr__(self, 'decoded_manifest_hash', sha256)