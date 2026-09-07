/**
 * validation-discrepancies.fixtures.ts
 * =====================================
 * Comprehensive visual verification and hostile test fixtures for Discrepancies & Reconciliation.
 * Strictly isolated for test/harness usage; not leaking into production default.
 */

import {
  DiscrepanciesWorkspaceModel,
  DiscrepancyItem,
  ScopeNavigatorItem
} from './validation-discrepancies.models';

const SOURCE_ENDPOINT = {
  provider: 'PostgreSQL 16',
  label: 'Primary Operational Cluster',
  location: 'pg-prod-01.internal:5432/core'
};

const TARGET_ENDPOINT = {
  provider: 'ClickHouse 24.3',
  label: 'Analytics Warehouse Replica',
  location: 'ch-dw-01.internal:8123/default'
};

// --- Sample Discrepancy Items ---

export const DISC_01_CUSTOMER_VALUE_DIFF: DiscrepancyItem = {
  id: 'DISC-2026-0089-001',
  objectName: 'public.customers',
  partitionId: 'p_2026_q1',
  recordKey: 'customer_id=84021',
  category: 'VALUE_DIFFERENCE',
  proofTier: 'TIER_4_ATTRIBUTE',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Current balance and billing address format mismatch across endpoints.',
  affectedAttributes: ['balance', 'billing_address', 'updated_at'],
  totalAttributesCompared: 8,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'customer_id',
      sourceValue: 84021,
      sourceValueKind: 'SCALAR',
      sourceType: 'BIGINT',
      targetValue: 84021,
      targetValueKind: 'SCALAR',
      targetType: 'UInt64',
      diffType: 'MATCH',
      isKey: true
    },
    {
      attributeName: 'full_name',
      sourceValue: 'Aalok Ladwa',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(255)',
      targetValue: 'Aalok Ladwa',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH'
    },
    {
      attributeName: 'billing_address',
      sourceValue: '14 Residency Rd, Suite 400',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(500)',
      targetValue: '14 Residency Road, Suite 400',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'DIFFERENT'
    },
    {
      attributeName: 'city',
      sourceValue: 'Hubballi',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(100)',
      targetValue: 'Hubballi',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH'
    },
    {
      attributeName: 'balance',
      sourceValue: 14250.75,
      sourceValueKind: 'SCALAR',
      sourceType: 'NUMERIC(18,2)',
      targetValue: 14190.00,
      targetValueKind: 'SCALAR',
      targetType: 'Decimal(18,2)',
      diffType: 'DIFFERENT'
    },
    {
      attributeName: 'status',
      sourceValue: 'ACTIVE',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(20)',
      targetValue: 'ACTIVE',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH'
    },
    {
      attributeName: 'tax_identifier',
      sourceValue: 'PROTECTED',
      sourceValueKind: 'PROTECTED',
      sourceType: 'VARCHAR(50)',
      targetValue: 'PROTECTED',
      targetValueKind: 'PROTECTED',
      targetType: 'String',
      diffType: 'MATCH',
      isSensitive: true
    },
    {
      attributeName: 'updated_at',
      sourceValue: '2026-09-07T08:12:44.102Z',
      sourceValueKind: 'SCALAR',
      sourceType: 'TIMESTAMPTZ',
      targetValue: '2026-09-07T08:10:00.000Z',
      targetValueKind: 'SCALAR',
      targetType: 'DateTime64(3)',
      diffType: 'DIFFERENT'
    }
  ],
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z',
    baselineHash: 'sha256:7f83b1657ff1fc53b92dc18148e1d6e355c2826a7989'
  },
  transformationContext: {
    sourceAttributeMapped: 'billing_address',
    targetAttributeMapped: 'billing_address',
    ruleName: 'Canonical Pass-Through',
    filterPredicate: 'is_active = TRUE'
  },
  governanceHandoff: {
    requiresGovernedRepair: true,
    repairEligible: true,
    repairPolicyNote: 'Requires P7B Governed Dual-Operator Signoff before Target Reconciliation.'
  }
};

