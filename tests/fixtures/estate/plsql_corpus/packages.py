"""12 package specifications + 12 package bodies (build-spec §10-§11).

Each package groups several related procedures/functions (not trivial
wrappers), and bodies call across schema/package boundaries where natural.
"""
from __future__ import annotations

from .model import PLSQLObject

_PACKAGES = [
    ("IDENTITY_ACCESS_MGMT", "IAM_PKG", "complex",
     """CREATE OR REPLACE PACKAGE IDENTITY_ACCESS_MGMT.IAM_PKG IS
  FUNCTION IS_SESSION_VALID(p_session_id IN CHAR) RETURN NUMBER;
  PROCEDURE REVOKE_ALL_SESSIONS(p_user_id IN NUMBER);
  PROCEDURE GRANT_ROLE(p_user_id IN NUMBER, p_role_id IN NUMBER);
END IAM_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY IDENTITY_ACCESS_MGMT.IAM_PKG IS
  FUNCTION IS_SESSION_VALID(p_session_id IN CHAR) RETURN NUMBER IS
    v_expires TIMESTAMP;
  BEGIN
    SELECT expires_at INTO v_expires FROM IDENTITY_ACCESS_MGMT.sessions WHERE session_id = p_session_id AND revoked = 0;
    RETURN CASE WHEN v_expires > SYSTIMESTAMP THEN 1 ELSE 0 END;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN 0;
  END IS_SESSION_VALID;

  PROCEDURE REVOKE_ALL_SESSIONS(p_user_id IN NUMBER) IS
  BEGIN
    UPDATE IDENTITY_ACCESS_MGMT.sessions SET revoked = 1 WHERE user_id = p_user_id;
  END REVOKE_ALL_SESSIONS;

  PROCEDURE GRANT_ROLE(p_user_id IN NUMBER, p_role_id IN NUMBER) IS
  BEGIN
    INSERT INTO IDENTITY_ACCESS_MGMT.user_roles (user_id, role_id, assigned_at) VALUES (p_user_id, p_role_id, SYSTIMESTAMP);
  EXCEPTION
    WHEN DUP_VAL_ON_INDEX THEN NULL;
  END GRANT_ROLE;
END IAM_PKG;""",
     ["IN_PARAM", "SELECT_INTO", "EXCEPTION_HANDLER", "NO_DATA_FOUND", "UPDATE", "INSERT", "DUP_VAL_ON_INDEX"]),

    ("COMMERCE_ORDERS", "ORDER_MGMT_PKG", "very_complex",
     """CREATE OR REPLACE PACKAGE COMMERCE_ORDERS.ORDER_MGMT_PKG IS
  g_default_currency CONSTANT CHAR(3) := 'USD';
  FUNCTION NORMALIZE_CURRENCY(p_amount IN NUMBER, p_currency IN CHAR) RETURN NUMBER;
  PROCEDURE PROCESS_REFUND(p_payment_id IN NUMBER, p_amount IN NUMBER);
  PROCEDURE RECALC_ORDER_TOTAL(p_order_id IN NUMBER);
END ORDER_MGMT_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY COMMERCE_ORDERS.ORDER_MGMT_PKG IS
  FUNCTION NORMALIZE_CURRENCY(p_amount IN NUMBER, p_currency IN CHAR) RETURN NUMBER IS
  BEGIN
    IF p_currency = g_default_currency THEN
      RETURN p_amount;
    END IF;
    RETURN FINANCIAL_LEDGER.FN_CONVERT_CURRENCY(p_amount, p_currency, g_default_currency, SYSDATE);
  END NORMALIZE_CURRENCY;

  PROCEDURE PROCESS_REFUND(p_payment_id IN NUMBER, p_amount IN NUMBER) IS
  BEGIN
    INSERT INTO COMMERCE_ORDERS.refunds (payment_id, amount, processed_at) VALUES (p_payment_id, p_amount, SYSTIMESTAMP);
    COMMIT;
  END PROCESS_REFUND;

  PROCEDURE RECALC_ORDER_TOTAL(p_order_id IN NUMBER) IS
    v_total NUMBER;
  BEGIN
    v_total := FN_CALCULATE_ORDER_TOTAL(p_order_id);
    UPDATE COMMERCE_ORDERS.orders SET order_total = v_total WHERE id = p_order_id;
  END RECALC_ORDER_TOTAL;
END ORDER_MGMT_PKG;""",
     ["CONSTANT", "IN_PARAM", "IF", "CROSS_SCHEMA_CALL", "INSERT", "COMMIT", "LOCAL_VAR", "CROSS_OBJECT_CALL", "UPDATE"]),

    ("FINANCIAL_LEDGER", "LEDGER_PKG", "very_complex",
     """CREATE OR REPLACE PACKAGE FINANCIAL_LEDGER.LEDGER_PKG IS
  TYPE t_posting_rec IS RECORD (account_id NUMBER, debit NUMBER, credit NUMBER);
  PROCEDURE POST_ENTRY(p_journal_id IN NUMBER, p_entry IN t_posting_rec);
  FUNCTION GET_TRIAL_BALANCE(p_period_id IN NUMBER) RETURN NUMBER;
END LEDGER_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY FINANCIAL_LEDGER.LEDGER_PKG IS
  PROCEDURE POST_ENTRY(p_journal_id IN NUMBER, p_entry IN t_posting_rec) IS
    v_next_line NUMBER;
  BEGIN
    SELECT NVL(MAX(line_no), 0) + 1 INTO v_next_line FROM FINANCIAL_LEDGER.postings WHERE journal_id = p_journal_id;
    INSERT INTO FINANCIAL_LEDGER.postings (journal_id, line_no, account_id, debit, credit)
    VALUES (p_journal_id, v_next_line, p_entry.account_id, p_entry.debit, p_entry.credit);
  END POST_ENTRY;

  FUNCTION GET_TRIAL_BALANCE(p_period_id IN NUMBER) RETURN NUMBER IS
    v_balance NUMBER;
  BEGIN
    SELECT SUM(p.debit - p.credit) INTO v_balance
      FROM FINANCIAL_LEDGER.postings p
      JOIN FINANCIAL_LEDGER.journals j ON j.id = p.journal_id
     WHERE j.fiscal_period_id = p_period_id;
    RETURN NVL(v_balance, 0);
  END GET_TRIAL_BALANCE;
END LEDGER_PKG;""",
     ["RECORD_TYPE", "IN_PARAM", "SELECT_INTO", "NVL", "INSERT", "JOIN", "RETURN"]),

    ("CATALOG_PRODUCTS", "CATALOG_PKG", "moderate",
     """CREATE OR REPLACE PACKAGE CATALOG_PRODUCTS.CATALOG_PKG IS
  FUNCTION GET_EFFECTIVE_PRICE(p_price_book_id IN NUMBER, p_sku_code IN VARCHAR2) RETURN NUMBER;
  PROCEDURE DEACTIVATE_SKU(p_sku_code IN VARCHAR2);
END CATALOG_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY CATALOG_PRODUCTS.CATALOG_PKG IS
  FUNCTION GET_EFFECTIVE_PRICE(p_price_book_id IN NUMBER, p_sku_code IN VARCHAR2) RETURN NUMBER IS
    v_price NUMBER;
  BEGIN
    SELECT price INTO v_price FROM CATALOG_PRODUCTS.price_book_entries
     WHERE price_book_id = p_price_book_id AND sku_code = p_sku_code;
    RETURN v_price;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN NULL;
  END GET_EFFECTIVE_PRICE;

  PROCEDURE DEACTIVATE_SKU(p_sku_code IN VARCHAR2) IS
  BEGIN
    UPDATE CATALOG_PRODUCTS.products SET is_active = 0
     WHERE id = (SELECT product_id FROM CATALOG_PRODUCTS.skus WHERE sku_code = p_sku_code);
  END DEACTIVATE_SKU;
END CATALOG_PKG;""",
     ["IN_PARAM", "SELECT_INTO", "NO_DATA_FOUND", "EXCEPTION_HANDLER", "UPDATE", "SUBQUERY"]),

    ("WAREHOUSE_INVENTORY", "INVENTORY_PKG", "complex",
     """CREATE OR REPLACE PACKAGE WAREHOUSE_INVENTORY.INVENTORY_PKG IS
  PROCEDURE TRANSFER_STOCK(p_sku_code IN VARCHAR2, p_from_wh IN NUMBER, p_to_wh IN NUMBER, p_qty IN NUMBER);
  FUNCTION TOTAL_ON_HAND(p_sku_code IN VARCHAR2) RETURN NUMBER;
END INVENTORY_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY WAREHOUSE_INVENTORY.INVENTORY_PKG IS
  PROCEDURE TRANSFER_STOCK(p_sku_code IN VARCHAR2, p_from_wh IN NUMBER, p_to_wh IN NUMBER, p_qty IN NUMBER) IS
  BEGIN
    UPDATE WAREHOUSE_INVENTORY.stock_balances SET quantity_on_hand = quantity_on_hand - p_qty
     WHERE warehouse_id = p_from_wh AND sku_code = p_sku_code;
    UPDATE WAREHOUSE_INVENTORY.stock_balances SET quantity_on_hand = quantity_on_hand + p_qty
     WHERE warehouse_id = p_to_wh AND sku_code = p_sku_code;
    INSERT INTO WAREHOUSE_INVENTORY.movements (sku_code, warehouse_id, movement_type, quantity, occurred_at)
    VALUES (p_sku_code, p_from_wh, 'TRANSFER_OUT', p_qty, SYSTIMESTAMP);
    INSERT INTO WAREHOUSE_INVENTORY.movements (sku_code, warehouse_id, movement_type, quantity, occurred_at)
    VALUES (p_sku_code, p_to_wh, 'TRANSFER_IN', p_qty, SYSTIMESTAMP);
    COMMIT;
  END TRANSFER_STOCK;

  FUNCTION TOTAL_ON_HAND(p_sku_code IN VARCHAR2) RETURN NUMBER IS
    v_total NUMBER;
  BEGIN
    SELECT NVL(SUM(quantity_on_hand), 0) INTO v_total FROM WAREHOUSE_INVENTORY.stock_balances WHERE sku_code = p_sku_code;
    RETURN v_total;
  END TOTAL_ON_HAND;
END INVENTORY_PKG;""",
     ["IN_PARAM", "UPDATE", "INSERT", "COMMIT", "SELECT_INTO", "NVL", "RETURN"]),

    ("FULFILLMENT_LOGISTICS", "LOGISTICS_PKG", "moderate",
     """CREATE OR REPLACE PACKAGE FULFILLMENT_LOGISTICS.LOGISTICS_PKG IS
  PROCEDURE RECORD_TRACKING_EVENT(p_shipment_id IN NUMBER, p_event_code IN VARCHAR2, p_location IN VARCHAR2);
  FUNCTION LATEST_STATUS(p_shipment_id IN NUMBER) RETURN VARCHAR2;
END LOGISTICS_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY FULFILLMENT_LOGISTICS.LOGISTICS_PKG IS
  PROCEDURE RECORD_TRACKING_EVENT(p_shipment_id IN NUMBER, p_event_code IN VARCHAR2, p_location IN VARCHAR2) IS
  BEGIN
    INSERT INTO FULFILLMENT_LOGISTICS.tracking_events (shipment_id, event_code, occurred_at, location)
    VALUES (p_shipment_id, p_event_code, SYSTIMESTAMP, p_location);
  END RECORD_TRACKING_EVENT;

  FUNCTION LATEST_STATUS(p_shipment_id IN NUMBER) RETURN VARCHAR2 IS
    v_status VARCHAR2(16);
  BEGIN
    SELECT status INTO v_status FROM FULFILLMENT_LOGISTICS.shipments WHERE id = p_shipment_id;
    RETURN v_status;
  END LATEST_STATUS;
END LOGISTICS_PKG;""",
     ["IN_PARAM", "INSERT", "SELECT_INTO", "RETURN"]),

    ("ORGANIZATION_HR", "HR_PKG", "complex",
     """CREATE OR REPLACE PACKAGE ORGANIZATION_HR.HR_PKG IS
  FUNCTION IS_ACTIVE_EMPLOYEE(p_employee_id IN NUMBER) RETURN NUMBER;
  PROCEDURE TERMINATE_EMPLOYEE(p_employee_id IN NUMBER, p_termination_date IN DATE);
END HR_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY ORGANIZATION_HR.HR_PKG IS
  FUNCTION IS_ACTIVE_EMPLOYEE(p_employee_id IN NUMBER) RETURN NUMBER IS
    v_term DATE;
  BEGIN
    SELECT termination_date INTO v_term FROM ORGANIZATION_HR.employees WHERE id = p_employee_id;
    RETURN CASE WHEN v_term IS NULL THEN 1 ELSE 0 END;
  END IS_ACTIVE_EMPLOYEE;

  PROCEDURE TERMINATE_EMPLOYEE(p_employee_id IN NUMBER, p_termination_date IN DATE) IS
  BEGIN
    UPDATE ORGANIZATION_HR.employees SET termination_date = p_termination_date WHERE id = p_employee_id;
    INSERT INTO ORGANIZATION_HR.employment_history (employee_id, change_type, changed_at, new_value)
    VALUES (p_employee_id, 'TERMINATION', SYSTIMESTAMP, TO_CHAR(p_termination_date));
    COMMIT;
  END TERMINATE_EMPLOYEE;
END HR_PKG;""",
     ["IN_PARAM", "SELECT_INTO", "CASE", "UPDATE", "INSERT", "TO_CHAR", "COMMIT"]),

    ("CONTENT_DOCUMENTS", "DOCUMENT_PKG", "moderate",
     """CREATE OR REPLACE PACKAGE CONTENT_DOCUMENTS.DOCUMENT_PKG IS
  PROCEDURE CREATE_REVISION(p_document_id IN NUMBER, p_editor_ref IN VARCHAR2);
  FUNCTION REVISION_COUNT(p_document_id IN NUMBER) RETURN NUMBER;
END DOCUMENT_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY CONTENT_DOCUMENTS.DOCUMENT_PKG IS
  PROCEDURE CREATE_REVISION(p_document_id IN NUMBER, p_editor_ref IN VARCHAR2) IS
    v_next NUMBER;
  BEGIN
    v_next := FN_LATEST_REVISION_NO(p_document_id) + 1;
    INSERT INTO CONTENT_DOCUMENTS.document_revisions (document_id, revision_no, edited_at, editor_ref)
    VALUES (p_document_id, v_next, SYSTIMESTAMP, p_editor_ref);
  END CREATE_REVISION;

  FUNCTION REVISION_COUNT(p_document_id IN NUMBER) RETURN NUMBER IS
    v_cnt NUMBER;
  BEGIN
    SELECT COUNT(*) INTO v_cnt FROM CONTENT_DOCUMENTS.document_revisions WHERE document_id = p_document_id;
    RETURN v_cnt;
  END REVISION_COUNT;
END DOCUMENT_PKG;""",
     ["IN_PARAM", "CROSS_OBJECT_CALL", "INSERT", "SELECT_INTO", "RETURN"]),

    ("AUDIT_COMPLIANCE", "AUDIT_PKG", "complex",
     """CREATE OR REPLACE PACKAGE AUDIT_COMPLIANCE.AUDIT_PKG IS
  PROCEDURE LOG_CHANGE(p_entity_ref IN VARCHAR2, p_changed_by IN VARCHAR2, p_before IN VARCHAR2, p_after IN VARCHAR2);
  FUNCTION FRAMEWORK_OBSERVATION_COUNT(p_framework_id IN NUMBER) RETURN NUMBER;
END AUDIT_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY AUDIT_COMPLIANCE.AUDIT_PKG IS
  PROCEDURE LOG_CHANGE(p_entity_ref IN VARCHAR2, p_changed_by IN VARCHAR2, p_before IN VARCHAR2, p_after IN VARCHAR2) IS
    PRAGMA AUTONOMOUS_TRANSACTION;
  BEGIN
    INSERT INTO AUDIT_COMPLIANCE.change_histories (entity_ref, changed_by, changed_at, before_json, after_json)
    VALUES (p_entity_ref, p_changed_by, SYSTIMESTAMP, p_before, p_after);
    COMMIT;
  END LOG_CHANGE;

  FUNCTION FRAMEWORK_OBSERVATION_COUNT(p_framework_id IN NUMBER) RETURN NUMBER IS
    v_cnt NUMBER;
  BEGIN
    SELECT COUNT(*) INTO v_cnt FROM AUDIT_COMPLIANCE.compliance_observations WHERE framework_id = p_framework_id;
    RETURN v_cnt;
  END FRAMEWORK_OBSERVATION_COUNT;
END AUDIT_PKG;""",
     ["IN_PARAM", "PRAGMA_AUTONOMOUS_TRANSACTION", "INSERT", "COMMIT", "SELECT_INTO", "RETURN"]),

    ("OPERATIONAL_METRICS", "METRICS_PKG", "moderate",
     """CREATE OR REPLACE PACKAGE OPERATIONAL_METRICS.METRICS_PKG IS
  PROCEDURE RECORD_SAMPLE(p_metric_code IN VARCHAR2, p_value IN BINARY_DOUBLE);
  FUNCTION LATEST_VALUE(p_metric_code IN VARCHAR2) RETURN BINARY_DOUBLE;
END METRICS_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY OPERATIONAL_METRICS.METRICS_PKG IS
  PROCEDURE RECORD_SAMPLE(p_metric_code IN VARCHAR2, p_value IN BINARY_DOUBLE) IS
    v_metric_id NUMBER;
  BEGIN
    SELECT id INTO v_metric_id FROM OPERATIONAL_METRICS.metrics_definitions WHERE code = p_metric_code;
    INSERT INTO OPERATIONAL_METRICS.metric_samples (metric_id, sampled_at, value) VALUES (v_metric_id, SYSTIMESTAMP, p_value);
  END RECORD_SAMPLE;

  FUNCTION LATEST_VALUE(p_metric_code IN VARCHAR2) RETURN BINARY_DOUBLE IS
    v_value BINARY_DOUBLE;
  BEGIN
    SELECT value INTO v_value FROM OPERATIONAL_METRICS.metric_samples ms
      JOIN OPERATIONAL_METRICS.metrics_definitions md ON md.id = ms.metric_id
     WHERE md.code = p_metric_code
     ORDER BY sampled_at DESC
     FETCH FIRST 1 ROW ONLY;
    RETURN v_value;
  END LATEST_VALUE;
END METRICS_PKG;""",
     ["IN_PARAM", "SELECT_INTO", "INSERT", "JOIN", "FETCH_FIRST", "RETURN"]),

    ("INTEGRATION_REGISTRY", "INTEGRATION_PKG", "complex",
     """CREATE OR REPLACE PACKAGE INTEGRATION_REGISTRY.INTEGRATION_PKG IS
  PROCEDURE DELIVER_WEBHOOK(p_webhook_id IN NUMBER, p_payload IN VARCHAR2);
  FUNCTION FAILURE_COUNT_LAST_HOUR(p_webhook_id IN NUMBER) RETURN NUMBER;
END INTEGRATION_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY INTEGRATION_REGISTRY.INTEGRATION_PKG IS
  PROCEDURE DELIVER_WEBHOOK(p_webhook_id IN NUMBER, p_payload IN VARCHAR2) IS
  BEGIN
    INSERT INTO INTEGRATION_REGISTRY.webhook_deliveries (webhook_id, delivered_at, payload)
    VALUES (p_webhook_id, SYSTIMESTAMP, p_payload);
  END DELIVER_WEBHOOK;

  FUNCTION FAILURE_COUNT_LAST_HOUR(p_webhook_id IN NUMBER) RETURN NUMBER IS
    v_cnt NUMBER;
  BEGIN
    SELECT COUNT(*) INTO v_cnt FROM INTEGRATION_REGISTRY.webhook_deliveries
     WHERE webhook_id = p_webhook_id AND response_code >= 500 AND delivered_at > SYSTIMESTAMP - INTERVAL '1' HOUR;
    RETURN v_cnt;
  END FAILURE_COUNT_LAST_HOUR;
END INTEGRATION_PKG;""",
     ["IN_PARAM", "INSERT", "SELECT_INTO", "INTERVAL_LITERAL", "RETURN"]),

    ("COMPATIBILITY_LAB", "COMPAT_UTIL_PKG", "moderate",
     """CREATE OR REPLACE PACKAGE COMPATIBILITY_LAB.COMPAT_UTIL_PKG IS
  FUNCTION SAFE_DIVIDE(p_num IN NUMBER, p_den IN NUMBER) RETURN NUMBER;
  FUNCTION NORMALIZE_UNICODE(p_text IN NVARCHAR2) RETURN NVARCHAR2;
END COMPAT_UTIL_PKG;""",
     """CREATE OR REPLACE PACKAGE BODY COMPATIBILITY_LAB.COMPAT_UTIL_PKG IS
  FUNCTION SAFE_DIVIDE(p_num IN NUMBER, p_den IN NUMBER) RETURN NUMBER IS
  BEGIN
    RETURN CASE WHEN p_den = 0 THEN NULL ELSE p_num / p_den END;
  END SAFE_DIVIDE;

  FUNCTION NORMALIZE_UNICODE(p_text IN NVARCHAR2) RETURN NVARCHAR2 IS
  BEGIN
    RETURN TRIM(p_text);
  END NORMALIZE_UNICODE;
END COMPAT_UTIL_PKG;""",
     ["IN_PARAM", "CASE", "TRIM", "RETURN"]),
]


def build_packages():
    objs = []
    for schema, name, band, spec_sql, body_sql, constructs in _PACKAGES:
        objs.append(PLSQLObject(f"PACKAGE_SPEC.{schema}.{name}", "PACKAGE_SPEC", schema, name, spec_sql, band,
                                 constructs=["PACKAGE_SPEC"], dependencies=[]))
        objs.append(PLSQLObject(f"PACKAGE_BODY.{schema}.{name}", "PACKAGE_BODY", schema, name, body_sql, band,
                                 constructs=constructs + ["PACKAGE_BODY"], dependencies=[f"PACKAGE_SPEC.{schema}.{name}"]))
    return objs


PACKAGES = build_packages()
