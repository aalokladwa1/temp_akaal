import { WorkstationViewModel } from './validation-workstation.models';

export const FIXTURE_NOT_CONNECTED: WorkstationViewModel = {
  validationId: 'VAL-2026-0089',
  validationName: 'Production Data Verification Mission',
  environment: 'Enterprise Staging',
  activeTab: 'overview',
  executionState: 'NOT_CONNECTED',
  verdict: 'NOT_EVALUATED',
  source: {
    provider: 'PostgreSQL 16',
    label: 'Primary Operational Cluster',
    host: 'pg-prod-01.internal:5432/core'
  },
  target: {
    provider: 'ClickHouse 24.3',
    label: 'Analytics Warehouse Replica',
    host: 'ch-dw-01.internal:8123/default'
  },
  donut: {
    mode: 'NOT_CONNECTED',
    centerPercentage: null,
    centerLabel: 'Comparison State Unavailable',
    centerSubtext: 'Awaiting Canonical Engine Link',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: null,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: null
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Pending canonical validation engine link. No schema comparison run.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Pending canonical validation engine link. Volumetric counts not evaluated.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Pending canonical validation engine link. Partition hash trees not computed.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Pending canonical validation engine link. Deep scalar comparisons deferred.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: null,
      evaluated: null,
      remaining: null,
      differencesDetected: null,
      inconclusive: null
    },
    {
      dimension: 'Records',
      inScope: null,
      evaluated: null,
      remaining: null,
      differencesDetected: null,
      inconclusive: null
    },
    {
      dimension: 'Attributes',
      inScope: null,
      evaluated: null,
      remaining: null,
      differencesDetected: null,
      inconclusive: null
    }
  ],
  semanticContext: {
    samplingPolicy: 'Full Scope (100% Non-Sampled)',
    tolerance: 'Strict 0-diff (No Divergence Allowed)',
    concurrency: '8 Parallel Partition Workers',
    failureThreshold: 'Fail-fast on Unrecoverable Protocol Error'
  },
  attentionItems: [],
  remediation: {
    baselineStatus: 'NOT_AVAILABLE',
    autoRepairPolicy: 'Manual Governed Approval Required',
    revalidationCount: 0
  },
  technicalDrawer: {
    canonicalValidationId: 'VAL-2026-0089',
    draftId: 'DFT-VAL-8821',
    enginePlacement: 'Local Validation Daemon (Pending Link)',
    engineVersion: 'v0.9.4-m8-validation',
    workerCount: null,
    maxMemoryLimit: '16.0 GiB Dedicated',
    capabilities: [
      'Structural Schema Introspection',
      'Bounded Cardinality Counting',
      'Partition Tree Hash Comparison',
      'Scalar Attribute Verification',
      'Immutable Evidence Bundle Signing'
    ]
  },
  isProductionDefault: true,
  drawerOpen: false
};

export const FIXTURE_RUNNING_CLEAN: WorkstationViewModel = {
  ...FIXTURE_NOT_CONNECTED,
  isProductionDefault: false,
  executionState: 'RUNNING',
  verdict: 'NOT_EVALUATED',
  elapsedFormatted: '01m 42s',
  throughputFormatted: '248,500 rec/s',
  etaFormatted: '~45s remaining',
  activeWorkers: 8,
  checkpointsCount: 14,
  donut: {
    mode: 'INDEPENDENT_VALIDATION',
    centerPercentage: 68,
    centerLabel: '68% Evaluated',
    centerSubtext: '12.4M / 18.2M Records',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: 42,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: 42
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'PASSED',
      evaluatedCount: 42,
      totalCount: 42,
      discrepancyCount: 0,
      details: '42 of 42 tables inspected. Schema definitions, types, and primary key signatures match perfectly.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'PASSED',
      evaluatedCount: 12400000,
      totalCount: 18200000,
      discrepancyCount: 0,
      details: '12.4M records evaluated so far. Total row volume matches across active partition boundaries.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'EVALUATING',
      evaluatedCount: 44,
      totalCount: 64,
      discrepancyCount: 0,
      details: '44 of 64 partition tree hashes verified. Zero hash mismatches detected in verified partitions.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'EVALUATING',
      evaluatedCount: 12400000,
      totalCount: 18200000,
      discrepancyCount: 0,
      details: 'In-flight streaming scalar evaluation across 340 columns. 0 discrepancies found.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: 42,
      evaluated: 42,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Records',
      inScope: 18200000,
      evaluated: 12400000,
      remaining: 5800000,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Attributes',
      inScope: 340,
      evaluated: 340,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    }
  ],
  attentionItems: [],
  technicalDrawer: {
    ...FIXTURE_NOT_CONNECTED.technicalDrawer,
    workerCount: 8,
    evidenceUri: 'file:///var/akaal/evidence/VAL-2026-0089/stream.tmp'
  }
};