export const DISC_02_MISSING_ON_TARGET: DiscrepancyItem = {
  id: 'DISC-2026-0089-002',
  objectName: 'public.customers',
  partitionId: 'p_2026_q1',
  recordKey: 'customer_id=84109',
  category: 'MISSING_ON_TARGET',
  proofTier: 'TIER_4_ATTRIBUTE',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Primary key exists at Source (PostgreSQL) but is absent on Target (ClickHouse).',
  affectedAttributes: ['ALL_ATTRIBUTES'],
  totalAttributesCompared: 8,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'customer_id',
      sourceValue: 84109,
      sourceValueKind: 'SCALAR',
      sourceType: 'BIGINT',
      targetValue: null,
      targetValueKind: 'ABSENT',
      targetType: 'UInt64',
      diffType: 'SOURCE_ONLY',
      isKey: true
    },
    {
      attributeName: 'full_name',
      sourceValue: 'Rajesh Sharma',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(255)',
      targetValue: null,
      targetValueKind: 'ABSENT',
      targetType: 'String',
      diffType: 'SOURCE_ONLY'
    },
    {
      attributeName: 'billing_address',
      sourceValue: '22 MG Road, Indiranagar',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(500)',
      targetValue: null,
      targetValueKind: 'ABSENT',
      targetType: 'String',
      diffType: 'SOURCE_ONLY'
    },
    {
      attributeName: 'balance',
      sourceValue: 5200.00,
      sourceValueKind: 'SCALAR',
      sourceType: 'NUMERIC(18,2)',
      targetValue: null,
      targetValueKind: 'ABSENT',
      targetType: 'Decimal(18,2)',
      diffType: 'SOURCE_ONLY'
    }
  ],
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: true,
    repairEligible: true,
    repairPolicyNote: 'Row insertion into Target requires CDC pipeline sync or governed re-ingest.'
  }
};

export const DISC_03_EXTRA_ON_TARGET: DiscrepancyItem = {
  id: 'DISC-2026-0089-003',
  objectName: 'public.orders',
  partitionId: 'p_2026_q2',
  recordKey: 'order_id=ORD-99182',
  category: 'EXTRA_ON_TARGET',
  proofTier: 'TIER_4_ATTRIBUTE',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Record exists on Target (ClickHouse) without corresponding Source row in baseline scope.',
  affectedAttributes: ['ALL_ATTRIBUTES'],
  totalAttributesCompared: 6,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'order_id',
      sourceValue: null,
      sourceValueKind: 'ABSENT',
      sourceType: 'VARCHAR(64)',
      targetValue: 'ORD-99182',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'TARGET_ONLY',
      isKey: true
    },
    {
      attributeName: 'total_amount',
      sourceValue: null,
      sourceValueKind: 'ABSENT',
      sourceType: 'NUMERIC(18,2)',
      targetValue: 890.50,
      targetValueKind: 'SCALAR',
      targetType: 'Decimal(18,2)',
      diffType: 'TARGET_ONLY'
    },
    {
      attributeName: 'order_status',
      sourceValue: null,
      sourceValueKind: 'ABSENT',
      sourceType: 'VARCHAR(20)',
      targetValue: 'COMPLETED',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'TARGET_ONLY'
    }
  ],
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: true,
    repairEligible: false,
    repairPolicyNote: 'Target row provenance unconfirmed. Direct deletion prohibited without audit trace.'
  }
};

export const DISC_04_CARDINALITY_DIFF: DiscrepancyItem = {
  id: 'DISC-2026-0089-004',
  objectName: 'public.transactions_2026',
  partitionId: 'p_2026_m08',
  recordKey: 'scope:partition[p_2026_m08]',
  category: 'CARDINALITY_DIFFERENCE',
  proofTier: 'TIER_2_CARDINALITY',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Bounded row count divergence: 1,004,218 Source rows vs 1,004,216 Target rows (Delta: 2 rows).',
  affectedAttributes: ['ROW_COUNT'],
  totalAttributesCompared: 1,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'row_count',
      sourceValue: 1004218,
      sourceValueKind: 'SCALAR',
      sourceType: 'BIGINT',
      targetValue: 1004216,
      targetValueKind: 'SCALAR',
      targetType: 'UInt64',
      diffType: 'DIFFERENT'
    }
  ],
  cardinalitySummary: {
    sourceCount: 1004218,
    targetCount: 1004216,
    delta: -2,
    localizationStatus: 'UNAVAILABLE',
    boundaryFilter: "created_at >= '2026-08-01' AND created_at < '2026-09-01'"
  },
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: false,
    repairEligible: false,
    repairPolicyNote: 'Partition-level cardinality delta. Run Tier 4 Attribute scan to localize specific primary keys.'
  }
};

