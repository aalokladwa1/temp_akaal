"""
Akaal — Conversion Rules
========================
Implements metadata schemas, declarative rule specifications, and default system rules.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from akaal.core.conversion.api.models import DataType, DbVersion, TypeCategory, ConversionContext
from akaal.core.conversion.internal.capabilities import NegotiationLevel
from akaal.core.conversion.exceptions import RegistryError

@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    version: str
    author: str
    created_at: str
    deprecated: bool = False
    replaced_by_rule_id: Optional[str] = None
    tags: Tuple[str, ...] = field(default_factory=tuple)
    vendor_scope: Tuple[str, str] = field(default_factory=tuple)  # (Source Vendor, Target Vendor)


class ConversionRule(ABC):
    """Abstract interface representing a data type conversion rule."""

    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """Returns the rule metadata."""
        pass

    @abstractmethod
    def matches(self, source: DataType, context: ConversionContext) -> bool:
        """Determines if this rule applies to the source DataType under the given context."""
        pass

    @abstractmethod
    def convert(self, source: DataType, context: ConversionContext) -> DataType:
        """Applies transformation logic to construct the target DataType."""
        pass

    @property
    @abstractmethod
    def negotiation_level(self) -> NegotiationLevel:
        """Returns the capability negotiation level of the converted type."""
        pass

    @property
    def specificity_score(self) -> int:
        """Calculates a specificity score. Rules with higher specificity are resolved first."""
        return 10  # Base priority


class DeclarativeConversionRule(ConversionRule):
    """A rule constructed dynamically from a JSON rule definition schema."""

    def __init__(self, definition: Dict[str, Any]):
        self._validate_definition(definition)
        self._definition = definition
        
        # Build metadata
        meta = definition.get("metadata", {})
        self._metadata = RuleMetadata(
            rule_id=definition["rule_id"],
            version=definition.get("version", "1.0.0"),
            author=definition.get("author", "Akaal Core Team"),
            created_at=definition.get("created_at", "2026-07-14"),
            deprecated=definition.get("deprecated", False),
            replaced_by_rule_id=definition.get("replaced_by_rule_id"),
            tags=tuple(definition.get("tags", [])),
            vendor_scope=(definition["source_vendor"], definition["target_vendor"])
        )
        
        # Setup caching for matcher performance
        self._source_vendor = definition["source_vendor"].upper()
        self._target_vendor = definition["target_vendor"].upper()
        
        match_section = definition["source_match"]
        self._match_category = TypeCategory(match_section["category"])
        self._match_names = {name.upper() for name in match_section.get("type_names", [])}
        
        self._min_source_version = DbVersion.parse(match_section.get("min_version", "0.0.0"))
        self._max_source_version = DbVersion.parse(match_section.get("max_version", "9999.99.99"))

    def _validate_definition(self, d: Dict[str, Any]):
        required = ["rule_id", "source_vendor", "target_vendor", "source_match", "target_definition", "negotiation_level"]
        for key in required:
            if key not in d:
                raise RegistryError(f"Missing required declarative rule property: '{key}'")
        
        sm = d["source_match"]
        if "category" not in sm:
            raise RegistryError("source_match section must contain 'category'")

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    @property
    def negotiation_level(self) -> NegotiationLevel:
        return NegotiationLevel(self._definition["negotiation_level"])

    @property
    def specificity_score(self) -> int:
        score = 10
        # Exact type name matches have much higher priority
        if self._match_names:
            score += 100
        # If source version is bounded, increase specificity
        if self._definition["source_match"].get("min_version") or self._definition["source_match"].get("max_version"):
            score += 20
        return score

    def matches(self, source: DataType, context: ConversionContext) -> bool:
        # Check vendors
        if context.source_vendor.upper() != self._source_vendor:
            return False
        if context.target_vendor.upper() != self._target_vendor:
            return False
        
        # Check source version bounds
        if not (self._min_source_version <= context.source_version <= self._max_source_version):
            return False

        # Check category match
        if source.category != self._match_category:
            return False

        # Check exact names list if provided
        if self._match_names and source.name.upper() not in self._match_names:
            return False

        return True

    def convert(self, source: DataType, context: ConversionContext) -> DataType:
        td = self._definition["target_definition"]
        target_name = td["type_name"]

        # Parse expressions safely without eval()
        precision = self._evaluate_expression(td.get("precision_expression"), source)
        scale = self._evaluate_expression(td.get("scale_expression"), source)
        length = self._evaluate_expression(td.get("length_expression"), source)
        unsigned = self._evaluate_expression(td.get("unsigned_expression"), source)
        timezone = self._evaluate_expression(td.get("timezone_expression"), source)
        charset = self._evaluate_expression(td.get("charset_expression"), source)
        collation = self._evaluate_expression(td.get("collation_expression"), source)

        # Fallback fields directly from source type if expressions not specified
        if unsigned is None:
            unsigned = source.unsigned
        if timezone is None:
            timezone = source.timezone
        if charset is None:
            charset = source.charset
        if collation is None:
            collation = source.collation

        from akaal.core.conversion.internal.normalizer import TypeNormalizer
        target_category = TypeNormalizer()._resolve_category(target_name, target_name)

        return DataType(
            name=target_name,
            category=target_category,
            precision=precision,
            scale=scale,
            length=length,
            nullable=source.nullable,
            unsigned=unsigned,
            auto_increment=source.auto_increment,
            timezone=timezone,
            charset=charset,
            collation=collation,
            spatial=source.spatial,
            is_array=source.is_array,
            array_dimensions=source.array_dimensions,
            generated_expression=source.generated_expression,
            vendor_metadata={}
        )

    def _evaluate_expression(self, expr: Optional[str], source: DataType) -> Any:
        if not expr:
            return None
        expr = expr.strip()
        
        # Exact property maps
        if expr == "source.precision":
            return source.precision
        if expr == "source.scale":
            return source.scale
        if expr == "source.length":
            return source.length
        if expr == "source.unsigned":
            return source.unsigned
        if expr == "source.timezone":
            return source.timezone
        if expr == "source.charset":
            return source.charset
        if expr == "source.collation":
            return source.collation
        
        # Pattern fallback: "source.precision or X"
        match_or = re.match(r'^source\.(precision|scale|length)\s+or\s+(\d+)$', expr)
        if match_or:
            attr = match_or.group(1)
            val = int(match_or.group(2))
            actual = getattr(source, attr)
            return actual if actual is not None else val

        # Literals
        if expr.isdigit():
            return int(expr)
        if expr == "True":
            return True
        if expr == "False":
            return False
        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]
        
        return expr
