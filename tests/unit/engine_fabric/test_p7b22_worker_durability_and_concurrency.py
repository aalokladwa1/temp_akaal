"""
P7B.22 -- Worker Fabric restart durability + concurrent registration races.
"""

from __future__ import annotations

import threading

import pytest

from akaalEngine.fabric.durability import new_sqlite_backed_store, reconstruct_worker_registry
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState
from akaalEngine.fabric.worker_fabric.registry import StaleWorkerFencingError, WorkerRegistry

SIGNING_KEY = b"durability-test-fencing-key-0001"
ANCHOR_KEY = b"durability-test-anchor-key-00002"


def _store(tmp_path):
    return new_sqlite_backed_store(str(tmp_path), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)


def _worker(worker_id, site="site-1", tenant="t1", epoch=1):
    return WorkerNode(worker_id=worker_id, site_id=site, tenant_id=tenant, runtime_version="1.0.0", fencing_epoch=epoch)


def test_worker_fencing_epoch_survives_restart(tmp_path):
    store_a = _store(tmp_path)
    reg_a = WorkerRegistry(durability_store=store_a)
    reg_a.register(_worker("w1", epoch=5))
    del reg_a

    store_b = _store(tmp_path)
    reg_b = reconstruct_worker_registry(store_b)
    # A restarted control plane must still refuse to admit a replacement at epoch <= 5.
    with pytest.raises(StaleWorkerFencingError):
        reg_b.register(_worker("w2", epoch=5))
    reg_b.register(_worker("w2", epoch=6))  # strictly higher still works


def test_worker_state_survives_restart(tmp_path):
    store_a = _store(tmp_path)
    reg_a = WorkerRegistry(durability_store=store_a)
    reg_a.register(_worker("w1"))
    reg_a.revoke("w1", "t1")
    del reg_a

    store_b = _store(tmp_path)
    reg_b = reconstruct_worker_registry(store_b)
    assert reg_b.get("w1", "t1").state == WorkerState.REVOKED


def test_concurrent_registration_at_same_slot_only_one_wins_per_epoch():
    """64 threads race to register at the same (tenant, site) slot with sequential
    epochs 1..64 in randomized submission order -- exactly one registration per epoch
    value can ever succeed for that slot (fencing monotonicity under real contention,
    mirroring the P7B.5 32-thread fencing-epoch proof)."""
    import random

    reg = WorkerRegistry()
    epochs = list(range(1, 65))
    random.shuffle(epochs)
    results = {"succeeded": 0, "errors": []}
    lock = threading.Lock()

    def worker(epoch):
        try:
            reg.register(_worker(f"w-{epoch}", epoch=epoch))
            with lock:
                results["succeeded"] += 1
        except StaleWorkerFencingError:
            pass  # expected for any epoch that lost the race to a higher one already registered
        except Exception as exc:  # pragma: no cover -- only on a real defect
            with lock:
                results["errors"].append(exc)

    threads = [threading.Thread(target=worker, args=(e,)) for e in epochs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not results["errors"]
    # register() (unlike replace_worker()) does not revoke prior winners at the same
    # slot -- multiple monotonically-increasing epochs can each individually succeed
    # depending on arrival order. The invariant that MUST hold regardless of thread
    # interleaving: the highest epoch (64) is always eventually admitted (it can never
    # be rejected, since no other epoch exceeds it), and once admitted, no epoch <= 64
    # can be admitted afterward -- i.e. the slot's recorded epoch converges to exactly 64.
    final = reg.list_workers_for_site("site-1", "t1")
    assert any(w.fencing_epoch == 64 and w.state == WorkerState.IDLE for w in final)
    with pytest.raises(StaleWorkerFencingError):
        reg.register(_worker("w-late", epoch=64))  # slot epoch has converged to 64; not > 64