export const DISC_05_FINGERPRINT_DIFF: DiscrepancyItem = {
  id: 'DISC-2026-0089-005',
  objectName: 'public.accounts_audit',
  partitionId: 'chunk_0042_hash',
  recordKey: 'partition:chunk_0042_hash',
  category: 'PARTITION_FINGERPRINT',
  proofTier: 'TIER_3_PARTITION',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Cryptographic hash tree mismatch across partition range [0x4200..0x42FF].',
  affectedAttributes: ['HASH_TREE_ROOT'],
  totalAttributesCompared: 1,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'hash_tree_digest',
      sourceValue: 'sha256:4f8e9102ab3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f7a8b9c0d1e2f3a',
      sourceValueKind: 'SCALAR',
      sourceType: 'CHAR(64)',
      targetValue: 'sha256:9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
      targetValueKind: 'SCALAR',
      targetType: 'FixedString(64)',
      diffType: 'DIFFERENT'
    }
  ],
  fingerprintSummary: {
    sourceHash: 'sha256:4f8e9102ab3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f7a8b9c0d1e2f3a',
    targetHash: 'sha256:9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    partitionRange: 'ID range [420,000..429,999]',
    localizationStatus: 'UNAVAILABLE',
    hostileXorNote: 'Hostile XOR Defect Guard: Merkle tree localization unavailable in current execution path. Individual disputed keys not materialized.'
  },
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: false,
    repairEligible: false,
    repairPolicyNote: 'Requires attribute-level localization pass before repair planning.'
  }
};

export const DISC_06_TRANSFORMATION_EXPLAINED: DiscrepancyItem = {
  id: 'DISC-2026-0089-006',
  objectName: 'public.customers',
  partitionId: 'p_2026_q1',
  recordKey: 'customer_id=84050',
  category: 'VALUE_DIFFERENCE',
  proofTier: 'TIER_4_ATTRIBUTE',
  reconciliationState: 'EXPLAINED_BY_TRANSFORMATION',
  differenceSummary: 'Full name format transformed from split first/last columns into single target column.',
  affectedAttributes: ['full_name'],
  totalAttributesCompared: 8,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'customer_id',
      sourceValue: 84050,
      sourceValueKind: 'SCALAR',
      sourceType: 'BIGINT',
      targetValue: 84050,
      targetValueKind: 'SCALAR',
      targetType: 'UInt64',
      diffType: 'MATCH',
      isKey: true
    },
    {
      attributeName: 'full_name',
      sourceValue: 'Vikram Mehta',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(255)',
      targetValue: 'VIKRAM MEHTA',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'DIFFERENT',
      transformationNote: 'Canonical uppercase transformation policy applied: UPPER(first_name || \' \' || last_name)'
    },
    {
      attributeName: 'status',
      sourceValue: 'ACTIVE',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(20)',
      targetValue: 'ACTIVE',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH'
    }
  ],
  transformationContext: {
    sourceAttributeMapped: 'first_name, last_name',
    targetAttributeMapped: 'full_name',
    ruleName: 'RULE-CONCAT-UPPERCASE-01',
    transformationType: 'Expression (UPPER)',
    filterPredicate: 'is_deleted = FALSE',
    dedupPolicy: 'Distinct on customer_id'
  },
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: false,
    repairEligible: false,
    repairPolicyNote: 'Expected variance. Explained by intentional canonical pipeline transformation.'
  }
};

export const DISC_07_NULL_VS_EMPTY_STRING: DiscrepancyItem = {
  id: 'DISC-2026-0089-007',
  objectName: 'public.customers',
  partitionId: 'p_2026_q1',
  recordKey: 'customer_id=84099',
  category: 'VALUE_DIFFERENCE',
  proofTier: 'TIER_4_ATTRIBUTE',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Semantic value divergence: Source contains explicit NULL while Target contains empty string ("").',
  affectedAttributes: ['middle_name', 'secondary_email'],
  totalAttributesCompared: 8,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'customer_id',
      sourceValue: 84099,
      sourceValueKind: 'SCALAR',
      sourceType: 'BIGINT',
      targetValue: 84099,
      targetValueKind: 'SCALAR',
      targetType: 'UInt64',
      diffType: 'MATCH',
      isKey: true
    },
    {
      attributeName: 'middle_name',
      sourceValue: null,
      sourceValueKind: 'NULL',
      sourceType: 'VARCHAR(50)',
      targetValue: '',
      targetValueKind: 'EMPTY_STRING',
      targetType: 'String',
      diffType: 'DIFFERENT'
    },
    {
      attributeName: 'secondary_email',
      sourceValue: '   ',
      sourceValueKind: 'WHITESPACE',
      sourceType: 'VARCHAR(255)',
      targetValue: null,
      targetValueKind: 'NULL',
      targetType: 'Nullable(String)',
      diffType: 'DIFFERENT'
    },
    {
      attributeName: 'status',
      sourceValue: 'ACTIVE',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(20)',
      targetValue: 'ACTIVE',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH'
    }
  ],
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: true,
    repairEligible: true,
    repairPolicyNote: 'Nullability handling divergence across database engines. Requires target null cast.'
  }
};

