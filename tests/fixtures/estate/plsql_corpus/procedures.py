"""24+ Oracle stored procedures covering the construct matrix in build-spec §11."""
from __future__ import annotations

from .model import PLSQLObject

_DEFS = [
    ("COMMERCE_ORDERS", "PRC_PLACE_ORDER", "complex",
     [{"name": "p_customer_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_order_total", "mode": "IN", "type": "NUMBER"},
      {"name": "p_order_id", "mode": "OUT", "type": "NUMBER"}],
     """PROCEDURE PRC_PLACE_ORDER(p_customer_id IN NUMBER, p_order_total IN NUMBER, p_order_id OUT NUMBER) IS
  v_status VARCHAR2(16) := 'PLACED';
  e_invalid_total EXCEPTION;
BEGIN
  IF p_order_total <= 0 THEN
    RAISE e_invalid_total;
  END IF;
  INSERT INTO COMMERCE_ORDERS.orders (customer_id, order_total, status, placed_at)
  VALUES (p_customer_id, p_order_total, v_status, SYSTIMESTAMP)
  RETURNING id INTO p_order_id;
  COMMIT;
EXCEPTION
  WHEN e_invalid_total THEN
    RAISE_APPLICATION_ERROR(-20100, 'order total must be positive');
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END PRC_PLACE_ORDER;""",
     ["IN_PARAM", "OUT_PARAM", "LOCAL_VAR", "CUSTOM_EXCEPTION", "RAISE", "RAISE_APPLICATION_ERROR",
      "RETURNING_INTO", "COMMIT", "ROLLBACK", "EXCEPTION_HANDLER"]),

    ("COMMERCE_ORDERS", "PRC_CANCEL_ORDER_LINES", "moderate",
     [{"name": "p_order_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_CANCEL_ORDER_LINES(p_order_id IN NUMBER) IS
  CURSOR c_lines IS
    SELECT id FROM COMMERCE_ORDERS.order_lines WHERE order_id = p_order_id;
BEGIN
  FOR r_line IN c_lines LOOP
    UPDATE COMMERCE_ORDERS.order_lines SET quantity = 0 WHERE id = r_line.id;
  END LOOP;
END PRC_CANCEL_ORDER_LINES;""",
     ["IN_PARAM", "EXPLICIT_CURSOR", "CURSOR_FOR_LOOP", "UPDATE"]),

    ("COMMERCE_ORDERS", "PRC_APPLY_BULK_DISCOUNT", "very_complex",
     [{"name": "p_discount_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_order_ids", "mode": "IN", "type": "SYS.ODCINUMBERLIST"}],
     """PROCEDURE PRC_APPLY_BULK_DISCOUNT(p_discount_id IN NUMBER, p_order_ids IN SYS.ODCINUMBERLIST) IS
  TYPE t_amount_tab IS TABLE OF NUMBER INDEX BY PLS_INTEGER;
  v_amounts t_amount_tab;
BEGIN
  FORALL i IN INDICES OF p_order_ids
    INSERT INTO COMMERCE_ORDERS.order_discounts (order_id, discount_id, applied_amount)
    VALUES (p_order_ids(i), p_discount_id, 0);

  FOR i IN 1 .. p_order_ids.COUNT LOOP
    v_amounts(i) := i * 1.0;
  END LOOP;
END PRC_APPLY_BULK_DISCOUNT;""",
     ["IN_PARAM", "COLLECTION_TYPE", "ASSOCIATIVE_ARRAY", "FORALL", "NUMERIC_FOR_LOOP"]),

    ("FINANCIAL_LEDGER", "PRC_POST_JOURNAL", "very_complex",
     [{"name": "p_journal_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_POST_JOURNAL(p_journal_id IN NUMBER) IS
  CURSOR c_postings IS
    SELECT account_id, debit, credit FROM FINANCIAL_LEDGER.postings WHERE journal_id = p_journal_id;
  v_total_debit NUMBER := 0;
  v_total_credit NUMBER := 0;
  e_unbalanced EXCEPTION;
BEGIN
  FOR r IN c_postings LOOP
    v_total_debit := v_total_debit + NVL(r.debit, 0);
    v_total_credit := v_total_credit + NVL(r.credit, 0);
  END LOOP;

  IF v_total_debit != v_total_credit THEN
    RAISE e_unbalanced;
  END IF;

  UPDATE FINANCIAL_LEDGER.journals SET status = 'POSTED', posted_at = SYSTIMESTAMP WHERE id = p_journal_id;
  COMMIT;
EXCEPTION
  WHEN e_unbalanced THEN
    RAISE_APPLICATION_ERROR(-20110, 'journal does not balance: debit != credit');
END PRC_POST_JOURNAL;""",
     ["IN_PARAM", "EXPLICIT_CURSOR", "CURSOR_FOR_LOOP", "LOCAL_VAR", "NVL", "CUSTOM_EXCEPTION",
      "RAISE", "RAISE_APPLICATION_ERROR", "UPDATE", "COMMIT"]),

    ("FINANCIAL_LEDGER", "PRC_RECALC_ACCOUNT_BALANCE", "complex",
     [{"name": "p_account_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_RECALC_ACCOUNT_BALANCE(p_account_id IN NUMBER) IS
  v_balance FINANCIAL_LEDGER.accounts.balance%TYPE;
BEGIN
  SELECT NVL(SUM(debit - credit), 0) INTO v_balance
    FROM FINANCIAL_LEDGER.postings WHERE account_id = p_account_id;
  UPDATE FINANCIAL_LEDGER.accounts SET balance = v_balance WHERE id = p_account_id;
END PRC_RECALC_ACCOUNT_BALANCE;""",
     ["IN_PARAM", "PERCENT_TYPE", "SELECT_INTO", "NVL", "UPDATE"]),

    ("FINANCIAL_LEDGER", "PRC_CLOSE_FISCAL_PERIOD", "moderate",
     [{"name": "p_period_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_closed", "mode": "OUT", "type": "NUMBER"}],
     """PROCEDURE PRC_CLOSE_FISCAL_PERIOD(p_period_id IN NUMBER, p_closed OUT NUMBER) IS
BEGIN
  UPDATE FINANCIAL_LEDGER.fiscal_periods SET is_closed = 1 WHERE id = p_period_id;
  p_closed := SQL%ROWCOUNT;
END PRC_CLOSE_FISCAL_PERIOD;""",
     ["IN_PARAM", "OUT_PARAM", "UPDATE", "SQL_ROWCOUNT"]),

    ("CATALOG_PRODUCTS", "PRC_DEACTIVATE_PRODUCT_TREE", "complex",
     [{"name": "p_category_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_DEACTIVATE_PRODUCT_TREE(p_category_id IN NUMBER) IS
BEGIN
  UPDATE CATALOG_PRODUCTS.products SET is_active = 0 WHERE category_id = p_category_id;

  FOR r_child IN (SELECT id FROM CATALOG_PRODUCTS.categories WHERE parent_category_id = p_category_id) LOOP
    PRC_DEACTIVATE_PRODUCT_TREE(r_child.id);  -- recursive cross-call
  END LOOP;
END PRC_DEACTIVATE_PRODUCT_TREE;""",
     ["IN_PARAM", "UPDATE", "IMPLICIT_CURSOR_FOR_LOOP", "RECURSIVE_CALL"]),

    ("CATALOG_PRODUCTS", "PRC_REPRICE_SKU", "moderate",
     [{"name": "p_price_book_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_sku_code", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_new_price", "mode": "IN OUT", "type": "NUMBER"}],
     """PROCEDURE PRC_REPRICE_SKU(p_price_book_id IN NUMBER, p_sku_code IN VARCHAR2, p_new_price IN OUT NUMBER) IS
BEGIN
  IF p_new_price < 0 THEN
    p_new_price := 0;
  END IF;
  MERGE INTO CATALOG_PRODUCTS.price_book_entries t
  USING (SELECT p_price_book_id AS pbid, p_sku_code AS sku FROM DUAL) s
  ON (t.price_book_id = s.pbid AND t.sku_code = s.sku)
  WHEN MATCHED THEN UPDATE SET price = p_new_price
  WHEN NOT MATCHED THEN INSERT (price_book_id, sku_code, price) VALUES (s.pbid, s.sku, p_new_price);
END PRC_REPRICE_SKU;""",
     ["IN_PARAM", "IN_OUT_PARAM", "IF", "MERGE", "DUAL"]),

    ("WAREHOUSE_INVENTORY", "PRC_RESERVE_STOCK", "very_complex",
     [{"name": "p_warehouse_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_sku_code", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_quantity", "mode": "IN", "type": "NUMBER"},
      {"name": "p_success", "mode": "OUT", "type": "NUMBER"}],
     """PROCEDURE PRC_RESERVE_STOCK(p_warehouse_id IN NUMBER, p_sku_code IN VARCHAR2, p_quantity IN NUMBER, p_success OUT NUMBER) IS
  v_available NUMBER;
  e_insufficient EXCEPTION;
  PRAGMA EXCEPTION_INIT(e_insufficient, -20200);
BEGIN
  SELECT quantity_on_hand - quantity_reserved INTO v_available
    FROM WAREHOUSE_INVENTORY.stock_balances
   WHERE warehouse_id = p_warehouse_id AND sku_code = p_sku_code
     FOR UPDATE;

  IF v_available < p_quantity THEN
    RAISE_APPLICATION_ERROR(-20200, 'insufficient stock to reserve');
  END IF;

  UPDATE WAREHOUSE_INVENTORY.stock_balances
     SET quantity_reserved = quantity_reserved + p_quantity
   WHERE warehouse_id = p_warehouse_id AND sku_code = p_sku_code;

  p_success := 1;
EXCEPTION
  WHEN e_insufficient THEN
    p_success := 0;
END PRC_RESERVE_STOCK;""",
     ["IN_PARAM", "OUT_PARAM", "SELECT_INTO", "FOR_UPDATE", "PRAGMA_EXCEPTION_INIT",
      "RAISE_APPLICATION_ERROR", "UPDATE", "EXCEPTION_HANDLER"]),

    ("WAREHOUSE_INVENTORY", "PRC_RECEIVE_LOT", "moderate",
     [{"name": "p_lot_number", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_sku_code", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_quantity", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_RECEIVE_LOT(p_lot_number IN VARCHAR2, p_sku_code IN VARCHAR2, p_quantity IN NUMBER) IS
BEGIN
  INSERT INTO WAREHOUSE_INVENTORY.lots (lot_number, sku_code, quantity)
  VALUES (p_lot_number, p_sku_code, p_quantity);
END PRC_RECEIVE_LOT;""",
     ["IN_PARAM", "INSERT"]),

    ("WAREHOUSE_INVENTORY", "PRC_CYCLE_COUNT_ADJUST", "complex",
     [{"name": "p_warehouse_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_sku_code", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_counted_qty", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_CYCLE_COUNT_ADJUST(p_warehouse_id IN NUMBER, p_sku_code IN VARCHAR2, p_counted_qty IN NUMBER) IS
  v_system_qty NUMBER;
  v_delta NUMBER;
BEGIN
  SELECT quantity_on_hand INTO v_system_qty
    FROM WAREHOUSE_INVENTORY.stock_balances
   WHERE warehouse_id = p_warehouse_id AND sku_code = p_sku_code;

  v_delta := p_counted_qty - v_system_qty;

  IF v_delta != 0 THEN
    INSERT INTO WAREHOUSE_INVENTORY.movements (sku_code, warehouse_id, movement_type, quantity, occurred_at)
    VALUES (p_sku_code, p_warehouse_id, CASE WHEN v_delta > 0 THEN 'INBOUND' ELSE 'OUTBOUND' END, ABS(v_delta), SYSTIMESTAMP);
  END IF;
END PRC_CYCLE_COUNT_ADJUST;""",
     ["IN_PARAM", "SELECT_INTO", "LOCAL_VAR", "IF", "CASE", "INSERT", "ABS"]),

    ("FULFILLMENT_LOGISTICS", "PRC_DISPATCH_SHIPMENT", "complex",
     [{"name": "p_shipment_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_DISPATCH_SHIPMENT(p_shipment_id IN NUMBER) IS
BEGIN
  UPDATE FULFILLMENT_LOGISTICS.shipments SET status = 'SHIPPED', shipped_at = SYSTIMESTAMP WHERE id = p_shipment_id;
  INSERT INTO FULFILLMENT_LOGISTICS.tracking_events (shipment_id, event_code, occurred_at)
  VALUES (p_shipment_id, 'DISPATCHED', SYSTIMESTAMP);
COMMIT;
END PRC_DISPATCH_SHIPMENT;""",
     ["IN_PARAM", "UPDATE", "INSERT", "COMMIT"]),

    ("FULFILLMENT_LOGISTICS", "PRC_RECORD_DELIVERY_ATTEMPT", "simple",
     [{"name": "p_shipment_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_outcome", "mode": "IN", "type": "VARCHAR2"}],
     """PROCEDURE PRC_RECORD_DELIVERY_ATTEMPT(p_shipment_id IN NUMBER, p_outcome IN VARCHAR2) IS
BEGIN
  INSERT INTO FULFILLMENT_LOGISTICS.delivery_attempts (shipment_id, attempted_at, outcome)
  VALUES (p_shipment_id, SYSTIMESTAMP, p_outcome);
END PRC_RECORD_DELIVERY_ATTEMPT;""",
     ["IN_PARAM", "INSERT"]),

    ("ORGANIZATION_HR", "PRC_RUN_PAYROLL", "very_complex",
     [{"name": "p_payroll_run_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_RUN_PAYROLL(p_payroll_run_id IN NUMBER) IS
  TYPE t_emp_rec IS RECORD (employee_id NUMBER, gross_pay NUMBER, net_pay NUMBER);
  TYPE t_emp_tab IS TABLE OF t_emp_rec;
  v_emps t_emp_tab := t_emp_tab();
  CURSOR c_emp IS SELECT id, salary FROM ORGANIZATION_HR.employees WHERE termination_date IS NULL;
BEGIN
  FOR r IN c_emp LOOP
    v_emps.EXTEND;
    v_emps(v_emps.COUNT) := t_emp_rec(r.id, NVL(r.salary, 0) / 12, NVL(r.salary, 0) / 12 * 0.75);
  END LOOP;

  FORALL i IN 1 .. v_emps.COUNT
    INSERT INTO ORGANIZATION_HR.payroll_entries (payroll_run_id, employee_id, gross_pay, net_pay)
    VALUES (p_payroll_run_id, v_emps(i).employee_id, v_emps(i).gross_pay, v_emps(i).net_pay);
END PRC_RUN_PAYROLL;""",
     ["IN_PARAM", "RECORD_TYPE", "COLLECTION_TYPE", "EXPLICIT_CURSOR", "CURSOR_FOR_LOOP",
      "COLLECTION_EXTEND", "FORALL", "NVL"]),

    ("ORGANIZATION_HR", "PRC_TRANSFER_EMPLOYEE", "moderate",
     [{"name": "p_employee_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_new_department_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_TRANSFER_EMPLOYEE(p_employee_id IN NUMBER, p_new_department_id IN NUMBER) IS
BEGIN
  UPDATE ORGANIZATION_HR.employees SET department_id = p_new_department_id WHERE id = p_employee_id;
END PRC_TRANSFER_EMPLOYEE;""",
     ["IN_PARAM", "UPDATE"]),

    ("CONTENT_DOCUMENTS", "PRC_ARCHIVE_OLD_DOCUMENTS", "complex",
     [{"name": "p_cutoff_days", "mode": "IN", "type": "NUMBER"},
      {"name": "p_archived_count", "mode": "OUT", "type": "NUMBER"}],
     """PROCEDURE PRC_ARCHIVE_OLD_DOCUMENTS(p_cutoff_days IN NUMBER, p_archived_count OUT NUMBER) IS
BEGIN
  UPDATE CONTENT_DOCUMENTS.documents
     SET mime_type = mime_type
   WHERE created_at < SYSDATE - p_cutoff_days;
  p_archived_count := SQL%ROWCOUNT;
END PRC_ARCHIVE_OLD_DOCUMENTS;""",
     ["IN_PARAM", "OUT_PARAM", "UPDATE", "SQL_ROWCOUNT", "DATE_ARITHMETIC"]),

    ("CONTENT_DOCUMENTS", "PRC_TAG_DOCUMENT", "simple",
     [{"name": "p_document_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_tag_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_TAG_DOCUMENT(p_document_id IN NUMBER, p_tag_id IN NUMBER) IS
BEGIN
  INSERT INTO CONTENT_DOCUMENTS.document_tags (document_id, tag_id) VALUES (p_document_id, p_tag_id);
EXCEPTION
  WHEN DUP_VAL_ON_INDEX THEN
    NULL;
END PRC_TAG_DOCUMENT;""",
     ["IN_PARAM", "INSERT", "DUP_VAL_ON_INDEX"]),

    ("AUDIT_COMPLIANCE", "PRC_RECORD_AUDIT_EVENT", "moderate",
     [{"name": "p_actor_ref", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_action", "mode": "IN", "type": "VARCHAR2"},
      {"name": "p_resource_ref", "mode": "IN", "type": "VARCHAR2"}],
     """PROCEDURE PRC_RECORD_AUDIT_EVENT(p_actor_ref IN VARCHAR2, p_action IN VARCHAR2, p_resource_ref IN VARCHAR2) IS
  PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
  INSERT INTO AUDIT_COMPLIANCE.audit_events (actor_ref, action, resource_ref, occurred_at)
  VALUES (p_actor_ref, p_action, p_resource_ref, SYSTIMESTAMP);
  COMMIT;
END PRC_RECORD_AUDIT_EVENT;""",
     ["IN_PARAM", "PRAGMA_AUTONOMOUS_TRANSACTION", "INSERT", "COMMIT"]),

    ("AUDIT_COMPLIANCE", "PRC_ESCALATE_OBSERVATION", "moderate",
     [{"name": "p_observation_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_ESCALATE_OBSERVATION(p_observation_id IN NUMBER) IS
BEGIN
  UPDATE AUDIT_COMPLIANCE.compliance_observations SET severity = 'CRITICAL' WHERE id = p_observation_id;
END PRC_ESCALATE_OBSERVATION;""",
     ["IN_PARAM", "UPDATE"]),

    ("OPERATIONAL_METRICS", "PRC_RECORD_METRIC_SAMPLE", "simple",
     [{"name": "p_metric_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_value", "mode": "IN", "type": "BINARY_DOUBLE"}],
     """PROCEDURE PRC_RECORD_METRIC_SAMPLE(p_metric_id IN NUMBER, p_value IN BINARY_DOUBLE) IS
BEGIN
  INSERT INTO OPERATIONAL_METRICS.metric_samples (metric_id, sampled_at, value)
  VALUES (p_metric_id, SYSTIMESTAMP, p_value);
END PRC_RECORD_METRIC_SAMPLE;""",
     ["IN_PARAM", "INSERT"]),

    ("INTEGRATION_REGISTRY", "PRC_RETRY_FAILED_DELIVERIES", "complex",
     [{"name": "p_webhook_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_RETRY_FAILED_DELIVERIES(p_webhook_id IN NUMBER) IS
  v_sql VARCHAR2(500);
BEGIN
  v_sql := 'UPDATE INTEGRATION_REGISTRY.webhook_deliveries SET response_code = NULL WHERE webhook_id = :1 AND response_code >= 500';
  EXECUTE IMMEDIATE v_sql USING p_webhook_id;
END PRC_RETRY_FAILED_DELIVERIES;""",
     ["IN_PARAM", "LOCAL_VAR", "DYNAMIC_SQL", "EXECUTE_IMMEDIATE", "BIND_PARAMETER"]),

    ("INTEGRATION_REGISTRY", "PRC_ROTATE_WEBHOOK_SECRET", "simple",
     [{"name": "p_webhook_id", "mode": "IN", "type": "NUMBER"},
      {"name": "p_new_secret_ref", "mode": "IN", "type": "VARCHAR2"}],
     """PROCEDURE PRC_ROTATE_WEBHOOK_SECRET(p_webhook_id IN NUMBER, p_new_secret_ref IN VARCHAR2) IS
BEGIN
  UPDATE INTEGRATION_REGISTRY.webhooks SET secret_ref = p_new_secret_ref WHERE id = p_webhook_id;
END PRC_ROTATE_WEBHOOK_SECRET;""",
     ["IN_PARAM", "UPDATE"]),

    ("COMPATIBILITY_LAB", "PRC_NORMALIZE_NUMERIC_EDGE_CASE", "complex",
     [{"name": "p_id", "mode": "IN", "type": "NUMBER"}],
     """PROCEDURE PRC_NORMALIZE_NUMERIC_EDGE_CASE(p_id IN NUMBER) IS
  r_row COMPATIBILITY_LAB.numeric_edge_cases%ROWTYPE;
BEGIN
  SELECT * INTO r_row FROM COMPATIBILITY_LAB.numeric_edge_cases WHERE id = p_id;
  UPDATE COMPATIBILITY_LAB.numeric_edge_cases
     SET num_high_precision = ROUND(NVL(num_high_precision, 0), 4)
   WHERE id = p_id;
END PRC_NORMALIZE_NUMERIC_EDGE_CASE;""",
     ["IN_PARAM", "ROWTYPE", "SELECT_INTO", "UPDATE", "ROUND", "NVL"]),

    ("COMPATIBILITY_LAB", "PRC_SEED_PORTABILITY_NOTE", "simple",
     [{"name": "p_code", "mode": "IN", "type": "VARCHAR2"}, {"name": "p_description", "mode": "IN", "type": "VARCHAR2"}],
     """PROCEDURE PRC_SEED_PORTABILITY_NOTE(p_code IN VARCHAR2, p_description IN VARCHAR2) IS
BEGIN
  INSERT INTO COMPATIBILITY_LAB.portability_notes (code, description) VALUES (p_code, p_description);
EXCEPTION
  WHEN DUP_VAL_ON_INDEX THEN
    UPDATE COMPATIBILITY_LAB.portability_notes SET description = p_description WHERE code = p_code;
END PRC_SEED_PORTABILITY_NOTE;""",
     ["IN_PARAM", "INSERT", "DUP_VAL_ON_INDEX", "EXCEPTION_HANDLER", "UPDATE"]),

    ("OPERATIONAL_METRICS", "PRC_PURGE_OLD_TELEMETRY", "moderate",
     [{"name": "p_cutoff_days", "mode": "IN", "type": "NUMBER"}, {"name": "p_deleted_count", "mode": "OUT", "type": "NUMBER"}],
     """PROCEDURE PRC_PURGE_OLD_TELEMETRY(p_cutoff_days IN NUMBER, p_deleted_count OUT NUMBER) IS
BEGIN
  DELETE FROM OPERATIONAL_METRICS.telemetry_events WHERE occurred_at < SYSTIMESTAMP - p_cutoff_days;
  p_deleted_count := SQL%ROWCOUNT;
  COMMIT;
END PRC_PURGE_OLD_TELEMETRY;""",
     ["IN_PARAM", "OUT_PARAM", "DELETE", "SQL_ROWCOUNT", "DATE_ARITHMETIC", "COMMIT"]),
]


def build_procedures():
    objs = []
    for schema, name, band, params, sql, constructs in _DEFS:
        objs.append(PLSQLObject(f"PROCEDURE.{schema}.{name}", "PROCEDURE", schema, name, sql, band,
                                 constructs=constructs, dependencies=[], parameters=params))
    return objs


PROCEDURES = build_procedures()
