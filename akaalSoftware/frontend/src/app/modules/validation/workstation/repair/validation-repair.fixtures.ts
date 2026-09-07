/**
 * validation-repair.fixtures.ts
 * =====================================
 * Canonical fixtures for Controlled Repair & Revalidation workspace.
 * Strict adherence to:
 * - Production default: UNAVAILABLE / NOT_CONNECTED
 * - Non-mutating Validation #11 law
 * - UNKNOWN commit outcome preservation
 * - Separate repair vs validation dimensions
 * - Sensitive data fail-closed masking
 */

import { RepairWorkspaceState, RepairOperationFamily, GovernanceDimension, ExecutionDimension, RevalidationDimension } from './validation-repair.models';

export const REPAIR_FIXTURES: Record<string, RepairWorkspaceState> = {

  // 1. Truthful Production Default (Standby / Disconnected)
  DEFAULT_NOT_CONNECTED: {
    viewStatus: 'UNAVAILABLE',
    summary: {
      overallState: 'Standby / Executor Unavailable',
      conciseExplanation: 'Controlled repair execution is not currently available. The current validation runtime is strictly read-only.',
      eligibility: 'UNAVAILABLE',
      proposalState: 'UNAVAILABLE',
      governanceState: 'UNAVAILABLE',
      executionState: 'UNAVAILABLE',
      revalidationState: 'UNAVAILABLE',
      isExecutorAvailable: false,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-none',
      totalSelectedFindings: 0,
      selectedObjects: [],
      affectedRecordKeys: [],
      findingCategories: [],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:00:00Z',
      isBulkAggregate: false
    },
    proposal: null,
    impact: null,
    governance: null,
    execution: null,
    revalidation: null,
    technicalDetails: null,
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'DEFAULT_NOT_CONNECTED'
  },

  // 2. Canonical Empty State (Zero Discrepancies / No Remediation Required)
  NO_REMEDIATION_REQUIRED: {
    viewStatus: 'NO_REMEDIATION_REQUIRED',
    summary: {
      overallState: 'No Remediation Required',
      conciseExplanation: 'No findings currently require controlled remediation. All validated objects satisfy required proof obligations.',
      eligibility: 'NOT_EVALUATED',
      proposalState: 'UNAVAILABLE',
      governanceState: 'NOT_EVALUATED',
      executionState: 'NOT_STARTED',
      revalidationState: 'NOT_REQUIRED',
      isExecutorAvailable: false,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-clean-0',
      totalSelectedFindings: 0,
      selectedObjects: [],
      affectedRecordKeys: [],
      findingCategories: [],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:00:00Z',
      isBulkAggregate: false
    },
    proposal: null,
    impact: null,
    governance: null,
    execution: null,
    revalidation: null,
    technicalDetails: null,
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'NO_REMEDIATION_REQUIRED'
  },

  // 3. Audit-Only Mission (Policy Read-Only)
  AUDIT_ONLY_MISSION: {
    viewStatus: 'AUDIT_ONLY',
    summary: {
      overallState: 'Audit-Only Mission',
      conciseExplanation: 'This mission is configured as read-only. Controlled target remediation is prohibited by governance policy.',
      eligibility: 'INELIGIBLE',
      proposalState: 'UNAVAILABLE',
      governanceState: 'NOT_EVALUATED',
      executionState: 'UNAVAILABLE',
      revalidationState: 'NOT_REQUIRED',
      isExecutorAvailable: false,
      isReadonlyMission: true
    },
    selectedScope: {
      selectionSetId: 'sel-audit-readonly',
      totalSelectedFindings: 5,
      selectedObjects: ['financial_ledger_entries', 'account_balances'],
      affectedRecordKeys: ['TXN-2026-9901', 'TXN-2026-9902'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:10:00Z',
      isBulkAggregate: false
    },
    proposal: null,
    impact: null,
    governance: null,
    execution: null,
    revalidation: null,
    technicalDetails: {
      revalidationMissionId: 'vm-prod-audit-2026-09-07'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'AUDIT_ONLY_MISSION'
  },

  // 4. Standard Operational Case: Single Update Proposal (Ready for Review)
  SINGLE_UPDATE_PROPOSAL: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Repair Proposal Established — Governance Review Required',
      conciseExplanation: 'A targeted attribute update proposal has been compiled from discrepancy findings. Governance authorization is required before execution.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVAL_REQUIRED',
      executionState: 'NOT_STARTED',
      revalidationState: 'REQUIRED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-disc-108482',
      totalSelectedFindings: 1,
      selectedObjects: ['enterprise_customers'],
      affectedRecordKeys: ['CUST-009281'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:15:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-m8-20260907-001',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:4f8e91c7a2b53d6e1f0a9b8c7d6e5f4a3b2c1d0e',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'enterprise_customers',
      recordKey: 'CUST-009281',
      summaryNote: 'Update differing account credit limit and status attributes on target endpoint to match canonical transformed source values.',
      detailedRationale: 'Validation Tier 4 detected attribute divergence on non-key financial attributes. Source record has been updated since initial snapshot.',
      createdAt: '2026-09-07T12:14:30Z',
      canonicalDmlPreview: 'UPDATE enterprise_customers SET credit_limit = 500000.00, account_status = \'ACTIVE\', updated_at = \'2026-09-07 12:14:30\' WHERE customer_id = \'CUST-009281\';',
      proposedChanges: [
        {
          attributeName: 'customer_id',
          sourceValue: 'CUST-009281',
          sourceValueKind: 'SCALAR',
          sourceType: 'VARCHAR(32)',
          currentTargetValue: 'CUST-009281',
          currentTargetValueKind: 'SCALAR',
          currentTargetType: 'VARCHAR(32)',
          proposedTargetValue: 'CUST-009281',
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'VARCHAR(32)',
          isKey: true,
          isSensitive: false
        },
        {
          attributeName: 'account_status',
          sourceValue: 'ACTIVE',
          sourceValueKind: 'SCALAR',
          sourceType: 'VARCHAR(16)',
          currentTargetValue: 'SUSPENDED',
          currentTargetValueKind: 'SCALAR',
          currentTargetType: 'VARCHAR(16)',
          proposedTargetValue: 'ACTIVE',
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'VARCHAR(16)',
          isKey: false,
          isSensitive: false,
          transformationNote: 'Direct mapping (Rule R-01)'
        },
        {
          attributeName: 'credit_limit',
          sourceValue: 500000.00,
          sourceValueKind: 'SCALAR',
          sourceType: 'DECIMAL(14,2)',
          currentTargetValue: 250000.00,
          currentTargetValueKind: 'SCALAR',
          currentTargetType: 'DECIMAL(14,2)',
          proposedTargetValue: 500000.00,
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'DECIMAL(14,2)',
          isKey: false,
          isSensitive: false,
          transformationNote: 'Currency alignment to target ledger standard'
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 2,
      targetSystem: 'PostgreSQL Enterprise Cluster',
      targetEndpointLabel: 'Target Analytics & Billing DB',
      targetLocation: 'pg-prod-cluster.internal:5432/enterprise_db',
      estimatedWriteScope: '1 row updated',
      protectedDataInvolved: false,
      revalidationObligation: 'Mandatory Tier 4 Attribute Rescan on Partition part-2026-q3',
      riskLevel: 'LOW',
      riskExplanation: 'Target update affects 1 non-destructive record. Primary key identity is conserved.'
    },
    governance: {
      state: 'APPROVAL_REQUIRED',
      policyId: 'pol-gov-financial-tier2',
      policyName: 'Tier 2 Financial Remediation Policy',
      policySummary: 'Requires single Data Custodian or Lead Validation Engineer approval before target write execution.',
      approvalRequired: true,
      quorumRequired: 1,
      quorumSatisfied: 0,
      makerCheckerSatisfied: false,
      approvers: [
        {
          role: 'Data Custodian / Migration Lead',
          status: 'PENDING'
        }
      ],
      conditions: [
        'Target cluster snapshot verification satisfied',
        'Lease fence token verified on P7B Fabric',
        'Mandatory revalidation schedule attached'
      ],
      boundPlanFingerprint: 'sha256:4f8e91c7a2b53d6e1f0a9b8c7d6e5f4a3b2c1d0e',
      isAuthorized: false,
      authorizationNote: 'Awaiting operator sign-off before dispatching to mutating pipeline.'
    },
    execution: {
      state: 'NOT_STARTED',
      totalOperations: 1,
      appliedCount: 0,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      progressPercent: 0,
      providerCommitState: 'UNCONFIRMED',
      p7bContext: {
        site: 'us-east-dc1',
        placement: 'Worker Node 04 (Governed Executor)',
        locality: 'Local Region',
        residency: 'US-Data-Zone',
        ownershipFencing: 'Fence-Epoch-4921 (Active)',
        recoveryStatus: 'Nominal'
      }
    },
    revalidation: {
      state: 'REQUIRED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PENDING', detail: 'Schema structure unchanged', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PENDING', detail: 'Row count parity', differencesFound: 0 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: 'Hash rescan pending', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PENDING', detail: 'Target row value re-check required', differencesFound: 1 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Revalidation will automatically trigger upon successful repair execution.'
    },
    technicalDetails: {
      proposalId: 'prop-m8-20260907-001',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:4f8e91c7a2b53d6e1f0a9b8c7d6e5f4a3b2c1d0e',
      p7bPlacementDigest: 'sha256:9981a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1',
      checkpointSequence: 'chk-epoch-4921-seq-0082',
      revalidationMissionId: 'vm-20260907-001',
      canonicalDmlStatement: 'UPDATE enterprise_customers SET credit_limit = 500000.00, account_status = \'ACTIVE\', updated_at = \'2026-09-07 12:14:30\' WHERE customer_id = \'CUST-009281\';'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'SINGLE_UPDATE_PROPOSAL'
  },

  // 5. Sensitive Data & Transformation-Aware Proposal
  SENSITIVE_DATA_TRANSFORMATION: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Sensitive Data Proposal — Governance Dual-Approval Required',
      conciseExplanation: 'The proposed remediation affects protected personal and financial data. Fail-closed masking is enforced.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'PENDING',
      executionState: 'NOT_STARTED',
      revalidationState: 'REQUIRED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-sec-88192',
      totalSelectedFindings: 1,
      selectedObjects: ['customer_payment_methods'],
      affectedRecordKeys: ['PAY-99201'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:20:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-sec-20260907-009',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:8829a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'customer_payment_methods',
      recordKey: 'PAY-99201',
      summaryNote: 'Update tokenized payment routing reference and billing postal code.',
      detailedRationale: 'Source transformation token was re-keyed during boundary migration. Target required compensating cryptographic token update.',
      createdAt: '2026-09-07T12:19:00Z',
      proposedChanges: [
        {
          attributeName: 'payment_method_id',
          sourceValue: 'PAY-99201',
          sourceValueKind: 'SCALAR',
          sourceType: 'VARCHAR(32)',
          currentTargetValue: 'PAY-99201',
          currentTargetValueKind: 'SCALAR',
          currentTargetType: 'VARCHAR(32)',
          proposedTargetValue: 'PAY-99201',
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'VARCHAR(32)',
          isKey: true,
          isSensitive: false
        },
        {
          attributeName: 'tokenized_pan',
          sourceValue: '••••••••••••4921',
          sourceValueKind: 'PROTECTED',
          sourceType: 'VARCHAR(64)',
          currentTargetValue: '••••••••••••0000',
          currentTargetValueKind: 'PROTECTED',
          currentTargetType: 'VARCHAR(64)',
          proposedTargetValue: '••••••••••••4921',
          proposedTargetValueKind: 'PROTECTED',
          proposedTargetType: 'VARCHAR(64)',
          isKey: false,
          isSensitive: true,
          transformationNote: 'PCI-DSS Tokenization Vault Transform (T-09)'
        },
        {
          attributeName: 'billing_postal_code',
          sourceValue: '94105',
          sourceValueKind: 'SCALAR',
          sourceType: 'VARCHAR(12)',
          currentTargetValue: null,
          currentTargetValueKind: 'NULL',
          currentTargetType: 'VARCHAR(12)',
          proposedTargetValue: '94105',
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'VARCHAR(12)',
          isKey: false,
          isSensitive: false,
          transformationNote: 'Null fill from canonical source'
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 2,
      targetSystem: 'Oracle Enterprise Cloud DB',
      targetEndpointLabel: 'Target Payment Core',
      targetLocation: 'ora-pay-cluster.internal:1521/paydb',
      estimatedWriteScope: '1 row updated',
      protectedDataInvolved: true,
      revalidationObligation: 'Mandatory Cryptographic Token Re-verification',
      riskLevel: 'HIGH',
      riskExplanation: 'Contains PCI-DSS sensitive data. Dual authorization and cryptographic audit recording enforced.'
    },
    governance: {
      state: 'PENDING',
      policyId: 'pol-gov-pci-strict',
      policyName: 'PCI-DSS Dual-Custodian Policy',
      policySummary: 'Requires two independent security officers to cryptographically sign the repair plan.',
      approvalRequired: true,
      quorumRequired: 2,
      quorumSatisfied: 1,
      makerCheckerSatisfied: true,
      approvers: [
        {
          role: 'Security Officer 1',
          userName: 'm.chen@enterprise.internal',
          status: 'APPROVED',
          timestamp: '2026-09-07T12:21:10Z',
          signatureDigest: 'ed25519:7718aa...b8'
        },
        {
          role: 'Security Officer 2 / Compliance Lead',
          status: 'PENDING'
        }
      ],
      conditions: [
        'HSM Tokenization vault reachable',
        'Audit trail Ed25519 signing enabled',
        'Execution lease bound to single session'
      ],
      boundPlanFingerprint: 'sha256:8829a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8',
      isAuthorized: false,
      authorizationNote: 'Awaiting 2nd signature (Security Officer 2) to complete quorum.'
    },
    execution: {
      state: 'NOT_STARTED',
      totalOperations: 1,
      appliedCount: 0,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      progressPercent: 0,
      providerCommitState: 'UNCONFIRMED'
    },
    revalidation: {
      state: 'REQUIRED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PENDING', detail: 'Schema unchanged', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PENDING', detail: 'Count match', differencesFound: 0 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: 'Hash rescan pending', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PENDING', detail: 'Sensitive attribute comparison pending', differencesFound: 1 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Revalidation will verify token equivalence without exposing raw secrets.'
    },
    technicalDetails: {
      proposalId: 'prop-sec-20260907-009',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:8829a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8',
      evidenceRef: 'aev-audit-sec-20260907-009'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'SENSITIVE_DATA_TRANSFORMATION'
  },

  // 6. Missing Record Insert Proposal
  MISSING_RECORD_INSERT: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Missing Record Proposal — Authorized & Ready',
      conciseExplanation: 'Compensating INSERT proposal is fully authorized by governance policy and ready for controlled execution.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVED',
      executionState: 'NOT_STARTED',
      revalidationState: 'REQUIRED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-ord-missing-1',
      totalSelectedFindings: 1,
      selectedObjects: ['order_line_items'],
      affectedRecordKeys: ['ORD-LINE-882190-03'],
      findingCategories: ['MISSING_ON_TARGET'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:25:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-ins-20260907-044',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:11223344556677889900aabbccddeeff00112233',
      operationFamily: 'INSERT_MISSING_TARGET',
      targetObject: 'order_line_items',
      recordKey: 'ORD-LINE-882190-03',
      summaryNote: 'Insert missing order line record into target database with canonical transformation mappings applied.',
      detailedRationale: 'Source record was committed during initial boundary scan but was omitted on target due to an interrupted ETL batch.',
      createdAt: '2026-09-07T12:24:00Z',
      canonicalDmlPreview: 'INSERT INTO order_line_items (line_id, order_id, sku, quantity, unit_price) VALUES (\'ORD-LINE-882190-03\', \'ORD-882190\', \'SKU-4921\', 2, 49.99);',
      proposedChanges: [
        {
          attributeName: 'line_id',
          sourceValue: 'ORD-LINE-882190-03',
          sourceValueKind: 'SCALAR',
          sourceType: 'VARCHAR(32)',
          currentTargetValue: null,
          currentTargetValueKind: 'ABSENT',
          currentTargetType: 'VARCHAR(32)',
          proposedTargetValue: 'ORD-LINE-882190-03',
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'VARCHAR(32)',
          isKey: true,
          isSensitive: false
        },
        {
          attributeName: 'order_id',
          sourceValue: 'ORD-882190',
          sourceValueKind: 'SCALAR',
          sourceType: 'VARCHAR(32)',
          currentTargetValue: null,
          currentTargetValueKind: 'ABSENT',
          currentTargetType: 'VARCHAR(32)',
          proposedTargetValue: 'ORD-882190',
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'VARCHAR(32)',
          isKey: false,
          isSensitive: false
        },
        {
          attributeName: 'quantity',
          sourceValue: 2,
          sourceValueKind: 'SCALAR',
          sourceType: 'INT',
          currentTargetValue: null,
          currentTargetValueKind: 'ABSENT',
          currentTargetType: 'INT',
          proposedTargetValue: 2,
          proposedTargetValueKind: 'SCALAR',
          proposedTargetType: 'INT',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 3,
      targetSystem: 'MySQL Aurora Cluster',
      targetEndpointLabel: 'Target Order Fulfillment DB',
      targetLocation: 'aurora-orders.internal:3306/orders',
      estimatedWriteScope: '1 row inserted',
      protectedDataInvolved: false,
      revalidationObligation: 'Mandatory Tier 2 Cardinality & Tier 4 Attribute Rescan',
      riskLevel: 'LOW',
      riskExplanation: 'Insert operation. No existing target data will be overwritten.'
    },
    governance: {
      state: 'APPROVED',
      policyId: 'pol-gov-standard',
      policyName: 'Standard Remediation Policy',
      policySummary: 'Single lead approval satisfies quorum for non-destructive insert operations.',
      approvalRequired: true,
      quorumRequired: 1,
      quorumSatisfied: 1,
      makerCheckerSatisfied: true,
      approvers: [
        {
          role: 'Validation Lead',
          userName: 'a.ladwa@akaal.internal',
          status: 'APPROVED',
          timestamp: '2026-09-07T12:24:45Z',
          signatureDigest: 'ed25519:3381ba...f1'
        }
      ],
      conditions: ['Idempotency conflict check passed'],
      boundPlanFingerprint: 'sha256:11223344556677889900aabbccddeeff00112233',
      expiresAt: '2026-09-07T18:00:00Z',
      isAuthorized: true,
      authorizationNote: 'Plan is fully authorized and within valid lease window.'
    },
    execution: {
      state: 'NOT_STARTED',
      totalOperations: 1,
      appliedCount: 0,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      progressPercent: 0,
      providerCommitState: 'UNCONFIRMED'
    },
    revalidation: {
      state: 'REQUIRED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PENDING', detail: 'Schema verified', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PENDING', detail: 'Row count delta will resolve to 0', differencesFound: 1 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: 'Hash rescan pending', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PENDING', detail: 'New row attribute match check pending', differencesFound: 1 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Validation #11 will verify the inserted record matches canonical proof rules.'
    },
    technicalDetails: {
      proposalId: 'prop-ins-20260907-044',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:11223344556677889900aabbccddeeff00112233',
      canonicalDmlStatement: 'INSERT INTO order_line_items (line_id, order_id, sku, quantity, unit_price) VALUES (\'ORD-LINE-882190-03\', \'ORD-882190\', \'SKU-4921\', 2, 49.99);'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'MISSING_RECORD_INSERT'
  },

  // 7. Extra Record Deletion Proposal (Consequential Destructive Action)
  EXTRA_RECORD_DELETE: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Destructive Deletion Proposal — High Consequence Action',
      conciseExplanation: 'Compensating DELETE proposal will permanently remove an orphaned record from the target database.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVAL_REQUIRED',
      executionState: 'NOT_STARTED',
      revalidationState: 'REQUIRED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-del-extra-1',
      totalSelectedFindings: 1,
      selectedObjects: ['legacy_sync_journal'],
      affectedRecordKeys: ['JRN-ORPHAN-9901'],
      findingCategories: ['EXTRA_ON_TARGET'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:30:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-del-20260907-012',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:ffeeddccbbaa99887766554433221100ffeeddcc',
      operationFamily: 'DELETE_EXTRA_TARGET',
      targetObject: 'legacy_sync_journal',
      recordKey: 'JRN-ORPHAN-9901',
      summaryNote: 'Delete unreferenced target record not present in canonical source dataset.',
      detailedRationale: 'Validation Tier 2 detected +1 extra row on target endpoint created during aborted test script.',
      createdAt: '2026-09-07T12:29:00Z',
      canonicalDmlPreview: 'DELETE FROM legacy_sync_journal WHERE journal_id = \'JRN-ORPHAN-9901\';',
      proposedChanges: [
        {
          attributeName: 'journal_id',
          sourceValue: null,
          sourceValueKind: 'ABSENT',
          sourceType: 'VARCHAR(32)',
          currentTargetValue: 'JRN-ORPHAN-9901',
          currentTargetValueKind: 'SCALAR',
          currentTargetType: 'VARCHAR(32)',
          proposedTargetValue: null,
          proposedTargetValueKind: 'ABSENT',
          proposedTargetType: 'VARCHAR(32)',
          isKey: true,
          isSensitive: false
        },
        {
          attributeName: 'payload_data',
          sourceValue: null,
          sourceValueKind: 'ABSENT',
          sourceType: 'TEXT',
          currentTargetValue: '{"test_flag": true, "session": "orphaned_test"}',
          currentTargetValueKind: 'SCALAR',
          currentTargetType: 'TEXT',
          proposedTargetValue: null,
          proposedTargetValueKind: 'ABSENT',
          proposedTargetType: 'TEXT',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 2,
      targetSystem: 'PostgreSQL Enterprise Cluster',
      targetEndpointLabel: 'Target Journal Storage',
      targetLocation: 'pg-prod-cluster.internal:5432/enterprise_db',
      estimatedWriteScope: '1 row deleted (DESTRUCTIVE)',
      protectedDataInvolved: false,
      revalidationObligation: 'Mandatory Tier 2 Cardinality Rescan',
      riskLevel: 'CONSEQUENTIAL_DESTRUCTIVE',
      riskExplanation: 'Target record will be permanently deleted. Ensure backup snapshot is confirmed before sign-off.'
    },
    governance: {
      state: 'APPROVAL_REQUIRED',
      policyId: 'pol-gov-destructive-delete',
      policyName: 'Destructive Action Governance Policy',
      policySummary: 'Requires explicit deletion confirmation and Dual Custodian authorization.',
      approvalRequired: true,
      quorumRequired: 2,
      quorumSatisfied: 0,
      makerCheckerSatisfied: false,
      approvers: [
        { role: 'Database Administrator', status: 'PENDING' },
        { role: 'Validation Lead', status: 'PENDING' }
      ],
      conditions: [
        'Target table backup snapshot confirmed within last 60 minutes',
        'Foreign key constraint integrity verified'
      ],
      boundPlanFingerprint: 'sha256:ffeeddccbbaa99887766554433221100ffeeddcc',
      isAuthorized: false,
      authorizationNote: 'Awaiting dual sign-off for destructive target operation.'
    },
    execution: {
      state: 'NOT_STARTED',
      totalOperations: 1,
      appliedCount: 0,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      progressPercent: 0,
      providerCommitState: 'UNCONFIRMED'
    },
    revalidation: {
      state: 'REQUIRED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PENDING', detail: 'Schema verified', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PENDING', detail: 'Delta will reduce from +1 to 0', differencesFound: 1 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: 'Hash rescan pending', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PENDING', detail: 'Target row absence check pending', differencesFound: 0 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Revalidation will confirm complete removal of extra target record.'
    },
    technicalDetails: {
      proposalId: 'prop-del-20260907-012',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:ffeeddccbbaa99887766554433221100ffeeddcc',
      canonicalDmlStatement: 'DELETE FROM legacy_sync_journal WHERE journal_id = \'JRN-ORPHAN-9901\';'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'EXTRA_RECORD_DELETE'
  },

  // 8. Structural Remediation Unsupported
  STRUCTURAL_UNSUPPORTED: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Automatic Remediation Unsupported — Manual DDL Required',
      conciseExplanation: 'Schema structural differences cannot be safely remediated via automated row-level mutation. Manual DDL migration is required.',
      eligibility: 'INELIGIBLE',
      proposalState: 'UNAVAILABLE',
      governanceState: 'NOT_EVALUATED',
      executionState: 'UNAVAILABLE',
      revalidationState: 'REQUIRED',
      isExecutorAvailable: false,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-struct-01',
      totalSelectedFindings: 1,
      selectedObjects: ['product_catalog_v2'],
      affectedRecordKeys: ['TABLE_DEFINITION'],
      findingCategories: ['STRUCTURAL_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:35:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-struct-none',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:0000000000000000000000000000000000000000',
      operationFamily: 'STRUCTURAL_UNSUPPORTED',
      targetObject: 'product_catalog_v2',
      recordKey: 'TABLE_DEFINITION',
      summaryNote: 'Automatic schema remediation is unavailable for structural column definition mismatches.',
      detailedRationale: 'Source column type is JSONB whereas Target column type is TEXT. Automated DDL altering table types carries schema locking and truncation risk.',
      createdAt: '2026-09-07T12:34:00Z',
      proposedChanges: []
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 0,
      affectedAttributesCount: 1,
      targetSystem: 'PostgreSQL Enterprise Cluster',
      targetEndpointLabel: 'Target Analytics DB',
      targetLocation: 'pg-prod-cluster.internal:5432/enterprise_db',
      estimatedWriteScope: '0 rows (DDL required)',
      protectedDataInvolved: false,
      revalidationObligation: 'Mandatory Tier 1 Structural Re-evaluation',
      riskLevel: 'HIGH',
      riskExplanation: 'Manual schema alignment required outside controlled data repair pipeline.'
    },
    governance: null,
    execution: null,
    revalidation: {
      state: 'REQUIRED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'FAILED', detail: 'Column type mismatch (JSONB vs TEXT)', differencesFound: 1 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PASSED', detail: 'Row count parity verified', differencesFound: 0 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: 'Pending structural resolution', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PENDING', detail: 'Pending structural resolution', differencesFound: 0 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Validation #11 Tier 1 Structural verification will re-run once DDL migration is applied.'
    },
    technicalDetails: {
      revalidationMissionId: 'vm-20260907-001'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'STRUCTURAL_UNSUPPORTED'
  },

  // 9. Governance Rejection State
  APPROVAL_REJECTED: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Repair Proposal Rejected by Governance',
      conciseExplanation: 'The proposed remediation was reviewed and rejected. No mutations were dispatched to the target system.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'REJECTED',
      executionState: 'NOT_STARTED',
      revalidationState: 'NOT_REQUIRED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-disc-rejected',
      totalSelectedFindings: 1,
      selectedObjects: ['customer_balances'],
      affectedRecordKeys: ['BAL-99012'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:40:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-rej-20260907-099',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:7766554433221100aabbccddeeff001122334455',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'customer_balances',
      recordKey: 'BAL-99012',
      summaryNote: 'Proposed overwrite of customer settlement balance.',
      detailedRationale: 'Rejected: Source update originated from an uncommitted month-end staging batch.',
      createdAt: '2026-09-07T12:38:00Z',
      proposedChanges: [
        {
          attributeName: 'balance_amount',
          sourceValue: 12500.00,
          sourceValueKind: 'SCALAR',
          currentTargetValue: 10000.00,
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 12500.00,
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 1,
      targetSystem: 'Oracle Enterprise Cloud DB',
      targetEndpointLabel: 'Target Settlement Core',
      targetLocation: 'ora-pay-cluster.internal:1521/paydb',
      estimatedWriteScope: '1 row (BLOCKED)',
      protectedDataInvolved: false,
      revalidationObligation: 'None (Operation Rejected)',
      riskLevel: 'MEDIUM',
      riskExplanation: 'Execution blocked by governance rejection.'
    },
    governance: {
      state: 'REJECTED',
      policyId: 'pol-gov-financial-tier2',
      policyName: 'Tier 2 Financial Remediation Policy',
      policySummary: 'Requires sign-off from Finance Controller.',
      approvalRequired: true,
      quorumRequired: 1,
      quorumSatisfied: 0,
      makerCheckerSatisfied: false,
      approvers: [
        {
          role: 'Finance Controller',
          userName: 'e.morales@enterprise.internal',
          status: 'REJECTED',
          timestamp: '2026-09-07T12:41:20Z'
        }
      ],
      conditions: [],
      boundPlanFingerprint: 'sha256:7766554433221100aabbccddeeff001122334455',
      rejectionReason: 'Source discrepancy is an un-settled intraday transfer. Must be reconciled during end-of-day batch.',
      isAuthorized: false,
      authorizationNote: 'Proposal rejected. Target remains untouched.'
    },
    execution: null,
    revalidation: null,
    technicalDetails: {
      proposalId: 'prop-rej-20260907-099',
      proposalFingerprint: 'sha256:7766554433221100aabbccddeeff001122334455'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'APPROVAL_REJECTED'
  },

  // 10. Execution Interrupted with UNKNOWN Commit Outcome (Crucial Hostile Law)
  EXECUTION_INTERRUPTED_UNKNOWN_OUTCOME: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Execution Interrupted — Target Commit Outcome UNKNOWN',
      conciseExplanation: 'Network disconnect occurred during transaction commit. Automatic replay is withheld until provider-native verification resolves ambiguity.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVED',
      executionState: 'OUTCOME_UNKNOWN',
      revalidationState: 'INTERRUPTED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-ambig-990',
      totalSelectedFindings: 1,
      selectedObjects: ['financial_transactions'],
      affectedRecordKeys: ['TXN-2026-881920'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:45:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-ambig-20260907-088',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:abcdef0123456789abcdef0123456789abcdef01',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'financial_transactions',
      recordKey: 'TXN-2026-881920',
      summaryNote: 'Update transaction settlement status.',
      detailedRationale: 'Source transaction reached final confirmed state.',
      createdAt: '2026-09-07T12:44:00Z',
      proposedChanges: [
        {
          attributeName: 'status',
          sourceValue: 'SETTLED',
          sourceValueKind: 'SCALAR',
          currentTargetValue: 'PENDING_SETTLEMENT',
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 'SETTLED',
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 1,
      targetSystem: 'PostgreSQL Enterprise Cluster',
      targetEndpointLabel: 'Target Transaction DB',
      targetLocation: 'pg-prod-cluster.internal:5432/enterprise_db',
      estimatedWriteScope: '1 row (Ambiguous Outcome)',
      protectedDataInvolved: false,
      revalidationObligation: 'Provider-Native Commit Probe Required',
      riskLevel: 'HIGH',
      riskExplanation: 'Ambiguous commit state. Blind retry prohibited by permanent architectural law.'
    },
    governance: {
      state: 'APPROVED',
      policyId: 'pol-gov-financial-tier2',
      policyName: 'Tier 2 Financial Remediation Policy',
      policySummary: 'Approved prior to dispatch.',
      approvalRequired: true,
      quorumRequired: 1,
      quorumSatisfied: 1,
      makerCheckerSatisfied: true,
      approvers: [{ role: 'Lead Validation Engineer', userName: 'a.ladwa@akaal.internal', status: 'APPROVED', timestamp: '2026-09-07T12:45:10Z' }],
      conditions: ['Single execution lock enforced'],
      boundPlanFingerprint: 'sha256:abcdef0123456789abcdef0123456789abcdef01',
      isAuthorized: true
    },
    execution: {
      state: 'OUTCOME_UNKNOWN',
      executionId: 'exec-20260907-00918',
      startedAt: '2026-09-07T12:46:00Z',
      progressPercent: 50,
      totalOperations: 1,
      appliedCount: 0,
      unresolvedCount: 0,
      unknownOutcomeCount: 1,
      providerCommitState: 'UNKNOWN',
      errorMessage: 'SocketTimeoutException: Connection dropped while awaiting PostgreSQL COMMIT ACK packet.',
      unknownOutcomeWarning: 'CRITICAL: The target mutation was submitted to the database provider, but local connection severed before the commit acknowledgement was received. Provider-native verification must establish whether the transaction committed before any further action is permitted.',
      p7bContext: {
        site: 'us-east-dc1',
        placement: 'Worker Node 02',
        locality: 'Local Region',
        residency: 'US-Data-Zone',
        ownershipFencing: 'Fence-Epoch-4922 (Quarantine)',
        recoveryStatus: 'Awaiting Provider Verification'
      }
    },
    revalidation: {
      state: 'INTERRUPTED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PENDING', detail: 'Withheld until outcome resolved', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PENDING', detail: 'Withheld until outcome resolved', differencesFound: 0 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: 'Withheld until outcome resolved', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'WITHHELD', detail: 'Target commit state ambiguous', differencesFound: 1 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Revalidation withheld. Cannot evaluate proof obligations while target transaction state is unknown.'
    },
    technicalDetails: {
      proposalId: 'prop-ambig-20260907-088',
      executionId: 'exec-20260907-00918',
      providerOperationId: 'pg-tx-990812903',
      checkpointSequence: 'chk-epoch-4922-seq-0001',
      recoveryJournalRef: 'rjr-quarantine-4922'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'EXECUTION_INTERRUPTED_UNKNOWN_OUTCOME'
  },

  // 11. Repair Completed — Revalidation Passed
  REVALIDATION_PASSED: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Controlled Repair Completed — Revalidation PASSED',
      conciseExplanation: 'Compensating target mutation executed successfully. Validation #11 re-evaluated the repaired partition and confirmed 100% proof satisfaction.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVED',
      executionState: 'COMPLETED',
      revalidationState: 'PASSED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-pass-001',
      totalSelectedFindings: 1,
      selectedObjects: ['enterprise_customers'],
      affectedRecordKeys: ['CUST-009281'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:50:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-pass-001',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:4f8e91c7a2b53d6e1f0a9b8c7d6e5f4a3b2c1d0e',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'enterprise_customers',
      recordKey: 'CUST-009281',
      summaryNote: 'Update account credit limit and status.',
      detailedRationale: 'Remediated attribute divergence.',
      createdAt: '2026-09-07T12:49:00Z',
      proposedChanges: [
        {
          attributeName: 'account_status',
          sourceValue: 'ACTIVE',
          sourceValueKind: 'SCALAR',
          currentTargetValue: 'ACTIVE',
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 'ACTIVE',
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false
        },
        {
          attributeName: 'credit_limit',
          sourceValue: 500000.00,
          sourceValueKind: 'SCALAR',
          currentTargetValue: 500000.00,
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 500000.00,
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 2,
      targetSystem: 'PostgreSQL Enterprise Cluster',
      targetEndpointLabel: 'Target Analytics & Billing DB',
      targetLocation: 'pg-prod-cluster.internal:5432/enterprise_db',
      estimatedWriteScope: '1 row updated (CONFIRMED)',
      protectedDataInvolved: false,
      revalidationObligation: 'Validation #11 4-Tier Verification (PASSED)',
      riskLevel: 'LOW',
      riskExplanation: 'Mutation applied and verified.'
    },
    governance: {
      state: 'APPROVED',
      policyId: 'pol-gov-financial-tier2',
      policyName: 'Tier 2 Financial Remediation Policy',
      policySummary: 'Approved and executed.',
      approvalRequired: true,
      quorumRequired: 1,
      quorumSatisfied: 1,
      makerCheckerSatisfied: true,
      approvers: [{ role: 'Lead Validation Engineer', userName: 'a.ladwa@akaal.internal', status: 'APPROVED', timestamp: '2026-09-07T12:50:10Z' }],
      conditions: ['All conditions verified'],
      boundPlanFingerprint: 'sha256:4f8e91c7a2b53d6e1f0a9b8c7d6e5f4a3b2c1d0e',
      isAuthorized: true
    },
    execution: {
      state: 'COMPLETED',
      executionId: 'exec-20260907-00991',
      startedAt: '2026-09-07T12:51:00Z',
      completedAt: '2026-09-07T12:51:04Z',
      progressPercent: 100,
      totalOperations: 1,
      appliedCount: 1,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      providerCommitState: 'CONFIRMED',
      p7bContext: {
        site: 'us-east-dc1',
        placement: 'Worker Node 04',
        locality: 'Local Region',
        residency: 'US-Data-Zone',
        ownershipFencing: 'Fence-Epoch-4921 (Released)',
        recoveryStatus: 'Nominal'
      }
    },
    revalidation: {
      state: 'PASSED',
      revalidationId: 'reval-m8-20260907-001',
      engine: 'Validation #11 Canonical Engine',
      startedAt: '2026-09-07T12:51:05Z',
      completedAt: '2026-09-07T12:51:12Z',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PASSED', detail: 'Schema structure 100% matched', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PASSED', detail: 'Exact record count parity (delta = 0)', differencesFound: 0 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PASSED', detail: 'HMAC-SHA256 Multi-tree digest match', differencesFound: 0 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PASSED', detail: 'All attributes verified identical', differencesFound: 0 }
      ],
      remainingDiscrepanciesCount: 0,
      verdictSummary: 'Validation #11 re-evaluated the partition and established complete proof satisfaction across all 4 tiers.'
    },
    technicalDetails: {
      proposalId: 'prop-pass-001',
      executionId: 'exec-20260907-00991',
      providerOperationId: 'pg-tx-10029104',
      revalidationMissionId: 'reval-m8-20260907-001',
      evidenceRef: 'aev-audit-reval-20260907-001'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'REVALIDATION_PASSED'
  },

  // 12. Repair Completed — Revalidation FAILED (Crucial Law: Repair Success != Validation Success)
  REVALIDATION_FAILED: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Repair Executed — But Revalidation FAILED',
      conciseExplanation: 'Target mutation executed successfully, but post-repair Validation #11 rescan detected remaining attribute divergences.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVED',
      executionState: 'COMPLETED',
      revalidationState: 'FAILED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-fail-002',
      totalSelectedFindings: 1,
      selectedObjects: ['financial_ledger_entries'],
      affectedRecordKeys: ['TXN-99120'],
      findingCategories: ['VALUE_DIFFERENCE'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:55:00Z',
      isBulkAggregate: false
    },
    proposal: {
      proposalId: 'prop-fail-002',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:bbccddeeff0011223344556677889900aabbccdd',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'financial_ledger_entries',
      recordKey: 'TXN-99120',
      summaryNote: 'Update posted ledger balance.',
      detailedRationale: 'Remediated posted balance amount.',
      createdAt: '2026-09-07T12:54:00Z',
      proposedChanges: [
        {
          attributeName: 'posted_balance',
          sourceValue: 88400.00,
          sourceValueKind: 'SCALAR',
          currentTargetValue: 88400.00,
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 88400.00,
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 1,
      affectedRecordsCount: 1,
      affectedAttributesCount: 1,
      targetSystem: 'Oracle Enterprise Cloud DB',
      targetEndpointLabel: 'Target Financial Ledger',
      targetLocation: 'ora-pay-cluster.internal:1521/paydb',
      estimatedWriteScope: '1 row updated',
      protectedDataInvolved: false,
      revalidationObligation: 'Validation #11 4-Tier Verification (FAILED)',
      riskLevel: 'MEDIUM',
      riskExplanation: 'Repair succeeded at provider level, but data remains non-compliant with Validation #11 proof rules.'
    },
    governance: {
      state: 'APPROVED',
      policyId: 'pol-gov-financial-tier2',
      policyName: 'Tier 2 Financial Remediation Policy',
      policySummary: 'Approved and executed.',
      approvalRequired: true,
      quorumRequired: 1,
      quorumSatisfied: 1,
      makerCheckerSatisfied: true,
      approvers: [{ role: 'Lead Validation Engineer', status: 'APPROVED', timestamp: '2026-09-07T12:54:30Z' }],
      conditions: [],
      boundPlanFingerprint: 'sha256:bbccddeeff0011223344556677889900aabbccdd',
      isAuthorized: true
    },
    execution: {
      state: 'COMPLETED',
      executionId: 'exec-20260907-00995',
      startedAt: '2026-09-07T12:55:00Z',
      completedAt: '2026-09-07T12:55:03Z',
      progressPercent: 100,
      totalOperations: 1,
      appliedCount: 1,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      providerCommitState: 'CONFIRMED'
    },
    revalidation: {
      state: 'FAILED',
      revalidationId: 'reval-m8-20260907-002',
      engine: 'Validation #11 Canonical Engine',
      startedAt: '2026-09-07T12:55:04Z',
      completedAt: '2026-09-07T12:55:10Z',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PASSED', detail: 'Schema matched', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PASSED', detail: 'Record count matched', differencesFound: 0 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'FAILED', detail: 'Partition hash mismatch persists', differencesFound: 1 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'FAILED', detail: 'Calculated checksum column `calc_hash` diverges on target', differencesFound: 1 }
      ],
      remainingDiscrepanciesCount: 1,
      verdictSummary: 'Validation #11 rescan established that dependent calculated column `calc_hash` remains in divergence. Target is NOT certified.',
      findingsNote: 'Target trigger generated unexpected checksum divergence after update.'
    },
    technicalDetails: {
      proposalId: 'prop-fail-002',
      executionId: 'exec-20260907-00995',
      revalidationMissionId: 'reval-m8-20260907-002'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'REVALIDATION_FAILED'
  },

  // 13. Large Bulk Aggregate Repair (Scalable Bounded Preview)
  LARGE_BULK_REPAIR: {
    viewStatus: 'READY',
    summary: {
      overallState: 'Bulk Repair Proposal Established — 1,420 Operations in Scope',
      conciseExplanation: 'Large-scale batch remediation compiled across 4 enterprise objects. Bounded preview and dual-approval governance active.',
      eligibility: 'ELIGIBLE',
      proposalState: 'ESTABLISHED',
      governanceState: 'APPROVAL_REQUIRED',
      executionState: 'NOT_STARTED',
      revalidationState: 'REQUIRED',
      isExecutorAvailable: true,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'sel-bulk-1420',
      totalSelectedFindings: 1420,
      selectedObjects: ['inventory_records', 'warehouse_stock', 'replenishment_logs', 'bin_allocations'],
      affectedRecordKeys: ['INV-001 ... INV-1420 (Bounded Summary)'],
      findingCategories: ['VALUE_DIFFERENCE', 'MISSING_ON_TARGET'],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T13:00:00Z',
      isBulkAggregate: true
    },
    proposal: {
      proposalId: 'prop-bulk-20260907-0088',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:1234567890abcdef1234567890abcdef12345678',
      operationFamily: 'UPDATE_DIFFERING_ATTRIBUTES',
      targetObject: 'inventory_records (Aggregate Batch)',
      recordKey: 'Bounded Sample: INV-009180',
      summaryNote: 'Batch synchronization of warehouse stock counts and allocation states across 4 partition blocks.',
      detailedRationale: 'Source warehouse ingestion backlog cleared. Target counts require atomic multi-table compensating synchronization.',
      createdAt: '2026-09-07T12:59:00Z',
      canonicalDmlPreview: '-- Bounded DML Batch (1,420 operations)\nUPDATE inventory_records SET quantity_on_hand = 142 WHERE sku_id = \'SKU-9901\';\nINSERT INTO warehouse_stock (bin_id, sku_id, quantity) VALUES (\'BIN-44A\', \'SKU-9901\', 142);\n-- [1,418 additional bounded statements encapsulated in signed plan package]',
      proposedChanges: [
        {
          attributeName: 'sku_id',
          sourceValue: 'SKU-9901',
          sourceValueKind: 'SCALAR',
          currentTargetValue: 'SKU-9901',
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 'SKU-9901',
          proposedTargetValueKind: 'SCALAR',
          isKey: true,
          isSensitive: false
        },
        {
          attributeName: 'quantity_on_hand',
          sourceValue: 142,
          sourceValueKind: 'SCALAR',
          currentTargetValue: 110,
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 142,
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false,
          transformationNote: 'Warehouse delta recalculation'
        },
        {
          attributeName: 'bin_location',
          sourceValue: 'BIN-44A',
          sourceValueKind: 'SCALAR',
          currentTargetValue: 'BIN-UNKNOWN',
          currentTargetValueKind: 'SCALAR',
          proposedTargetValue: 'BIN-44A',
          proposedTargetValueKind: 'SCALAR',
          isKey: false,
          isSensitive: false
        }
      ]
    },
    impact: {
      affectedObjectsCount: 4,
      affectedRecordsCount: 1420,
      affectedAttributesCount: 4260,
      targetSystem: 'PostgreSQL Enterprise Cluster',
      targetEndpointLabel: 'Target Inventory DB',
      targetLocation: 'pg-prod-cluster.internal:5432/inventory',
      estimatedWriteScope: '1,420 rows (1,280 updates, 140 inserts)',
      protectedDataInvolved: false,
      revalidationObligation: 'Mandatory Full Partition Rescan (Partitions p-01, p-02, p-03, p-04)',
      riskLevel: 'HIGH',
      riskExplanation: 'Large batch mutation. Dual governance approval and phased chunking required.'
    },
    governance: {
      state: 'APPROVAL_REQUIRED',
      policyId: 'pol-gov-bulk-operations',
      policyName: 'Bulk Mutation Operations Policy (>1,000 Rows)',
      policySummary: 'Requires dual sign-off from Migration Architect and Operations Lead.',
      approvalRequired: true,
      quorumRequired: 2,
      quorumSatisfied: 0,
      makerCheckerSatisfied: false,
      approvers: [
        { role: 'Migration Architect', status: 'PENDING' },
        { role: 'Operations Lead', status: 'PENDING' }
      ],
      conditions: [
        'Batch chunk size configured to 500 rows per transaction',
        'Checkpoint recovery journal initialized',
        'P7B Fabric worker fence verified'
      ],
      boundPlanFingerprint: 'sha256:1234567890abcdef1234567890abcdef12345678',
      isAuthorized: false,
      authorizationNote: 'Awaiting dual sign-off for bulk batch execution.'
    },
    execution: {
      state: 'NOT_STARTED',
      totalOperations: 1420,
      appliedCount: 0,
      unresolvedCount: 0,
      unknownOutcomeCount: 0,
      progressPercent: 0,
      providerCommitState: 'UNCONFIRMED',
      p7bContext: {
        site: 'us-east-dc1',
        placement: 'Worker Pool (4 Dedicated Nodes)',
        locality: 'Local Region',
        residency: 'US-Data-Zone',
        ownershipFencing: 'Fence-Epoch-4930 (Active)',
        recoveryStatus: 'Nominal'
      }
    },
    revalidation: {
      state: 'REQUIRED',
      engine: 'Validation #11 Canonical Engine',
      proofTiers: [
        { tier: 'Tier 1', name: 'Structural Schema', status: 'PENDING', detail: '4 objects schema check', differencesFound: 0 },
        { tier: 'Tier 2', name: 'Cardinality', status: 'PENDING', detail: 'Aggregate delta check (+140 missing)', differencesFound: 140 },
        { tier: 'Tier 3', name: 'Partition Fingerprint', status: 'PENDING', detail: '4 partition block hashes', differencesFound: 4 },
        { tier: 'Tier 4', name: 'Attribute Logical Diff', status: 'PENDING', detail: 'Batch sample diff verification', differencesFound: 1420 }
      ],
      remainingDiscrepanciesCount: 1420,
      verdictSummary: 'Validation #11 will rescan all 4 affected partition blocks post-execution.'
    },
    technicalDetails: {
      proposalId: 'prop-bulk-20260907-0088',
      proposalVersion: 'v1.0.0',
      proposalFingerprint: 'sha256:1234567890abcdef1234567890abcdef12345678',
      checkpointSequence: 'chk-bulk-epoch-4930-seq-0001',
      p7bPlacementDigest: 'sha256:bulk-pool-digest-4930'
    },
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'LARGE_BULK_REPAIR'
  },

  // 14. Loading Skeleton State
  LOADING_SKELETON: {
    viewStatus: 'LOADING',
    summary: {
      overallState: 'Loading Remediation Context...',
      conciseExplanation: 'Retrieving canonical repair proposals, governance policies, and revalidation state.',
      eligibility: 'NOT_EVALUATED',
      proposalState: 'UNAVAILABLE',
      governanceState: 'NOT_EVALUATED',
      executionState: 'NOT_STARTED',
      revalidationState: 'NOT_REQUIRED',
      isExecutorAvailable: false,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'loading',
      totalSelectedFindings: 0,
      selectedObjects: [],
      affectedRecordKeys: [],
      findingCategories: [],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:00:00Z',
      isBulkAggregate: false
    },
    proposal: null,
    impact: null,
    governance: null,
    execution: null,
    revalidation: null,
    technicalDetails: null,
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'LOADING_SKELETON'
  },

  // 15. Error State
  ERROR_STATE: {
    viewStatus: 'ERROR',
    summary: {
      overallState: 'Data Retrieval Error',
      conciseExplanation: 'Failed to retrieve repair proposal from canonical governance authority.',
      eligibility: 'UNAVAILABLE',
      proposalState: 'UNAVAILABLE',
      governanceState: 'UNAVAILABLE',
      executionState: 'UNAVAILABLE',
      revalidationState: 'UNAVAILABLE',
      isExecutorAvailable: false,
      isReadonlyMission: false
    },
    selectedScope: {
      selectionSetId: 'error',
      totalSelectedFindings: 0,
      selectedObjects: [],
      affectedRecordKeys: [],
      findingCategories: [],
      originatingWorkspace: 'DISCREPANCIES',
      selectionTimestamp: '2026-09-07T12:00:00Z',
      isBulkAggregate: false
    },
    proposal: null,
    impact: null,
    governance: null,
    execution: null,
    revalidation: null,
    technicalDetails: null,
    errorMessage: 'GatewayTimeout: Governance policy service unreachable at endpoint https://gov.akaal.internal/v1/policies/pol-gov-financial-tier2',
    isConfirmModalOpen: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'ERROR_STATE'
  }
};
