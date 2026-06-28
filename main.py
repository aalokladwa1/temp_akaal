"""
Akaal — Main Entrypoint
========================
Run a full end-to-end migration.

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

from akaal.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy


async def main():
    # ──────────────────────────────────────────────────────────────────
    # CONFIGURE YOUR MIGRATION HERE
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
    # RUN
    # ──────────────────────────────────────────────────────────────────

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


if __name__ == "__main__":
    asyncio.run(main())
