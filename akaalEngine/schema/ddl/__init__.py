"""
akaalEngine.schema.ddl
======================
Target DDL generation, identifiers, staged execution packaging, and provider emitters.
"""

from akaalEngine.schema.ddl.emitter import (
    BaseTargetDDLEmitter,
    DDLStage,
    StagedDDLPackage,
    StructuredDDLArtifact,
)
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer

__all__ = [
    "DDLStage",
    "StructuredDDLArtifact",
    "StagedDDLPackage",
    "BaseTargetDDLEmitter",
    "IdentifierSanitizer",
    "DDLGenerator",
]
