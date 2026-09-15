"""The 12-schema, ~216-table declarative estate definition.

Row-count arithmetic is done at import time via `distribute()` (largest
remainder method) so that summing every TableSpec.row_count reproduces the
exact per-schema targets from build-spec section 4, which sum to exactly
1,000,000. This is asserted at the bottom of this module and re-verified
independently later by the source manifest (manifests/source_manifest.py)
against the physically built database -- this module is a *declaration*,
not the proof.
"""
from __future__ import annotations

from .schema_spec import (
    ColType, PKStyle, TableKind, ColumnSpec, ForeignKeySpec, TableSpec,
    col, surrogate_id, uuid_like, audit_columns, money_column, distribute,
)

SCHEMA_TARGETS = {
    "IDENTITY_ACCESS_MGMT": 140_000,
    "COMMERCE_ORDERS": 200_000,
    "FINANCIAL_LEDGER": 130_000,
    "CATALOG_PRODUCTS": 70_000,
    "WAREHOUSE_INVENTORY": 90_000,
    "FULFILLMENT_LOGISTICS": 80_000,
    "ORGANIZATION_HR": 40_000,
    "CONTENT_DOCUMENTS": 50_000,
    "AUDIT_COMPLIANCE": 90_000,
    "OPERATIONAL_METRICS": 50_000,
    "INTEGRATION_REGISTRY": 30_000,
    "COMPATIBILITY_LAB": 30_000,
}
assert sum(SCHEMA_TARGETS.values()) == 1_000_000, "schema targets must reconcile to exactly 1,000,000"

SCHEMAS = list(SCHEMA_TARGETS.keys())


# ---------------------------------------------------------------- helpers --

def lookup_table(schema, name, row_count, code_len=24, extra_cols=None, empty=False):
    cols = [
        surrogate_id(),
        col("code", ColType.VARCHAR2, length=code_len, nullable=False),
        col("description", ColType.VARCHAR2, length=200, nullable=True),
        col("is_active", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="1"),
        col("sort_order", ColType.INTEGER, nullable=True),
    ]
    if extra_cols:
        cols += extra_cols
    return TableSpec(
        schema=schema, name=name, columns=cols, primary_key=("id",),
        pk_style=PKStyle.SURROGATE, unique_constraints=[("code",)],
        row_count=0 if empty else row_count,
        kind=TableKind.EMPTY if empty else TableKind.POPULATED,
    )


def fk(columns, ref_table, ref_columns, self_ref=False, cross_schema=False):
    if isinstance(columns, str):
        columns = (columns,)
    if isinstance(ref_columns, str):
        ref_columns = (ref_columns,)
    return ForeignKeySpec(columns=tuple(columns), ref_table=ref_table,
                           ref_columns=tuple(ref_columns), self_referencing=self_ref,
                           cross_schema=cross_schema)


def apply_weighted_rows(specs_and_weights, target_total, fixed_total):
    """specs_and_weights: list of (TableSpec, weight). Mutates row_count in place."""
    remaining = target_total - fixed_total
    assert remaining >= 0, f"fixed rows {fixed_total} exceed target {target_total}"
    weights = [w for _, w in specs_and_weights]
    counts = distribute(remaining, weights)
    for (spec, _), n in zip(specs_and_weights, counts):
        spec.row_count = n


# =========================================================== 1. IDENTITY_ACCESS_MGMT

