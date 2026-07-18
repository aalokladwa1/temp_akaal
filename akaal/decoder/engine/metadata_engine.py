"""
Akaal — Metadata Normalization Engine
=====================================
Single-responsibility engine converting schema/table/column discovery metadata into CanonicalObject models.
Supports both dataclass and dictionary representations of DiscoveryReport inventories.
"""

from typing import List, Tuple, Optional, Any, Dict
from akaal.scout.models.discovery_report import DiscoveryReport
from akaal.decoder.models.canonical_object import CanonicalSchema, CanonicalTable, CanonicalColumn, CanonicalView
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph
from akaal.decoder.engine.datatype_engine import DatatypeEngine


class MetadataEngine:
    """Normalizes database metadata into CanonicalObjectGraph nodes."""

    def __init__(self, datatype_engine: Optional[DatatypeEngine] = None) -> None:
        self.datatype_engine = datatype_engine or DatatypeEngine()

    def normalize_metadata(self, report: DiscoveryReport) -> Tuple[CanonicalObjectGraph, List[CanonicalSchema]]:
        graph = CanonicalObjectGraph()
        schemas_list: List[CanonicalSchema] = []

        sch_inv = report.schema_inventory
        if isinstance(sch_inv, dict):
            raw_schemas = sch_inv.get("schemas", ["public"])
            raw_tables = sch_inv.get("tables", [])
            raw_views = sch_inv.get("views", [])
        elif sch_inv and hasattr(sch_inv, "schemas"):
            raw_schemas = getattr(sch_inv, "schemas", ["public"])
            raw_tables = getattr(sch_inv, "tables", [])
            raw_views = getattr(sch_inv, "views", [])
        else:
            raw_schemas = ["public"]
            raw_tables = []
            raw_views = []

        vendor_engine = report.engine_info.system_type if report.engine_info and hasattr(report.engine_info, "system_type") else "GENERIC"

        for s_name in raw_schemas:
            c_schema = CanonicalSchema(name=s_name)
            
            for t_meta in raw_tables:
                if isinstance(t_meta, dict):
                    t_sname = t_meta.get("schema_name", "public")
                    t_name = t_meta.get("table_name", "unknown")
                    t_cols = t_meta.get("columns", [])
                else:
                    t_sname = getattr(t_meta, "schema_name", "public")
                    t_name = getattr(t_meta, "table_name", "unknown")
                    t_cols = getattr(t_meta, "columns", [])

                if t_sname == s_name or (not t_sname and s_name == "public"):
                    cols: List[CanonicalColumn] = []
                    pk_cols: List[str] = []

                    for col_info in t_cols:
                        if isinstance(col_info, dict):
                            c_name = col_info.get("name", col_info.get("column_name", "unknown"))
                            raw_t = col_info.get("data_type", "varchar")
                            is_pk = col_info.get("primary_key", col_info.get("is_primary_key", False))
                            is_null = col_info.get("nullable", col_info.get("is_nullable", True))
                        else:
                            c_name = getattr(col_info, "name", "unknown")
                            raw_t = getattr(col_info, "data_type", "varchar")
                            is_pk = getattr(col_info, "primary_key", False)
                            is_null = getattr(col_info, "nullable", True)

                        if is_pk:
                            pk_cols.append(c_name)

                        c_type = self.datatype_engine.normalize_datatype(raw_t, vendor_engine)
                        col_obj = CanonicalColumn(
                            name=c_name,
                            data_type=c_type,
                            is_nullable=is_null,
                            is_primary_key=is_pk,
                        )
                        cols.append(col_obj)
                        graph.add_object(col_obj)

                    table_obj = CanonicalTable(
                        name=t_name,
                        schema_name=s_name,
                        columns=cols,
                        primary_key=pk_cols,
                    )
                    c_schema.tables.append(table_obj)
                    graph.add_object(table_obj)

            schemas_list.append(c_schema)
            graph.add_object(c_schema)

        return graph, schemas_list
