"""24+ Oracle functions covering the construct matrix in build-spec §11."""
from __future__ import annotations

from .model import PLSQLObject

_DEFS = [
    ("COMMERCE_ORDERS", "FN_CALCULATE_ORDER_TOTAL", "NUMBER", "moderate",
     [{"name": "p_order_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_CALCULATE_ORDER_TOTAL(p_order_id IN NUMBER) RETURN NUMBER IS
  v_total NUMBER := 0;
BEGIN
  SELECT NVL(SUM(line_total), 0) INTO v_total FROM COMMERCE_ORDERS.order_lines WHERE order_id = p_order_id;
  RETURN v_total;
END FN_CALCULATE_ORDER_TOTAL;""",
     ["IN_PARAM", "LOCAL_VAR", "SELECT_INTO", "NVL", "RETURN"]),

    ("COMMERCE_ORDERS", "FN_IS_ORDER_CANCELLABLE", "NUMBER", "simple",
     [{"name": "p_status", "mode": "IN", "type": "VARCHAR2"}],
     """FUNCTION FN_IS_ORDER_CANCELLABLE(p_status IN VARCHAR2) RETURN NUMBER IS
BEGIN
  RETURN CASE WHEN p_status IN ('PLACED', 'PROCESSING') THEN 1 ELSE 0 END;
END FN_IS_ORDER_CANCELLABLE;""",
     ["IN_PARAM", "CASE", "RETURN"]),

    ("FINANCIAL_LEDGER", "FN_CALCULATE_LINE_TAX", "NUMBER", "moderate",
     [{"name": "p_invoice_id", "mode": "IN", "type": "NUMBER"}, {"name": "p_amount", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_CALCULATE_LINE_TAX(p_invoice_id IN NUMBER, p_amount IN NUMBER) RETURN NUMBER IS
  v_rate NUMBER;
BEGIN
  SELECT NVL(MAX(tr.rate_percent), 0) INTO v_rate
    FROM FINANCIAL_LEDGER.invoice_lines il
    JOIN FINANCIAL_LEDGER.tax_rates tr ON tr.id = il.tax_rate_id
   WHERE il.invoice_id = p_invoice_id;
  RETURN ROUND(p_amount * v_rate / 100, 2);
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN 0;
END FN_CALCULATE_LINE_TAX;""",
     ["IN_PARAM", "LOCAL_VAR", "SELECT_INTO", "JOIN", "ROUND", "NO_DATA_FOUND", "EXCEPTION_HANDLER", "RETURN"]),

    ("FINANCIAL_LEDGER", "FN_CONVERT_CURRENCY", "NUMBER", "complex",
     [{"name": "p_amount", "mode": "IN", "type": "NUMBER"}, {"name": "p_from", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_to", "mode": "IN", "type": "VARCHAR2"}, {"name": "p_date", "mode": "IN", "type": "DATE"}],
     """FUNCTION FN_CONVERT_CURRENCY(p_amount IN NUMBER, p_from IN VARCHAR2, p_to IN VARCHAR2, p_date IN DATE) RETURN NUMBER IS
  v_rate BINARY_DOUBLE;
BEGIN
  IF p_from = p_to THEN
    RETURN p_amount;
  END IF;
  SELECT rate INTO v_rate FROM FINANCIAL_LEDGER.exchange_rates
   WHERE from_currency = p_from AND to_currency = p_to AND rate_date = TRUNC(p_date);
  RETURN p_amount * v_rate;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20300, 'no exchange rate found for ' || p_from || '->' || p_to);
END FN_CONVERT_CURRENCY;""",
     ["IN_PARAM", "IF", "SELECT_INTO", "TRUNC", "NO_DATA_FOUND", "RAISE_APPLICATION_ERROR", "RETURN"]),

    ("FINANCIAL_LEDGER", "FN_FISCAL_PERIOD_FOR_DATE", "NUMBER", "moderate",
     [{"name": "p_date", "mode": "IN", "type": "DATE"}],
     """FUNCTION FN_FISCAL_PERIOD_FOR_DATE(p_date IN DATE) RETURN NUMBER IS
  v_id NUMBER;
BEGIN
  SELECT id INTO v_id FROM FINANCIAL_LEDGER.fiscal_periods
   WHERE p_date BETWEEN period_start AND period_end;
  RETURN v_id;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN NULL;
  WHEN TOO_MANY_ROWS THEN
    RETURN NULL;
END FN_FISCAL_PERIOD_FOR_DATE;""",
     ["IN_PARAM", "SELECT_INTO", "BETWEEN", "NO_DATA_FOUND", "TOO_MANY_ROWS", "RETURN"]),

    ("CATALOG_PRODUCTS", "FN_PRODUCT_DISPLAY_NAME", "VARCHAR2", "simple",
     [{"name": "p_product_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_PRODUCT_DISPLAY_NAME(p_product_id IN NUMBER) RETURN VARCHAR2 IS
  v_name CATALOG_PRODUCTS.products.name%TYPE;
BEGIN
  SELECT name INTO v_name FROM CATALOG_PRODUCTS.products WHERE id = p_product_id;
  RETURN INITCAP(v_name);
END FN_PRODUCT_DISPLAY_NAME;""",
     ["IN_PARAM", "PERCENT_TYPE", "SELECT_INTO", "INITCAP", "RETURN"]),

    ("CATALOG_PRODUCTS", "FN_CATEGORY_DEPTH", "NUMBER", "very_complex",
     [{"name": "p_category_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_CATEGORY_DEPTH(p_category_id IN NUMBER) RETURN NUMBER IS
  v_parent NUMBER;
  v_depth NUMBER := 0;
  v_current NUMBER := p_category_id;
BEGIN
  LOOP
    SELECT parent_category_id INTO v_parent FROM CATALOG_PRODUCTS.categories WHERE id = v_current;
    EXIT WHEN v_parent IS NULL;
    v_depth := v_depth + 1;
    v_current := v_parent;
    EXIT WHEN v_depth > 50;
  END LOOP;
  RETURN v_depth;
END FN_CATEGORY_DEPTH;""",
     ["IN_PARAM", "LOCAL_VAR", "LOOP", "SELECT_INTO", "EXIT_WHEN", "RETURN"]),

    ("WAREHOUSE_INVENTORY", "FN_AVAILABLE_QUANTITY", "NUMBER", "moderate",
     [{"name": "p_warehouse_id", "mode": "IN", "type": "NUMBER"}, {"name": "p_sku_code", "mode": "IN", "type": "VARCHAR2"}],
     """FUNCTION FN_AVAILABLE_QUANTITY(p_warehouse_id IN NUMBER, p_sku_code IN VARCHAR2) RETURN NUMBER IS
  v_qty NUMBER;
BEGIN
  SELECT quantity_on_hand - quantity_reserved INTO v_qty
    FROM WAREHOUSE_INVENTORY.stock_balances
   WHERE warehouse_id = p_warehouse_id AND sku_code = p_sku_code;
  RETURN NVL(v_qty, 0);
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN 0;
END FN_AVAILABLE_QUANTITY;""",
     ["IN_PARAM", "SELECT_INTO", "NVL", "NO_DATA_FOUND", "RETURN"]),

    ("WAREHOUSE_INVENTORY", "FN_IS_LOT_EXPIRED", "NUMBER", "simple",
     [{"name": "p_lot_number", "mode": "IN", "type": "VARCHAR2"}],
     """FUNCTION FN_IS_LOT_EXPIRED(p_lot_number IN VARCHAR2) RETURN NUMBER IS
  v_expires DATE;
BEGIN
  SELECT expires_at INTO v_expires FROM WAREHOUSE_INVENTORY.lots WHERE lot_number = p_lot_number;
  RETURN CASE WHEN v_expires IS NOT NULL AND v_expires < SYSDATE THEN 1 ELSE 0 END;
END FN_IS_LOT_EXPIRED;""",
     ["IN_PARAM", "SELECT_INTO", "CASE", "RETURN"]),

    ("FULFILLMENT_LOGISTICS", "FN_ESTIMATED_DELIVERY_DATE", "DATE", "moderate",
     [{"name": "p_shipment_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_ESTIMATED_DELIVERY_DATE(p_shipment_id IN NUMBER) RETURN DATE IS
  v_shipped DATE;
BEGIN
  SELECT shipped_at INTO v_shipped FROM FULFILLMENT_LOGISTICS.shipments WHERE id = p_shipment_id;
  RETURN NVL(v_shipped, SYSDATE) + 5;
END FN_ESTIMATED_DELIVERY_DATE;""",
     ["IN_PARAM", "SELECT_INTO", "NVL", "DATE_ARITHMETIC", "RETURN"]),

    ("FULFILLMENT_LOGISTICS", "FN_CARRIER_SUCCESS_RATE", "NUMBER", "complex",
     [{"name": "p_carrier_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_CARRIER_SUCCESS_RATE(p_carrier_id IN NUMBER) RETURN NUMBER IS
  v_total NUMBER;
  v_success NUMBER;
BEGIN
  SELECT COUNT(*), SUM(CASE WHEN outcome = 'DELIVERED' THEN 1 ELSE 0 END)
    INTO v_total, v_success
    FROM FULFILLMENT_LOGISTICS.delivery_attempts da
    JOIN FULFILLMENT_LOGISTICS.shipments s ON s.id = da.shipment_id
   WHERE s.carrier_id = p_carrier_id;
  IF v_total = 0 THEN
    RETURN NULL;
  END IF;
  RETURN ROUND(v_success / v_total * 100, 2);
END FN_CARRIER_SUCCESS_RATE;""",
     ["IN_PARAM", "SELECT_INTO_MULTI", "CASE", "JOIN", "IF", "ROUND", "RETURN"]),

    ("ORGANIZATION_HR", "FN_EMPLOYEE_TENURE_YEARS", "NUMBER", "simple",
     [{"name": "p_employee_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_EMPLOYEE_TENURE_YEARS(p_employee_id IN NUMBER) RETURN NUMBER IS
  v_hire DATE;
BEGIN
  SELECT hire_date INTO v_hire FROM ORGANIZATION_HR.employees WHERE id = p_employee_id;
  RETURN TRUNC(MONTHS_BETWEEN(SYSDATE, v_hire) / 12);
END FN_EMPLOYEE_TENURE_YEARS;""",
     ["IN_PARAM", "SELECT_INTO", "MONTHS_BETWEEN", "TRUNC", "RETURN"]),

    ("ORGANIZATION_HR", "FN_IS_MANAGER", "NUMBER", "moderate",
     [{"name": "p_employee_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_IS_MANAGER(p_employee_id IN NUMBER) RETURN NUMBER IS
  v_cnt NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_cnt FROM ORGANIZATION_HR.reporting_lines WHERE manager_id = p_employee_id;
  RETURN CASE WHEN v_cnt > 0 THEN 1 ELSE 0 END;
END FN_IS_MANAGER;""",
     ["IN_PARAM", "SELECT_INTO", "CASE", "RETURN"]),

    ("CONTENT_DOCUMENTS", "FN_LATEST_REVISION_NO", "NUMBER", "simple",
     [{"name": "p_document_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_LATEST_REVISION_NO(p_document_id IN NUMBER) RETURN NUMBER IS
  v_max NUMBER;
BEGIN
  SELECT NVL(MAX(revision_no), 0) INTO v_max FROM CONTENT_DOCUMENTS.document_revisions WHERE document_id = p_document_id;
  RETURN v_max;
END FN_LATEST_REVISION_NO;""",
     ["IN_PARAM", "SELECT_INTO", "NVL", "RETURN"]),

    ("CONTENT_DOCUMENTS", "FN_DOCUMENT_WORD_COUNT", "NUMBER", "moderate",
     [{"name": "p_document_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_DOCUMENT_WORD_COUNT(p_document_id IN NUMBER) RETURN NUMBER IS
  v_text CLOB;
BEGIN
  SELECT text_content INTO v_text FROM CONTENT_DOCUMENTS.documents WHERE id = p_document_id;
  IF v_text IS NULL THEN
    RETURN 0;
  END IF;
  RETURN LENGTH(v_text) - LENGTH(REPLACE(v_text, ' ', '')) + 1;
END FN_DOCUMENT_WORD_COUNT;""",
     ["IN_PARAM", "SELECT_INTO", "CLOB_HANDLING", "IF", "LENGTH", "REPLACE", "RETURN"]),

    ("AUDIT_COMPLIANCE", "FN_OBSERVATION_SEVERITY_RANK", "NUMBER", "simple",
     [{"name": "p_severity", "mode": "IN", "type": "VARCHAR2"}],
     """FUNCTION FN_OBSERVATION_SEVERITY_RANK(p_severity IN VARCHAR2) RETURN NUMBER IS
BEGIN
  RETURN CASE p_severity
           WHEN 'CRITICAL' THEN 4
           WHEN 'HIGH' THEN 3
           WHEN 'MEDIUM' THEN 2
           WHEN 'LOW' THEN 1
           ELSE 0
         END;
END FN_OBSERVATION_SEVERITY_RANK;""",
     ["IN_PARAM", "CASE", "RETURN"]),

    ("AUDIT_COMPLIANCE", "FN_HAS_OPEN_REMEDIATION", "NUMBER", "moderate",
     [{"name": "p_observation_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_HAS_OPEN_REMEDIATION(p_observation_id IN NUMBER) RETURN NUMBER IS
  v_cnt NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_cnt FROM AUDIT_COMPLIANCE.change_histories
   WHERE entity_ref = TO_CHAR(p_observation_id);
  RETURN CASE WHEN v_cnt > 0 THEN 1 ELSE 0 END;
END FN_HAS_OPEN_REMEDIATION;""",
     ["IN_PARAM", "SELECT_INTO", "TO_CHAR", "CASE", "RETURN"]),

    ("OPERATIONAL_METRICS", "FN_METRIC_MOVING_AVG", "NUMBER", "complex",
     [{"name": "p_metric_id", "mode": "IN", "type": "NUMBER"}, {"name": "p_window", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_METRIC_MOVING_AVG(p_metric_id IN NUMBER, p_window IN NUMBER) RETURN NUMBER IS
  CURSOR c_samples IS
    SELECT value FROM OPERATIONAL_METRICS.metric_samples
     WHERE metric_id = p_metric_id
     ORDER BY sampled_at DESC
     FETCH FIRST p_window ROWS ONLY;
  v_sum BINARY_DOUBLE := 0;
  v_cnt NUMBER := 0;
BEGIN
  FOR r IN c_samples LOOP
    v_sum := v_sum + r.value;
    v_cnt := v_cnt + 1;
  END LOOP;
  IF v_cnt = 0 THEN
    RETURN NULL;
  END IF;
  RETURN v_sum / v_cnt;
END FN_METRIC_MOVING_AVG;""",
     ["IN_PARAM", "EXPLICIT_CURSOR", "FETCH_FIRST", "CURSOR_FOR_LOOP", "IF", "RETURN"]),

    ("INTEGRATION_REGISTRY", "FN_WEBHOOK_IS_HEALTHY", "NUMBER", "complex",
     [{"name": "p_webhook_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_WEBHOOK_IS_HEALTHY(p_webhook_id IN NUMBER) RETURN NUMBER IS
  v_recent_failures NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_recent_failures
    FROM INTEGRATION_REGISTRY.webhook_deliveries
   WHERE webhook_id = p_webhook_id AND response_code >= 500
     AND delivered_at > SYSTIMESTAMP - INTERVAL '1' DAY;
  RETURN CASE WHEN v_recent_failures >= 5 THEN 0 ELSE 1 END;
END FN_WEBHOOK_IS_HEALTHY;""",
     ["IN_PARAM", "SELECT_INTO", "INTERVAL_LITERAL", "CASE", "RETURN"]),

    ("INTEGRATION_REGISTRY", "FN_NEXT_RETRY_DELAY_SECONDS", "NUMBER", "moderate",
     [{"name": "p_attempt_no", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_NEXT_RETRY_DELAY_SECONDS(p_attempt_no IN NUMBER) RETURN NUMBER IS
BEGIN
  RETURN LEAST(POWER(2, p_attempt_no) * 10, 3600);
END FN_NEXT_RETRY_DELAY_SECONDS;""",
     ["IN_PARAM", "LEAST", "POWER", "RETURN"]),

    ("COMPATIBILITY_LAB", "FN_ROUND_HALF_UP", "NUMBER", "simple",
     [{"name": "p_value", "mode": "IN", "type": "NUMBER"}, {"name": "p_scale", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_ROUND_HALF_UP(p_value IN NUMBER, p_scale IN NUMBER) RETURN NUMBER IS
BEGIN
  RETURN ROUND(p_value, p_scale);
END FN_ROUND_HALF_UP;""",
     ["IN_PARAM", "ROUND", "RETURN"]),

    ("COMPATIBILITY_LAB", "FN_SAFE_DIVIDE", "NUMBER", "moderate",
     [{"name": "p_numerator", "mode": "IN", "type": "NUMBER"}, {"name": "p_denominator", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_SAFE_DIVIDE(p_numerator IN NUMBER, p_denominator IN NUMBER) RETURN NUMBER IS
BEGIN
  IF p_denominator = 0 THEN
    RETURN NULL;
  END IF;
  RETURN p_numerator / p_denominator;
EXCEPTION
  WHEN ZERO_DIVIDE THEN
    RETURN NULL;
END FN_SAFE_DIVIDE;""",
     ["IN_PARAM", "IF", "ZERO_DIVIDE", "EXCEPTION_HANDLER", "RETURN"]),

    ("COMPATIBILITY_LAB", "FN_UNICODE_LENGTH", "NUMBER", "simple",
     [{"name": "p_text", "mode": "IN", "type": "NVARCHAR2"}],
     """FUNCTION FN_UNICODE_LENGTH(p_text IN NVARCHAR2) RETURN NUMBER IS
BEGIN
  RETURN NVL(LENGTHC(p_text), 0);
END FN_UNICODE_LENGTH;""",
     ["IN_PARAM", "LENGTHC", "NVL", "RETURN"]),

    ("COMPATIBILITY_LAB", "FN_QUOTED_IDENT_ECHO", "VARCHAR2", "simple",
     [{"name": "p_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_QUOTED_IDENT_ECHO(p_id IN NUMBER) RETURN VARCHAR2 IS
  v_val VARCHAR2(50);
BEGIN
  SELECT "Mixed_Case_Col" INTO v_val FROM COMPATIBILITY_LAB."Quoted_Case_Table" WHERE id = p_id;
  RETURN v_val;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RETURN NULL;
END FN_QUOTED_IDENT_ECHO;""",
     ["IN_PARAM", "QUOTED_IDENTIFIER", "SELECT_INTO", "NO_DATA_FOUND", "EXCEPTION_HANDLER", "RETURN"]),

    ("ORGANIZATION_HR", "FN_DEPARTMENT_HEADCOUNT", "NUMBER", "moderate",
     [{"name": "p_department_id", "mode": "IN", "type": "NUMBER"}],
     """FUNCTION FN_DEPARTMENT_HEADCOUNT(p_department_id IN NUMBER) RETURN NUMBER IS
  v_cnt NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_cnt FROM ORGANIZATION_HR.employees
   WHERE department_id = p_department_id AND termination_date IS NULL;
  RETURN v_cnt;
END FN_DEPARTMENT_HEADCOUNT;""",
     ["IN_PARAM", "SELECT_INTO", "RETURN"]),
]


def build_functions():
    objs = []
    for schema, name, ret, band, params, sql, constructs in _DEFS:
        objs.append(PLSQLObject(f"FUNCTION.{schema}.{name}", "FUNCTION", schema, name, sql, band,
                                 constructs=constructs, dependencies=[], parameters=params, returns=ret))
    return objs


FUNCTIONS = build_functions()
