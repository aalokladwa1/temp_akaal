"""akaalEngine.intelligence.producers
=====================================
Campaign B (P7C.7-P7C.12) intelligence producers. Every producer here is a thin
IntelligenceKernel-compatible function that wraps REAL, existing deterministic or
analytical AKAAL engines (schema assessment, dependency graph, DDL/dialect
conversion, capacity math) -- per the P7C brief's law: "DO NOT USE AN LLM TO
REPLACE A DETERMINISTIC OR QUANTITATIVE AUTHORITY THAT CAN BE IMPLEMENTED
CORRECTLY WITHOUT ONE." No producer in this package re-implements assessment/
optimization logic that a canonical AKAAL authority already owns.
"""
