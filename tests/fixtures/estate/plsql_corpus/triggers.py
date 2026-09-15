"""24+ Oracle triggers covering BEFORE/AFTER INSERT/UPDATE/DELETE, row/statement level,
audit and validation behavior (build-spec §10-§11)."""
from __future__ import annotations

from .model import PLSQLObject

_DEFS = [
    ("IDENTITY_ACCESS_MGMT", "trg_users_biu_audit", "users", "BEFORE", "INSERT OR UPDATE", "ROW", "moderate",
     """BEGIN
  :NEW.updated_at := SYSTIMESTAMP;
  IF :NEW.email IS NULL THEN
    RAISE_APPLICATION_ERROR(-20001, 'email is required');
  END IF;
END;""",
     ["RAISE_APPLICATION_ERROR", "NEW_QUALIFIER"]),
    ("IDENTITY_ACCESS_MGMT", "trg_sessions_ai_log", "sessions", "AFTER", "INSERT", "ROW", "simple",
     """BEGIN
  INSERT INTO IDENTITY_ACCESS_MGMT.authentication_events (user_id, event_type, occurred_at, outcome)
  VALUES (:NEW.user_id, 'SESSION_CREATED', SYSTIMESTAMP, 'SUCCESS');
END;""",
     ["INSERT", "NEW_QUALIFIER"]),
    ("COMMERCE_ORDERS", "trg_orders_bu_status", "orders", "BEFORE", "UPDATE", "ROW", "moderate",
     """BEGIN
  IF :OLD.status = 'CANCELLED' AND :NEW.status != 'CANCELLED' THEN
    RAISE_APPLICATION_ERROR(-20002, 'cannot un-cancel an order');
  END IF;
  INSERT INTO COMMERCE_ORDERS.order_status_history (order_id, status, changed_at)
  VALUES (:NEW.id, :NEW.status, SYSTIMESTAMP);
END;""",
     ["OLD_QUALIFIER", "NEW_QUALIFIER", "RAISE_APPLICATION_ERROR", "INSERT"]),
    ("COMMERCE_ORDERS", "trg_order_lines_bi_total", "order_lines", "BEFORE", "INSERT", "ROW", "simple",
     """BEGIN
  :NEW.line_total := :NEW.quantity * :NEW.unit_price;
END;""",
     ["NEW_QUALIFIER", "COMPUTED_COLUMN"]),
    ("COMMERCE_ORDERS", "trg_payments_ai_notify", "payments", "AFTER", "INSERT", "STATEMENT", "simple",
     """BEGIN
  NULL; -- statement-level hook point for downstream notification pipeline
END;""",
     ["STATEMENT_LEVEL"]),
    ("FINANCIAL_LEDGER", "trg_journals_bu_lock_posted", "journals", "BEFORE", "UPDATE", "ROW", "moderate",
     """BEGIN
  IF :OLD.status = 'POSTED' THEN
    RAISE_APPLICATION_ERROR(-20010, 'posted journals are immutable');
  END IF;
END;""",
     ["OLD_QUALIFIER", "RAISE_APPLICATION_ERROR"]),
    ("FINANCIAL_LEDGER", "trg_postings_ai_balance", "postings", "AFTER", "INSERT", "ROW", "complex",
     """DECLARE
  v_delta NUMBER;
BEGIN
  v_delta := :NEW.debit - :NEW.credit;
  UPDATE FINANCIAL_LEDGER.accounts
     SET balance = balance + v_delta
   WHERE id = :NEW.account_id;
EXCEPTION
  WHEN OTHERS THEN
    RAISE_APPLICATION_ERROR(-20011, 'failed to update account balance: ' || SQLERRM);
END;""",
     ["DECLARE", "UPDATE", "EXCEPTION_HANDLER", "SQLERRM"]),
    ("FINANCIAL_LEDGER", "trg_accounts_bd_guard", "accounts", "BEFORE", "DELETE", "ROW", "moderate",
     """DECLARE
  v_cnt NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_cnt FROM FINANCIAL_LEDGER.postings WHERE account_id = :OLD.id;
  IF v_cnt > 0 THEN
    RAISE_APPLICATION_ERROR(-20012, 'cannot delete account with postings');
  END IF;
END;""",
     ["SELECT_INTO", "OLD_QUALIFIER", "RAISE_APPLICATION_ERROR"]),
    ("CATALOG_PRODUCTS", "trg_products_bu_touch", "products", "BEFORE", "UPDATE", "ROW", "simple",
     """BEGIN
  :NEW.updated_at := SYSTIMESTAMP;
END;""",
     ["NEW_QUALIFIER"]),
    ("CATALOG_PRODUCTS", "trg_categories_bi_selfref", "categories", "BEFORE", "INSERT", "ROW", "moderate",
     """BEGIN
  IF :NEW.parent_category_id = :NEW.id THEN
    RAISE_APPLICATION_ERROR(-20020, 'category cannot be its own parent');
  END IF;
END;""",
     ["NEW_QUALIFIER", "SELF_REFERENCE_CHECK"]),
    ("WAREHOUSE_INVENTORY", "trg_stock_balances_bu_nonneg", "stock_balances", "BEFORE", "UPDATE", "ROW", "moderate",
     """BEGIN
  IF :NEW.quantity_on_hand < 0 THEN
    RAISE_APPLICATION_ERROR(-20030, 'stock quantity cannot go negative');
  END IF;
END;""",
     ["NEW_QUALIFIER", "RAISE_APPLICATION_ERROR"]),
    ("WAREHOUSE_INVENTORY", "trg_movements_ai_apply", "movements", "AFTER", "INSERT", "ROW", "complex",
     """DECLARE
  v_sign NUMBER := CASE WHEN :NEW.movement_type = 'OUTBOUND' THEN -1 ELSE 1 END;
BEGIN
  UPDATE WAREHOUSE_INVENTORY.stock_balances
     SET quantity_on_hand = quantity_on_hand + (v_sign * :NEW.quantity),
         updated_at = SYSTIMESTAMP
   WHERE warehouse_id = :NEW.warehouse_id AND sku_code = :NEW.sku_code;
END;""",
     ["DECLARE", "CASE", "UPDATE", "NEW_QUALIFIER"]),
    ("FULFILLMENT_LOGISTICS", "trg_shipments_bu_ship_ts", "shipments", "BEFORE", "UPDATE", "ROW", "simple",
     """BEGIN
  IF :NEW.status = 'SHIPPED' AND :OLD.status != 'SHIPPED' THEN
    :NEW.shipped_at := SYSTIMESTAMP;
  END IF;
END;""",
     ["NEW_QUALIFIER", "OLD_QUALIFIER", "IF"]),
    ("FULFILLMENT_LOGISTICS", "trg_tracking_events_bi_validate", "tracking_events", "BEFORE", "INSERT", "ROW", "moderate",
     """BEGIN
  IF :NEW.event_code IS NULL THEN
    RAISE_APPLICATION_ERROR(-20040, 'event_code is required');
  END IF;
END;""",
     ["NEW_QUALIFIER", "RAISE_APPLICATION_ERROR"]),
    ("ORGANIZATION_HR", "trg_employees_bu_history", "employees", "BEFORE", "UPDATE", "ROW", "complex",
     """BEGIN
  IF NVL(:OLD.department_id, -1) != NVL(:NEW.department_id, -1) THEN
    INSERT INTO ORGANIZATION_HR.employment_history (employee_id, change_type, changed_at, old_value, new_value)
    VALUES (:NEW.id, 'DEPARTMENT_CHANGE', SYSTIMESTAMP, TO_CHAR(:OLD.department_id), TO_CHAR(:NEW.department_id));
  END IF;
END;""",
     ["NVL", "INSERT", "TO_CHAR", "OLD_QUALIFIER", "NEW_QUALIFIER"]),
    ("ORGANIZATION_HR", "trg_departments_bi_selfref", "departments", "BEFORE", "INSERT", "ROW", "moderate",
     """BEGIN
  IF :NEW.parent_department_id = :NEW.id THEN
    RAISE_APPLICATION_ERROR(-20050, 'department cannot be its own parent');
  END IF;
END;""",
     ["NEW_QUALIFIER", "SELF_REFERENCE_CHECK"]),
    ("CONTENT_DOCUMENTS", "trg_documents_bi_revision", "documents", "AFTER", "INSERT", "ROW", "simple",
     """BEGIN
  INSERT INTO CONTENT_DOCUMENTS.document_revisions (document_id, revision_no, edited_at)
  VALUES (:NEW.id, 1, SYSTIMESTAMP);
END;""",
     ["INSERT", "NEW_QUALIFIER"]),
    ("CONTENT_DOCUMENTS", "trg_document_revisions_bi_seq", "document_revisions", "BEFORE", "INSERT", "ROW", "complex",
     """DECLARE
  v_max NUMBER;
BEGIN
  SELECT NVL(MAX(revision_no), 0) + 1 INTO v_max
    FROM CONTENT_DOCUMENTS.document_revisions
   WHERE document_id = :NEW.document_id;
  :NEW.revision_no := v_max;
END;""",
     ["DECLARE", "SELECT_INTO", "NVL", "NEW_QUALIFIER"]),
    ("AUDIT_COMPLIANCE", "trg_signatures_bi_hash_check", "signatures", "BEFORE", "INSERT", "ROW", "moderate",
     """BEGIN
  IF :NEW.signature_hash IS NULL THEN
    RAISE_APPLICATION_ERROR(-20060, 'signature_hash is required');
  END IF;
END;""",
     ["NEW_QUALIFIER", "RAISE_APPLICATION_ERROR"]),
    ("AUDIT_COMPLIANCE", "trg_change_histories_bi_touch", "change_histories", "BEFORE", "INSERT", "ROW", "simple",
     """BEGIN
  :NEW.changed_at := NVL(:NEW.changed_at, SYSTIMESTAMP);
END;""",
     ["NEW_QUALIFIER", "NVL"]),
    ("OPERATIONAL_METRICS", "trg_metric_samples_bi_range", "metric_samples", "BEFORE", "INSERT", "ROW", "moderate",
     """BEGIN
  IF :NEW.value IS NULL THEN
    RAISE_APPLICATION_ERROR(-20070, 'metric value is required');
  END IF;
END;""",
     ["NEW_QUALIFIER", "RAISE_APPLICATION_ERROR"]),
    ("INTEGRATION_REGISTRY", "trg_webhooks_bu_touch", "webhooks", "BEFORE", "UPDATE", "STATEMENT", "simple",
     """BEGIN
  NULL; -- statement-level placeholder for audit pipeline hook
END;""",
     ["STATEMENT_LEVEL"]),
    ("INTEGRATION_REGISTRY", "trg_webhook_deliveries_ai_alert", "webhook_deliveries", "AFTER", "INSERT", "ROW", "complex",
     """BEGIN
  IF :NEW.response_code IS NOT NULL AND :NEW.response_code >= 500 THEN
    INSERT INTO AUDIT_COMPLIANCE.audit_events (actor_ref, action, resource_ref, occurred_at, detail)
    VALUES ('SYSTEM', 'WEBHOOK_DELIVERY_FAILED', TO_CHAR(:NEW.webhook_id), SYSTIMESTAMP, 'response_code=' || :NEW.response_code);
  END IF;
END;""",
     ["NEW_QUALIFIER", "IF", "INSERT", "CROSS_SCHEMA_INSERT"]),
    ("COMPATIBILITY_LAB", "trg_numeric_edge_cases_biu_check", "numeric_edge_cases", "BEFORE", "INSERT OR UPDATE", "ROW", "moderate",
     """BEGIN
  IF :NEW.num_38 IS NOT NULL AND LENGTH(TRIM(TRANSLATE(:NEW.num_38, '0123456789-', ' '))) IS NOT NULL THEN
    NULL; -- placeholder for precision/scale validation logic
  END IF;
END;""",
     ["NEW_QUALIFIER", "TRANSLATE", "TRIM"]),
    ("COMPATIBILITY_LAB", "trg_lob_edge_cases_bi_default", "lob_edge_cases", "BEFORE", "INSERT", "ROW", "simple",
     """BEGIN
  :NEW.clob_col := NVL(:NEW.clob_col, EMPTY_CLOB());
END;""",
     ["NEW_QUALIFIER", "NVL", "EMPTY_CLOB"]),
    ("COMMERCE_ORDERS", "trg_carts_ad_cleanup", "carts", "AFTER", "DELETE", "ROW", "moderate",
     """BEGIN
  DELETE FROM COMMERCE_ORDERS.cart_items WHERE cart_id = :OLD.cart_id;
END;""",
     ["OLD_QUALIFIER", "DELETE"]),
]


def build_triggers():
    objs = []
    for schema, name, table, timing, event, level, band, body, constructs in _DEFS:
        sql = (f"CREATE OR REPLACE TRIGGER {schema}.{name}\n"
               f"{timing} {event} ON {schema}.{table}\n"
               f"{'FOR EACH ROW' if level == 'ROW' else ''}\n"
               f"{body}").replace("\n\n", "\n")
        objs.append(PLSQLObject(f"TRIGGER.{schema}.{name}", "TRIGGER", schema, name, sql, band,
                                 constructs=constructs + [timing.replace(' ', '_'), event.replace(' ', '_'), level],
                                 dependencies=[f"{schema}.{table}"]))
    return objs


TRIGGERS = build_triggers()