export const DISC_08_LONG_VALUES_LOB: DiscrepancyItem = {
  id: 'DISC-2026-0089-008',
  objectName: 'enterprise_global_financial_settlements_and_clearing_archive_ledger_v2',
  partitionId: 'partition_apac_singapore_financial_quarter_2026_q3_final_settled',
  recordKey: 'settlement_uuid=550e8400-e29b-41d4-a716-446655440000-apac-sg-corp-settle',
  category: 'VALUE_DIFFERENCE',
  proofTier: 'TIER_4_ATTRIBUTE',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'XML Clearing Payload (64.2 KB) hash mismatch across endpoints.',
  affectedAttributes: ['payload_xml', 'legal_entity_notes'],
  totalAttributesCompared: 12,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'settlement_uuid',
      sourceValue: '550e8400-e29b-41d4-a716-446655440000-apac-sg-corp-settle',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(128)',
      targetValue: '550e8400-e29b-41d4-a716-446655440000-apac-sg-corp-settle',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH',
      isKey: true
    },
    {
      attributeName: 'payload_xml',
      sourceValue: '<?xml version="1.0" encoding="UTF-8"?><SettlementDoc xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><GrpHdr><MsgId>APAC-2026-0907-889102</MsgId><CreDtTm>2026-09-07T08:14:22Z</CreDtTm><NbOfTxs>1</NbOfTxs><SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf></GrpHdr><CdtTrfTxInf><PmtId><EndToEndId>E2E-991823901</EndToEndId></PmtId><IntrBkSttlmAmt Ccy="SGD">8450000.00</IntrBkSttlmAmt></CdtTrfTxInf></SettlementDoc>',
      sourceValueKind: 'LOB_TRUNCATED',
      sourceType: 'TEXT / XML',
      targetValue: '<?xml version="1.0" encoding="UTF-8"?><SettlementDoc xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><GrpHdr><MsgId>APAC-2026-0907-889102</MsgId><CreDtTm>2026-09-07T08:14:00Z</CreDtTm><NbOfTxs>1</NbOfTxs><SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf></GrpHdr><CdtTrfTxInf><PmtId><EndToEndId>E2E-991823901</EndToEndId></PmtId><IntrBkSttlmAmt Ccy="SGD">8450000.00</IntrBkSttlmAmt></CdtTrfTxInf></SettlementDoc>',
      targetValueKind: 'LOB_TRUNCATED',
      targetType: 'String',
      diffType: 'DIFFERENT',
      lobMetadata: {
        byteLength: 65740,
        mimeType: 'application/xml',
        digest: 'sha256:d8a9f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8'
      }
    },
    {
      attributeName: 'legal_entity_notes',
      sourceValue: 'Cross-border clearing settlement for institutional financial counterparty under international Swift ISO 20022 clearing mandate.',
      sourceValueKind: 'SCALAR',
      sourceType: 'VARCHAR(2000)',
      targetValue: 'Cross-border clearing settlement for institutional financial counterparty under international Swift ISO 20022 clearing mandate.',
      targetValueKind: 'SCALAR',
      targetType: 'String',
      diffType: 'MATCH'
    }
  ],
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: true,
    repairEligible: true,
    repairPolicyNote: 'Large payload timestamp mismatch. Governed reconciliation plan required.'
  }
};

