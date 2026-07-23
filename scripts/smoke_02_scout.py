"""AKAAL Smoke Migration — Step 2: Scout Discovery on PostgreSQL public schema."""
import asyncio, os
os.environ['AKAAL_PG_USER'] = 'postgres'
os.environ['AKAAL_PG_PASSWORD'] = 'postgres'

from akaal.scout.api import discover
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType

conn = ConnectionConfig(
    system_type=SystemType.POSTGRESQL,
    host='127.0.0.1',
    port=5432,
    database_name='postgres',
    credentials_ref='postgres:postgres',
    read_only=True,
    extra={},
)

async def run():
    print('=== SCOUT DISCOVERY ===')
    report = await discover(conn)
    s = report.statistics
    print(f'Health: {report.health.overall_status}  Errors: {report.health.error_count}')
    print(f'Tables: {s.total_tables}  Columns: {s.total_columns}  Indexes: {s.total_indexes}  FKs: {s.total_foreign_keys}')
    print(f'Discovery duration: {report.performance.total_discovery_duration_ms:.1f}ms')
    print()
    inv = report.schema_inventory
    print('Schemas:', inv.get('schemas', []))
    tables = inv.get('tables', [])
    print(f'Tables discovered: {len(tables)}')
    for t in tables:
        tname = t.table_name if hasattr(t, 'table_name') else t.get('table_name', '?')
        cols = t.columns if hasattr(t, 'columns') else t.get('columns', [])
        idxs = t.indexes if hasattr(t, 'indexes') else t.get('indexes', [])
        cons = t.constraints if hasattr(t, 'constraints') else t.get('constraints', [])
        print(f'  {tname}: {len(cols)} cols, {len(idxs)} indexes, {len(cons)} constraints')
    fks = inv.get('foreign_keys', [])
    print(f'Foreign Keys: {len(fks)}')
    for fk in fks:
        print(' ', fk)
    print()
    print('SCOUT DISCOVERY COMPLETE')
    return report

report = asyncio.run(run())