export const FIXTURE_RUNNING_DIFFS: WorkstationViewModel = {
  ...FIXTURE_NOT_CONNECTED,
  isProductionDefault: false,
  executionState: 'RUNNING',
  verdict: 'NOT_EVALUATED',
  elapsedFormatted: '02m 15s',
  throughputFormatted: '195,000 rec/s',
  etaFormatted: '~1m 10s remaining',
  activeWorkers: 8,
  checkpointsCount: 18,
  donut: {
    mode: 'INDEPENDENT_VALIDATION',
    centerPercentage: 42,
    centerLabel: '42% Evaluated',
    centerSubtext: '18 Discrepancies Flagged',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: 42,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: 42
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'PASSED',
      evaluatedCount: 42,
      totalCount: 42,
      discrepancyCount: 0,
      details: '42 of 42 tables matched structurally.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'FAILED',
      evaluatedCount: 7600000,
      totalCount: 18200000,
      discrepancyCount: 14,
      details: '14 rows missing in target table `public.orders` in partition range 2026-Q1.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'FAILED',
      evaluatedCount: 27,
      totalCount: 64,
      discrepancyCount: 2,
      details: '2 partition chunk hash mismatches isolated in chunk #12 and chunk #19.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'EVALUATING',
      evaluatedCount: 7600000,
      totalCount: 18200000,
      discrepancyCount: 4,
      details: '4 divergent attribute values identified in `customer_accounts.balance_cents`.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: 42,
      evaluated: 42,
      remaining: 0,
      differencesDetected: 1,
      inconclusive: 0
    },
    {
      dimension: 'Records',
      inScope: 18200000,
      evaluated: 7600000,
      remaining: 10600000,
      differencesDetected: 18,
      inconclusive: 0
    },
    {
      dimension: 'Attributes',
      inScope: 340,
      evaluated: 340,
      remaining: 0,
      differencesDetected: 4,
      inconclusive: 0
    }
  ],
  attentionItems: [
    {
      id: 'ATTN-001',
      severity: 'blocker',
      category: 'missing_target',
      title: '14 Missing Rows in Target Endpoint',
      description: 'Target table `public.orders` is missing 14 rows identified in source partition `p2026_01`. Primary keys: [884102..884115].',
      location: 'public.orders (partition p2026_01)'
    },
    {
      id: 'ATTN-002',
      severity: 'warning',
      category: 'difference',
      title: '4 Divergent Scalar Values in Customer Balances',
      description: 'Attribute `balance_cents` differs between source and target for accounts [10921, 10924, 11045, 11088].',
      location: 'public.customer_accounts.balance_cents'
    }
  ],
  remediation: {
    linkedMigrationId: 'MIG-2026-0042',
    linkedMigrationName: 'Core PostgreSQL to ClickHouse Pipeline',
    baselineId: 'BSL-9981-FROZEN',
    baselineHash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    baselineStatus: 'VALID',
    autoRepairPolicy: 'Manual Governed Approval Required',
    revalidationCount: 1,
    lastRevalidationTimestamp: '2026-09-07T10:14:00Z'
  },
  technicalDrawer: {
    ...FIXTURE_NOT_CONNECTED.technicalDrawer,
    workerCount: 8,
    evidenceUri: 'file:///var/akaal/evidence/VAL-2026-0089/stream.tmp'
  }
};