export const DISC_09_STRUCTURAL_DIFF: DiscrepancyItem = {
  id: 'DISC-2026-0089-009',
  objectName: 'public.payment_methods',
  recordKey: 'table:public.payment_methods',
  category: 'STRUCTURAL_DIFFERENCE',
  proofTier: 'TIER_1_STRUCTURAL',
  reconciliationState: 'UNRESOLVED',
  differenceSummary: 'Target schema missing column "is_primary" (BOOLEAN NOT NULL DEFAULT FALSE).',
  affectedAttributes: ['is_primary'],
  totalAttributesCompared: 7,
  sourceEndpoint: SOURCE_ENDPOINT,
  targetEndpoint: TARGET_ENDPOINT,
  attributes: [
    {
      attributeName: 'is_primary',
      sourceValue: 'BOOLEAN NOT NULL DEFAULT false',
      sourceValueKind: 'SCALAR',
      sourceType: 'COLUMN_DEF',
      targetValue: null,
      targetValueKind: 'ABSENT',
      targetType: 'MISSING_IN_TARGET',
      diffType: 'SOURCE_ONLY'
    }
  ],
  structuralSummary: {
    sourceSchemaDetails: 'Column "is_primary" type BOOLEAN, nullable: NO, default: false',
    targetSchemaDetails: 'Column does not exist in target ClickHouse table definition',
    differenceDetail: 'DDL alteration required on target schema to achieve structural parity.'
  },
  baselineContext: {
    baselineId: 'BSL-9981-FROZEN',
    baselineStatus: 'VALID',
    snapshotTimestamp: '2026-09-07T08:00:00Z'
  },
  governanceHandoff: {
    requiresGovernedRepair: true,
    repairEligible: false,
    repairPolicyNote: 'Schema DDL repair requires DBA governed change window.'
  }
};

// --- Scope Navigator Fixture Items ---

const NAVIGATOR_ITEMS_NORMAL: ScopeNavigatorItem[] = [
  {
    objectName: 'public.customers',
    totalFindings: 12,
    categoryCounts: {
      VALUE_DIFFERENCE: 8,
      MISSING_ON_TARGET: 3,
      EXPLAINED_BY_TRANSFORMATION: 1
    },
    partitions: [
      { partitionId: 'p_2026_q1', findingsCount: 8, status: 'DIFFS' },
      { partitionId: 'p_2026_q2', findingsCount: 4, status: 'DIFFS' }
    ],
    localizationAvailable: true
  },
  {
    objectName: 'public.orders',
    totalFindings: 4,
    categoryCounts: {
      EXTRA_ON_TARGET: 3,
      VALUE_DIFFERENCE: 1
    },
    partitions: [
      { partitionId: 'p_2026_q2', findingsCount: 4, status: 'DIFFS' }
    ],
    localizationAvailable: true
  },
  {
    objectName: 'public.transactions_2026',
    totalFindings: 2,
    categoryCounts: {
      CARDINALITY_DIFFERENCE: 2
    },
    partitions: [
      { partitionId: 'p_2026_m08', findingsCount: 2, status: 'DIFFS' }
    ],
    localizationAvailable: false
  },
  {
    objectName: 'public.accounts_audit',
    totalFindings: 1,
    categoryCounts: {
      PARTITION_FINGERPRINT: 1
    },
    partitions: [
      { partitionId: 'chunk_0042_hash', findingsCount: 1, status: 'DIFFS' }
    ],
    localizationAvailable: false
  }
];

// --- Workspace Models ---

export const FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED: DiscrepanciesWorkspaceModel = {
  summary: {
    totalDiscrepancies: null,
    totalDiscrepanciesFormatted: '—',
    affectedObjectsCount: null,
    evaluatedScopeCount: null,
    localizationStatus: 'UNAVAILABLE',
    baselineStatus: 'NOT_AVAILABLE',
    unresolvedCount: null,
    explainedCount: null,
    isLargeAggregate: false,
    boundedPageSize: 20,
    totalKnownPages: null,
    currentPage: 1
  },
  navigator: [],
  items: [],
  selectedDiscrepancyId: null,
  selectedObjectFilter: null,
  selectedPartitionFilter: null,
  selectedCategoryFilter: 'ALL',
  selectedProofTierFilter: 'ALL',
  selectedReconciliationFilter: 'ALL',
  searchQuery: '',
  showDifferencesOnly: true,
  pagination: {
    currentPage: 1,
    pageSize: 20,
    totalItems: null,
    isServerBacked: true
  },
  viewStatus: 'UNAVAILABLE'
};

