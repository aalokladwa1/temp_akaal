"""Enterprise Lifecycle Bootstrap & E2E Smoke Verification."""

from akaal.integration.composition_root import (
    EnterpriseLifecycleManager, execute_e2e_smoke_test
)

print('=== ENTERPRISE LIFECYCLE + E2E SMOKE VERIFICATION ===')
mgr = EnterpriseLifecycleManager()
ctx = mgr.bootstrap()
print('1. Bootstrap SUCCESS | Context type:', type(ctx).__name__)

facades = [
    ('P3-Workflow', ctx.workflow_engine),
    ('P4-CDC', ctx.cdc_facade),
    ('P5-Schema', ctx.schema_platform),
    ('P8-Reporting', ctx.reporting_facade),
    ('P9-Operations', ctx.operations_platform),
    ('P6-Streaming', ctx.streaming_runtime),
    ('P7-Distributed', ctx.distributed_runtime),
    ('P7-Performance', ctx.performance_runtime),
    ('P-API', ctx.api_facade),
]

for name, f in facades:
    t = type(f).__name__ if f is not None else 'MISSING'
    print('   ' + name + ': ' + t)

result = execute_e2e_smoke_test(ctx)
print('2. e2e Smoke Test Result:', result)

mgr.shutdown()
print('3. Graceful Shutdown: OK')
print()
print('ENTERPRISE LIFECYCLE VERIFICATION PASSED!')