export const FIXTURE_PASSED: WorkstationViewModel = {
  ...FIXTURE_NOT_CONNECTED,
  isProductionDefault: false,
  executionState: 'COMPLETED',
  verdict: 'PASSED',
  elapsedFormatted: '02m 44s',
  throughputFormatted: '221,950 rec/s avg',
  etaFormatted: 'Completed in 2m 44s',
  activeWorkers: 0,
  checkpointsCount: 22,
  donut: {
    mode: 'MIGRATION_SYNC',
    canonicalComparisonMode: 'SYNC',
    centerPercentage: 100,
    centerLabel: 'SYNC',
    centerSubtext: '18.2M Records Matched',
    centerSecondaryText: 'Comparison Complete',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: 42,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: 42
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'PASSED',
      evaluatedCount: 42,
      totalCount: 42,
      discrepancyCount: 0,
      details: 'All 42 tables structurally identical. Schemas, datatypes, and constraints verified.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'PASSED',
      evaluatedCount: 18200000,
      totalCount: 18200000,
      discrepancyCount: 0,
      details: '18,200,000 of 18,200,000 records matched. Volumetric parity confirmed across all partitions.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'PASSED',
      evaluatedCount: 64,
      totalCount: 64,
      discrepancyCount: 0,
      details: 'All 64 partition tree hashes match deterministically across endpoints.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'PASSED',
      evaluatedCount: 18200000,
      totalCount: 18200000,
      discrepancyCount: 0,
      details: 'Deep scalar equality verified across 340 columns. Zero divergence found.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: 42,
      evaluated: 42,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Records',
      inScope: 18200000,
      evaluated: 18200000,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Attributes',
      inScope: 340,
      evaluated: 340,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    }
  ],
  attentionItems: [],
  remediation: {
    linkedMigrationId: 'MIG-2026-0042',
    linkedMigrationName: 'Core PostgreSQL to ClickHouse Pipeline',
    baselineId: 'BSL-9981-FROZEN',
    baselineHash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    baselineStatus: 'VALID',
    autoRepairPolicy: 'Manual Governed Approval Required',
    revalidationCount: 0
  },
  technicalDrawer: {
    ...FIXTURE_NOT_CONNECTED.technicalDrawer,
    workerCount: 8,
    evidenceHash: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    signingKeyId: 'KEY-ED25519-PROD-2026-A',
    evidenceUri: 'file:///var/akaal/evidence/VAL-2026-0089/evidence.aev'
  }
};

export const FIXTURE_FAILED: WorkstationViewModel = {
  ...FIXTURE_NOT_CONNECTED,
  isProductionDefault: false,
  executionState: 'COMPLETED',
  verdict: 'FAILED',
  elapsedFormatted: '03m 05s',
  throughputFormatted: '198,200 rec/s avg',
  etaFormatted: 'Completed with Failures',
  activeWorkers: 0,
  checkpointsCount: 22,
  donut: {
    mode: 'MIGRATION_SYNC',
    canonicalComparisonMode: 'SYNC',
    centerPercentage: 100,
    centerLabel: 'SYNC',
    centerSubtext: 'Discrepancies Confirmed',
    centerSecondaryText: 'Comparison Complete',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: 42,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: 42
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'PASSED',
      evaluatedCount: 42,
      totalCount: 42,
      discrepancyCount: 0,
      details: 'All 42 tables matched structurally.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'FAILED',
      evaluatedCount: 18200000,
      totalCount: 18200000,
      discrepancyCount: 14,
      details: '14 rows missing in target table `public.orders`.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'FAILED',
      evaluatedCount: 64,
      totalCount: 64,
      discrepancyCount: 2,
      details: '2 partition chunk hash mismatches detected in chunks #12 and #19.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'FAILED',
      evaluatedCount: 18200000,
      totalCount: 18200000,
      discrepancyCount: 4,
      details: '4 divergent attribute values identified in `customer_accounts.balance_cents`.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: 42,
      evaluated: 42,
      remaining: 0,
      differencesDetected: 1,
      inconclusive: 0
    },
    {
      dimension: 'Records',
      inScope: 18200000,
      evaluated: 18200000,
      remaining: 0,
      differencesDetected: 18,
      inconclusive: 0
    },
    {
      dimension: 'Attributes',
      inScope: 340,
      evaluated: 340,
      remaining: 0,
      differencesDetected: 4,
      inconclusive: 0
    }
  ],
  attentionItems: [
    {
      id: 'ATTN-001',
      severity: 'blocker',
      category: 'missing_target',
      title: '14 Missing Rows in Target Endpoint',
      description: 'Target table `public.orders` is missing 14 rows identified in source partition `p2026_01`. Primary keys: [884102..884115].',
      location: 'public.orders (partition p2026_01)'
    },
    {
      id: 'ATTN-002',
      severity: 'warning',
      category: 'difference',
      title: '4 Divergent Scalar Values in Customer Balances',
      description: 'Attribute `balance_cents` differs between source and target for accounts [10921, 10924, 11045, 11088].',
      location: 'public.customer_accounts.balance_cents'
    }
  ],
  remediation: {
    linkedMigrationId: 'MIG-2026-0042',
    linkedMigrationName: 'Core PostgreSQL to ClickHouse Pipeline',
    baselineId: 'BSL-9981-FROZEN',
    baselineHash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    baselineStatus: 'VALID',
    autoRepairPolicy: 'Manual Governed Approval Required',
    revalidationCount: 1,
    lastRevalidationTimestamp: '2026-09-07T10:14:00Z'
  },
  technicalDrawer: {
    ...FIXTURE_NOT_CONNECTED.technicalDrawer,
    workerCount: 8,
    evidenceHash: 'sha256:bb12c84298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b999',
    signingKeyId: 'KEY-ED25519-PROD-2026-A',
    evidenceUri: 'file:///var/akaal/evidence/VAL-2026-0089/discrepancies.aev'
  }
};

