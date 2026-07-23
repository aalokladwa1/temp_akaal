"""
AKAAL Medium-Scale Migration — Step 2: Scout Discovery & Phase 9 Migration Intelligence.

Runs:
1. Scout Discovery against the 50-table PostgreSQL schema
2. Phase 9 Intelligence Pipeline (Scout -> Rulebook -> Decoder -> RiskScorer -> Planner -> Advisor)
"""

import sys
import os
import io
import asyncio
import json

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ['AKAAL_PG_USER'] = 'postgres'
os.environ['AKAAL_PG_PASSWORD'] = 'postgres'

from akaal.scout.api import discover
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType
from akaal.advisory.orchestrator import OrchestratorV1

async def run_scout_and_intelligence():
    print("=================================================================")
    print("      SCOUT DISCOVERY & PHASE 9 INTELLIGENCE PIPELINE")
    print("=================================================================\n")

    # 1. SCOUT DISCOVERY
    print("[1/2] Running Scout Discovery against 50-table PostgreSQL schema...")
    conn_cfg = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host='127.0.0.1',
        port=5432,
        database_name='postgres',
        credentials_ref='postgres:postgres',
        read_only=True,
        extra={},
    )

    scout_report = await discover(conn_cfg)
    stats = scout_report.statistics
    inv = scout_report.schema_inventory
    tables = inv.get('tables', [])

    print(f"  [OK] Scout Status:        {scout_report.health.overall_status}")
    print(f"  [OK] Discovered Tables:   {len(tables)}")
    print(f"  [OK] Discovered Columns:  {stats.total_columns}")
    print(f"  [OK] Discovered Indexes:  {stats.total_indexes}")
    print(f"  [OK] Foreign Keys:        {stats.total_foreign_keys}")
    print(f"  [OK] Discovery Duration:  {scout_report.performance.total_discovery_duration_ms:.1f} ms")

    # 2. PHASE 9 MIGRATION INTELLIGENCE PIPELINE
    print("\n[2/2] Running Phase 9 Migration Intelligence Pipeline across all column types...")
    orchestrator = OrchestratorV1()

    sample_types = [
        ('INTEGER', 'emp_id / dept_id'),
        ('BIGINT', 'order_id / item_id'),
        ('NUMERIC', 'salary / budget / total_amount'),
        ('VARCHAR', 'email / first_name / dept_code'),
        ('TEXT', 'notes / bio / log_msg'),
        ('UUID', 'ext_uuid / log_uuid'),
        ('BOOLEAN', 'is_active / is_vip'),
        ('DATE', 'hire_date / order_date'),
        ('TIMESTAMPTZ', 'created_at / placed_at'),
        ('BYTEA', 'avatar_blob / payload_blob')
    ]

    blocking_issues = []
    mapped_results = []

    for raw_t, ctx_desc in sample_types:
        r = orchestrator.run({'source_type': 'postgresql', 'raw_type': raw_t})
        status = r['final_status']
        stages = r.get('stages', {})
        decoded = stages.get('decoder', stages.get('decode', {}))
        target_t = decoded.get('target_type', decoded.get('mapped_type', 'N/A')) if isinstance(decoded, dict) else 'N/A'

        mapped_results.append({'source_type': raw_t, 'target_type': target_t, 'status': status, 'context': ctx_desc})
        if status != 'SUCCESS':
            blocking_issues.append(raw_t)
        print(f"  --> {raw_t:12s} ({ctx_desc:32s}) -> {target_t:16s} [{status}]")

    print("\n=================================================================")
    print("                PHASE 9 INTELLIGENCE SUMMARY")
    print("=================================================================")
    health_score = scout_report.health_assessment.get('overall_health_score', 100.0) if isinstance(scout_report.health_assessment, dict) else getattr(scout_report.health_assessment, 'overall_health_score', 100.0)
    print(f"  Scout Health Score:     {health_score:.1f}%")
    print(f"  Types Evaluated:        {len(sample_types)}")
    print(f"  Successful Mappings:    {sum(1 for m in mapped_results if m['status'] == 'SUCCESS')}")
    print(f"  Blocking Issues:        {len(blocking_issues)}")
    print("=================================================================\n")

    if blocking_issues:
        print("❌ PHASE 9 INTELLIGENCE PIPELINE FAILED: Blocking issues present.")
        sys.exit(1)
    else:
        print("✅ PHASE 9 INTELLIGENCE PIPELINE PASSED: Ready for execution.\n")

if __name__ == '__main__':
    asyncio.run(run_scout_and_intelligence())
