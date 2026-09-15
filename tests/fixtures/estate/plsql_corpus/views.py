"""~32 Oracle views: simple, join, aggregate, nested/dependent, function-calling."""
from __future__ import annotations

from .model import PLSQLObject

_SIMPLE = [
    ("IDENTITY_ACCESS_MGMT", "vw_active_users", "IDENTITY_ACCESS_MGMT.users", "status = 'ACTIVE'"),
    ("IDENTITY_ACCESS_MGMT", "vw_active_tenants", "IDENTITY_ACCESS_MGMT.tenants", "is_active = 1"),
    ("COMMERCE_ORDERS", "vw_open_orders", "COMMERCE_ORDERS.orders", "status IN ('PLACED','PROCESSING')"),
    ("COMMERCE_ORDERS", "vw_active_discounts", "COMMERCE_ORDERS.discounts", "is_active = 1"),
    ("FINANCIAL_LEDGER", "vw_open_invoices", "FINANCIAL_LEDGER.invoices", "status = 'OPEN'"),
    ("CATALOG_PRODUCTS", "vw_active_products", "CATALOG_PRODUCTS.products", "is_active = 1"),
    ("WAREHOUSE_INVENTORY", "vw_low_stock", "WAREHOUSE_INVENTORY.stock_balances", "quantity_on_hand < 10"),
    ("FULFILLMENT_LOGISTICS", "vw_pending_shipments", "FULFILLMENT_LOGISTICS.shipments", "status = 'PENDING'"),
    ("ORGANIZATION_HR", "vw_current_employees", "ORGANIZATION_HR.employees", "termination_date IS NULL"),
    ("CONTENT_DOCUMENTS", "vw_recent_documents", "CONTENT_DOCUMENTS.documents", "created_at > SYSDATE - 90"),
]

_JOIN = [
    ("COMMERCE_ORDERS", "vw_order_customer_detail",
     """SELECT o.id AS order_id, o.order_number, o.order_total, c.customer_code, c.full_name
FROM COMMERCE_ORDERS.orders o
JOIN COMMERCE_ORDERS.customers c ON c.id = o.customer_id""",
     ["COMMERCE_ORDERS.orders", "COMMERCE_ORDERS.customers"]),
    ("COMMERCE_ORDERS", "vw_order_line_detail",
     """SELECT ol.order_id, ol.line_no, ol.product_ref, ol.quantity, o.status
FROM COMMERCE_ORDERS.order_lines ol
JOIN COMMERCE_ORDERS.orders o ON o.id = ol.order_id""",
     ["COMMERCE_ORDERS.order_lines", "COMMERCE_ORDERS.orders"]),
    ("FINANCIAL_LEDGER", "vw_invoice_account_detail",
     """SELECT i.invoice_number, i.total_amount, a.account_code, a.account_name
FROM FINANCIAL_LEDGER.invoices i
JOIN FINANCIAL_LEDGER.accounts a ON a.id = i.account_id""",
     ["FINANCIAL_LEDGER.invoices", "FINANCIAL_LEDGER.accounts"]),
    ("FINANCIAL_LEDGER", "vw_posting_journal_detail",
     """SELECT p.journal_id, p.line_no, p.debit, p.credit, j.journal_type, j.status
FROM FINANCIAL_LEDGER.postings p
JOIN FINANCIAL_LEDGER.journals j ON j.id = p.journal_id""",
     ["FINANCIAL_LEDGER.postings", "FINANCIAL_LEDGER.journals"]),
    ("CATALOG_PRODUCTS", "vw_product_category_detail",
     """SELECT p.product_code, p.name, c.name AS category_name
FROM CATALOG_PRODUCTS.products p
JOIN CATALOG_PRODUCTS.categories c ON c.id = p.category_id""",
     ["CATALOG_PRODUCTS.products", "CATALOG_PRODUCTS.categories"]),
    ("CATALOG_PRODUCTS", "vw_sku_variant_detail",
     """SELECT s.sku_code, s.upc, v.variant_name
FROM CATALOG_PRODUCTS.skus s
JOIN CATALOG_PRODUCTS.variants v ON v.sku_code = s.sku_code""",
     ["CATALOG_PRODUCTS.skus", "CATALOG_PRODUCTS.variants"]),
    ("WAREHOUSE_INVENTORY", "vw_stock_by_warehouse",
     """SELECT w.warehouse_id, w.code AS warehouse_code, sb.sku_code, sb.quantity_on_hand
FROM WAREHOUSE_INVENTORY.stock_balances sb
JOIN WAREHOUSE_INVENTORY.warehouses w ON w.id = sb.warehouse_id""",
     ["WAREHOUSE_INVENTORY.stock_balances", "WAREHOUSE_INVENTORY.warehouses"]),
    ("FULFILLMENT_LOGISTICS", "vw_shipment_carrier_detail",
     """SELECT s.id AS shipment_id, s.status, c.code AS carrier_code
FROM FULFILLMENT_LOGISTICS.shipments s
JOIN FULFILLMENT_LOGISTICS.carriers c ON c.id = s.carrier_id""",
     ["FULFILLMENT_LOGISTICS.shipments", "FULFILLMENT_LOGISTICS.carriers"]),
    ("ORGANIZATION_HR", "vw_employee_department_detail",
     """SELECT e.employee_code, e.full_name, d.name AS department_name
FROM ORGANIZATION_HR.employees e
JOIN ORGANIZATION_HR.departments d ON d.id = e.department_id""",
     ["ORGANIZATION_HR.employees", "ORGANIZATION_HR.departments"]),
    ("AUDIT_COMPLIANCE", "vw_observation_framework_detail",
     """SELECT co.id, co.severity, cf.code AS framework_code
FROM AUDIT_COMPLIANCE.compliance_observations co
JOIN AUDIT_COMPLIANCE.compliance_frameworks cf ON cf.id = co.framework_id""",
     ["AUDIT_COMPLIANCE.compliance_observations", "AUDIT_COMPLIANCE.compliance_frameworks"]),
]