export const FIXTURE_INTERRUPTED: WorkstationViewModel = {
  ...FIXTURE_NOT_CONNECTED,
  isProductionDefault: false,
  executionState: 'INTERRUPTED',
  verdict: 'WITHHELD',
  elapsedFormatted: '00m 52s',
  throughputFormatted: '0 rec/s (interrupted)',
  etaFormatted: 'Interrupted by Operator',
  activeWorkers: 0,
  checkpointsCount: 6,
  donut: {
    mode: 'INDEPENDENT_VALIDATION',
    centerPercentage: 31,
    centerLabel: '31% Evaluated',
    centerSubtext: 'Execution Interrupted',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: 42,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: 42
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'PASSED',
      evaluatedCount: 42,
      totalCount: 42,
      discrepancyCount: 0,
      details: 'Structural inspection completed prior to interruption.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'NOT_EVALUATED',
      evaluatedCount: 5640000,
      totalCount: 18200000,
      discrepancyCount: null,
      details: 'Cardinality counting halted at checkpoint 6.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'SKIPPED',
      evaluatedCount: 0,
      totalCount: 64,
      discrepancyCount: null,
      details: 'Partition hashing not started before interruption.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'SKIPPED',
      evaluatedCount: 0,
      totalCount: 18200000,
      discrepancyCount: null,
      details: 'Deep scalar comparison skipped due to interruption.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: 42,
      evaluated: 42,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Records',
      inScope: 18200000,
      evaluated: 5640000,
      remaining: 12560000,
      differencesDetected: 0,
      inconclusive: 12560000
    },
    {
      dimension: 'Attributes',
      inScope: 340,
      evaluated: 105,
      remaining: 235,
      differencesDetected: 0,
      inconclusive: 235
    }
  ],
  attentionItems: [
    {
      id: 'ATTN-INT-1',
      severity: 'warning',
      category: 'difference',
      title: 'Validation Execution Interrupted',
      description: 'Worker pool received SIGINT from operator console. Evaluation halted cleanly at checkpoint 6 with no state corruption.',
      location: 'Engine Worker Orchestrator'
    }
  ],
  technicalDrawer: {
    ...FIXTURE_NOT_CONNECTED.technicalDrawer,
    workerCount: 0
  }
};

