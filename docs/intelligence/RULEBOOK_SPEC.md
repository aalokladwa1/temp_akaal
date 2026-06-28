AKAAL — RULEBOOK SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The Rulebook is the deterministic semantic compiler for database migration.



It converts raw database schema types into a Universal Data Model (UDM) representation.



It is NOT a mapper registry, heuristic engine, fallback resolver, or best-effort interpreter.



It is a strict transformation system with deterministic rules.





2\. CORE PRINCIPLE



Migration must be deterministic, repeatable, and failure-safe.



If a type cannot be resolved:



The system MUST fail.



The system MUST NOT guess.



The system MUST NOT return UNKNOWN.





3\. FOUR PROCESSING PHASES



Phase 1 — Normalization Layer:



Trim input, normalize to uppercase, normalize aliases, clean whitespace.



No semantic interpretation at this phase.



Phase 2 — Semantic Resolution Layer:



Map source type → semantic concept.



Determine family classification.



Resolve engine-independent meaning.



Phase 3 — Contract Enforcement Layer:



Validate UDM schema.



Enforce allowed keys only.



Reject invalid mappings.



Any violation = HARD FAILURE.



Phase 4 — Output Emission Layer:



Produce final UDM object.



Ensure schema consistency.



Remove any engine-specific leakage.





4\. UNIVERSAL DATA MODEL (UDM)



Allowed keys only:



concept. family. precision. scale. length. timezone. status.



Any other key must be removed or rejected.



Required fields in every UDM object:



concept. family. status.



Status values: mapped (success), unsupported (hard failure only, never for guesses).





5\. CONCEPT SYSTEM



A concept is the engine-agnostic meaning of a type.



Supported concepts: INTEGER, BIGINT, FLOAT, DECIMAL, STRING, TEXT, BOOLEAN, DATE, TIME, TIMESTAMP, INTERVAL, JSON, ARRAY, BINARY, GEOMETRY, NETWORK, IDENTIFIER.



Rules:



Concepts MUST be predefined.



Concepts MUST be deterministic.



Concepts MUST NOT be inferred dynamically.



Concepts MUST NOT be UNKNOWN under normal flow.





6\. FAMILY SYSTEM



ConceptFamilyINTEGER, BIGINT, FLOAT, DECIMALnumericSTRING, TEXT, IDENTIFIERstringBOOLEANbooleanDATE, TIME, TIMESTAMP, INTERVALtemporalJSON, ARRAYstructuredBINARYbinaryGEOMETRYspatialNETWORKnetwork





7\. NORMALIZATION RULES



Convert type names to uppercase.



Remove whitespace noise.



Normalize aliases:



TIMESTAMPTZ → TIMESTAMP (set timezone=true).



TIME WITH TIME ZONE → TIME (set timezone=true).



TIME WITHOUT TIME ZONE → TIME.



INT → INTEGER.



INT4 → INTEGER.



INT8 → BIGINT.



FLOAT4 → FLOAT.



FLOAT8 → FLOAT.



VARCHAR2 → STRING.



NVARCHAR2 → STRING.



NUMBER → DECIMAL (extract precision and scale if provided).



Normalization MUST NOT change meaning, only representation.





8\. PARAMETER EXTRACTION RULES



precision → numeric types only (INTEGER, BIGINT, DECIMAL, FLOAT).



scale → DECIMAL only.



length → STRING, TEXT only.



timezone → TIMESTAMP, TIME only (boolean true if timezone-aware).



Invalid assignment = HARD FAILURE.





9\. FAILURE MODEL



Hard fail conditions (MUST throw error):



Type cannot be resolved.



Concept not in registry.



Invalid type format.



Ambiguous type mapping.



Unsupported engine behavior.



Forbidden behavior:



Return UNKNOWN.



Guess a concept.



Fallback silently.



Partially map data.



Continue execution after invalid mapping.





10\. ENGINE ROLE



Engines (MySQL, Oracle, PostgreSQL) are NOT semantic authorities.



They are metadata providers only.



They MAY provide raw type info and syntax details.



They MUST NOT define UDM concepts, decide families, or override Rulebook decisions.





11\. DESIGN GUARANTEE



Deterministic migration output.



Zero UNKNOWN states.



Strict schema validation.



Engine-agnostic semantics.



Reproducible results across runs.

