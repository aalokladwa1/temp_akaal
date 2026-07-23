"""
AKAAL Smoke Migration — Step 3: Migration Intelligence Pipeline.
Runs: Scout → Rulebook → Decoder → RiskScorer → Planner → Advisor
"""
import os
os.environ['AKAAL_PG_USER'] = 'postgres'
os.environ['AKAAL_PG_PASSWORD'] = 'postgres'

from akaal.advisory.orchestrator import OrchestratorV1

# Tables and their representative column types discovered by Scout
source_objects = [
    # customers
    {'source_type': 'postgresql', 'raw_type': 'INTEGER',                  'context': 'customers.customer_id (PK)'},
    {'source_type': 'postgresql', 'raw_type': 'UUID',                     'context': 'customers.ext_uuid'},
    {'source_type': 'postgresql', 'raw_type': 'CHARACTER VARYING',        'context': 'customers.first_name'},
    {'source_type': 'postgresql', 'raw_type': 'TEXT',                     'context': 'customers.notes'},
    {'source_type': 'postgresql', 'raw_type': 'BOOLEAN',                  'context': 'customers.is_active'},
    {'source_type': 'postgresql', 'raw_type': 'NUMERIC',                  'context': 'customers.credit_limit'},
    {'source_type': 'postgresql', 'raw_type': 'TIMESTAMP WITH TIME ZONE', 'context': 'customers.created_at'},
    # products
    {'source_type': 'postgresql', 'raw_type': 'INTEGER',                  'context': 'products.stock_qty'},
    {'source_type': 'postgresql', 'raw_type': 'NUMERIC',                  'context': 'products.unit_price'},
    # orders
    {'source_type': 'postgresql', 'raw_type': 'BIGINT',                   'context': 'orders.order_id (PK)'},
    {'source_type': 'postgresql', 'raw_type': 'DATE',                     'context': 'orders.order_date'},
    {'source_type': 'postgresql', 'raw_type': 'CHARACTER',                'context': 'orders.currency'},
    # order_items
    {'source_type': 'postgresql', 'raw_type': 'NUMERIC',                  'context': 'order_items.discount_pct'},
    {'source_type': 'postgresql', 'raw_type': 'INTEGER',                  'context': 'order_items.quantity'},
]

print('=== MIGRATION INTELLIGENCE PIPELINE ===')
orchestrator = OrchestratorV1()

results = []
warnings = []
blocking_issues = []

for obj in source_objects:
    r = orchestrator.run({'source_type': obj['source_type'], 'raw_type': obj['raw_type']})
    status = r['final_status']
    results.append({'context': obj['context'], 'raw_type': obj['raw_type'], 'status': status, 'result': r})
    if status != 'SUCCESS':
        blocking_issues.append(obj['context'])
    else:
        # Check for any warnings in the pipeline stages
        stages = r.get('stages', {})
        for stage_name, stage_data in stages.items():
            if isinstance(stage_data, dict) and stage_data.get('warnings'):
                warnings.extend(stage_data['warnings'])

print(f'Objects analyzed: {len(source_objects)}')
print(f'Successful: {sum(1 for r in results if r["status"] == "SUCCESS")}')
print(f'Warnings: {len(warnings)}')
print(f'Blocking Issues: {len(blocking_issues)}')
print()

print('Type Mapping Results:')
for r in results:
    stages = r['result'].get('stages', {})
    decoded = stages.get('decoder', stages.get('decode', {}))
    target_type = 'N/A'
    if isinstance(decoded, dict):
        target_type = decoded.get('target_type', decoded.get('mapped_type', 'N/A'))
    print(f'  {r["context"]}: {r["raw_type"]} → {target_type} [{r["status"]}]')

if blocking_issues:
    print()
    print('BLOCKING ISSUES:', blocking_issues)
    print('MIGRATION INTELLIGENCE: FAILED - Cannot proceed')
else:
    if warnings:
        print('WARNINGS (non-blocking):', warnings[:3])
    print()
    print('MIGRATION INTELLIGENCE: PASSED - No blocking issues')
    print('Migration plan approved for execution')
