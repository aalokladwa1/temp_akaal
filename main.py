"""
Akaal — Main Entrypoint
========================
Run a full end-to-end migration via unified Enterprise Lifecycle Manager bootstrap.

Usage:
    python main.py

Edit the config block below to point at your source and target databases.
"""

import asyncio
import logging
import sys
import os

# Make akaal importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

from akaal.integration.composition_root import EnterpriseLifecycleManager, execute_e2e_smoke_test
from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy


async def main():
    # ──────────────────────────────────────────────────────────────────
    # 1. UNIFIED ENTERPRISE BOOTSTRAP (Phase 12 Stage 1)
    # ──────────────────────────────────────────────────────────────────
    lifecycle_manager = EnterpriseLifecycleManager()
    context = lifecycle_manager.bootstrap()
    
    # Optional smoke test verification of all registered platforms & engines
    smoke_results = execute_e2e_smoke_test(context)
    logging.info("Unified Platform Bootstrap complete. E2E Smoke Summary: %s", smoke_results["e2e_summary"])

    # ──────────────────────────────────────────────────────────────────
    # 2. CONFIGURE YOUR MIGRATION HERE
    # ──────────────────────────────────────────────────────────────────
    source_config = ConnectionConfig(
        system_type=SystemType.ORACLE,
        host="oracle-prod.example.com",       # ← your source DB host
        port=1521,
        database_name="ORCL",
        credentials_ref="vault://oracle/prod",
        read_only=True,
    )

    target_config = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host="postgres-target.example.com",   # ← your target DB host
        port=5432,
        database_name="target_db",
        credentials_ref="vault://postgres/target",
        read_only=False,
    )

    config = MigrationConfig(
        source_config=source_config,
        target_config=target_config,
        strategy=MigrationStrategy.BIG_BANG,
        workspace_dir="./akaal_workspace",
        project_name="My Migration",
        auto_approve=True,                    # ← set False for manual approval gate
        ddl_schema_path=None,                 # ← set path to .sql DDL for pre-analysis
    )

    # ──────────────────────────────────────────────────────────────────
    # 3. RUN MIGRATION WORKFLOW
    # ──────────────────────────────────────────────────────────────────
    lifecycle_manager.mark_running()
    pipeline = AkaalPipeline()
    result = await pipeline.run(config)

    print("\n" + "=" * 70)
    print("  AKAAL MIGRATION RESULT")
    print("=" * 70)
    print(f"  Status:   {result['status'].upper()}")
    print(f"  Duration: {result['duration_seconds']}s")

    if result.get("advisory"):
        adv = result["advisory"]
        risk = adv.get("risk_summary", {})
        print(f"\n  Pre-Migration Analysis:")
        print(f"    Tables analyzed:  {adv.get('tables_analyzed', 0)}")
        print(f"    Columns scored:   {risk.get('total_columns_scored', 0)}")
        print(f"    Avg risk score:   {risk.get('average_score', 'N/A')}")
        print(f"    Overall risk:     {risk.get('overall_level', 'N/A')}")

    if result.get("migration"):
        mig = result["migration"]
        print(f"\n  Migration:")
        print(f"    Project ID: {mig.get('project_id', 'N/A')}")
        print(f"    Completed:  {mig.get('completed_at', 'N/A')}")

    print("=" * 70)

    # Graceful shutdown
    lifecycle_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
