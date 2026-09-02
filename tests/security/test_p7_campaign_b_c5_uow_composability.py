"""tests.security.test_p7_campaign_b_c5_uow_composability
========================================================
Final verification-only check: does an authority-level `_commit()` (added to
MFAAuthority/JITIdentityAuthority/SCIMProvisioningService in the previous pass to
guarantee standalone durability) prematurely commit an externally-owned larger
Unit-of-Work transaction, defeating that outer transaction's atomicity/rollback?

Case A proves standalone durability still works (must continue to work).
Case B hostile-tests whether an authority call inside a `with uow:` block breaks outer
rollback.
"""

from __future__ import annotations

import pytest

from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.mfa import MFAAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

_MRK = b"\x33" * 32


def _fresh_uow(db_path: str) -> SQLiteUnitOfWork:
    u = SQLiteUnitOfWork(db_path)
    u.initialize_schema()
    return u


# ---------------------------------------------------------------------------
# Case A -- standalone authority call: durability must continue to work
# ---------------------------------------------------------------------------

def test_c5_case_a_standalone_authority_call_is_durable_across_reconnect(tmp_path):
    db_path = str(tmp_path / "case_a.db")
    uow1 = _fresh_uow(db_path)
    uow1.tenants.create_tenant("t1", "T1")
    uow1.principals.create(tenant_id="t1", principal_id="p1", principal_type="HUMAN", username="p1", created_at="2026-01-01T00:00:00+00:00")
    uow1.connection.commit()  # setup only -- not part of the thing under test

    ks1 = KeyStoreAuthority(uow1.keyring, master_root_key=_MRK)
    mfa1 = MFAAuthority(ks1, uow1.mfa)
    enrollment = mfa1.enroll_totp("t1", "p1", account_label="p1@x.com")  # standalone call, no outer `with uow:`

    # Reconnect: a fresh connection must see the enrollment without any explicit commit
    # from the test -- MFAAuthority's own _commit() must have made it durable.
    uow2 = _fresh_uow(db_path)
    factor = uow2.mfa.get_factor("t1", enrollment.factor_id)
    assert factor is not None
    assert factor["status"] == "PENDING_ACTIVATION"


# ---------------------------------------------------------------------------
# Case B -- authority participates inside an externally-owned `with uow:` transaction
# ---------------------------------------------------------------------------

def test_c5_case_b_authority_commit_inside_outer_transaction_defeats_outer_rollback(tmp_path):
    """
    Hostile construction: outer transaction begins, writes an unrelated row, calls a
    Campaign B authority (which self-commits), then the outer transaction is forced to
    fail and roll back. If composability were correct, BOTH the unrelated write and the
    authority's write would be rolled back together. This test determines which actually
    happens.
    """
    db_path = str(tmp_path / "case_b.db")
    setup = _fresh_uow(db_path)
    setup.tenants.create_tenant("t1", "T1")
    setup.principals.create(tenant_id="t1", principal_id="p1", principal_type="HUMAN", username="p1", created_at="2026-01-01T00:00:00+00:00")
    setup.connection.commit()

    uow = _fresh_uow(db_path)
    ks = KeyStoreAuthority(uow.keyring, master_root_key=_MRK)
    mfa = MFAAuthority(ks, uow.mfa)

    class _InducedFailure(Exception):
        pass

    unrelated_tenant_id = "t-unrelated-outer-write"
    with pytest.raises(_InducedFailure):
        with uow:  # externally-owned transaction, BEGIN IMMEDIATE
            uow.tenants.create_tenant(unrelated_tenant_id, "Unrelated Outer Write")  # operation A
            mfa.enroll_totp("t1", "p1", account_label="p1@x.com")  # Campaign B authority mutation (self-commits internally)
            raise _InducedFailure("induced failure after authority call, before outer exit")
    # SQLiteUnitOfWork.__exit__ on exception calls self.rollback() -> self._conn.rollback()

    # Reconnect and check what actually persisted.
    check = _fresh_uow(db_path)
    unrelated_tenant = check.tenants.get_by_id(unrelated_tenant_id)
    mfa_factors_exist = len(check.mfa.list_active_factors("t1", "p1")) >= 0  # PENDING factors aren't "active"; check raw table instead
    cur = check.connection.execute("SELECT COUNT(*) as cnt FROM mfa_factors WHERE tenant_id = 't1' AND principal_id = 'p1'")
    mfa_factor_count = cur.fetchone()["cnt"]

    if unrelated_tenant is not None or mfa_factor_count > 0:
        # COMPOSABILITY DEFECT PROVEN: the authority's internal _commit() flushed the
        # outer transaction's connection, so the later rollback had nothing left to undo
        # for either the unrelated write or the authority's own write.
        pytest.fail(
            "COMPOSABILITY_DEFECT_PROVEN: authority-level _commit() prematurely committed "
            f"the externally-owned transaction. unrelated_tenant_persisted={unrelated_tenant is not None}, "
            f"mfa_factor_persisted={mfa_factor_count > 0} -- outer rollback could not undo either write."
        )
    # If we reach here, rollback genuinely undid everything -- no defect.