_AGG = [
    ("COMMERCE_ORDERS", "vw_customer_order_totals",
     """SELECT customer_id, COUNT(*) AS order_count, SUM(order_total) AS total_spent, AVG(order_total) AS avg_order_value
FROM COMMERCE_ORDERS.orders
GROUP BY customer_id""",
     ["COMMERCE_ORDERS.orders"]),
    ("FINANCIAL_LEDGER", "vw_account_balances_by_type",
     """SELECT account_type, COUNT(*) AS account_count, SUM(balance) AS total_balance
FROM FINANCIAL_LEDGER.accounts
GROUP BY account_type""",
     ["FINANCIAL_LEDGER.accounts"]),
    ("WAREHOUSE_INVENTORY", "vw_warehouse_stock_summary",
     """SELECT warehouse_id, COUNT(DISTINCT sku_code) AS distinct_skus, SUM(quantity_on_hand) AS total_units
FROM WAREHOUSE_INVENTORY.stock_balances
GROUP BY warehouse_id""",
     ["WAREHOUSE_INVENTORY.stock_balances"]),
    ("OPERATIONAL_METRICS", "vw_metric_sample_stats",
     """SELECT metric_id, COUNT(*) AS sample_count, MIN(value) AS min_value, MAX(value) AS max_value, AVG(value) AS avg_value
FROM OPERATIONAL_METRICS.metric_samples
GROUP BY metric_id""",
     ["OPERATIONAL_METRICS.metric_samples"]),
    ("AUDIT_COMPLIANCE", "vw_observation_severity_counts",
     """SELECT framework_id, severity, COUNT(*) AS observation_count
FROM AUDIT_COMPLIANCE.compliance_observations
GROUP BY framework_id, severity""",
     ["AUDIT_COMPLIANCE.compliance_observations"]),
    ("INTEGRATION_REGISTRY", "vw_webhook_delivery_success_rate",
     """SELECT webhook_id, COUNT(*) AS delivery_count,
       SUM(CASE WHEN response_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_count
FROM INTEGRATION_REGISTRY.webhook_deliveries
GROUP BY webhook_id""",
     ["INTEGRATION_REGISTRY.webhook_deliveries"]),
]

