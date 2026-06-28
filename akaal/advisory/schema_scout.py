from __future__ import annotations

import re
from pathlib import Path


CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:`([^`]+)`|\"([^\"]+)\"|'([^']+)'|(\w+))\s*\(",
    re.IGNORECASE | re.DOTALL,
)

TABLE_CONSTRAINT_PATTERN = re.compile(
    r"^\s*(?:PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE\s+(?:KEY|INDEX)|"
    r"KEY|INDEX|CONSTRAINT|CHECK)\b",
    re.IGNORECASE,
)

COLUMN_DEFINITION_PATTERN = re.compile(
    r"^(?:`([^`]+)`|\"([^\"]+)\"|'([^']+)'|(\w+))\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)

INLINE_CONSTRAINT_PATTERN = re.compile(
    r"\b(?:PRIMARY\s+KEY|NOT\s+NULL|NULL|DEFAULT|UNIQUE|REFERENCES|CHECK|"
    r"AUTO_INCREMENT|COMMENT|COLLATE|CHARACTER\s+SET|ON\s+UPDATE|CONSTRAINT)\b",
    re.IGNORECASE,
)

FOREIGN_KEY_REFERENCE_PATTERN = re.compile(
    r"\bFOREIGN\s+KEY\b.*?\bREFERENCES\s+"
    r"(?:`([^`]+)`|\"([^\"]+)\"|'([^']+)'|(\w+))",
    re.IGNORECASE | re.DOTALL,
)


class Scout:
    """Discovers source schema metadata and prepares migration blueprints."""

    SUPPORTED_ENGINES = frozenset({"mysql", "oracle", "postgres"})

    def __init__(self, engine: str = "mysql") -> None:
        normalized = engine.strip().lower()
        if normalized not in self.SUPPORTED_ENGINES:
            supported = ", ".join(sorted(self.SUPPORTED_ENGINES))
            raise ValueError(f"Unsupported engine {engine!r}. Supported: {supported}")
        self.engine = normalized

    def load_schema(self, path: str | Path) -> str:
        """Read schema DDL from a file and return its text content."""
        schema_path = Path(path)
        if not schema_path.is_file():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        return schema_path.read_text(encoding="utf-8")

    def parse_tables(self, schema_text: str) -> list[dict]:
        """Extract table objects from simple CREATE TABLE statements."""
        tables: list[dict] = []

        for match in CREATE_TABLE_PATTERN.finditer(schema_text):
            table_name = next(group for group in match.groups() if group)
            body_start = match.end()
            body = _extract_balanced_body(schema_text, body_start)
            if body is None:
                continue

            attributes = []
            for definition in _split_definitions(body):
                column = _parse_column_definition(definition)
                if column is not None:
                    attributes.append(column)

            tables.append(
                {
                    "type": "table",
                    "name": table_name,
                    "attributes": attributes,
                }
            )

        return tables

    def parse_relationships(self, schema_text: str) -> list[dict]:
        """Extract foreign-key relationships from CREATE TABLE statements."""
        relationships: list[dict] = []

        for match in CREATE_TABLE_PATTERN.finditer(schema_text):
            source_table = next(group for group in match.groups() if group)
            body_start = match.end()
            body = _extract_balanced_body(schema_text, body_start)
            if body is None:
                continue

            for definition in _split_definitions(body):
                relationship = _parse_foreign_key_relationship(source_table, definition)
                if relationship is not None:
                    relationships.append(relationship)

        return relationships

    def generate_blueprint(self, schema_text: str) -> dict:
        """Build a migration blueprint from raw schema DDL."""
        objects = self.parse_tables(schema_text)
        relationships = self.parse_relationships(schema_text)
        return {
            "source": {
                "engine": self.engine,
                "version": "",
            },
            "objects": objects,
            "relationships": relationships,
            "metadata": {
                "object_count": len(objects),
            },
        }


def _extract_balanced_body(text: str, start: int) -> str | None:
    depth = 1
    index = start
    while index < len(text) and depth:
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:index]
        index += 1
    return None


def _split_definitions(body: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []

    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)

    remainder = "".join(current).strip()
    if remainder:
        parts.append(remainder)
    return parts


def _parse_column_definition(definition: str) -> dict | None:
    definition = definition.strip().rstrip(",")
    if not definition or TABLE_CONSTRAINT_PATTERN.match(definition):
        return None

    match = COLUMN_DEFINITION_PATTERN.match(definition)
    if match is None:
        return None

    name = next(group for group in match.groups()[:4] if group)
    remainder = match.group(5).strip()
    source_type = _extract_source_type(remainder)
    if not source_type:
        return None

    nullable = _is_nullable(remainder)
    return {
        "name": name,
        "source_type": source_type,
        "nullable": nullable,
    }


def _extract_source_type(remainder: str) -> str:
    constraint = INLINE_CONSTRAINT_PATTERN.search(remainder)
    type_text = remainder[: constraint.start()].strip() if constraint else remainder.strip()
    return " ".join(type_text.split()).upper()


def _is_nullable(remainder: str) -> bool:
    if re.search(r"\bNOT\s+NULL\b", remainder, re.IGNORECASE):
        return False
    if re.search(r"\bPRIMARY\s+KEY\b", remainder, re.IGNORECASE):
        return False
    return True


def _parse_foreign_key_relationship(source_table: str, definition: str) -> dict | None:
    match = FOREIGN_KEY_REFERENCE_PATTERN.search(definition)
    if match is None:
        return None

    target_table = next(group for group in match.groups() if group)
    return {
        "source_object": source_table,
        "target_object": target_table,
        "relationship_type": "foreign_key",
    }