def _iam_tables():
    S = "IDENTITY_ACCESS_MGMT"
    target = SCHEMA_TARGETS[S]

    tenants = TableSpec(S, "tenants", [
        surrogate_id(), col("tenant_code", ColType.VARCHAR2, length=32, nullable=False),
        col("legal_name", ColType.NVARCHAR2, length=200, nullable=False, unicode_profile="mixed"),
        col("region", ColType.VARCHAR2, length=8, nullable=False),
        col("is_active", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="1"),
        *audit_columns(),
    ], primary_key=("id",), pk_style=PKStyle.SURROGATE, unique_constraints=[("tenant_code",)], row_count=500)

    roles = lookup_table(S, "roles", 150, extra_cols=[col("is_system_role", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="0")])
    permissions = lookup_table(S, "permissions", 400)
    identity_providers = lookup_table(S, "identity_providers", 40)

    role_permissions = TableSpec(S, "role_permissions", [
        col("role_id", ColType.NUMBER_38, nullable=False),
        col("permission_id", ColType.NUMBER_38, nullable=False),
        col("granted_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("role_id", "permission_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("role_id", f"{S}.roles", "id"), fk("permission_id", f"{S}.permissions", "id")],
       row_count=3000)

    service_principals = TableSpec(S, "service_principals", [
        uuid_like("principal_id"), col("tenant_id", ColType.NUMBER_38, nullable=False),
        col("display_name", ColType.VARCHAR2, length=120, nullable=False),
        col("secret_ref", ColType.VARCHAR2, length=200, nullable=False),
        col("is_active", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="1"),
        *audit_columns(),
    ], primary_key=("principal_id",), pk_style=PKStyle.UUID_LIKE,
       foreign_keys=[fk("tenant_id", f"{S}.tenants", "id")], row_count=1200)

    access_policies = TableSpec(S, "access_policies", [
        surrogate_id(), col("policy_name", ColType.VARCHAR2, length=120, nullable=False),
        col("policy_document", ColType.JSON, nullable=False),
        col("version", ColType.INTEGER, nullable=False, default="1"),
        *audit_columns(),
    ], primary_key=("id",), pk_style=PKStyle.SURROGATE, row_count=900)

    users = TableSpec(S, "users", [
        surrogate_id(), col("tenant_id", ColType.NUMBER_38, nullable=False),
        col("username", ColType.VARCHAR2, length=64, nullable=False),
        col("email", ColType.VARCHAR2, length=254, nullable=False),
        col("display_name", ColType.NVARCHAR2, length=150, nullable=True, unicode_profile="mixed"),
        col("locale", ColType.VARCHAR2, length=10, nullable=True),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'ACTIVE'"),
        col("failed_login_count", ColType.INTEGER, nullable=False, default="0"),
        col("last_login_at", ColType.TIMESTAMP_TZ, nullable=True),
        col("mfa_enabled", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="0"),
        *audit_columns(),
    ], primary_key=("id",), pk_style=PKStyle.SURROGATE,
       foreign_keys=[fk("tenant_id", f"{S}.tenants", "id")],
       unique_constraints=[("tenant_id", "email")])

    user_roles = TableSpec(S, "user_roles", [
        col("user_id", ColType.NUMBER_38, nullable=False),
        col("role_id", ColType.NUMBER_38, nullable=False),
        col("assigned_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("user_id", "role_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("user_id", f"{S}.users", "id"), fk("role_id", f"{S}.roles", "id")])

    access_policy_grants = TableSpec(S, "access_policy_grants", [
        col("policy_id", ColType.NUMBER_38, nullable=False),
        col("user_id", ColType.NUMBER_38, nullable=False),
        col("granted_at", ColType.TIMESTAMP, nullable=False),
        col("expires_at", ColType.TIMESTAMP, nullable=True),
    ], primary_key=("policy_id", "user_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("policy_id", f"{S}.access_policies", "id"), fk("user_id", f"{S}.users", "id")])

    user_identities = TableSpec(S, "user_identities", [
        col("provider_id", ColType.NUMBER_38, nullable=False),
        col("external_id", ColType.VARCHAR2, length=200, nullable=False),
        col("user_id", ColType.NUMBER_38, nullable=False),
        col("linked_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("provider_id", "external_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("provider_id", f"{S}.identity_providers", "id"), fk("user_id", f"{S}.users", "id")])

    sessions = TableSpec(S, "sessions", [
        uuid_like("session_id"), col("user_id", ColType.NUMBER_38, nullable=False),
        col("issued_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("expires_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("ip_address", ColType.VARCHAR2, length=45, nullable=True),
        col("user_agent", ColType.VARCHAR2, length=300, nullable=True),
        col("revoked", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="0"),
    ], primary_key=("session_id",), pk_style=PKStyle.UUID_LIKE,
       foreign_keys=[fk("user_id", f"{S}.users", "id")])

    authentication_events = TableSpec(S, "authentication_events", [
        col("user_id", ColType.NUMBER_38, nullable=True),
        col("event_type", ColType.VARCHAR2, length=32, nullable=False),
        col("occurred_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("source_ip", ColType.VARCHAR2, length=45, nullable=True),
        col("outcome", ColType.VARCHAR2, length=16, nullable=False),
        col("detail", ColType.CLOB, nullable=True, lob_band="tiny"),
    ], primary_key=None, pk_style=PKStyle.NONE,
       foreign_keys=[fk("user_id", f"{S}.users", "id")])

    password_reset_events = TableSpec(S, "password_reset_events", [
        surrogate_id(), col("user_id", ColType.NUMBER_38, nullable=False),
        col("requested_at", ColType.TIMESTAMP, nullable=False),
        col("completed_at", ColType.TIMESTAMP, nullable=True),
        col("reset_token_ref", ColType.VARCHAR2, length=128, nullable=False),
    ], primary_key=("id",), pk_style=PKStyle.SURROGATE, foreign_keys=[fk("user_id", f"{S}.users", "id")])

    mfa_devices = TableSpec(S, "mfa_devices", [
        surrogate_id(), col("user_id", ColType.NUMBER_38, nullable=False),
        col("device_type", ColType.VARCHAR2, length=24, nullable=False),
        col("registered_at", ColType.TIMESTAMP, nullable=False),
        col("last_used_at", ColType.TIMESTAMP, nullable=True),
    ], primary_key=("id",), pk_style=PKStyle.SURROGATE, foreign_keys=[fk("user_id", f"{S}.users", "id")])

    api_keys = TableSpec(S, "api_keys", [
        col("key_id", ColType.CHAR, length=36, nullable=False),
        col("principal_id", ColType.CHAR, length=36, nullable=False),
        col("key_hash", ColType.RAW, length=32, nullable=False),
        col("created_at", ColType.TIMESTAMP, nullable=False),
        col("revoked_at", ColType.TIMESTAMP, nullable=True),
    ], primary_key=("key_id",), pk_style=PKStyle.UUID_LIKE,
       foreign_keys=[fk("principal_id", f"{S}.service_principals", "principal_id")])

    permission_scopes = lookup_table(S, "permission_scopes", 60)
    session_types = lookup_table(S, "session_types", 10)
    risk_levels = lookup_table(S, "risk_levels", 8)
    password_policies = lookup_table(S, "password_policies", 15)
    notification_preferences = TableSpec(S, "notification_preferences", [
        col("user_id", ColType.NUMBER_38, nullable=False),
        col("channel", ColType.VARCHAR2, length=16, nullable=False),
        col("enabled", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="1"),
    ], primary_key=("user_id", "channel"), pk_style=PKStyle.COMPOSITE, foreign_keys=[fk("user_id", f"{S}.users", "id")])
    tenant_settings = TableSpec(S, "tenant_settings", [
        col("tenant_id", ColType.NUMBER_38, nullable=False),
        col("setting_key", ColType.VARCHAR2, length=64, nullable=False),
        col("setting_value", ColType.VARCHAR2, length=500, nullable=True),
    ], primary_key=("tenant_id", "setting_key"), pk_style=PKStyle.COMPOSITE, foreign_keys=[fk("tenant_id", f"{S}.tenants", "id")])

    deprecated_role_templates = lookup_table(S, "deprecated_role_templates", 0, empty=True)
    legacy_permission_migrations = lookup_table(S, "legacy_permission_migrations", 0, empty=True)

    login_methods = lookup_table(S, "login_methods", 15)
    tenant_regions = lookup_table(S, "tenant_regions", 25)
    device_types = lookup_table(S, "device_types", 20)
    consent_types = lookup_table(S, "consent_types", 12)

    weighted = [
        (users, 40), (user_roles, 18), (access_policy_grants, 8), (user_identities, 6),
        (sessions, 22), (authentication_events, 22), (password_reset_events, 3),
        (mfa_devices, 4), (api_keys, 3), (notification_preferences, 10), (tenant_settings, 2),
    ]
    fixed_total = (tenants.row_count + roles.row_count + permissions.row_count + identity_providers.row_count
                   + role_permissions.row_count + service_principals.row_count + access_policies.row_count
                   + permission_scopes.row_count + session_types.row_count + risk_levels.row_count
                   + password_policies.row_count + login_methods.row_count + tenant_regions.row_count
                   + device_types.row_count + consent_types.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        tenants, roles, permissions, identity_providers, role_permissions, service_principals,
        access_policies, users, user_roles, access_policy_grants, user_identities, sessions,
        authentication_events, password_reset_events, mfa_devices, api_keys, permission_scopes,
        session_types, risk_levels, password_policies, notification_preferences, tenant_settings,
        login_methods, tenant_regions, device_types, consent_types,
        deprecated_role_templates, legacy_permission_migrations,
    ]


# =========================================================== 2. COMMERCE_ORDERS

def _commerce_tables():
    S = "COMMERCE_ORDERS"
    target = SCHEMA_TARGETS[S]

    customers = TableSpec(S, "customers", [
        surrogate_id(), col("customer_code", ColType.VARCHAR2, length=24, nullable=False),
        col("full_name", ColType.NVARCHAR2, length=200, nullable=False, unicode_profile="mixed"),
        col("email", ColType.VARCHAR2, length=254, nullable=True),
        col("loyalty_tier", ColType.VARCHAR2, length=16, nullable=True),
        col("lifetime_value", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False, default="0"),
        *audit_columns(),
    ], primary_key=("id",), unique_constraints=[("customer_code",)])

    carts = TableSpec(S, "carts", [
        uuid_like("cart_id"), col("customer_id", ColType.NUMBER_38, nullable=True),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'OPEN'"),
        col("created_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("cart_id",), pk_style=PKStyle.UUID_LIKE, foreign_keys=[fk("customer_id", f"{S}.customers", "id")])

    cart_items = TableSpec(S, "cart_items", [
        col("cart_id", ColType.CHAR, length=36, nullable=False),
        col("line_no", ColType.INTEGER, nullable=False),
        col("product_ref", ColType.VARCHAR2, length=40, nullable=False),
        col("quantity", ColType.INTEGER, nullable=False),
        col("unit_price", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
    ], primary_key=("cart_id", "line_no"), pk_style=PKStyle.COMPOSITE, foreign_keys=[fk("cart_id", f"{S}.carts", "cart_id")])

    discounts = lookup_table(S, "discounts", 300, extra_cols=[col("percent_off", ColType.NUMBER_P_S, precision=5, scale=2, nullable=True)])

    quotes = TableSpec(S, "quotes", [
        surrogate_id(), col("customer_id", ColType.NUMBER_38, nullable=False),
        col("status", ColType.VARCHAR2, length=16, nullable=False),
        col("valid_until", ColType.DATE, nullable=True),
        *audit_columns(),
    ], primary_key=("id",), foreign_keys=[fk("customer_id", f"{S}.customers", "id")])

    quote_lines = TableSpec(S, "quote_lines", [
        surrogate_id(), col("quote_id", ColType.NUMBER_38, nullable=False),
        col("product_ref", ColType.VARCHAR2, length=40, nullable=False),
        col("quantity", ColType.INTEGER, nullable=False),
        col("unit_price", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("quote_id", f"{S}.quotes", "id")])

    orders = TableSpec(S, "orders", [
        surrogate_id(), col("order_number", ColType.VARCHAR2, length=32, nullable=False),
        col("customer_id", ColType.NUMBER_38, nullable=False),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'PLACED'"),
        col("order_total", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
        col("currency", ColType.CHAR, length=3, nullable=False, default="'USD'"),
        col("placed_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("notes", ColType.NVARCHAR2, length=1000, nullable=True, unicode_profile="mixed"),
        *audit_columns(),
    ], primary_key=("id",), unique_constraints=[("order_number",)], foreign_keys=[fk("customer_id", f"{S}.customers", "id")])

    order_lines = TableSpec(S, "order_lines", [
        surrogate_id(), col("order_id", ColType.NUMBER_38, nullable=False),
        col("line_no", ColType.INTEGER, nullable=False),
        col("product_ref", ColType.VARCHAR2, length=40, nullable=False),
        col("quantity", ColType.INTEGER, nullable=False),
        col("unit_price", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
        col("line_total", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
    ], primary_key=("id",), unique_constraints=[("order_id", "line_no")], foreign_keys=[fk("order_id", f"{S}.orders", "id")])

    order_discounts = TableSpec(S, "order_discounts", [
        col("order_id", ColType.NUMBER_38, nullable=False),
        col("discount_id", ColType.NUMBER_38, nullable=False),
        col("applied_amount", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
    ], primary_key=("order_id", "discount_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("order_id", f"{S}.orders", "id"), fk("discount_id", f"{S}.discounts", "id")])

    payments = TableSpec(S, "payments", [
        surrogate_id(), col("order_id", ColType.NUMBER_38, nullable=False),
        col("amount", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
        col("method", ColType.VARCHAR2, length=24, nullable=False),
        col("status", ColType.VARCHAR2, length=16, nullable=False),
        col("processed_at", ColType.TIMESTAMP_TZ, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("order_id", f"{S}.orders", "id")])

    refunds = TableSpec(S, "refunds", [
        surrogate_id(), col("payment_id", ColType.NUMBER_38, nullable=False),
        col("amount", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
        col("reason", ColType.NVARCHAR2, length=500, nullable=True, unicode_profile="mixed"),
        col("processed_at", ColType.TIMESTAMP_TZ, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("payment_id", f"{S}.payments", "id")])

    checkout_events = TableSpec(S, "checkout_events", [
        col("cart_id", ColType.CHAR, length=36, nullable=True),
        col("event_type", ColType.VARCHAR2, length=32, nullable=False),
        col("occurred_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("payload", ColType.JSON, nullable=True),
    ], primary_key=None, pk_style=PKStyle.NONE, foreign_keys=[fk("cart_id", f"{S}.carts", "cart_id")])

    shipping_addresses = TableSpec(S, "shipping_addresses", [
        surrogate_id(), col("order_id", ColType.NUMBER_38, nullable=False),
        col("line1", ColType.NVARCHAR2, length=200, nullable=False, unicode_profile="mixed"),
        col("city", ColType.NVARCHAR2, length=100, nullable=False, unicode_profile="mixed"),
        col("postal_code", ColType.VARCHAR2, length=20, nullable=True),
        col("country", ColType.CHAR, length=2, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("order_id", f"{S}.orders", "id")])

    billing_addresses = TableSpec(S, "billing_addresses", [
        surrogate_id(), col("order_id", ColType.NUMBER_38, nullable=False),
        col("line1", ColType.NVARCHAR2, length=200, nullable=False, unicode_profile="mixed"),
        col("city", ColType.NVARCHAR2, length=100, nullable=False, unicode_profile="mixed"),
        col("postal_code", ColType.VARCHAR2, length=20, nullable=True),
        col("country", ColType.CHAR, length=2, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("order_id", f"{S}.orders", "id")])

    order_status_history = TableSpec(S, "order_status_history", [
        surrogate_id(), col("order_id", ColType.NUMBER_38, nullable=False),
        col("status", ColType.VARCHAR2, length=16, nullable=False),
        col("changed_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("order_id", f"{S}.orders", "id")])

    order_channels = lookup_table(S, "order_channels", 30)
    currencies = lookup_table(S, "currencies", 40, code_len=3)
    payment_methods = lookup_table(S, "payment_methods", 20)

    deprecated_cart_templates = lookup_table(S, "deprecated_cart_templates", 0, empty=True)
    legacy_quote_archive = lookup_table(S, "legacy_quote_archive", 0, empty=True)

    return_reasons = lookup_table(S, "return_reasons", 20)
    shipping_methods = lookup_table(S, "shipping_methods", 15)
    gift_card_types = lookup_table(S, "gift_card_types", 10)
    cart_abandonment_reasons = lookup_table(S, "cart_abandonment_reasons", 12)

    weighted = [
        (customers, 16), (carts, 10), (cart_items, 16), (quotes, 5), (quote_lines, 8),
        (orders, 28), (order_lines, 45), (order_discounts, 6), (payments, 13), (refunds, 4),
        (checkout_events, 16), (shipping_addresses, 9), (billing_addresses, 9), (order_status_history, 11),
    ]
    fixed_total = (discounts.row_count + order_channels.row_count + currencies.row_count + payment_methods.row_count
                   + return_reasons.row_count + shipping_methods.row_count + gift_card_types.row_count
                   + cart_abandonment_reasons.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        customers, carts, cart_items, discounts, quotes, quote_lines, orders, order_lines,
        order_discounts, payments, refunds, checkout_events, shipping_addresses, billing_addresses,
        order_status_history, order_channels, currencies, payment_methods,
        return_reasons, shipping_methods, gift_card_types, cart_abandonment_reasons,
        deprecated_cart_templates, legacy_quote_archive,
    ]


# =========================================================== 3. FINANCIAL_LEDGER

def _financial_tables():
    S = "FINANCIAL_LEDGER"
    target = SCHEMA_TARGETS[S]

    accounts = TableSpec(S, "accounts", [
        surrogate_id(), col("account_code", ColType.VARCHAR2, length=20, nullable=False),
        col("account_name", ColType.NVARCHAR2, length=150, nullable=False, unicode_profile="mixed"),
        col("account_type", ColType.VARCHAR2, length=20, nullable=False),
        col("balance", ColType.NUMBER_P_S, precision=20, scale=4, nullable=False, default="0"),
        *audit_columns(),
    ], primary_key=("id",), unique_constraints=[("account_code",)])

    fiscal_periods = lookup_table(S, "fiscal_periods", 96, extra_cols=[
        col("period_start", ColType.DATE, nullable=False), col("period_end", ColType.DATE, nullable=False),
        col("is_closed", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="0"),
    ])

    journals = TableSpec(S, "journals", [
        surrogate_id(), col("fiscal_period_id", ColType.NUMBER_38, nullable=False),
        col("journal_type", ColType.VARCHAR2, length=20, nullable=False),
        col("posted_at", ColType.TIMESTAMP, nullable=True),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'DRAFT'"),
        *audit_columns(),
    ], primary_key=("id",), foreign_keys=[fk("fiscal_period_id", f"{S}.fiscal_periods", "id")])

    postings = TableSpec(S, "postings", [
        col("journal_id", ColType.NUMBER_38, nullable=False),
        col("line_no", ColType.INTEGER, nullable=False),
        col("account_id", ColType.NUMBER_38, nullable=False),
        col("debit", ColType.NUMBER_P_S, precision=20, scale=4, nullable=False, default="0"),
        col("credit", ColType.NUMBER_P_S, precision=20, scale=4, nullable=False, default="0"),
    ], primary_key=("journal_id", "line_no"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("journal_id", f"{S}.journals", "id"), fk("account_id", f"{S}.accounts", "id")])

    journal_lines = TableSpec(S, "journal_lines", [
        col("journal_id", ColType.NUMBER_38, nullable=False),
        col("memo", ColType.NVARCHAR2, length=500, nullable=True, unicode_profile="mixed"),
        col("recorded_at", ColType.TIMESTAMP, nullable=False),
        col("amount", ColType.NUMBER_P_S, precision=20, scale=4, nullable=False),
    ], primary_key=None, pk_style=PKStyle.NONE, foreign_keys=[fk("journal_id", f"{S}.journals", "id")])

    invoices = TableSpec(S, "invoices", [
        surrogate_id(), col("invoice_number", ColType.VARCHAR2, length=32, nullable=False),
        col("account_id", ColType.NUMBER_38, nullable=False),
        col("issued_at", ColType.DATE, nullable=False),
        col("due_at", ColType.DATE, nullable=True),
        col("total_amount", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'OPEN'"),
    ], primary_key=("id",), unique_constraints=[("invoice_number",)], foreign_keys=[fk("account_id", f"{S}.accounts", "id")])

    invoice_lines = TableSpec(S, "invoice_lines", [
        surrogate_id(), col("invoice_id", ColType.NUMBER_38, nullable=False),
        col("description", ColType.NVARCHAR2, length=300, nullable=True, unicode_profile="mixed"),
        col("amount", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
        col("tax_rate_id", ColType.NUMBER_38, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("invoice_id", f"{S}.invoices", "id"), fk("tax_rate_id", f"{S}.tax_rates", "id")])

    taxes = lookup_table(S, "taxes", 60)
    tax_rates = TableSpec(S, "tax_rates", [
        surrogate_id(), col("tax_id", ColType.NUMBER_38, nullable=False),
        col("rate_percent", ColType.NUMBER_P_S, precision=5, scale=2, nullable=False),
        col("effective_from", ColType.DATE, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("tax_id", f"{S}.taxes", "id")], row_count=200)

    exchange_rates = TableSpec(S, "exchange_rates", [
        col("from_currency", ColType.CHAR, length=3, nullable=False),
        col("to_currency", ColType.CHAR, length=3, nullable=False),
        col("rate_date", ColType.DATE, nullable=False),
        col("rate", ColType.BINARY_DOUBLE, nullable=False),
    ], primary_key=("from_currency", "to_currency", "rate_date"), pk_style=PKStyle.COMPOSITE)

    settlements = TableSpec(S, "settlements", [
        surrogate_id(), col("account_id", ColType.NUMBER_38, nullable=False),
        col("settled_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("amount", ColType.NUMBER_P_S, precision=18, scale=2, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("account_id", f"{S}.accounts", "id")])

    payment_terms = lookup_table(S, "payment_terms", 40)
    ledger_categories = lookup_table(S, "ledger_categories", 80)
    currency_codes = lookup_table(S, "currency_codes", 40, code_len=3)

    deprecated_ledger_snapshots = lookup_table(S, "deprecated_ledger_snapshots", 0, empty=True)
    legacy_tax_regimes = lookup_table(S, "legacy_tax_regimes", 0, empty=True)

    expense_categories = lookup_table(S, "expense_categories", 40)
    budget_lines = lookup_table(S, "budget_lines", 60)
    gl_mapping_rules = lookup_table(S, "gl_mapping_rules", 50)
    statement_templates = lookup_table(S, "statement_templates", 20)

    weighted = [
        (accounts, 8), (journals, 10), (postings, 26), (journal_lines, 34), (invoices, 15),
        (invoice_lines, 20), (exchange_rates, 4), (settlements, 8),
    ]
    fixed_total = (fiscal_periods.row_count + taxes.row_count + tax_rates.row_count + payment_terms.row_count
                   + ledger_categories.row_count + currency_codes.row_count + expense_categories.row_count
                   + budget_lines.row_count + gl_mapping_rules.row_count + statement_templates.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        accounts, fiscal_periods, journals, postings, journal_lines, invoices, invoice_lines,
        taxes, tax_rates, exchange_rates, settlements, payment_terms, ledger_categories,
        currency_codes, expense_categories, budget_lines, gl_mapping_rules, statement_templates,
        deprecated_ledger_snapshots, legacy_tax_regimes,
    ]


# =========================================================== 4. CATALOG_PRODUCTS

def _catalog_tables():
    S = "CATALOG_PRODUCTS"
    target = SCHEMA_TARGETS[S]

    categories = TableSpec(S, "categories", [
        surrogate_id(), col("name", ColType.NVARCHAR2, length=150, nullable=False, unicode_profile="mixed"),
        col("parent_category_id", ColType.NUMBER_38, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("parent_category_id", f"{S}.categories", "id", self_ref=True)], row_count=300)

    attributes = lookup_table(S, "attributes", 250)
    price_books = lookup_table(S, "price_books", 40)

    products = TableSpec(S, "products", [
        surrogate_id(), col("product_code", ColType.VARCHAR2, length=32, nullable=False),
        col("category_id", ColType.NUMBER_38, nullable=False),
        col("name", ColType.NVARCHAR2, length=250, nullable=False, unicode_profile="mixed"),
        col("description", ColType.CLOB, nullable=True, lob_band="small"),
        col("is_active", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="1"),
        *audit_columns(),
    ], primary_key=("id",), unique_constraints=[("product_code",)], foreign_keys=[fk("category_id", f"{S}.categories", "id")])

    skus = TableSpec(S, "skus", [
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("product_id", ColType.NUMBER_38, nullable=False),
        col("upc", ColType.VARCHAR2, length=14, nullable=True),
        col("weight_kg", ColType.BINARY_FLOAT, nullable=True),
    ], primary_key=("sku_code",), pk_style=PKStyle.ALPHANUMERIC, foreign_keys=[fk("product_id", f"{S}.products", "id")])

    variants = TableSpec(S, "variants", [
        surrogate_id(), col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("variant_name", ColType.NVARCHAR2, length=100, nullable=False, unicode_profile="mixed"),
        col("attribute_value", ColType.VARCHAR2, length=100, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("sku_code", f"{S}.skus", "sku_code")])

    product_attributes = TableSpec(S, "product_attributes", [
        col("product_id", ColType.NUMBER_38, nullable=False),
        col("attribute_id", ColType.NUMBER_38, nullable=False),
        col("value", ColType.VARCHAR2, length=200, nullable=True),
    ], primary_key=("product_id", "attribute_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("product_id", f"{S}.products", "id"), fk("attribute_id", f"{S}.attributes", "id")])

    price_book_entries = TableSpec(S, "price_book_entries", [
        col("price_book_id", ColType.NUMBER_38, nullable=False),
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("price", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
    ], primary_key=("price_book_id", "sku_code"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("price_book_id", f"{S}.price_books", "id"), fk("sku_code", f"{S}.skus", "sku_code")])

    product_relationships = TableSpec(S, "product_relationships", [
        col("product_id", ColType.NUMBER_38, nullable=False),
        col("related_product_id", ColType.NUMBER_38, nullable=False),
        col("relationship_type", ColType.VARCHAR2, length=24, nullable=False),
    ], primary_key=("product_id", "related_product_id", "relationship_type"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("product_id", f"{S}.products", "id"), fk("related_product_id", f"{S}.products", "id")])

    brands = lookup_table(S, "brands", 200)
    units_of_measure = lookup_table(S, "units_of_measure", 30)

    deprecated_product_lines = lookup_table(S, "deprecated_product_lines", 0, empty=True)
    legacy_price_books = lookup_table(S, "legacy_price_books", 0, empty=True)

    product_families = lookup_table(S, "product_families", 60)
    warranty_types = lookup_table(S, "warranty_types", 15)
    size_charts = lookup_table(S, "size_charts", 30)
    supplier_codes = lookup_table(S, "supplier_codes", 120)

    weighted = [
        (products, 30), (skus, 30), (variants, 15), (product_attributes, 10),
        (price_book_entries, 12), (product_relationships, 6),
    ]
    fixed_total = (categories.row_count + attributes.row_count + price_books.row_count + brands.row_count
                   + units_of_measure.row_count + product_families.row_count + warranty_types.row_count
                   + size_charts.row_count + supplier_codes.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        categories, attributes, price_books, products, skus, variants, product_attributes,
        price_book_entries, product_relationships, brands, units_of_measure,
        product_families, warranty_types, size_charts, supplier_codes,
        deprecated_product_lines, legacy_price_books,
    ]


# =========================================================== 5. WAREHOUSE_INVENTORY

def _warehouse_tables():
    S = "WAREHOUSE_INVENTORY"
    target = SCHEMA_TARGETS[S]

    warehouses = lookup_table(S, "warehouses", 60, extra_cols=[col("region", ColType.VARCHAR2, length=8, nullable=True)])

    bins = TableSpec(S, "bins", [
        surrogate_id(), col("warehouse_id", ColType.NUMBER_38, nullable=False),
        col("bin_code", ColType.VARCHAR2, length=20, nullable=False),
    ], primary_key=("id",), unique_constraints=[("warehouse_id", "bin_code")], foreign_keys=[fk("warehouse_id", f"{S}.warehouses", "id")])

    stock_balances = TableSpec(S, "stock_balances", [
        col("warehouse_id", ColType.NUMBER_38, nullable=False),
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("quantity_on_hand", ColType.INTEGER, nullable=False, default="0"),
        col("quantity_reserved", ColType.INTEGER, nullable=False, default="0"),
        col("updated_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("warehouse_id", "sku_code"), pk_style=PKStyle.COMPOSITE, foreign_keys=[fk("warehouse_id", f"{S}.warehouses", "id")])

    lots = TableSpec(S, "lots", [
        surrogate_id(), col("lot_number", ColType.VARCHAR2, length=32, nullable=False),
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("expires_at", ColType.DATE, nullable=True),
        col("quantity", ColType.INTEGER, nullable=False),
    ], primary_key=("id",), unique_constraints=[("lot_number",)])

    serialized_units = TableSpec(S, "serialized_units", [
        col("serial_number", ColType.VARCHAR2, length=48, nullable=False),
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("warehouse_id", ColType.NUMBER_38, nullable=True),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'IN_STOCK'"),
    ], primary_key=("serial_number",), pk_style=PKStyle.NATURAL, foreign_keys=[fk("warehouse_id", f"{S}.warehouses", "id")])

    movements = TableSpec(S, "movements", [
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("warehouse_id", ColType.NUMBER_38, nullable=False),
        col("movement_type", ColType.VARCHAR2, length=16, nullable=False),
        col("quantity", ColType.INTEGER, nullable=False),
        col("occurred_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=None, pk_style=PKStyle.NONE, foreign_keys=[fk("warehouse_id", f"{S}.warehouses", "id")])

    reservations = TableSpec(S, "reservations", [
        surrogate_id(), col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("warehouse_id", ColType.NUMBER_38, nullable=False),
        col("quantity", ColType.INTEGER, nullable=False),
        col("reserved_at", ColType.TIMESTAMP, nullable=False),
        col("released_at", ColType.TIMESTAMP, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("warehouse_id", f"{S}.warehouses", "id")])

    movement_reason_codes = lookup_table(S, "movement_reason_codes", 30)
    bin_types = lookup_table(S, "bin_types", 12)

    deprecated_bin_layouts = lookup_table(S, "deprecated_bin_layouts", 0, empty=True)
    legacy_lot_archive = lookup_table(S, "legacy_lot_archive", 0, empty=True)

    zone_types = lookup_table(S, "zone_types", 15)
    equipment_types = lookup_table(S, "equipment_types", 25)
    cycle_count_types = lookup_table(S, "cycle_count_types", 10)
    damage_codes = lookup_table(S, "damage_codes", 20)

    weighted = [(bins, 10), (stock_balances, 30), (lots, 15), (serialized_units, 15), (movements, 20), (reservations, 8)]
    fixed_total = (warehouses.row_count + movement_reason_codes.row_count + bin_types.row_count
                   + zone_types.row_count + equipment_types.row_count + cycle_count_types.row_count
                   + damage_codes.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        warehouses, bins, stock_balances, lots, serialized_units, movements, reservations,
        movement_reason_codes, bin_types, zone_types, equipment_types, cycle_count_types, damage_codes,
        deprecated_bin_layouts, legacy_lot_archive,
    ]


# =========================================================== 6. FULFILLMENT_LOGISTICS

def _fulfillment_tables():
    S = "FULFILLMENT_LOGISTICS"
    target = SCHEMA_TARGETS[S]

    carriers = lookup_table(S, "carriers", 40)
    routes = lookup_table(S, "routes", 300)

    shipments = TableSpec(S, "shipments", [
        surrogate_id(), col("order_ref", ColType.VARCHAR2, length=32, nullable=False),
        col("carrier_id", ColType.NUMBER_38, nullable=False),
        col("route_id", ColType.NUMBER_38, nullable=True),
        col("status", ColType.VARCHAR2, length=16, nullable=False, default="'PENDING'"),
        col("shipped_at", ColType.TIMESTAMP_TZ, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("carrier_id", f"{S}.carriers", "id"), fk("route_id", f"{S}.routes", "id")])

    shipment_lines = TableSpec(S, "shipment_lines", [
        surrogate_id(), col("shipment_id", ColType.NUMBER_38, nullable=False),
        col("sku_code", ColType.VARCHAR2, length=40, nullable=False),
        col("quantity", ColType.INTEGER, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("shipment_id", f"{S}.shipments", "id")])

    manifests = TableSpec(S, "manifests", [
        surrogate_id(), col("carrier_id", ColType.NUMBER_38, nullable=False),
        col("manifest_date", ColType.DATE, nullable=False),
        col("total_shipments", ColType.INTEGER, nullable=False, default="0"),
    ], primary_key=("id",), foreign_keys=[fk("carrier_id", f"{S}.carriers", "id")])

    tracking_events = TableSpec(S, "tracking_events", [
        col("shipment_id", ColType.NUMBER_38, nullable=False),
        col("event_code", ColType.VARCHAR2, length=24, nullable=False),
        col("occurred_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("location", ColType.NVARCHAR2, length=150, nullable=True, unicode_profile="mixed"),
    ], primary_key=None, pk_style=PKStyle.NONE, foreign_keys=[fk("shipment_id", f"{S}.shipments", "id")])

    delivery_attempts = TableSpec(S, "delivery_attempts", [
        surrogate_id(), col("shipment_id", ColType.NUMBER_38, nullable=False),
        col("attempted_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("outcome", ColType.VARCHAR2, length=16, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("shipment_id", f"{S}.shipments", "id")])

    service_levels = lookup_table(S, "service_levels", 15)
    package_types = lookup_table(S, "package_types", 20)

    deprecated_routes = lookup_table(S, "deprecated_routes", 0, empty=True)
    legacy_manifest_batches = lookup_table(S, "legacy_manifest_batches", 0, empty=True)

    customs_codes = lookup_table(S, "customs_codes", 80)
    delivery_windows = lookup_table(S, "delivery_windows", 20)
    address_types = lookup_table(S, "address_types", 10)
    exception_codes = lookup_table(S, "exception_codes", 25)

    weighted = [(shipments, 30), (shipment_lines, 25), (manifests, 8), (tracking_events, 30), (delivery_attempts, 7)]
    fixed_total = (carriers.row_count + routes.row_count + service_levels.row_count + package_types.row_count
                   + customs_codes.row_count + delivery_windows.row_count + address_types.row_count
                   + exception_codes.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        carriers, routes, shipments, shipment_lines, manifests, tracking_events, delivery_attempts,
        service_levels, package_types, customs_codes, delivery_windows, address_types, exception_codes,
        deprecated_routes, legacy_manifest_batches,
    ]


# =========================================================== 7. ORGANIZATION_HR

def _hr_tables():
    S = "ORGANIZATION_HR"
    target = SCHEMA_TARGETS[S]

    departments = TableSpec(S, "departments", [
        surrogate_id(), col("name", ColType.NVARCHAR2, length=150, nullable=False, unicode_profile="mixed"),
        col("parent_department_id", ColType.NUMBER_38, nullable=True),
        col("cost_center", ColType.VARCHAR2, length=20, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("parent_department_id", f"{S}.departments", "id", self_ref=True)], row_count=120)

    shifts = lookup_table(S, "shifts", 40, extra_cols=[col("starts_at", ColType.VARCHAR2, length=8, nullable=True), col("ends_at", ColType.VARCHAR2, length=8, nullable=True)])
    payroll_runs = lookup_table(S, "payroll_runs", 60, extra_cols=[col("run_date", ColType.DATE, nullable=True)])

    employees = TableSpec(S, "employees", [
        surrogate_id(), col("employee_code", ColType.VARCHAR2, length=20, nullable=False),
        col("department_id", ColType.NUMBER_38, nullable=False),
        col("full_name", ColType.NVARCHAR2, length=200, nullable=False, unicode_profile="mixed"),
        col("hire_date", ColType.DATE, nullable=False),
        col("termination_date", ColType.DATE, nullable=True),
        col("salary", ColType.NUMBER_P_S, precision=14, scale=2, nullable=True),
        *audit_columns(),
    ], primary_key=("id",), unique_constraints=[("employee_code",)], foreign_keys=[fk("department_id", f"{S}.departments", "id")])

    reporting_lines = TableSpec(S, "reporting_lines", [
        col("employee_id", ColType.NUMBER_38, nullable=False),
        col("manager_id", ColType.NUMBER_38, nullable=False),
        col("effective_from", ColType.DATE, nullable=False),
    ], primary_key=("employee_id", "manager_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("employee_id", f"{S}.employees", "id"), fk("manager_id", f"{S}.employees", "id")])

    employee_shifts = TableSpec(S, "employee_shifts", [
        surrogate_id(), col("employee_id", ColType.NUMBER_38, nullable=False),
        col("shift_id", ColType.NUMBER_38, nullable=False),
        col("work_date", ColType.DATE, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("employee_id", f"{S}.employees", "id"), fk("shift_id", f"{S}.shifts", "id")])

    employment_history = TableSpec(S, "employment_history", [
        surrogate_id(), col("employee_id", ColType.NUMBER_38, nullable=False),
        col("change_type", ColType.VARCHAR2, length=24, nullable=False),
        col("changed_at", ColType.TIMESTAMP, nullable=False),
        col("old_value", ColType.VARCHAR2, length=200, nullable=True),
        col("new_value", ColType.VARCHAR2, length=200, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("employee_id", f"{S}.employees", "id")])

    payroll_entries = TableSpec(S, "payroll_entries", [
        surrogate_id(), col("payroll_run_id", ColType.NUMBER_38, nullable=False),
        col("employee_id", ColType.NUMBER_38, nullable=False),
        col("gross_pay", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
        col("net_pay", ColType.NUMBER_P_S, precision=14, scale=2, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("payroll_run_id", f"{S}.payroll_runs", "id"), fk("employee_id", f"{S}.employees", "id")])

    job_titles = lookup_table(S, "job_titles", 150)
    leave_types = lookup_table(S, "leave_types", 12)

    deprecated_org_units = lookup_table(S, "deprecated_org_units", 0, empty=True)
    legacy_shift_templates = lookup_table(S, "legacy_shift_templates", 0, empty=True)

    benefit_plans = lookup_table(S, "benefit_plans", 25)
    certification_types = lookup_table(S, "certification_types", 40)
    performance_ratings = lookup_table(S, "performance_ratings", 10)
    termination_reasons = lookup_table(S, "termination_reasons", 15)

    weighted = [(employees, 26), (reporting_lines, 20), (employee_shifts, 16), (employment_history, 10), (payroll_entries, 20)]
    fixed_total = (departments.row_count + shifts.row_count + payroll_runs.row_count + job_titles.row_count
                   + leave_types.row_count + benefit_plans.row_count + certification_types.row_count
                   + performance_ratings.row_count + termination_reasons.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        departments, shifts, payroll_runs, employees, reporting_lines, employee_shifts,
        employment_history, payroll_entries, job_titles, leave_types,
        benefit_plans, certification_types, performance_ratings, termination_reasons,
        deprecated_org_units, legacy_shift_templates,
    ]


# =========================================================== 8. CONTENT_DOCUMENTS

def _content_tables():
    S = "CONTENT_DOCUMENTS"
    target = SCHEMA_TARGETS[S]

    retention_policies = lookup_table(S, "retention_policies", 30)
    tags = lookup_table(S, "tags", 200)

    documents = TableSpec(S, "documents", [
        surrogate_id(), col("title", ColType.NVARCHAR2, length=300, nullable=False, unicode_profile="mixed"),
        col("mime_type", ColType.VARCHAR2, length=100, nullable=False),
        col("retention_policy_id", ColType.NUMBER_38, nullable=True),
        col("text_content", ColType.CLOB, nullable=True, lob_band="mixed"),
        col("binary_content", ColType.BLOB, nullable=True, lob_band="mixed"),
        col("owner_ref", ColType.VARCHAR2, length=64, nullable=True),
        *audit_columns(),
    ], primary_key=("id",), foreign_keys=[fk("retention_policy_id", f"{S}.retention_policies", "id")])

    document_revisions = TableSpec(S, "document_revisions", [
        surrogate_id(), col("document_id", ColType.NUMBER_38, nullable=False),
        col("revision_no", ColType.INTEGER, nullable=False),
        col("edited_at", ColType.TIMESTAMP, nullable=False),
        col("editor_ref", ColType.VARCHAR2, length=64, nullable=True),
    ], primary_key=("id",), unique_constraints=[("document_id", "revision_no")], foreign_keys=[fk("document_id", f"{S}.documents", "id")])

    document_metadata = TableSpec(S, "document_metadata", [
        col("document_id", ColType.NUMBER_38, nullable=False),
        col("meta_key", ColType.VARCHAR2, length=64, nullable=False),
        col("meta_value", ColType.NVARCHAR2, length=500, nullable=True, unicode_profile="mixed"),
    ], primary_key=("document_id", "meta_key"), pk_style=PKStyle.COMPOSITE, foreign_keys=[fk("document_id", f"{S}.documents", "id")])

    document_ownership = TableSpec(S, "document_ownership", [
        surrogate_id(), col("document_id", ColType.NUMBER_38, nullable=False),
        col("owner_ref", ColType.VARCHAR2, length=64, nullable=False),
        col("granted_at", ColType.TIMESTAMP, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("document_id", f"{S}.documents", "id")])

    document_tags = TableSpec(S, "document_tags", [
        col("document_id", ColType.NUMBER_38, nullable=False),
        col("tag_id", ColType.NUMBER_38, nullable=False),
    ], primary_key=("document_id", "tag_id"), pk_style=PKStyle.COMPOSITE,
       foreign_keys=[fk("document_id", f"{S}.documents", "id"), fk("tag_id", f"{S}.tags", "id")])

    document_types = lookup_table(S, "document_types", 60)
    languages = lookup_table(S, "languages", 40, code_len=8)

    deprecated_document_types = lookup_table(S, "deprecated_document_types", 0, empty=True)
    legacy_retention_rules = lookup_table(S, "legacy_retention_rules", 0, empty=True)

    access_levels = lookup_table(S, "access_levels", 10)
    classification_labels = lookup_table(S, "classification_labels", 15)
    workflow_states = lookup_table(S, "workflow_states", 12)
    review_statuses = lookup_table(S, "review_statuses", 10)

    weighted = [(documents, 26), (document_revisions, 20), (document_metadata, 16), (document_ownership, 8), (document_tags, 11)]
    fixed_total = (retention_policies.row_count + tags.row_count + document_types.row_count + languages.row_count
                   + access_levels.row_count + classification_labels.row_count + workflow_states.row_count
                   + review_statuses.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        retention_policies, tags, documents, document_revisions, document_metadata,
        document_ownership, document_tags, document_types, languages,
        access_levels, classification_labels, workflow_states, review_statuses,
        deprecated_document_types, legacy_retention_rules,
    ]


# =========================================================== 9. AUDIT_COMPLIANCE

def _audit_tables():
    S = "AUDIT_COMPLIANCE"
    target = SCHEMA_TARGETS[S]

    compliance_frameworks = lookup_table(S, "compliance_frameworks", 30)

    audit_events = TableSpec(S, "audit_events", [
        col("actor_ref", ColType.VARCHAR2, length=64, nullable=True),
        col("action", ColType.VARCHAR2, length=64, nullable=False),
        col("resource_ref", ColType.VARCHAR2, length=128, nullable=True),
        col("occurred_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("detail", ColType.CLOB, nullable=True, lob_band="tiny"),
    ], primary_key=None, pk_style=PKStyle.NONE)

    compliance_observations = TableSpec(S, "compliance_observations", [
        surrogate_id(), col("framework_id", ColType.NUMBER_38, nullable=False),
        col("observed_at", ColType.TIMESTAMP, nullable=False),
        col("severity", ColType.VARCHAR2, length=16, nullable=False),
        col("description", ColType.NVARCHAR2, length=500, nullable=True, unicode_profile="mixed"),
    ], primary_key=("id",), foreign_keys=[fk("framework_id", f"{S}.compliance_frameworks", "id")])

    signatures = TableSpec(S, "signatures", [
        surrogate_id(), col("signer_ref", ColType.VARCHAR2, length=64, nullable=False),
        col("signed_at", ColType.TIMESTAMP, nullable=False),
        col("signature_hash", ColType.RAW, length=32, nullable=False),
    ], primary_key=("id",))

    change_histories = TableSpec(S, "change_histories", [
        surrogate_id(), col("entity_ref", ColType.VARCHAR2, length=128, nullable=False),
        col("changed_by", ColType.VARCHAR2, length=64, nullable=True),
        col("changed_at", ColType.TIMESTAMP, nullable=False),
        col("before_json", ColType.JSON, nullable=True),
        col("after_json", ColType.JSON, nullable=True),
    ], primary_key=("id",))

    access_events = TableSpec(S, "access_events", [
        surrogate_id(), col("actor_ref", ColType.VARCHAR2, length=64, nullable=True),
        col("resource_ref", ColType.VARCHAR2, length=128, nullable=True),
        col("occurred_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("allowed", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False),
    ], primary_key=("id",))

    severity_levels = lookup_table(S, "severity_levels", 8)
    observation_categories = lookup_table(S, "observation_categories", 40)

    deprecated_audit_rules = lookup_table(S, "deprecated_audit_rules", 0, empty=True)
    legacy_compliance_frameworks = lookup_table(S, "legacy_compliance_frameworks", 0, empty=True)

    control_objectives = lookup_table(S, "control_objectives", 50)
    risk_categories = lookup_table(S, "risk_categories", 25)
    remediation_statuses = lookup_table(S, "remediation_statuses", 10)
    evidence_types = lookup_table(S, "evidence_types", 20)

    weighted = [(audit_events, 40), (compliance_observations, 15), (signatures, 8), (change_histories, 22), (access_events, 20)]
    fixed_total = (compliance_frameworks.row_count + severity_levels.row_count + observation_categories.row_count
                   + control_objectives.row_count + risk_categories.row_count + remediation_statuses.row_count
                   + evidence_types.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        compliance_frameworks, audit_events, compliance_observations, signatures, change_histories,
        access_events, severity_levels, observation_categories,
        control_objectives, risk_categories, remediation_statuses, evidence_types,
        deprecated_audit_rules, legacy_compliance_frameworks,
    ]


# =========================================================== 10. OPERATIONAL_METRICS

def _metrics_tables():
    S = "OPERATIONAL_METRICS"
    target = SCHEMA_TARGETS[S]

    metrics_definitions = lookup_table(S, "metrics_definitions", 150, extra_cols=[col("unit", ColType.VARCHAR2, length=16, nullable=True)])
    system_probes = lookup_table(S, "system_probes", 80)

    metric_samples = TableSpec(S, "metric_samples", [
        surrogate_id(), col("metric_id", ColType.NUMBER_38, nullable=False),
        col("sampled_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("value", ColType.BINARY_DOUBLE, nullable=False),
    ], primary_key=("id",), foreign_keys=[fk("metric_id", f"{S}.metrics_definitions", "id")])

    telemetry_events = TableSpec(S, "telemetry_events", [
        surrogate_id(), col("probe_id", ColType.NUMBER_38, nullable=False),
        col("event_type", ColType.VARCHAR2, length=32, nullable=False),
        col("occurred_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("payload", ColType.JSON, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("probe_id", f"{S}.system_probes", "id")])

    operational_counters = TableSpec(S, "operational_counters", [
        col("counter_name", ColType.VARCHAR2, length=64, nullable=False),
        col("window_start", ColType.TIMESTAMP, nullable=False),
        col("value", ColType.NUMBER_38, nullable=False, default="0"),
    ], primary_key=("counter_name", "window_start"), pk_style=PKStyle.COMPOSITE)

    metric_categories = lookup_table(S, "metric_categories", 30)
    alert_thresholds = lookup_table(S, "alert_thresholds", 60)

    deprecated_metric_defs = lookup_table(S, "deprecated_metric_defs", 0, empty=True)
    legacy_probe_configs = lookup_table(S, "legacy_probe_configs", 0, empty=True)

    aggregation_types = lookup_table(S, "aggregation_types", 10)
    sla_targets = lookup_table(S, "sla_targets", 30)
    dashboard_definitions = lookup_table(S, "dashboard_definitions", 40)
    retention_windows = lookup_table(S, "retention_windows", 15)

    weighted = [(metric_samples, 42), (telemetry_events, 30), (operational_counters, 10)]
    fixed_total = (metrics_definitions.row_count + system_probes.row_count + metric_categories.row_count
                   + alert_thresholds.row_count + aggregation_types.row_count + sla_targets.row_count
                   + dashboard_definitions.row_count + retention_windows.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        metrics_definitions, system_probes, metric_samples, telemetry_events, operational_counters,
        metric_categories, alert_thresholds, aggregation_types, sla_targets, dashboard_definitions,
        retention_windows, deprecated_metric_defs, legacy_probe_configs,
    ]


# =========================================================== 11. INTEGRATION_REGISTRY

def _integration_tables():
    S = "INTEGRATION_REGISTRY"
    target = SCHEMA_TARGETS[S]

    endpoints = lookup_table(S, "endpoints", 200, code_len=64)
    integrations = lookup_table(S, "integrations", 150)
    message_contracts = lookup_table(S, "message_contracts", 100)

    webhooks = TableSpec(S, "webhooks", [
        surrogate_id(), col("integration_id", ColType.NUMBER_38, nullable=False),
        col("target_url", ColType.VARCHAR2, length=500, nullable=False),
        col("secret_ref", ColType.VARCHAR2, length=200, nullable=True),
        col("is_active", ColType.NUMBER_P_S, precision=1, scale=0, nullable=False, default="1"),
    ], primary_key=("id",), foreign_keys=[fk("integration_id", f"{S}.integrations", "id")])

    webhook_deliveries = TableSpec(S, "webhook_deliveries", [
        surrogate_id(), col("webhook_id", ColType.NUMBER_38, nullable=False),
        col("delivered_at", ColType.TIMESTAMP_TZ, nullable=False),
        col("response_code", ColType.INTEGER, nullable=True),
        col("payload", ColType.JSON, nullable=True),
    ], primary_key=("id",), foreign_keys=[fk("webhook_id", f"{S}.webhooks", "id")])

    external_identifiers = TableSpec(S, "external_identifiers", [
        col("system_code", ColType.VARCHAR2, length=32, nullable=False),
        col("external_id", ColType.VARCHAR2, length=200, nullable=False),
        col("internal_ref", ColType.VARCHAR2, length=128, nullable=True),
    ], primary_key=("system_code", "external_id"), pk_style=PKStyle.COMPOSITE)

    connector_types = lookup_table(S, "connector_types", 25)
    contract_versions = lookup_table(S, "contract_versions", 40)

    deprecated_endpoints = lookup_table(S, "deprecated_endpoints", 0, empty=True)
    legacy_message_contracts = lookup_table(S, "legacy_message_contracts", 0, empty=True)

    auth_types = lookup_table(S, "auth_types", 12)
    rate_limit_policies = lookup_table(S, "rate_limit_policies", 25)
    environment_types = lookup_table(S, "environment_types", 6)
    protocol_types = lookup_table(S, "protocol_types", 15)

    weighted = [(webhooks, 20), (webhook_deliveries, 42), (external_identifiers, 16)]
    fixed_total = (endpoints.row_count + integrations.row_count + message_contracts.row_count
                   + connector_types.row_count + contract_versions.row_count + auth_types.row_count
                   + rate_limit_policies.row_count + environment_types.row_count + protocol_types.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        endpoints, integrations, message_contracts, webhooks, webhook_deliveries,
        external_identifiers, connector_types, contract_versions,
        auth_types, rate_limit_policies, environment_types, protocol_types,
        deprecated_endpoints, legacy_message_contracts,
    ]


# =========================================================== 12. COMPATIBILITY_LAB

def _compat_tables():
    S = "COMPATIBILITY_LAB"
    target = SCHEMA_TARGETS[S]

    numeric_edge_cases = TableSpec(S, "numeric_edge_cases", [
        surrogate_id(),
        col("num_generic", ColType.NUMBER, nullable=True),
        col("num_38", ColType.NUMBER_38, nullable=True),
        col("num_pos_scale", ColType.NUMBER_P_S, precision=10, scale=4, nullable=True),
        col("num_neg_scale", ColType.NUMBER_P_S, precision=10, scale=-2, nullable=True),
        col("num_zero_scale", ColType.NUMBER_P_S, precision=10, scale=0, nullable=True),
        col("num_high_precision", ColType.NUMBER_P_S, precision=38, scale=10, nullable=True),
        col("financial_decimal", ColType.NUMBER_P_S, precision=19, scale=4, nullable=True),
        col("approx_float", ColType.FLOAT, nullable=True),
        col("bin_float", ColType.BINARY_FLOAT, nullable=True),
        col("bin_double", ColType.BINARY_DOUBLE, nullable=True),
        col("scientific", ColType.BINARY_DOUBLE, nullable=True),
    ], primary_key=("id",))

    unicode_text_matrix = TableSpec(S, "unicode_text_matrix", [
        surrogate_id(),
        col("varchar2_ascii", ColType.VARCHAR2, length=200, nullable=True),
        col("nvarchar2_mixed", ColType.NVARCHAR2, length=500, nullable=True, unicode_profile="mixed"),
        col("char_fixed", ColType.CHAR, length=20, nullable=True),
        col("nchar_fixed", ColType.NCHAR, length=20, nullable=True, unicode_profile="mixed"),
        col("script_kannada", ColType.NVARCHAR2, length=200, nullable=True, unicode_profile="kn"),
        col("script_devanagari", ColType.NVARCHAR2, length=200, nullable=True, unicode_profile="hi"),
        col("script_arabic", ColType.NVARCHAR2, length=200, nullable=True, unicode_profile="ar"),
        col("script_cjk", ColType.NVARCHAR2, length=200, nullable=True, unicode_profile="cjk"),
        col("script_emoji_currency", ColType.NVARCHAR2, length=200, nullable=True, unicode_profile="emoji"),
        col("trailing_space_case", ColType.CHAR, length=30, nullable=True),
        col("empty_vs_null", ColType.VARCHAR2, length=10, nullable=True),
    ], primary_key=("id",))

    temporal_edge_cases = TableSpec(S, "temporal_edge_cases", [
        surrogate_id(),
        col("plain_date", ColType.DATE, nullable=True),
        col("ts_seconds", ColType.TIMESTAMP, nullable=True),
        col("ts_fractional", ColType.TIMESTAMP, nullable=True),
        col("ts_with_tz", ColType.TIMESTAMP_TZ, nullable=True),
        col("ts_with_local_tz", ColType.TIMESTAMP_LTZ, nullable=True),
        col("interval_year_month", ColType.INTERVAL_YM, nullable=True),
        col("interval_day_second", ColType.INTERVAL_DS, nullable=True),
        col("leap_day_case", ColType.DATE, nullable=True),
        col("historical_date", ColType.DATE, nullable=True),
        col("future_date", ColType.DATE, nullable=True),
        col("positive_offset", ColType.TIMESTAMP_TZ, nullable=True),
        col("negative_offset", ColType.TIMESTAMP_TZ, nullable=True),
    ], primary_key=("id",))

    binary_raw_matrix = TableSpec(S, "binary_raw_matrix", [
        surrogate_id(),
        col("raw_bytes", ColType.RAW, length=64, nullable=True),
        col("uuid_binary", ColType.RAW, length=16, nullable=True),
        col("zero_bytes", ColType.RAW, length=16, nullable=True),
        col("hash_payload", ColType.RAW, length=32, nullable=True),
    ], primary_key=("id",))

    structured_payloads = TableSpec(S, "structured_payloads", [
        surrogate_id(),
        col("json_doc", ColType.JSON, nullable=True),
        col("xml_doc", ColType.XMLTYPE, nullable=True),
    ], primary_key=("id",))

    null_and_default_matrix = TableSpec(S, "null_and_default_matrix", [
        surrogate_id(),
        col("mandatory_col", ColType.VARCHAR2, length=50, nullable=False, default="'DEFAULT_VALUE'"),
        col("nullable_col", ColType.VARCHAR2, length=50, nullable=True),
        col("defaulted_number", ColType.NUMBER_P_S, precision=8, scale=2, nullable=False, default="0"),
    ], primary_key=("id",))

    # deliberately quoted / reserved-word-shaped identifiers (Oracle-style mixed case + reserved word)
    quoted_identifier_cases = TableSpec(S, 'Quoted_Case_Table', [
        surrogate_id(),
        col('Order', ColType.VARCHAR2, length=50, nullable=True),   # reserved word as column name
        col('Mixed_Case_Col', ColType.VARCHAR2, length=50, nullable=True),
        col('has space', ColType.VARCHAR2, length=50, nullable=True),
    ], primary_key=("id",))

    lob_edge_cases = TableSpec(S, "lob_edge_cases", [
        surrogate_id(),
        col("clob_col", ColType.CLOB, nullable=True, lob_band="tiny"),
        col("nclob_col", ColType.NCLOB, nullable=True, lob_band="tiny"),
        col("blob_col", ColType.BLOB, nullable=True, lob_band="tiny"),
    ], primary_key=("id",))

    portability_notes = lookup_table(S, "portability_notes", 40)
    charset_profiles = lookup_table(S, "charset_profiles", 12)
    collation_profiles = lookup_table(S, "collation_profiles", 15)
    rounding_modes = lookup_table(S, "rounding_modes", 6)
    timezone_profiles = lookup_table(S, "timezone_profiles", 40)

    deprecated_edge_case_archive = lookup_table(S, "deprecated_edge_case_archive", 0, empty=True)
    legacy_portability_notes = lookup_table(S, "legacy_portability_notes", 0, empty=True)

    weighted = [
        (numeric_edge_cases, 15), (unicode_text_matrix, 15), (temporal_edge_cases, 15),
        (binary_raw_matrix, 10), (structured_payloads, 14), (null_and_default_matrix, 10),
        (quoted_identifier_cases, 8), (lob_edge_cases, 6),
    ]
    fixed_total = (portability_notes.row_count + charset_profiles.row_count + collation_profiles.row_count
                   + rounding_modes.row_count + timezone_profiles.row_count)
    apply_weighted_rows(weighted, target, fixed_total)

    return [
        numeric_edge_cases, unicode_text_matrix, temporal_edge_cases, binary_raw_matrix,
        structured_payloads, null_and_default_matrix, quoted_identifier_cases, lob_edge_cases,
        portability_notes, charset_profiles, collation_profiles, rounding_modes, timezone_profiles,
        deprecated_edge_case_archive, legacy_portability_notes,
    ]


# ------------------------------------------------------------------ assembly --

def all_tables():
    tables = (
        _iam_tables() + _commerce_tables() + _financial_tables() + _catalog_tables()
        + _warehouse_tables() + _fulfillment_tables() + _hr_tables() + _content_tables()
        + _audit_tables() + _metrics_tables() + _integration_tables() + _compat_tables()
    )
    return tables


ALL_TABLES = all_tables()

# ---- self-checks performed at import time (cheap, catch spec drift immediately) --

_total_rows = sum(t.row_count for t in ALL_TABLES)
assert _total_rows == 1_000_000, f"declared baseline must total exactly 1,000,000 rows, got {_total_rows}"

_by_schema = {}
for _t in ALL_TABLES:
    _by_schema.setdefault(_t.schema, 0)
    _by_schema[_t.schema] += _t.row_count
for _s, _target in SCHEMA_TARGETS.items():
    assert _by_schema.get(_s, 0) == _target, f"{_s}: declared {_by_schema.get(_s,0)} rows, target {_target}"

_no_pk_tables = [t for t in ALL_TABLES if t.primary_key is None]
_empty_tables = [t for t in ALL_TABLES if t.kind == TableKind.EMPTY]
_populated_tables = [t for t in ALL_TABLES if t.kind == TableKind.POPULATED]