_NESTED = [
    ("COMMERCE_ORDERS", "vw_top_customers",
     """SELECT customer_id, total_spent
FROM COMMERCE_ORDERS.vw_customer_order_totals
WHERE total_spent > 1000""",
     ["COMMERCE_ORDERS.vw_customer_order_totals"]),
    ("FINANCIAL_LEDGER", "vw_negative_balance_accounts",
     """SELECT account_type, total_balance
FROM FINANCIAL_LEDGER.vw_account_balances_by_type
WHERE total_balance < 0""",
     ["FINANCIAL_LEDGER.vw_account_balances_by_type"]),
    ("WAREHOUSE_INVENTORY", "vw_overstocked_warehouses",
     """SELECT warehouse_id, total_units
FROM WAREHOUSE_INVENTORY.vw_warehouse_stock_summary
WHERE total_units > 100000""",
     ["WAREHOUSE_INVENTORY.vw_warehouse_stock_summary"]),
    ("AUDIT_COMPLIANCE", "vw_high_severity_framework_summary",
     """SELECT framework_id, observation_count
FROM AUDIT_COMPLIANCE.vw_observation_severity_counts
WHERE severity = 'HIGH'""",
     ["AUDIT_COMPLIANCE.vw_observation_severity_counts"]),
]

_FUNCTION_CALLING = [
    ("COMMERCE_ORDERS", "vw_order_totals_normalized",
     """SELECT id AS order_id, order_total, ORDER_MGMT_PKG.NORMALIZE_CURRENCY(order_total, currency) AS normalized_total
FROM COMMERCE_ORDERS.orders""",
     ["COMMERCE_ORDERS.orders", "PACKAGE.COMMERCE_ORDERS.ORDER_MGMT_PKG"]),
    ("FINANCIAL_LEDGER", "vw_invoice_tax_calculated",
     """SELECT invoice_id, amount, FN_CALCULATE_LINE_TAX(invoice_id, amount) AS calculated_tax
FROM FINANCIAL_LEDGER.invoice_lines""",
     ["FINANCIAL_LEDGER.invoice_lines", "FUNCTION.FINANCIAL_LEDGER.FN_CALCULATE_LINE_TAX"]),
]


def build_views():
    objs = []
    for schema, name, table, predicate in _SIMPLE:
        sql = f"CREATE OR REPLACE VIEW {schema}.{name} AS\nSELECT *\nFROM {table}\nWHERE {predicate};"
        objs.append(PLSQLObject(f"VIEW.{schema}.{name}", "VIEW", schema, name, sql, "simple",
                                 constructs=["SELECT", "WHERE"], dependencies=[table]))
    for schema, name, body, deps in _JOIN:
        sql = f"CREATE OR REPLACE VIEW {schema}.{name} AS\n{body};"
        objs.append(PLSQLObject(f"VIEW.{schema}.{name}", "VIEW", schema, name, sql, "moderate",
                                 constructs=["SELECT", "JOIN"], dependencies=deps))
    for schema, name, body, deps in _AGG:
        sql = f"CREATE OR REPLACE VIEW {schema}.{name} AS\n{body};"
        objs.append(PLSQLObject(f"VIEW.{schema}.{name}", "VIEW", schema, name, sql, "moderate",
                                 constructs=["SELECT", "GROUP BY", "AGGREGATE"], dependencies=deps))
    for schema, name, body, deps in _NESTED:
        sql = f"CREATE OR REPLACE VIEW {schema}.{name} AS\n{body};"
        objs.append(PLSQLObject(f"VIEW.{schema}.{name}", "VIEW", schema, name, sql, "complex",
                                 constructs=["SELECT", "NESTED_VIEW_DEPENDENCY"], dependencies=deps))
    for schema, name, body, deps in _FUNCTION_CALLING:
        sql = f"CREATE OR REPLACE VIEW {schema}.{name} AS\n{body};"
        objs.append(PLSQLObject(f"VIEW.{schema}.{name}", "VIEW", schema, name, sql, "complex",
                                 constructs=["SELECT", "FUNCTION_CALL"], dependencies=deps))
    return objs


VIEWS = build_views()