export const FIXTURE_DISCREPANCIES_NORMAL: DiscrepanciesWorkspaceModel = {
  summary: {
    totalDiscrepancies: 19,
    totalDiscrepanciesFormatted: '19',
    affectedObjectsCount: 4,
    evaluatedScopeCount: 42,
    localizationStatus: 'AVAILABLE',
    baselineStatus: 'VALID',
    unresolvedCount: 18,
    explainedCount: 1,
    isLargeAggregate: false,
    boundedPageSize: 20,
    totalKnownPages: 1,
    currentPage: 1
  },
  navigator: NAVIGATOR_ITEMS_NORMAL,
  items: [
    DISC_01_CUSTOMER_VALUE_DIFF,
    DISC_02_MISSING_ON_TARGET,
    DISC_03_EXTRA_ON_TARGET,
    DISC_04_CARDINALITY_DIFF,
    DISC_05_FINGERPRINT_DIFF,
    DISC_06_TRANSFORMATION_EXPLAINED,
    DISC_07_NULL_VS_EMPTY_STRING,
    DISC_08_LONG_VALUES_LOB,
    DISC_09_STRUCTURAL_DIFF
  ],
  selectedDiscrepancyId: 'DISC-2026-0089-001',
  selectedObjectFilter: null,
  selectedPartitionFilter: null,
  selectedCategoryFilter: 'ALL',
  selectedProofTierFilter: 'ALL',
  selectedReconciliationFilter: 'ALL',
  searchQuery: '',
  showDifferencesOnly: true,
  pagination: {
    currentPage: 1,
    pageSize: 20,
    totalItems: 19,
    isServerBacked: true
  },
  viewStatus: 'READY'
};

export const FIXTURE_DISCREPANCIES_40M_AGGREGATE: DiscrepanciesWorkspaceModel = {
  summary: {
    totalDiscrepancies: 40000000,
    totalDiscrepanciesFormatted: '40,000,000',
    affectedObjectsCount: 128,
    evaluatedScopeCount: 1280,
    localizationStatus: 'LIMITED',
    baselineStatus: 'VALID',
    unresolvedCount: 39820000,
    explainedCount: 180000,
    isLargeAggregate: true,
    boundedPageSize: 25,
    totalKnownPages: 1600000,
    currentPage: 1
  },
  navigator: [
    {
      objectName: 'public.ledger_entries',
      totalFindings: 24500000,
      categoryCounts: { VALUE_DIFFERENCE: 24500000 },
      partitions: [
        { partitionId: 'p_2026_q1', findingsCount: 8200000, status: 'DIFFS' },
        { partitionId: 'p_2026_q2', findingsCount: 9100000, status: 'DIFFS' },
        { partitionId: 'p_2026_q3', findingsCount: 7200000, status: 'DIFFS' }
      ],
      localizationAvailable: true
    },
    {
      objectName: 'public.order_lines',
      totalFindings: 15500000,
      categoryCounts: { VALUE_DIFFERENCE: 15500000 },
      partitions: [
        { partitionId: 'p_ol_2026_01', findingsCount: 5200000, status: 'DIFFS' }
      ],
      localizationAvailable: false
    }
  ],
  items: [
    {
      ...DISC_01_CUSTOMER_VALUE_DIFF,
      id: 'DISC-40M-PAGE1-001',
      objectName: 'public.ledger_entries',
      recordKey: 'entry_id=9881023901',
      differenceSummary: 'Credit amount and timestamp diverge across financial ledger endpoints.'
    },
    {
      ...DISC_02_MISSING_ON_TARGET,
      id: 'DISC-40M-PAGE1-002',
      objectName: 'public.ledger_entries',
      recordKey: 'entry_id=9881023902'
    },
    {
      ...DISC_03_EXTRA_ON_TARGET,
      id: 'DISC-40M-PAGE1-003',
      objectName: 'public.order_lines',
      recordKey: 'line_id=OL-44091823'
    }
  ],
  selectedDiscrepancyId: 'DISC-40M-PAGE1-001',
  selectedObjectFilter: null,
  selectedPartitionFilter: null,
  selectedCategoryFilter: 'ALL',
  selectedProofTierFilter: 'ALL',
  selectedReconciliationFilter: 'ALL',
  searchQuery: '',
  showDifferencesOnly: true,
  pagination: {
    currentPage: 1,
    pageSize: 25,
    totalItems: 40000000,
    isServerBacked: true
  },
  viewStatus: 'READY'
};

