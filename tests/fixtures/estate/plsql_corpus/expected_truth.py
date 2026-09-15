"""Independent expected-truth classification for the PL/SQL corpus (build-spec §12).

This is NOT derived from running AKAAL's translator (that is forbidden this
session) and it is NOT a claim about what the translator will actually
output. It is an independent, honestly-labelled *prediction* the later
compulsory translation-accuracy campaign can score itself against.

Repository research (background research this session) established:
  - The canonical production translation path is P7C.11
    (akaalEngine/intelligence/producers/sql_translation.py), fed by
    akaalEngine/schema/procedural/parsers/plsql.py -> AOIR ->
    akaalEngine/schema/procedural/emitters/plpgsql.py.
  - P7C.11 today has a real AST entrypoint ONLY for PROCEDURE and FUNCTION
    objects (CanonicalRoutine). Its own docstring explicitly disclaims
    TRIGGER and PACKAGE support ("no trigger/package AST entrypoint exists
    in this repo yet"). VIEW and SEQUENCE are DDL objects P7C.11 does not
    translate at all (they are schema-DDL concerns, not procedural-logic
    concerns).
  - P7C.11's real classification enum is `TranslationCertification`:
    EXACT_TRANSLATION_PROVEN / SEMANTIC_EQUIVALENCE_PROVEN /
    COMPILES_BUT_EQUIVALENCE_UNPROVEN / MANUAL_REVIEW_REQUIRED / UNSUPPORTED.
    Only P7C.11 itself -- by actually running the pipeline -- can assign one
    of *those* values with authority; this module must not pretend to.

So this module assigns two things per object:
  1. `entrypoint_status`: whether P7C.11 has ANY production AST entrypoint
     for this object KIND today. PROCEDURE/FUNCTION -> HAS_ENTRYPOINT;
     everything else -> NO_PRODUCTION_ENTRYPOINT_YET. This is a repository
     fact, verifiable by inspection, independent of running anything.
  2. `predicted_difficulty`: for PROCEDURE/FUNCTION objects only, an
     independent, construct-based difficulty prediction (not a
     TranslationCertification claim) used later to check whether harder
     constructs correlate with worse real outcomes. Objects with only
     well-understood constructs (SELECT INTO, IF, basic exception
     handling, arithmetic) are predicted LIKELY_TRANSLATABLE; objects
     using constructs with known PL/pgSQL impedance mismatches (dynamic
     SQL, BULK COLLECT/FORALL, autonomous transactions, PRAGMA, weakly
     structured collections) are predicted LIKELY_MANUAL_REVIEW.
"""
from __future__ import annotations

from .model import PLSQLObject
from .views import VIEWS
from .materialized_views import MATERIALIZED_VIEWS
from .sequences import SEQUENCES
from .triggers import TRIGGERS
from .procedures import PROCEDURES
from .functions import FUNCTIONS
from .packages import PACKAGES

ENTRYPOINT_KINDS = {"PROCEDURE", "FUNCTION"}

HARD_CONSTRUCTS = {
    "DYNAMIC_SQL", "EXECUTE_IMMEDIATE", "BULK_COLLECT", "FORALL", "COLLECTION_TYPE",
    "ASSOCIATIVE_ARRAY", "PRAGMA_AUTONOMOUS_TRANSACTION", "PRAGMA_EXCEPTION_INIT",
    "RECURSIVE_CALL", "CROSS_SCHEMA_CALL", "CROSS_OBJECT_CALL", "RECORD_TYPE",
    "FETCH_FIRST", "FOR_UPDATE",
}


def classify(obj: PLSQLObject) -> dict:
    entrypoint_status = "HAS_ENTRYPOINT" if obj.kind in ENTRYPOINT_KINDS else "NO_PRODUCTION_ENTRYPOINT_YET"

    predicted_difficulty = None
    if obj.kind in ENTRYPOINT_KINDS:
        hard_hits = HARD_CONSTRUCTS.intersection(obj.constructs)
        if obj.complexity_band == "very_complex" or len(hard_hits) >= 2:
            predicted_difficulty = "LIKELY_MANUAL_REVIEW"
        elif hard_hits or obj.complexity_band == "complex":
            predicted_difficulty = "LIKELY_REWRITE_REQUIRED"
        else:
            predicted_difficulty = "LIKELY_TRANSLATABLE"

    return {
        "object_id": obj.object_id,
        "kind": obj.kind,
        "schema": obj.schema,
        "name": obj.name,
        "complexity_band": obj.complexity_band,
        "constructs": sorted(set(obj.constructs)),
        "dependencies": obj.dependencies,
        "source_loc": obj.source_loc,
        "source_bytes": obj.source_bytes,
        "entrypoint_status": entrypoint_status,
        "predicted_difficulty": predicted_difficulty,
        "forbidden_silent_omissions": [
            "must not report SUCCESS for an object type with NO_PRODUCTION_ENTRYPOINT_YET",
            "must not silently drop parameters, exception handlers, or dependencies from the report",
        ],
    }


def all_corpus_objects():
    return VIEWS + MATERIALIZED_VIEWS + SEQUENCES + TRIGGERS + PROCEDURES + FUNCTIONS + PACKAGES


def build_expected_truth():
    return [classify(o) for o in all_corpus_objects()]


ALL_OBJECTS = all_corpus_objects()
EXPECTED_TRUTH = build_expected_truth()
