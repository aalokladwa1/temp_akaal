"""
AKAAL PL/SQL Transpiler — PL/SQL Parser
========================================
Parses Oracle PL/SQL source text for Procedures, Functions, Triggers, and Packages into AST nodes.
"""

import re
from typing import Any, Dict, List, Optional
from akaal.transpiler.ast.nodes import (
    ProcedureNode,
    FunctionNode,
    TriggerNode,
    PackageNode,
    ParameterNode,
    VariableDeclNode,
)
from akaal.transpiler.rules.datatype_rules import DataTypeRulesEngine


class PLSQLParser:
    """Parses Oracle PL/SQL text into AST structures."""

    def parse_procedure(self, sql_text: str) -> ProcedureNode:
        proc_match = re.search(
            r'PROCEDURE\s+([A-Za-z0-9_"\.]+)\s*(\((.*?)\))?\s*(IS|AS)\s*(.*?)\bBEGIN\b\s*(.*?)\bEND\b',
            sql_text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if proc_match:
            name = proc_match.group(1).strip().replace('"', '')
            raw_params = proc_match.group(3) or ""
            raw_decls = proc_match.group(5) or ""
            raw_body = proc_match.group(6) or ""

            params = self._parse_parameters(raw_params)
            vars_list = self._parse_declarations(raw_decls)
            statements = [s.strip() for s in raw_body.split(';') if s.strip()]

            return ProcedureNode(
                name=name,
                parameters=params,
                variables=vars_list,
                body_statements=statements
            )

        # Fallback simple node if regex fails
        clean_name = self._extract_object_name("PROCEDURE", sql_text)
        return ProcedureNode(name=clean_name, body_statements=[sql_text])

    def parse_function(self, sql_text: str) -> FunctionNode:
        func_match = re.search(
            r'FUNCTION\s+([A-Za-z0-9_"\.]+)\s*(\((.*?)\))?\s*RETURN\s+([A-Za-z0-9_]+)\s*(IS|AS)\s*(.*?)\bBEGIN\b\s*(.*?)\bEND\b',
            sql_text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if func_match:
            name = func_match.group(1).strip().replace('"', '')
            raw_params = func_match.group(3) or ""
            ret_type = DataTypeRulesEngine.convert_type(func_match.group(4).strip())
            raw_decls = func_match.group(6) or ""
            raw_body = func_match.group(7) or ""

            params = self._parse_parameters(raw_params)
            vars_list = self._parse_declarations(raw_decls)
            statements = [s.strip() for s in raw_body.split(';') if s.strip()]

            return FunctionNode(
                name=name,
                parameters=params,
                return_type=ret_type,
                variables=vars_list,
                body_statements=statements
            )

        clean_name = self._extract_object_name("FUNCTION", sql_text)
        return FunctionNode(name=clean_name, body_statements=[sql_text])

    def parse_trigger(self, sql_text: str) -> TriggerNode:
        trig_match = re.search(
            r'TRIGGER\s+([A-Za-z0-9_"\.]+)\s+(BEFORE|AFTER|INSTEAD OF)\s+(.*?)\s+ON\s+([A-Za-z0-9_"\.]+)\s*(FOR EACH ROW)?\s*(.*?)\bBEGIN\b\s*(.*?)\bEND\b',
            sql_text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if trig_match:
            name = trig_match.group(1).strip().replace('"', '')
            timing = trig_match.group(2).upper()
            events = [e.strip() for e in trig_match.group(3).split('OR')]
            tbl_name = trig_match.group(4).strip().replace('"', '')
            for_each = bool(trig_match.group(5))
            raw_body = trig_match.group(7) or ""

            statements = [s.strip() for s in raw_body.split(';') if s.strip()]
            return TriggerNode(
                name=name,
                table_name=tbl_name,
                timing=timing,
                events=events,
                for_each_row=for_each,
                body_statements=statements
            )

        clean_name = self._extract_object_name("TRIGGER", sql_text)
        return TriggerNode(name=clean_name, body_statements=[sql_text])

    def _parse_parameters(self, raw_params: str) -> List[ParameterNode]:
        params = []
        if not raw_params.strip():
            return params
        for part in raw_params.split(','):
            tokens = part.strip().split()
            if tokens:
                p_name = tokens[0]
                p_mode = "IN"
                p_type = "VARCHAR"
                if len(tokens) >= 3 and tokens[1].upper() in ("IN", "OUT", "INOUT"):
                    p_mode = tokens[1].upper()
                    p_type = DataTypeRulesEngine.convert_type(tokens[2])
                elif len(tokens) >= 2:
                    p_type = DataTypeRulesEngine.convert_type(tokens[1])
                params.append(ParameterNode(name=p_name, mode=p_mode, data_type=p_type))
        return params

    def _parse_declarations(self, raw_decls: str) -> List[VariableDeclNode]:
        decls = []
        if not raw_decls.strip():
            return decls
        for line in raw_decls.split(';'):
            line = line.strip()
            if line:
                tokens = line.split()
                if len(tokens) >= 2:
                    v_name = tokens[0]
                    v_type = DataTypeRulesEngine.convert_type(tokens[1])
                    decls.append(VariableDeclNode(name=v_name, data_type=v_type))
        return decls

    def _extract_object_name(self, object_type: str, sql_text: str) -> str:
        m = re.search(rf'{object_type}\s+([A-Za-z0-9_"\.]+)', sql_text, re.IGNORECASE)
        return m.group(1).replace('"', '') if m else f"obj_{object_type.lower()}"
