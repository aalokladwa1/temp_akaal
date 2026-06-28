from __future__ import annotations


class RulebookError(Exception):
    """
    Base exception for all Rulebook V1 errors.
    """
    pass


# ==========================================================
# Normalization
# ==========================================================

class NormalizationError(RulebookError):
    """
    Raised when an incoming database type cannot be normalized.
    """
    pass


# ==========================================================
# Parser
# ==========================================================

class ParserError(RulebookError):
    """
    Base parser exception.
    """
    pass


class UnsupportedEngineError(ParserError):
    """
    Raised when an unsupported database engine is requested.
    """
    pass


class InvalidTypeSyntaxError(ParserError):
    """
    Raised when a database type has invalid syntax.
    """
    pass


class UnsupportedTypeError(ParserError):
    """
    Raised when an adapter encounters a type it does not support.
    """
    pass


# ==========================================================
# Resolver
# ==========================================================

class ResolverError(RulebookError):
    """
    Base semantic resolution exception.
    """
    pass


class UnknownConceptError(ResolverError):
    """
    Raised when no semantic concept exists for a parsed type.
    """
    pass


class AmbiguousTypeError(ResolverError):
    """
    Raised when multiple semantic interpretations exist.
    """
    pass


# ==========================================================
# Contract
# ==========================================================

class ContractViolationError(RulebookError):
    """
    Raised when the Universal Key contract is violated.
    """
    pass


class InvalidConceptError(ContractViolationError):
    """
    Raised when an invalid concept is emitted.
    """
    pass


class InvalidMetadataError(ContractViolationError):
    """
    Raised when metadata is incompatible with the resolved concept.
    """
    pass


# ==========================================================
# Rulebook
# ==========================================================

class RulebookExecutionError(RulebookError):
    """
    Raised when the Rulebook pipeline cannot complete.
    """
    pass