export const FIXTURE_BLOCKED: WorkstationViewModel = {
  ...FIXTURE_NOT_CONNECTED,
  isProductionDefault: false,
  executionState: 'BLOCKED',
  verdict: 'NOT_EVALUATED',
  elapsedFormatted: undefined,
  throughputFormatted: undefined,
  etaFormatted: 'Execution Blocked',
  activeWorkers: 0,
  donut: {
    mode: 'NOT_CONNECTED',
    centerPercentage: null,
    centerLabel: 'Execution Blocked',
    centerSubtext: 'Correspondence Map Missing',
    sourceLabel: 'PostgreSQL 16',
    sourceType: 'Source System',
    sourceHost: 'pg-prod-01.internal:5432/core',
    sourceObjectCount: 42,
    targetLabel: 'ClickHouse 24.3',
    targetType: 'Target System',
    targetHost: 'ch-dw-01.internal:8123/default',
    targetObjectCount: 38
  },
  proofTiers: [
    {
      id: 'structural',
      name: 'Structural Assurance',
      tierNumber: 1,
      description: 'Verifies table structures, column datatypes, nullability, constraints, and indexes across endpoints.',
      status: 'FAILED',
      evaluatedCount: 38,
      totalCount: 42,
      discrepancyCount: 4,
      details: '4 source tables lack target endpoint mapping in correspondence config.'
    },
    {
      id: 'cardinality',
      name: 'Cardinality Assurance',
      tierNumber: 2,
      description: 'Executes exact and partitioned row counts with boundary filters to verify volumetric equality.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Blocked by correspondence mapping failure.'
    },
    {
      id: 'partition',
      name: 'Partition Fingerprint',
      tierNumber: 3,
      description: 'Computes cryptographic hash trees across deterministic row chunks to localize divergent regions.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Blocked by correspondence mapping failure.',
      note: 'Hostile XOR Defect Guard: Does not claim multiset equality or cryptographic parity.'
    },
    {
      id: 'attribute',
      name: 'Complete Attribute Assurance',
      tierNumber: 4,
      description: 'Performs cell-by-cell scalar comparison across all columns within divergent partition ranges.',
      status: 'NOT_EVALUATED',
      evaluatedCount: null,
      totalCount: null,
      discrepancyCount: null,
      details: 'Blocked by correspondence mapping failure.'
    }
  ],
  coverage: [
    {
      dimension: 'Objects',
      inScope: 42,
      evaluated: 38,
      remaining: 4,
      differencesDetected: 4,
      inconclusive: 4
    },
    {
      dimension: 'Records',
      inScope: null,
      evaluated: null,
      remaining: null,
      differencesDetected: null,
      inconclusive: null
    },
    {
      dimension: 'Attributes',
      inScope: null,
      evaluated: null,
      remaining: null,
      differencesDetected: null,
      inconclusive: null
    }
  ],
  attentionItems: [
    {
      id: 'ATTN-BLK-1',
      severity: 'blocker',
      category: 'correspondence',
      title: 'Target Endpoint Mapping Missing for 4 Tables',
      description: 'Correspondence configuration is incomplete: tables [orders_archive, audit_logs, session_tokens, temp_queue] have no defined target destination.',
      location: 'Correspondence Configuration Map'
    }
  ],
  technicalDrawer: {
    ...FIXTURE_NOT_CONNECTED.technicalDrawer,
    workerCount: 0
  }
};

export const FIXTURE_LARGE_ENTERPRISE: WorkstationViewModel = {
  ...FIXTURE_PASSED,
  validationId: 'VAL-2026-GLOBAL-CORP',
  validationName: 'Global Multi-Region Financial Ledger Reconciliation',
  environment: 'Global Production (PCI/SOC-2)',
  throughputFormatted: '4,850,000 rec/s avg',
  activeWorkers: 64,
  checkpointsCount: 1420,
  donut: {
    mode: 'INDEPENDENT_VALIDATION',
    centerPercentage: 100,
    centerLabel: '100% Verified',
    centerSubtext: '2.45B Records Matched',
    sourceLabel: 'Oracle Exadata X9M',
    sourceType: 'Primary Core Banking',
    sourceHost: 'exa-dr-cluster.ny4.internal:1521/FINCORE',
    sourceObjectCount: 1280,
    targetLabel: 'Snowflake Enterprise',
    targetType: 'Analytics Lakehouse',
    targetHost: 'akaal_prod.us-east-1.snowflakecomputing.com',
    targetObjectCount: 1280
  },
  coverage: [
    {
      dimension: 'Objects',
      inScope: 1280,
      evaluated: 1280,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Records',
      inScope: 2450000000,
      evaluated: 2450000000,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    },
    {
      dimension: 'Attributes',
      inScope: 14500,
      evaluated: 14500,
      remaining: 0,
      differencesDetected: 0,
      inconclusive: 0
    }
  ]
};

export const FIXTURE_COMPLETED_PASSED_SYNC: WorkstationViewModel = {
  ...FIXTURE_PASSED,
  donut: {
    ...FIXTURE_PASSED.donut,
    mode: 'MIGRATION_SYNC',
    canonicalComparisonMode: 'SYNC',
    centerLabel: 'SYNC',
    centerSubtext: '18.2M Records Matched',
    centerSecondaryText: 'Comparison Complete'
  }
};

export const FIXTURE_COMPLETED_FAILED_SYNC: WorkstationViewModel = {
  ...FIXTURE_FAILED,
  donut: {
    ...FIXTURE_FAILED.donut,
    mode: 'MIGRATION_SYNC',
    canonicalComparisonMode: 'SYNC',
    centerLabel: 'SYNC',
    centerSubtext: '18 Discrepancies Flagged',
    centerSecondaryText: 'Comparison Complete'
  }
};