export const FIXTURE_DISCREPANCIES_BASELINE_DRIFT: DiscrepanciesWorkspaceModel = {
  ...FIXTURE_DISCREPANCIES_NORMAL,
  summary: {
    ...FIXTURE_DISCREPANCIES_NORMAL.summary,
    baselineStatus: 'STALE'
  },
  items: FIXTURE_DISCREPANCIES_NORMAL.items.map(item => ({
    ...item,
    baselineContext: {
      baselineId: 'BSL-9981-FROZEN',
      baselineStatus: 'STALE',
      snapshotTimestamp: '2026-09-07T08:00:00Z',
      baselineHash: 'sha256:7f83b1657ff1fc53b92dc18148e1d6e355c2826a7989'
    }
  }))
};

export const FIXTURE_DISCREPANCIES_EMPTY_PASSED: DiscrepanciesWorkspaceModel = {
  summary: {
    totalDiscrepancies: 0,
    totalDiscrepanciesFormatted: '0',
    affectedObjectsCount: 0,
    evaluatedScopeCount: 42,
    localizationStatus: 'AVAILABLE',
    baselineStatus: 'VALID',
    unresolvedCount: 0,
    explainedCount: 0,
    isLargeAggregate: false,
    boundedPageSize: 20,
    totalKnownPages: 0,
    currentPage: 1
  },
  navigator: [],
  items: [],
  selectedDiscrepancyId: null,
  selectedObjectFilter: null,
  selectedPartitionFilter: null,
  selectedCategoryFilter: 'ALL',
  selectedProofTierFilter: 'ALL',
  selectedReconciliationFilter: 'ALL',
  searchQuery: '',
  showDifferencesOnly: true,
  pagination: {
    currentPage: 1,
    pageSize: 20,
    totalItems: 0,
    isServerBacked: true
  },
  viewStatus: 'EMPTY'
};

export const FIXTURE_DISCREPANCIES_NOT_EVALUATED: DiscrepanciesWorkspaceModel = {
  ...FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED,
  viewStatus: 'NOT_EVALUATED'
};

export const FIXTURE_DISCREPANCIES_LOADING: DiscrepanciesWorkspaceModel = {
  ...FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED,
  viewStatus: 'LOADING'
};

export const FIXTURE_DISCREPANCIES_ERROR: DiscrepanciesWorkspaceModel = {
  ...FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED,
  viewStatus: 'ERROR',
  errorMessage: 'Failed to retrieve discrepancy stream: Connection refused on validation daemon RPC port :50051.'
};

export const FIXTURE_DISCREPANCIES_HISTORICAL: DiscrepanciesWorkspaceModel = {
  ...FIXTURE_DISCREPANCIES_NORMAL,
  isHistorical: true
};

export const DISCREPANCIES_FIXTURES: Record<string, DiscrepanciesWorkspaceModel> = {
  DEFAULT_NOT_CONNECTED: FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED,
  NORMAL_19_FINDINGS: FIXTURE_DISCREPANCIES_NORMAL,
  VALUE_DIFF: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-001' },
  MISSING_TARGET: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-002' },
  EXTRA_TARGET: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-003' },
  CARDINALITY_DIFF: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-004' },
  FINGERPRINT_DIFF: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-005' },
  TRANSFORMED_EXPLAINED: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-006' },
  NULL_EMPTY_ABSENT: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-007' },
  LONG_VALUES_LOB: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-008' },
  STRUCTURAL_DIFF: { ...FIXTURE_DISCREPANCIES_NORMAL, selectedDiscrepancyId: 'DISC-2026-0089-009' },
  BASELINE_DRIFT: FIXTURE_DISCREPANCIES_BASELINE_DRIFT,
  LARGE_40M_AGGREGATE: FIXTURE_DISCREPANCIES_40M_AGGREGATE,
  EMPTY_PASSED: FIXTURE_DISCREPANCIES_EMPTY_PASSED,
  NOT_EVALUATED: FIXTURE_DISCREPANCIES_NOT_EVALUATED,
  LOADING: FIXTURE_DISCREPANCIES_LOADING,
  ERROR: FIXTURE_DISCREPANCIES_ERROR,
  HISTORICAL: FIXTURE_DISCREPANCIES_HISTORICAL
};
