"""4 materialized-view metadata/DDL cases (build-spec §10)."""
from __future__ import annotations

from .model import PLSQLObject

_DEFS = [
    ("COMMERCE_ORDERS", "mv_daily_order_summary", "simple",
     """CREATE MATERIALIZED VIEW COMMERCE_ORDERS.mv_daily_order_summary
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
AS
SELECT TRUNC(placed_at) AS order_date, COUNT(*) AS order_count, SUM(order_total) AS total_revenue
FROM COMMERCE_ORDERS.orders
GROUP BY TRUNC(placed_at);""",
     ["COMMERCE_ORDERS.orders"]),
    ("FINANCIAL_LEDGER", "mv_account_balance_snapshot", "simple",
     """CREATE MATERIALIZED VIEW FINANCIAL_LEDGER.mv_account_balance_snapshot
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
AS
SELECT id AS account_id, account_code, balance
FROM FINANCIAL_LEDGER.accounts;""",
     ["FINANCIAL_LEDGER.accounts"]),
    ("WAREHOUSE_INVENTORY", "mv_warehouse_stock_join", "moderate",
     """CREATE MATERIALIZED VIEW WAREHOUSE_INVENTORY.mv_warehouse_stock_join
BUILD IMMEDIATE
REFRESH FORCE ON COMMIT
AS
SELECT w.id AS warehouse_id, w.code, sb.sku_code, sb.quantity_on_hand
FROM WAREHOUSE_INVENTORY.warehouses w
JOIN WAREHOUSE_INVENTORY.stock_balances sb ON sb.warehouse_id = w.id;""",
     ["WAREHOUSE_INVENTORY.warehouses", "WAREHOUSE_INVENTORY.stock_balances"]),
    ("AUDIT_COMPLIANCE", "mv_compliance_observation_rollup", "moderate",
     """CREATE MATERIALIZED VIEW AUDIT_COMPLIANCE.mv_compliance_observation_rollup
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
AS
SELECT framework_id, severity, COUNT(*) AS observation_count
FROM AUDIT_COMPLIANCE.compliance_observations
GROUP BY framework_id, severity;""",
     ["AUDIT_COMPLIANCE.compliance_observations"]),
]


def build_materialized_views():
    objs = []
    for schema, name, band, sql, deps in _DEFS:
        objs.append(PLSQLObject(f"MATERIALIZED_VIEW.{schema}.{name}", "MATERIALIZED_VIEW", schema, name, sql,
                                 band, constructs=["SELECT", "MATERIALIZED_VIEW", "REFRESH_CLAUSE"], dependencies=deps))
    return objs


MATERIALIZED_VIEWS = build_materialized_views()
