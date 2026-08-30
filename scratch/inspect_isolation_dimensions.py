"""
scratch/inspect_isolation_dimensions.py
=======================================
Detailed inspection of Cross-Migration (20) and Cross-Tenant (20) dimensions.
"""

import json
from pathlib import Path

REPORTS = Path("reports")

with open(REPORTS / "p512_cross_migration_isolation_matrix.json", "r", encoding="utf-8") as f:
    mig_matrix = json.load(f)

with open(REPORTS / "p512_tenant_isolation_matrix.json", "r", encoding="utf-8") as f:
    tenant_matrix = json.load(f)

mig_dims = mig_matrix.get("dimensions", [])
tenant_dims = tenant_matrix.get("dimensions", [])

print(f"Migration dimensions count: {len(mig_dims)}")
print(f"Tenant dimensions count:    {len(tenant_dims)}")
print(f"Total scenario rows:        {len(mig_dims) + len(tenant_dims)}")

# Extract names
mig_names = [d.get("isolation_dimension") or d.get("dimension") for d in mig_dims]
tenant_names = [d.get("isolation_dimension") or d.get("dimension") for d in tenant_dims]

print("\n--- Migration Dimensions (20) ---")
for idx, name in enumerate(mig_names, 1):
    print(f"  M{idx:02d}. {name}")

print("\n--- Tenant Dimensions (20) ---")
for idx, name in enumerate(tenant_names, 1):
    print(f"  T{idx:02d}. {name}")

unique_mig = set(mig_names)
unique_tenant = set(tenant_names)
all_unique = unique_mig | unique_tenant
shared = unique_mig & unique_tenant

print(f"\nUnique Migration names: {len(unique_mig)}")
print(f"Unique Tenant names:    {len(unique_tenant)}")
print(f"Total Unique Conceptual Dimension Names: {len(all_unique)}")
print(f"Shared Dimension Names between both: {len(shared)}")
print("\nShared Names:")
for s in sorted(shared):
    print(f"  - {s}")
