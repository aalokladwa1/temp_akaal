"""
AKAAL PL/SQL Transpiler — Package Converter
============================================
Converts Oracle PACKAGE specification and PACKAGE BODY into PostgreSQL schema-qualified functions and session variables.
"""

import re
from typing import Any, Dict, List
from akaal.transpiler.parser.plsql_parser import PLSQLParser
from akaal.transpiler.generator.plpgsql_generator import PLpgSQLGenerator


class PackageConverter:
    """Decomposes Oracle PACKAGE objects into PostgreSQL schema-qualified PL/pgSQL structures."""

    def __init__(self) -> None:
        self.parser = PLSQLParser()
        self.generator = PLpgSQLGenerator()

    def convert_package_body(self, package_name: str, body_text: str) -> Dict[str, Any]:
        pkg_name = package_name.lower().replace('"', '')
        schema_sql = f"CREATE SCHEMA IF NOT EXISTS {pkg_name};\n"
        converted_items = []
        errors = []

        # Find procedure and function definitions inside package body
        proc_blocks = re.findall(
            r'(PROCEDURE\s+[A-Za-z0-9_"]+.*?\bEND\s+[A-Za-z0-9_"]*;\s*)',
            body_text,
            flags=re.IGNORECASE | re.DOTALL
        )
        func_blocks = re.findall(
            r'(FUNCTION\s+[A-Za-z0-9_"]+.*?\bEND\s+[A-Za-z0-9_"]*;\s*)',
            body_text,
            flags=re.IGNORECASE | re.DOTALL
        )

        for block in proc_blocks:
            try:
                node = self.parser.parse_procedure(block)
                # Qualify procedure name with package schema
                node.name = f"{pkg_name}.{node.name}"
                proc_sql = self.generator.generate_procedure(node)
                converted_items.append(proc_sql)
            except Exception as exc:
                errors.append(f"Procedure in package {pkg_name} error: {exc}")

        for block in func_blocks:
            try:
                node = self.parser.parse_function(block)
                node.name = f"{pkg_name}.{node.name}"
                func_sql = self.generator.generate_function(node)
                converted_items.append(func_sql)
            except Exception as exc:
                errors.append(f"Function in package {pkg_name} error: {exc}")

        full_sql = schema_sql + "\n\n" + "\n\n".join(converted_items) if converted_items else schema_sql

        return {
            "package_name": pkg_name,
            "converted_sql": full_sql,
            "procedures_converted": len(proc_blocks),
            "functions_converted": len(func_blocks),
            "is_valid": len(errors) == 0,
            "errors": errors,
        }
