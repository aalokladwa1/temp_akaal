"""
scripts.benchmark_authorization_deep
====================================
Detailed, reproducible benchmark investigating:
1. Single-thread Uncached Full RBAC+Inheritance+Group+Scope+ABAC (DB-backed)
2. Single-thread Cached In-Memory L1 Decision (RAM lookup + monotonic rev check)
3. 2-Thread Concurrent In-Memory L1 Decision Throughput
4. 4-Thread Concurrent In-Memory L1 Decision Throughput
5. 8-Thread Concurrent In-Memory L1 Decision Throughput

Measures exact wall-clock time, GIL implications, per-thread latency, and throughput formula.
"""

import time
import threading
import concurrent.futures
import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import PrincipalType, PolicyEffect
from akaalPipeline.security.bootstrap import EnterpriseBootstrapCoordinator
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.identity.principals import PrincipalManager
from akaalPipeline.security.cache import AuthorizationCacheManager
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine, AuthorizationContext
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteCredentialRepository,
    SQLiteRoleRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleGrantRepository,
    SQLiteGroupRepository,
    SQLiteABACPolicyRepository,
    SQLiteTenantRepository,
    SQLiteWorkspaceRepository,
)
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


def run_auth_benchmarks():
    print("=" * 80)
    print("REPRODUCIBLE AUTHORIZATION BENCHMARK & THROUGHPUT RECONCILIATION")
    print("=" * 80)

    uow = SQLiteUnitOfWork(db_path=":memory:")
    bootstrapper = EnterpriseBootstrapCoordinator(uow)
    boot = bootstrapper.bootstrap("tenant-bench", "Enterprise Admin", "admin@corp.internal", "SecurePass123!")
    admin_id = boot["admin_principal_id"]

    conn = uow.conn
    principal_repo = SQLitePrincipalRepository(conn)
    credential_repo = SQLiteCredentialRepository(conn)
    tenant_repo = SQLiteTenantRepository(conn)
    role_repo = SQLiteRoleRepository(conn)
    role_perm_repo = SQLiteRolePermissionRepository(conn)
    role_grant_repo = SQLiteRoleGrantRepository(conn)
    group_repo = SQLiteGroupRepository(conn)
    abac_repo = SQLiteABACPolicyRepository(conn)

    config = SecurityBaselineConfig()
    cache_mgr = AuthorizationCacheManager()

    group_auth = GroupAuthority(group_repo, principal_repo)
    rbac_auth = RBACAuthority(role_repo, role_perm_repo, role_grant_repo)
    abac_auth = ABACAuthority(abac_repo)

    central_auth = CentralAuthorizationEngine(
        principal_repo=principal_repo,
        tenant_repo=tenant_repo,
        group_authority=group_auth,
        rbac_authority=rbac_auth,
        abac_authority=abac_auth,
        cache_manager=cache_mgr,
    )
    principal_mgr = PrincipalManager(principal_repo, credential_repo, config)

    # Create test principal
    p1 = principal_mgr.create_principal("tenant-bench", "engineer_alice", PrincipalType.HUMAN, password="AlicePassword123!")
    p1_id = p1["principal_id"]

    # Role Hierarchy: Operator -> SeniorOperator -> LeadOperator
    role_repo.create_role("role-op", "tenant-bench", "Operator")
    role_repo.create_role("role-sr-op", "tenant-bench", "SeniorOperator", parent_role_id="role-op")
    role_repo.create_role("role-lead-op", "tenant-bench", "LeadOperator", parent_role_id="role-sr-op")

    role_perm_repo.add_permission("tenant-bench", "role-op", PermissionRegistry.MIGRATION_READ)
    role_perm_repo.add_permission("tenant-bench", "role-sr-op", PermissionRegistry.MIGRATION_PLAN)
    role_perm_repo.add_permission("tenant-bench", "role-lead-op", PermissionRegistry.MIGRATION_EXECUTE)

    # Group
    grp_id = group_auth.create_group("tenant-bench", "grp-engineers", "Engineering Group")
    group_auth.add_member("tenant-bench", grp_id, p1_id)

    # Workspace
    workspace_repo = SQLiteWorkspaceRepository(conn)
    workspace_repo.create("tenant-bench", "ws-01", "Workspace 1", created_at=TimeAuthority.utc_iso_now())

    # Role grant to Group with Resource Scope (WORKSPACE ws-01)
    role_grant_repo.create_grant(
        grant_id="grant-grp-01",
        tenant_id="tenant-bench",
        subject_type="GROUP",
        subject_id=grp_id,
        role_id="role-lead-op",
        resource_type="WORKSPACE",
        resource_id="ws-01",
        granted_by=admin_id,
        granted_at=TimeAuthority.utc_iso_now(),
    )

    # ABAC Policy: ALLOW migration.execute only if environment == 'production' or classification == 'standard'
    abac_repo.create_policy(
        tenant_id="tenant-bench",
        policy_id="abac-pol-01",
        name="Allow Standard Execution",
        effect=PolicyEffect.ALLOW.value,
        target_action=PermissionRegistry.MIGRATION_EXECUTE,
        target_resource_type="WORKSPACE",
        condition_expression={"equals": {"resource.classification": "standard"}},
    )

    auth_ctx = AuthorizationContext(
        tenant_id="tenant-bench",
        principal_id=p1_id,
        action=PermissionRegistry.MIGRATION_EXECUTE,
        resource_type="WORKSPACE",
        resource_id="ws-01",
    )
    extra_abac = {"resource": {"classification": "standard", "type": "WORKSPACE", "id": "ws-01", "tenant_id": "tenant-bench"}}

    # 1. Warm-up
    central_auth.authorize(actor_context=auth_ctx, permission_id=PermissionRegistry.MIGRATION_EXECUTE, resource_type="WORKSPACE", resource_id="ws-01", extra_abac_context=extra_abac, raise_exceptions=False)

    # 2. Benchmark Single-Thread Uncached (DB-backed full decision)
    uncached_latencies_us = []
    uncached_ops = 500
    t0_uncached = time.perf_counter()
    for _ in range(uncached_ops):
        cache_mgr.clear()
        t_start = time.perf_counter_ns()
        central_auth.authorize(
            actor_context=auth_ctx,
            permission_id=PermissionRegistry.MIGRATION_EXECUTE,
            resource_type="WORKSPACE",
            resource_id="ws-01",
            extra_abac_context=extra_abac,
            raise_exceptions=False,
        )
        t_end = time.perf_counter_ns()
        uncached_latencies_us.append((t_end - t_start) / 1000.0)
    t1_uncached = time.perf_counter()
    elapsed_uncached = t1_uncached - t0_uncached
    uncached_latencies_us.sort()
    p50_uncached = uncached_latencies_us[int(len(uncached_latencies_us) * 0.50)]
    p95_uncached = uncached_latencies_us[int(len(uncached_latencies_us) * 0.95)]
    p99_uncached = uncached_latencies_us[int(len(uncached_latencies_us) * 0.99)]
    tps_uncached = uncached_ops / elapsed_uncached

    print(f"[1] Uncached DB-Backed Full Decision (1 Thread):")
    print(f"    - Operations: {uncached_ops} | Wall-clock: {elapsed_uncached:.4f}s")
    print(f"    - Latency: p50={p50_uncached:.1f}us, p95={p95_uncached:.1f}us, p99={p99_uncached:.1f}us")
    print(f"    - Measured Throughput: {tps_uncached:,.0f} ops/s")

    # 3. Benchmark Single-Thread Cached In-Memory L1 Decision
    cache_mgr.clear()
    auth_ctx_simple = AuthorizationContext(
        tenant_id="tenant-bench",
        principal_id=p1_id,
        action=PermissionRegistry.MIGRATION_READ,
        resource_type="WORKSPACE",
        resource_id="ws-01",
    )
    central_auth.authorize(actor_context=auth_ctx_simple, raise_exceptions=False)

    cached_latencies_us = []
    cached_ops = 5000
    t0_cached = time.perf_counter()
    for _ in range(cached_ops):
        t_start = time.perf_counter_ns()
        central_auth.authorize(actor_context=auth_ctx_simple, raise_exceptions=False)
        t_end = time.perf_counter_ns()
        cached_latencies_us.append((t_end - t_start) / 1000.0)
    t1_cached = time.perf_counter()
    elapsed_cached = t1_cached - t0_cached
    cached_latencies_us.sort()
    p50_cached = cached_latencies_us[int(len(cached_latencies_us) * 0.50)]
    p95_cached = cached_latencies_us[int(len(cached_latencies_us) * 0.95)]
    p99_cached = cached_latencies_us[int(len(cached_latencies_us) * 0.99)]
    tps_cached = cached_ops / elapsed_cached

    print(f"\n[2] Cached In-Memory L1 Decision (1 Thread):")
    print(f"    - Operations: {cached_ops} | Wall-clock: {elapsed_cached:.4f}s")
    print(f"    - Latency: p50={p50_cached:.1f}us, p95={p95_cached:.1f}us, p99={p99_cached:.1f}us")
    print(f"    - Measured Throughput: {tps_cached:,.0f} ops/s")

    # 4. Multithreaded In-Memory L1 Cache Throughput Tests
    thread_counts = [2, 4, 8]
    concurrent_results = {}

    for num_threads in thread_counts:
        ops_per_thread = 5000
        total_ops = ops_per_thread * num_threads

        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(lambda: [central_auth.authorize(actor_context=auth_ctx_simple, raise_exceptions=False) for _ in range(ops_per_thread)])
                for _ in range(num_threads)
            ]
            concurrent.futures.wait(futures)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        throughput = total_ops / elapsed
        concurrent_results[f"{num_threads}_threads"] = {
            "num_threads": num_threads,
            "total_ops": total_ops,
            "elapsed_seconds": elapsed,
            "throughput_ops_sec": throughput,
        }
        print(f"\n[3] Cached In-Memory L1 Decision ({num_threads} Threads):")
        print(f"    - Total Operations: {total_ops:,} ({ops_per_thread:,}/thread) | Wall-clock: {elapsed:.4f}s")
        print(f"    - Aggregate Measured Throughput: {throughput:,.0f} ops/s")

    out_data = {
        "uncached_1_thread": {"p50_us": p50_uncached, "p95_us": p95_uncached, "p99_us": p99_uncached, "tps": tps_uncached},
        "cached_1_thread": {"p50_us": p50_cached, "p95_us": p95_cached, "p99_us": p99_cached, "tps": tps_cached},
        "concurrent_cached": concurrent_results,
    }

    with open("reports/auth_deep_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print("\nSaved deep benchmark results to reports/auth_deep_benchmark.json")

if __name__ == "__main__":
    run_auth_benchmarks()
