"""~40 Oracle sequences with varied start/increment/cache/cycle/min/max (build-spec §10)."""
from __future__ import annotations

from .model import PLSQLObject

_SCHEMAS = [
    "IDENTITY_ACCESS_MGMT", "COMMERCE_ORDERS", "FINANCIAL_LEDGER", "CATALOG_PRODUCTS",
    "WAREHOUSE_INVENTORY", "FULFILLMENT_LOGISTICS", "ORGANIZATION_HR", "CONTENT_DOCUMENTS",
    "AUDIT_COMPLIANCE", "OPERATIONAL_METRICS", "INTEGRATION_REGISTRY", "COMPATIBILITY_LAB",
]

# variety matrix cycled across the 40 sequences: (start, increment, cache, cycle, minvalue, maxvalue)
_VARIANTS = [
    (1, 1, 20, False, 1, None),
    (1000, 1, 50, False, 1, None),
    (1, 10, 0, False, 1, None),               # NOCACHE
    (100, 5, 100, True, 1, 100000),            # CYCLE with bounds
    (0, 1, 20, False, 0, None),                # starts at zero
    (-1000, 1, 20, False, -1000, 1000000),     # negative start
    (1, 1, 20, True, 1, 999999),               # cycling
    (500000, 1, 30, False, 1, None),           # high start
]


def build_sequences():
    objs = []
    n = 0
    for schema in _SCHEMAS:
        for j in range(3 if schema not in ("COMMERCE_ORDERS", "FINANCIAL_LEDGER", "IDENTITY_ACCESS_MGMT", "CATALOG_PRODUCTS") else 4):
            n += 1
            name = f"seq_{schema.lower()}_{n:03d}"
            start, incr, cache, cycle, minv, maxv = _VARIANTS[n % len(_VARIANTS)]
            clauses = [f"START WITH {start}", f"INCREMENT BY {incr}"]
            clauses.append(f"MINVALUE {minv}")
            if maxv is not None:
                clauses.append(f"MAXVALUE {maxv}")
            else:
                clauses.append("NOMAXVALUE")
            clauses.append(f"CACHE {cache}" if cache > 0 else "NOCACHE")
            clauses.append("CYCLE" if cycle else "NOCYCLE")
            sql = f"CREATE SEQUENCE {schema}.{name}\n  " + "\n  ".join(clauses) + ";"
            band = "simple" if cache > 0 and not cycle else "moderate"
            objs.append(PLSQLObject(
                f"SEQUENCE.{schema}.{name}", "SEQUENCE", schema, name, sql, band,
                constructs=["SEQUENCE_DDL"] + (["CYCLE"] if cycle else []) + (["NOCACHE"] if cache == 0 else []),
                dependencies=[],
            ))
    return objs


SEQUENCES = build_sequences()
