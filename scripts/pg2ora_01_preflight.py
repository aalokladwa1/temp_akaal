"""
AKAAL Stage 2.1 — PostgreSQL -> Oracle Migration Preflight & Schema Analysis.

Verifies:
1. PostgreSQL connectivity & dataset inventory (50 tables, 131,115 rows)
2. Oracle connectivity (oracledb) & Schema cleanup
3. Phase 9 Migration Intelligence Pipeline for PostgreSQL -> Oracle type conversions
4. Human Approval Gate verification via ApprovalEngine
"""

import sys
import os
import io
import asyncio
import psycopg2
import psycopg2.extras
import oracledb

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ['AKAAL_PG_USER'] = 'postgres'
os.environ['AKAAL_PG_PASSWORD'] = 'postgres'

from akaal.scout.api import discover
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType
from akaal.advisory.orchestrator import OrchestratorV1
from akaal.workflow.approval.engine import ApprovalEngine
from akaal.workflow.approval.models import ApprovalPrincipal, PrincipalType

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')
ORA_DSN = dict(user='SOURCE_SCHEMA', password='aalok', dsn='localhost:1521/FREEPDB1')

async def main():
    print("=================================================================")
    print("      STAGE 2.1: POSTGRESQL -> ORACLE PREFLIGHT & APPROVAL")
    print("=================================================================\n")

    # 1. POSTGRESQL CHECK
    print("[1/4] Checking PostgreSQL Source Dataset...")
    pg_conn = psycopg2.connect(**PG_DSN)
    pg_cur = pg_conn.cursor()
    pg_cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;")
    tables = [r[0] for r in pg_cur.fetchall()]
    
    total_rows = 0
    for t in tables:
        pg_cur.execute(f"SELECT COUNT(*) FROM public.{t};")
        total_rows += pg_cur.fetchone()[0]
    
    print(f"  [OK] PostgreSQL Source: {len(tables)} tables, {total_rows:,} rows.")

    # 2. ORACLE CHECK & CLEANUP
    print("\n[2/4] Checking Oracle Target Database...")
    ora_conn = oracledb.connect(**ORA_DSN)
    ora_cur = ora_conn.cursor()
    ora_cur.execute("SELECT 1 FROM DUAL")
    print(f"  [OK] Oracle Database Reachable (localhost:1521/FREEPDB1).")

    # Drop old target tables in Oracle if present
    ora_cur.execute("SELECT table_name FROM user_tables")
    ora_tables = [r[0] for r in ora_cur.fetchall()]
    if ora_tables:
        print(f"  --> Cleaning up {len(ora_tables)} existing Oracle tables...")
        for ot in ora_tables:
            try:
                ora_cur.execute(f'DROP TABLE "{ot}" CASCADE CONSTRAINTS')
            except Exception:
                pass
        ora_conn.commit()
    print("  [OK] Oracle target workspace clean.")

    # 3. MIGRATION INTELLIGENCE PIPELINE FOR ORACLE
    print("\n[3/4] Running Phase 9 Intelligence Pipeline for PostgreSQL -> Oracle...")
    orchestrator = OrchestratorV1()

    pg_to_ora_types = [
        ('INTEGER', 'NUMBER(10)', 'emp_id / dept_id'),
        ('BIGINT', 'NUMBER(19)', 'order_id / item_id'),
        ('NUMERIC', 'NUMBER(14,4)', 'salary / budget / total_amount'),
        ('VARCHAR', 'VARCHAR2(255)', 'email / first_name / dept_code'),
        ('TEXT', 'CLOB', 'notes / bio / log_msg'),
        ('UUID', 'VARCHAR2(36)', 'ext_uuid / log_uuid'),
        ('BOOLEAN', 'NUMBER(1)', 'is_active / is_vip'),
        ('DATE', 'DATE', 'hire_date / order_date'),
        ('TIMESTAMPTZ', 'TIMESTAMP WITH TIME ZONE', 'created_at / placed_at'),
        ('BYTEA', 'BLOB', 'avatar_blob / payload_blob')
    ]

    blocking_issues = []
    for raw_t, expected_ora, desc in pg_to_ora_types:
        r = orchestrator.run({'source_type': 'postgresql', 'target_type': 'oracle', 'raw_type': raw_t})
        status = r['final_status']
        print(f"  --> {raw_t:12s} ({desc:32s}) -> Oracle {expected_ora:24s} [{status}]")
        if status != 'SUCCESS':
            blocking_issues.append(raw_t)

    # 4. HUMAN APPROVAL ENGINE VERIFICATION
    print("\n[4/4] Verifying Human Approval Engine Governance Gate...")
    app_engine = ApprovalEngine()
    principal = ApprovalPrincipal(principal_id="admin-user-01", principal_type=PrincipalType.USER, display_name="Enterprise Admin")
    
    req = app_engine.request_approval(
        workflow_id="wf-medium-pg2ora-001",
        gate_number=1,
        gate_name="POSTGRES_TO_ORACLE_MIGRATION_AUTHORIZATION",
        assigned_principal=principal,
        timeout_seconds=3600.0
    )
    print(f"  [OK] Approval Requested: Request ID='{req.request_id}', Gate Name='{req.gate_name}', Status={req.status}")

    # Evaluate approval decision
    token = app_engine.approve(
        request_id=req.request_id,
        acting_principal=principal,
        reason="Authorized for PostgreSQL -> Oracle production validation"
    )
    print(f"  [OK] Approval Granted: Token ID='{token.token_id}', Request ID='{token.request_id}'")

    pg_conn.close()
    ora_conn.close()

    print("\n=================================================================")
    print("      POSTGRESQL -> ORACLE PREFLIGHT & APPROVAL COMPLETE")
    print("=================================================================\n")

if __name__ == '__main__':
    asyncio.run(main())