export const FIXTURE_COMPLETED_PASSED_ASYNC: WorkstationViewModel = {
  ...FIXTURE_PASSED,
  donut: {
    ...FIXTURE_PASSED.donut,
    mode: 'INDEPENDENT_VALIDATION',
    canonicalComparisonMode: 'ASYNC',
    centerLabel: 'ASYNC',
    centerSubtext: '18.2M Records Matched',
    centerSecondaryText: 'Comparison Complete'
  }
};

export const FIXTURE_COMPLETED_FAILED_ASYNC: WorkstationViewModel = {
  ...FIXTURE_FAILED,
  donut: {
    ...FIXTURE_FAILED.donut,
    mode: 'INDEPENDENT_VALIDATION',
    canonicalComparisonMode: 'ASYNC',
    centerLabel: 'ASYNC',
    centerSubtext: 'Discrepancies Confirmed',
    centerSecondaryText: 'Comparison Complete'
  }
};

export const FIXTURE_COMPLETED_UNKNOWN_MODE: WorkstationViewModel = {
  ...FIXTURE_PASSED,
  donut: {
    ...FIXTURE_PASSED.donut,
    mode: 'INDEPENDENT_VALIDATION',
    canonicalComparisonMode: 'UNKNOWN',
    centerLabel: '100%',
    centerSubtext: 'Relationship Mode Unspecified',
    centerSecondaryText: 'Comparison Complete'
  }
};

export const FIXTURE_WITHHELD: WorkstationViewModel = {
  ...FIXTURE_PASSED,
  verdict: 'WITHHELD',
  donut: {
    ...FIXTURE_PASSED.donut,
    centerSubtext: 'Verdict Withheld by Policy'
  }
};

export const FIXTURE_RECOVERING: WorkstationViewModel = {
  ...FIXTURE_RUNNING_DIFFS,
  executionState: 'RECOVERING',
  verdict: 'NOT_EVALUATED',
  donut: {
    ...FIXTURE_RUNNING_DIFFS.donut,
    centerSubtext: 'Reconciling Checkpoint State'
  }
};

export const FIXTURE_BASELINE_INVALID: WorkstationViewModel = {
  ...FIXTURE_RUNNING_DIFFS,
  remediation: {
    ...FIXTURE_RUNNING_DIFFS.remediation,
    baselineStatus: 'STALE'
  },
  attentionItems: [
    {
      id: 'ATTN-BSL-1',
      severity: 'warning',
      category: 'baseline',
      title: 'Comparison Baseline Requires Attention',
      description: 'Frozen baseline hash does not match current source state. Data mutations detected after baseline registration.',
      location: 'Baseline Store (BSL-9981-FROZEN)'
    }
  ]
};

export const FIXTURE_AUDIT_ONLY_REPAIR_FORBIDDEN: WorkstationViewModel = {
  ...FIXTURE_FAILED,
  remediation: {
    ...FIXTURE_FAILED.remediation,
    autoRepairPolicy: 'Mutation Prohibited (Audit-Only Mission)'
  }
};

export const WORKSTATION_FIXTURES: Record<string, WorkstationViewModel> = {
  NOT_CONNECTED: FIXTURE_NOT_CONNECTED,
  RUNNING_CLEAN: FIXTURE_RUNNING_CLEAN,
  RUNNING_DIFFS: FIXTURE_RUNNING_DIFFS,
  PASSED: FIXTURE_PASSED,
  FAILED: FIXTURE_FAILED,
  COMPLETED_PASSED_SYNC: FIXTURE_COMPLETED_PASSED_SYNC,
  COMPLETED_FAILED_SYNC: FIXTURE_COMPLETED_FAILED_SYNC,
  COMPLETED_PASSED_ASYNC: FIXTURE_COMPLETED_PASSED_ASYNC,
  COMPLETED_FAILED_ASYNC: FIXTURE_COMPLETED_FAILED_ASYNC,
  COMPLETED_UNKNOWN_MODE: FIXTURE_COMPLETED_UNKNOWN_MODE,
  WITHHELD: FIXTURE_WITHHELD,
  INTERRUPTED: FIXTURE_INTERRUPTED,
  RECOVERING: FIXTURE_RECOVERING,
  BLOCKED: FIXTURE_BLOCKED,
  BASELINE_INVALID: FIXTURE_BASELINE_INVALID,
  AUDIT_ONLY_REPAIR_FORBIDDEN: FIXTURE_AUDIT_ONLY_REPAIR_FORBIDDEN,
  LARGE_ENTERPRISE: FIXTURE_LARGE_ENTERPRISE
};
