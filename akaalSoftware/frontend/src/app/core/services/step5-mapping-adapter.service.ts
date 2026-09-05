import { Injectable } from '@angular/core';
import { PhysicalProviderId, MigrationMode } from '../models/migration-view.models';
import {
  Step5MappingPacket,
  ObjectMappingContract,
  TranspilerObjectContract,
  CapabilityOptionRef,
  NamespaceRoutingRule,
  PrivacyItemContract,
  CleansingItemContract,
  FilterItemContract,
  DeduplicationItemContract,
  QualityItemContract,
  CompatibilityHelperRef
} from '../../modules/migration/create/steps/step5-mapping.models';

/**
 * Step5MappingAdapterService
 *
 * P7.D INTEGRATION BOUNDARY:
 * This service acts strictly as an adapter boundary between upstream backend IPC packets
 * and the frontend Step 5 UI state store.
 *
 * In this UI-only phase, it provides declarative contract snapshot packets for development
 * and testing without any algorithmic mapping, type conversion, or SQL transpilation in Angular.
 *
 * When P7.D is implemented, this adapter will connect to akaalIPC.GetProposedMapping(draftId)
 * and stream live canonical packets directly into Step5MappingStore without changing any UI code.
 */
@Injectable({
  providedIn: 'root'
})
export class Step5MappingAdapterService {

  /**
   * Universal Capability-Driven Privacy Options (Canonical vocabulary)
   */
  public readonly defaultPrivacyOptions: CapabilityOptionRef[] = [
    { id: 'NONE', label: 'None (Unmasked)', description: 'Data passes unchanged' },
    { id: 'STATIC_REDACT', label: 'Static Redact', description: 'Replace with fixed literal string', requiresParam: true, paramLabel: 'Redaction literal', paramPlaceholder: 'REDACTED' },
    { id: 'PARTIAL_MASK', label: 'Partial Mask', description: 'Mask characters except first and last N', requiresParam: true, paramLabel: 'Mask pattern', paramPlaceholder: 'keep_first=2,keep_last=2' },
    { id: 'NULLIFY', label: 'Nullify', description: 'Replace with NULL value' },
    { id: 'HASH', label: 'Cryptographic Hash (SHA-256)', description: 'One-way cryptographic hash' },
    { id: 'KEYED_PSEUDONYM', label: 'Keyed Pseudonym', description: 'Deterministic pseudonym using vault key reference', requiresParam: true, paramLabel: 'Secret reference', paramPlaceholder: 'vault://keys/customer-pseudo' },
    { id: 'FORMAT_PRESERVING_MASK', label: 'Format-Preserving Mask', description: 'Preserves string length, digit, and alphabetic shape' }
  ];

  /**
   * Universal Capability-Driven Cleansing Options (Canonical vocabulary)
   */
  public readonly defaultCleansingOptions: CapabilityOptionRef[] = [
    { id: 'NONE', label: 'None', description: 'No value transformation' },
    { id: 'TRIM', label: 'Trim Whitespace', description: 'Strip leading and trailing whitespace' },
    { id: 'UPPERCASE', label: 'Uppercase', description: 'Convert all characters to uppercase' },
    { id: 'LOWERCASE', label: 'Lowercase', description: 'Convert all characters to lowercase' },
    { id: 'DEFAULT', label: 'Default Fallback', description: 'Replace NULL or empty values with fallback literal', requiresParam: true, paramLabel: 'Default value', paramPlaceholder: 'N/A' },
    { id: 'REGEX_REPLACE', label: 'Regex Replace', description: 'Pattern-based substitution', requiresParam: true, paramLabel: 'Pattern & replacement', paramPlaceholder: 's/[^0-9]//g' }
  ];

  /**
   * Canonical Deduplication Survivor Policies (Backend contract aligned)
   */
  public readonly defaultSurvivorPolicyOptions: CapabilityOptionRef[] = [
    { id: 'FIRST', label: 'First Record (Earliest in stream)', description: 'Preserves first received record' },
    { id: 'LAST', label: 'Last Record (Latest Wins)', description: 'Overwrites existing keys with latest record' },
    { id: 'MIN_FIELD', label: 'Minimum Field Value', description: 'Selects record with smallest value in key field', requiresParam: true, paramLabel: 'Comparison field', paramPlaceholder: 'seq_id' },
    { id: 'MAX_FIELD', label: 'Maximum Field Value', description: 'Selects record with largest value in key field', requiresParam: true, paramLabel: 'Comparison field', paramPlaceholder: 'version' },
    { id: 'NEWEST', label: 'Newest Timestamp', description: 'Uses newest record by row timestamp', requiresParam: true, paramLabel: 'Timestamp field', paramPlaceholder: 'updated_at' },
    { id: 'OLDEST', label: 'Oldest Timestamp', description: 'Uses oldest record by row timestamp', requiresParam: true, paramLabel: 'Timestamp field', paramPlaceholder: 'created_at' },
    { id: 'PRIORITY', label: 'Priority Matrix', description: 'Selects record matching highest priority source value', requiresParam: true, paramLabel: 'Priority field', paramPlaceholder: 'source_system' },
    { id: 'FAIL_ON_DUPLICATE', label: 'Fail on Duplicate', description: 'Abort migration job if duplicate key occurs' },
    { id: 'REJECT_GROUP', label: 'Reject Duplicate Group', description: 'Drop all rows sharing the duplicate key' },
    { id: 'QUARANTINE_GROUP', label: 'Quarantine Group', description: 'Move duplicates to isolated quarantine storage' }
  ];

  /**
   * Retrieves the contract snapshot packet for the current migration context.
   * Declarative snapshot only — zero algorithmic inference in the frontend.
   */
  public getProposedMappingPacket(
    sourceProvider: PhysicalProviderId,
    targetProvider: PhysicalProviderId,
    mode: MigrationMode,
    scopedNodeIds?: string[]
  ): Step5MappingPacket {
    if (sourceProvider === 'MongoDB') {
      return this.createMongoDbSnapshot(targetProvider, mode);
    }
    if (sourceProvider === 'Apache Kafka') {
      return this.createKafkaSnapshot(targetProvider, mode);
    }
    if (sourceProvider === 'Amazon S3') {
      return this.createS3StorageSnapshot(targetProvider, mode);
    }

    // Default: Relational Snapshot (Oracle 19c -> PostgreSQL 16)
    return this.createRelationalSnapshot(sourceProvider, targetProvider, mode);
  }

  // =========================================================================
  // DECLARATIVE SNAPSHOT 1: RELATIONAL (Oracle -> PostgreSQL)
  // =========================================================================
  private createRelationalSnapshot(
    source: PhysicalProviderId,
    target: PhysicalProviderId,
    mode: MigrationMode
  ): Step5MappingPacket {
    const isDataOnly = mode === 'M7_DATA_ONLY';
    const isSchemaOnly = mode === 'M6_SCHEMA_ONLY';

    const namespaces: NamespaceRoutingRule[] = [
      {
        sourceNamespace: 'CORE_BANKING',
        proposedTargetNamespace: 'public',
        currentTargetNamespace: 'public',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        advancedPattern: '',
        advancedReplacement: '',
        affectedObjectsCount: 83,
        isModified: false,
        originalProposal: {
          targetNamespace: 'public',
          prefix: '',
          suffix: ''
        }
      },
      {
        sourceNamespace: 'PAYMENTS',
        proposedTargetNamespace: 'payments_prod',
        currentTargetNamespace: 'payments_prod',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        advancedPattern: '',
        advancedReplacement: '',
        affectedObjectsCount: 42,
        isModified: false,
        originalProposal: {
          targetNamespace: 'payments_prod',
          prefix: '',
          suffix: ''
        }
      },
      {
        sourceNamespace: 'CRM',
        proposedTargetNamespace: 'crm_stage',
        currentTargetNamespace: 'crm_stage',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        affectedObjectsCount: 29,
        isModified: false,
        originalProposal: {
          targetNamespace: 'crm_stage',
          prefix: '',
          suffix: ''
        }
      },
      {
        sourceNamespace: 'ARCHIVE',
        proposedTargetNamespace: 'archive_historical',
        currentTargetNamespace: 'archive_historical',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        affectedObjectsCount: 149,
        isModified: false,
        originalProposal: {
          targetNamespace: 'archive_historical',
          prefix: '',
          suffix: ''
        }
      }
    ];

    const objects: ObjectMappingContract[] = [
      {
        id: 'obj-customers',
        sourceName: 'CUSTOMERS',
        sourceNamespace: 'CORE_BANKING',
        sourceType: 'TABLE',
        sourceTypeLabel: 'Table',
        proposedTargetNamespace: 'public',
        currentTargetNamespace: 'public',
        proposedTargetName: 'customers',
        currentTargetName: 'customers',
        isIncluded: true,
        rowFilterMode: 'ALL',
        deduplication: {
          enabled: true,
          keyFields: ['tax_identifier', 'email'],
          survivorPolicy: 'NEWEST',
          priorityField: 'updated_at',
          duplicateDisposition: 'LOG_AND_DISCARD'
        },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 4,
          rewiredFkCount: 4,
          indexesCount: 7,
          dependentObjectsCount: 7,
          requiresGovernanceWaiver: true,
          dependentObjects: [
            { type: 'FOREIGN_KEY', name: 'FK_ORDERS_CUSTOMER', relation: 'ORDERS.customer_id -> CUSTOMERS.customer_id', impactDescription: 'Foreign key will be dropped or rewired to target table' },
            { type: 'FOREIGN_KEY', name: 'FK_PAYMENTS_CUSTOMER', relation: 'PAYMENTS.customer_id -> CUSTOMERS.customer_id', impactDescription: 'Foreign key reference constraint' },
            { type: 'FOREIGN_KEY', name: 'FK_ACCOUNTS_CUSTOMER', relation: 'ACCOUNTS.customer_id -> CUSTOMERS.customer_id', impactDescription: 'Cascade constraint rule' },
            { type: 'VIEW', name: 'V_ACTIVE_CUSTOMERS', impactDescription: 'Dependent view requires target table existence' },
            { type: 'VIEW', name: 'V_CUSTOMER_BALANCES', impactDescription: 'Dependent view requires target table existence' },
            { type: 'TRIGGER', name: 'TRG_AUDIT_CUSTOMERS', impactDescription: 'Row-level audit trigger will be detached' },
            { type: 'PROCEDURE', name: 'CLOSE_ACCOUNT', impactDescription: 'Procedural validation depends on customer status' }
          ]
        },
        uiWorkState: 'AUTOMATIC',
        conversionSafety: 'SEMANTICALLY_EQUIVALENT',
        readiness: 'READY',
        status: 'AUTO_MAPPED',
        issues: [],
        originalProposal: {
          targetNamespace: 'public',
          targetName: 'customers',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: {
            enabled: true,
            keyFields: ['tax_identifier', 'email'],
            survivorPolicy: 'NEWEST',
            priorityField: 'updated_at',
            duplicateDisposition: 'LOG_AND_DISCARD'
          }
        },
        columns: [
          {
            id: 'col-cust-id',
            sourceField: 'CUSTOMER_ID',
            sourceType: 'NUMBER(18)',
            proposedTargetField: 'customer_id',
            currentTargetField: 'customer_id',
            proposedTargetType: 'BIGINT',
            currentTargetType: 'BIGINT',
            targetTypeOptions: ['BIGINT', 'INTEGER', 'NUMERIC(18,0)', 'VARCHAR(32)'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'SEMANTICALLY_EQUIVALENT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            privacyOptionId: 'KEYED_PSEUDONYM',
            privacyParam: 'vault://keys/customer-pseudo',
            originalProposal: { targetField: 'customer_id', targetType: 'BIGINT', isIncluded: true }
          },
          {
            id: 'col-cust-first',
            sourceField: 'FIRST_NAME',
            sourceType: 'VARCHAR2(80)',
            proposedTargetField: 'first_name',
            currentTargetField: 'first_name',
            proposedTargetType: 'VARCHAR',
            currentTargetType: 'VARCHAR',
            sourceLength: 80,
            proposedLength: 80,
            currentLength: 80,
            targetTypeOptions: ['VARCHAR', 'TEXT', 'CHAR(80)'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'SEMANTICALLY_EQUIVALENT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            cleansingOptionId: 'TRIM',
            originalProposal: { targetField: 'first_name', targetType: 'VARCHAR', length: 80, isIncluded: true }
          },
          {
            id: 'col-cust-last',
            sourceField: 'LAST_NAME',
            sourceType: 'VARCHAR2(80)',
            proposedTargetField: 'last_name',
            currentTargetField: 'last_name',
            proposedTargetType: 'VARCHAR',
            currentTargetType: 'VARCHAR',
            sourceLength: 80,
            proposedLength: 80,
            currentLength: 80,
            targetTypeOptions: ['VARCHAR', 'TEXT', 'CHAR(80)'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'SEMANTICALLY_EQUIVALENT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            cleansingOptionId: 'TRIM',
            originalProposal: { targetField: 'last_name', targetType: 'VARCHAR', length: 80, isIncluded: true }
          },
          {
            id: 'col-cust-email',
            sourceField: 'EMAIL',
            sourceType: 'VARCHAR2(255)',
            proposedTargetField: 'email_address',
            currentTargetField: 'email_address',
            proposedTargetType: 'VARCHAR',
            currentTargetType: 'VARCHAR',
            sourceLength: 255,
            proposedLength: 255,
            currentLength: 255,
            targetTypeOptions: ['VARCHAR', 'TEXT', 'CITEXT'],
            isIncluded: true,
            uiWorkState: 'MODIFIED',
            conversionSafety: 'SEMANTICALLY_EQUIVALENT',
            readiness: 'READY',
            status: 'MODIFIED',
            isModified: true,
            privacyOptionId: 'PARTIAL_MASK',
            privacyParam: 'preserve_last=4',
            originalProposal: { targetField: 'email', targetType: 'VARCHAR', length: 255, isIncluded: true }
          },
          {
            id: 'col-cust-tax',
            sourceField: 'TAX_IDENTIFIER',
            sourceType: 'VARCHAR2(20)',
            proposedTargetField: 'tax_identifier',
            currentTargetField: 'tax_identifier',
            proposedTargetType: 'VARCHAR',
            currentTargetType: 'VARCHAR',
            sourceLength: 20,
            proposedLength: 20,
            currentLength: 20,
            targetTypeOptions: ['VARCHAR', 'TEXT'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            privacyOptionId: 'HASH',
            originalProposal: { targetField: 'tax_identifier', targetType: 'VARCHAR', length: 20, isIncluded: true }
          },
          {
            id: 'col-cust-phone',
            sourceField: 'PHONE_NUMBER',
            sourceType: 'VARCHAR2(30)',
            proposedTargetField: 'phone_number',
            currentTargetField: 'phone_number',
            proposedTargetType: 'VARCHAR',
            currentTargetType: 'VARCHAR',
            sourceLength: 30,
            proposedLength: 30,
            currentLength: 30,
            targetTypeOptions: ['VARCHAR', 'TEXT'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            cleansingOptionId: 'TRIM',
            originalProposal: { targetField: 'phone_number', targetType: 'VARCHAR', length: 30, isIncluded: true }
          },
          {
            id: 'col-cust-balance',
            sourceField: 'BALANCE',
            sourceType: 'NUMBER(38,8)',
            proposedTargetField: 'balance',
            currentTargetField: 'balance',
            proposedTargetType: 'DECIMAL(18,4)',
            currentTargetType: 'DECIMAL(18,4)',
            sourcePrecision: 38,
            sourceScale: 8,
            proposedPrecision: 18,
            proposedScale: 4,
            currentPrecision: 18,
            currentScale: 4,
            targetTypeOptions: ['DECIMAL(18,4)', 'NUMERIC(38,8)', 'DOUBLE PRECISION', 'MONEY'],
            isIncluded: true,
            uiWorkState: 'NEEDS_REVIEW',
            conversionSafety: 'LOSSY',
            readiness: 'READY_WITH_WARNINGS',
            status: 'NEEDS_REVIEW',
            lossinessReasons: ['TARGET_PRECISION_INSUFFICIENT', 'SCALE_REDUCTION_LOSSY'],
            issues: [
              {
                id: 'iss-balance-lossy',
                severity: 'NEEDS_REVIEW',
                code: 'SCALE_REDUCTION_LOSSY',
                title: 'Potential Precision and Scale Loss',
                reason: 'Target precision reduced from 38 to 18 and scale reduced from 8 to 4. Fractional cents or high-value accounts may truncate.',
                recommendation: 'Override target type to NUMERIC(38,8) to prevent mathematical truncation.',
                affectedField: 'BALANCE',
                lossinessReasons: ['TARGET_PRECISION_INSUFFICIENT', 'SCALE_REDUCTION_LOSSY']
              }
            ],
            originalProposal: { targetField: 'balance', targetType: 'DECIMAL(18,4)', precision: 18, scale: 4, isIncluded: true }
          },
          {
            id: 'col-cust-legacy',
            sourceField: 'LEGACY_FLAG',
            sourceType: 'CHAR(1)',
            proposedTargetField: '—',
            currentTargetField: '—',
            proposedTargetType: '—',
            currentTargetType: '—',
            isIncluded: false,
            uiWorkState: 'MODIFIED',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'MODIFIED',
            isModified: true,
            originalProposal: { targetField: 'legacy_flag', targetType: 'BOOLEAN', isIncluded: true }
          },
          {
            id: 'col-cust-created',
            sourceField: 'CREATED_AT',
            sourceType: 'TIMESTAMP WITH TIME ZONE',
            proposedTargetField: 'created_at',
            currentTargetField: 'created_at',
            proposedTargetType: 'TIMESTAMPTZ',
            currentTargetType: 'TIMESTAMPTZ',
            targetTypeOptions: ['TIMESTAMPTZ', 'TIMESTAMP'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'created_at', targetType: 'TIMESTAMPTZ', isIncluded: true }
          },
          {
            id: 'col-cust-updated',
            sourceField: 'UPDATED_AT',
            sourceType: 'TIMESTAMP WITH TIME ZONE',
            proposedTargetField: 'updated_at',
            currentTargetField: 'updated_at',
            proposedTargetType: 'TIMESTAMPTZ',
            currentTargetType: 'TIMESTAMPTZ',
            targetTypeOptions: ['TIMESTAMPTZ', 'TIMESTAMP'],
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'updated_at', targetType: 'TIMESTAMPTZ', isIncluded: true }
          }
        ]
      },
      {
        id: 'obj-accounts',
        sourceName: 'ACCOUNTS',
        sourceNamespace: 'CORE_BANKING',
        sourceType: 'TABLE',
        sourceTypeLabel: 'Table',
        proposedTargetNamespace: 'public',
        currentTargetNamespace: 'public',
        proposedTargetName: 'accounts',
        currentTargetName: 'accounts',
        isIncluded: true,
        rowFilterMode: 'ALL',
        deduplication: {
          enabled: false,
          keyFields: ['account_number'],
          survivorPolicy: 'FIRST'
        },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 2,
          rewiredFkCount: 2,
          indexesCount: 5,
          dependentObjectsCount: 3,
          dependentObjects: [
            { type: 'FOREIGN_KEY', name: 'FK_TXN_ACCOUNT', relation: 'TRANSACTIONS.account_id -> ACCOUNTS.account_id', impactDescription: 'Foreign key rewiring' }
          ]
        },
        uiWorkState: 'AUTOMATIC',
        conversionSafety: 'SEMANTICALLY_EQUIVALENT',
        readiness: 'READY',
        status: 'AUTO_MAPPED',
        issues: [],
        originalProposal: {
          targetNamespace: 'public',
          targetName: 'accounts',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: {
            enabled: false,
            keyFields: ['account_number'],
            survivorPolicy: 'FIRST'
          }
        },
        columns: [
          {
            id: 'col-acc-id',
            sourceField: 'ACCOUNT_ID',
            sourceType: 'NUMBER(18)',
            proposedTargetField: 'account_id',
            currentTargetField: 'account_id',
            proposedTargetType: 'BIGINT',
            currentTargetType: 'BIGINT',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'SEMANTICALLY_EQUIVALENT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'account_id', targetType: 'BIGINT', isIncluded: true }
          },
          {
            id: 'col-acc-num',
            sourceField: 'ACCOUNT_NUMBER',
            sourceType: 'VARCHAR2(34)',
            proposedTargetField: 'account_number',
            currentTargetField: 'account_number',
            proposedTargetType: 'VARCHAR(34)',
            currentTargetType: 'VARCHAR(34)',
            sourceLength: 34,
            proposedLength: 34,
            currentLength: 34,
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'account_number', targetType: 'VARCHAR(34)', isIncluded: true }
          },
          {
            id: 'col-acc-status',
            sourceField: 'STATUS',
            sourceType: 'VARCHAR2(16)',
            proposedTargetField: 'status',
            currentTargetField: 'status',
            proposedTargetType: 'VARCHAR(16)',
            currentTargetType: 'VARCHAR(16)',
            sourceLength: 16,
            proposedLength: 16,
            currentLength: 16,
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'status', targetType: 'VARCHAR(16)', isIncluded: true }
          }
        ]
      },
      {
        id: 'obj-transactions',
        sourceName: 'TRANSACTIONS',
        sourceNamespace: 'CORE_BANKING',
        sourceType: 'TABLE',
        sourceTypeLabel: 'Table',
        proposedTargetNamespace: 'public',
        currentTargetNamespace: 'public',
        proposedTargetName: 'transactions',
        currentTargetName: 'transactions',
        isIncluded: true,
        rowFilterMode: 'CUSTOM',
        rowFilterPredicate: 'tx_date >= \'2023-01-01\'',
        deduplication: {
          enabled: true,
          keyFields: ['txn_reference_code'],
          survivorPolicy: 'FIRST',
          duplicateDisposition: 'LOG_AND_DISCARD'
        },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 3,
          rewiredFkCount: 3,
          indexesCount: 8,
          dependentObjectsCount: 4,
          dependentObjects: []
        },
        originalProposal: {
          targetNamespace: 'public',
          targetName: 'transactions',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: {
            enabled: false,
            keyFields: ['txn_reference_code'],
            survivorPolicy: 'FIRST'
          }
        },
        uiWorkState: 'MODIFIED',
        conversionSafety: 'SEMANTICALLY_EQUIVALENT',
        readiness: 'READY',
        status: 'MODIFIED',
        isModified: true,
        issues: [],
        columns: [
          {
            id: 'col-txn-id',
            sourceField: 'TXN_ID',
            sourceType: 'NUMBER(18)',
            proposedTargetField: 'txn_id',
            currentTargetField: 'txn_id',
            proposedTargetType: 'BIGINT',
            currentTargetType: 'BIGINT',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'txn_id', targetType: 'BIGINT', isIncluded: true }
          },
          {
            id: 'col-txn-amt',
            sourceField: 'AMOUNT',
            sourceType: 'NUMBER(18,2)',
            proposedTargetField: 'amount',
            currentTargetField: 'amount',
            proposedTargetType: 'NUMERIC(18,2)',
            currentTargetType: 'NUMERIC(18,2)',
            sourcePrecision: 18,
            sourceScale: 2,
            proposedPrecision: 18,
            proposedScale: 2,
            currentPrecision: 18,
            currentScale: 2,
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'amount', targetType: 'NUMERIC(18,2)', isIncluded: true }
          }
        ]
      },
      {
        id: 'obj-payments',
        sourceName: 'PAYMENTS',
        sourceNamespace: 'PAYMENTS',
        sourceType: 'TABLE',
        sourceTypeLabel: 'Table',
        proposedTargetNamespace: 'payments_prod',
        currentTargetNamespace: 'payments_prod',
        proposedTargetName: 'payments',
        currentTargetName: 'payments',
        isIncluded: true,
        rowFilterMode: 'ALL',
        deduplication: {
          enabled: false,
          keyFields: ['payment_id'],
          survivorPolicy: 'FIRST'
        },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 2,
          rewiredFkCount: 2,
          indexesCount: 4,
          dependentObjectsCount: 2,
          dependentObjects: []
        },
        originalProposal: {
          targetNamespace: 'payments_prod',
          targetName: 'payments',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: {
            enabled: false,
            keyFields: ['payment_id'],
            survivorPolicy: 'FIRST'
          }
        },
        uiWorkState: 'AUTOMATIC',
        conversionSafety: 'EXACT',
        readiness: 'READY',
        status: 'AUTO_MAPPED',
        issues: [],
        columns: [
          {
            id: 'col-pay-id',
            sourceField: 'PAYMENT_ID',
            sourceType: 'NUMBER(18)',
            proposedTargetField: 'payment_id',
            currentTargetField: 'payment_id',
            proposedTargetType: 'BIGINT',
            currentTargetType: 'BIGINT',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'payment_id', targetType: 'BIGINT', isIncluded: true }
          }
        ]
      },
      {
        id: 'obj-archive-cust',
        sourceName: 'CUSTOMERS',
        sourceNamespace: 'ARCHIVE',
        sourceType: 'TABLE',
        sourceTypeLabel: 'Table',
        proposedTargetNamespace: 'archive_historical',
        currentTargetNamespace: 'archive_historical',
        proposedTargetName: 'customers_archive',
        currentTargetName: 'customers_archive',
        isIncluded: false,
        rowFilterMode: 'ALL',
        deduplication: {
          enabled: false,
          keyFields: ['customer_id'],
          survivorPolicy: 'FIRST'
        },
        structuralImpact: {
          primaryKeyStatus: 'REMOVED',
          foreignKeysCount: 3,
          rewiredFkCount: 0,
          indexesCount: 2,
          dependentObjectsCount: 3,
          requiresGovernanceWaiver: true,
          dependentObjects: [
            { type: 'FOREIGN_KEY', name: 'FK_ARCHIVE_ORDERS', relation: 'ARCHIVE_ORDERS.customer_id -> ARCHIVE.CUSTOMERS.customer_id', impactDescription: 'Exclusion drops 3 dependent historical foreign keys' },
            { type: 'VIEW', name: 'V_ARCHIVE_ANALYTICS', impactDescription: 'Exclusion breaks historical reporting view' }
          ]
        },
        originalProposal: {
          targetNamespace: 'archive_historical',
          targetName: 'customers_archive',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: {
            enabled: false,
            keyFields: ['customer_id'],
            survivorPolicy: 'FIRST'
          }
        },
        uiWorkState: 'MODIFIED',
        conversionSafety: 'USER_DECISION_REQUIRED',
        readiness: 'WAIVER_REQUIRED',
        status: 'MODIFIED',
        isModified: true,
        issues: [
          {
            id: 'iss-arch-cust-gov',
            severity: 'NEEDS_REVIEW',
            code: 'DEPENDENCY_GOVERNANCE_REQUIRED',
            title: 'Exclusion Requires Governance Review',
            reason: 'Exclusion of ARCHIVE.CUSTOMERS affects 3 dependent foreign keys and historical reporting views.',
            recommendation: 'Ensure governance sign-off or re-include object to maintain referential integrity.'
          }
        ],
        columns: []
      }
    ];

    // Data Controls Lists
    const privacyItems: PrivacyItemContract[] = [
      {
        id: 'priv-1',
        objectId: 'obj-customers',
        fieldId: 'col-cust-id',
        objectName: 'CUSTOMERS',
        fieldName: 'CUSTOMER_ID',
        strategy: 'KEYED_PSEUDONYM',
        strategyLabel: 'Keyed Pseudonym',
        configuration: 'vault://keys/customer-pseudo',
        secretReference: 'vault://keys/customer-pseudo',
        status: 'READY',
        originalProposal: {
          strategy: 'KEYED_PSEUDONYM',
          configuration: 'vault://keys/customer-pseudo',
          secretReference: 'vault://keys/customer-pseudo'
        }
      },
      {
        id: 'priv-2',
        objectId: 'obj-customers',
        fieldId: 'col-cust-email',
        objectName: 'CUSTOMERS',
        fieldName: 'EMAIL',
        strategy: 'PARTIAL_MASK',
        strategyLabel: 'Partial Mask',
        configuration: 'Preserve last 4 chars',
        status: 'READY',
        originalProposal: {
          strategy: 'PARTIAL_MASK',
          configuration: 'Preserve last 4 chars'
        }
      },
      {
        id: 'priv-3',
        objectId: 'obj-customers',
        fieldId: 'col-cust-tax',
        objectName: 'CUSTOMERS',
        fieldName: 'TAX_IDENTIFIER',
        strategy: 'HASH',
        strategyLabel: 'Cryptographic Hash',
        configuration: 'SHA-256',
        status: 'READY',
        originalProposal: {
          strategy: 'HASH',
          configuration: 'SHA-256'
        }
      }
    ];

    const cleansingItems: CleansingItemContract[] = [
      {
        id: 'cln-1',
        objectId: 'obj-customers',
        fieldId: 'col-cust-first',
        objectName: 'CUSTOMERS',
        fieldName: 'FIRST_NAME',
        ruleType: 'TRIM',
        ruleTypeLabel: 'Trim Whitespace',
        orderIndex: 1,
        status: 'READY',
        originalProposal: { ruleType: 'TRIM' }
      },
      {
        id: 'cln-2',
        objectId: 'obj-customers',
        fieldId: 'col-cust-last',
        objectName: 'CUSTOMERS',
        fieldName: 'LAST_NAME',
        ruleType: 'TRIM',
        ruleTypeLabel: 'Trim Whitespace',
        orderIndex: 2,
        status: 'READY',
        originalProposal: { ruleType: 'TRIM' }
      },
      {
        id: 'cln-3',
        objectId: 'obj-customers',
        fieldId: 'col-cust-phone',
        objectName: 'CUSTOMERS',
        fieldName: 'PHONE_NUMBER',
        ruleType: 'TRIM',
        ruleTypeLabel: 'Trim Whitespace',
        orderIndex: 3,
        status: 'READY',
        originalProposal: { ruleType: 'TRIM' }
      }
    ];

    const filterItems: FilterItemContract[] = [
      {
        id: 'flt-1',
        objectId: 'obj-transactions',
        objectName: 'TRANSACTIONS',
        mode: 'CUSTOM',
        predicate: 'tx_date >= \'2023-01-01\'',
        status: 'CONFIGURED',
        originalProposal: { mode: 'CUSTOM', predicate: 'tx_date >= \'2023-01-01\'' }
      },
      {
        id: 'flt-2',
        objectId: 'obj-customers',
        objectName: 'CUSTOMERS',
        mode: 'ALL',
        status: 'READY',
        originalProposal: { mode: 'ALL' }
      },
      {
        id: 'flt-3',
        objectId: 'obj-accounts',
        objectName: 'ACCOUNTS',
        mode: 'ALL',
        status: 'READY',
        originalProposal: { mode: 'ALL' }
      }
    ];

    const deduplicationItems: DeduplicationItemContract[] = [
      {
        id: 'dedup-1',
        objectId: 'obj-customers',
        objectName: 'CUSTOMERS',
        enabled: true,
        keyFields: ['tax_identifier', 'email'],
        survivorPolicy: 'NEWEST',
        survivorPolicyLabel: 'Newest Timestamp (Latest Wins)',
        priorityField: 'updated_at',
        disposition: 'LOG_AND_DISCARD',
        status: 'CONFIGURED',
        originalProposal: {
          enabled: true,
          keyFields: ['tax_identifier', 'email'],
          survivorPolicy: 'NEWEST',
          priorityField: 'updated_at',
          disposition: 'LOG_AND_DISCARD'
        }
      },
      {
        id: 'dedup-2',
        objectId: 'obj-transactions',
        objectName: 'TRANSACTIONS',
        enabled: true,
        keyFields: ['txn_reference_code'],
        survivorPolicy: 'FIRST',
        survivorPolicyLabel: 'First Record (Earliest in stream)',
        disposition: 'LOG_AND_DISCARD',
        status: 'CONFIGURED',
        originalProposal: {
          enabled: true,
          keyFields: ['txn_reference_code'],
          survivorPolicy: 'FIRST',
          disposition: 'LOG_AND_DISCARD'
        }
      }
    ];

    const qualityItems: QualityItemContract[] = [
      {
        id: 'qual-1',
        objectId: 'obj-customers',
        fieldId: 'col-cust-id',
        objectName: 'CUSTOMERS',
        fieldName: 'CUSTOMER_ID',
        ruleType: 'NOT_NULL',
        ruleLabel: 'Must Not Be NULL',
        disposition: 'FAIL_JOB',
        dispositionLabel: 'Fail Job Immediately',
        status: 'READY',
        originalProposal: { ruleType: 'NOT_NULL', disposition: 'FAIL_JOB' }
      },
      {
        id: 'qual-2',
        objectId: 'obj-customers',
        fieldId: 'col-cust-balance',
        objectName: 'CUSTOMERS',
        fieldName: 'BALANCE',
        ruleType: 'NUMERIC_OVERFLOW',
        ruleLabel: 'Numeric Overflow Check',
        constraintValue: '< 1000000000000',
        disposition: 'QUARANTINE_RECORD',
        dispositionLabel: 'Quarantine Record',
        status: 'CONFIGURED',
        originalProposal: { ruleType: 'NUMERIC_OVERFLOW', constraintValue: '< 1000000000000', disposition: 'QUARANTINE_RECORD' }
      },
      {
        id: 'qual-3',
        objectId: 'obj-customers',
        fieldId: 'col-cust-tax',
        objectName: 'CUSTOMERS',
        fieldName: 'TAX_IDENTIFIER',
        ruleType: 'REGEX_MATCH',
        ruleLabel: 'Regex Pattern Match',
        constraintValue: '^[A-Z0-9]{9,12}$',
        disposition: 'REJECT_RECORD',
        dispositionLabel: 'Reject Record to Dead-Letter',
        status: 'READY',
        originalProposal: { ruleType: 'REGEX_MATCH', constraintValue: '^[A-Z0-9]{9,12}$', disposition: 'REJECT_RECORD' }
      }
    ];

    // Procedural Code Objects
    const codeObjects: TranspilerObjectContract[] = isDataOnly ? [] : [
      {
        id: 'code-close-account',
        name: 'BANKING_API.CLOSE_ACCOUNT',
        category: 'PROCEDURE',
        categoryLabel: 'Procedure',
        sourceLanguage: 'Oracle PL/SQL',
        targetLanguage: 'PostgreSQL PL/pgSQL',
        status: 'NEEDS_REVIEW',
        lifecycleState: 'MANUAL_REVIEW_REQUIRED',
        sourceCode: `CREATE OR REPLACE PROCEDURE close_account (
    p_account_id IN NUMBER,
    p_reason IN VARCHAR2,
    p_closed_by IN VARCHAR2,
    p_status OUT VARCHAR2
) IS
    v_balance NUMBER(18,2);
    v_open_txns NUMBER;
BEGIN
    SELECT balance INTO v_balance FROM accounts WHERE account_id = p_account_id FOR UPDATE;
    IF v_balance > 0 THEN
        p_status := 'ERR_NONZERO_BALANCE';
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_open_txns FROM transactions
    WHERE account_id = p_account_id AND status = 'PENDING';

    IF v_open_txns > 0 THEN
        p_status := 'ERR_PENDING_TXNS';
        RETURN;
    END IF;

    UPDATE accounts
    SET status = 'CLOSED',
        closed_at = SYSDATE,
        closure_reason = p_reason
    WHERE account_id = p_account_id;

    INSERT INTO audit_log(entity_type, entity_id, action, performed_by, timestamp)
    VALUES ('ACCOUNT', p_account_id, 'CLOSE', p_closed_by, SYSDATE);

    p_status := 'SUCCESS';
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        p_status := 'ERR_NOT_FOUND';
    WHEN OTHERS THEN
        p_status := 'ERR_INTERNAL: ' || SQLERRM;
END close_account;`,
        proposedTargetCode: `CREATE OR REPLACE PROCEDURE banking_api.close_account(
    IN p_account_id BIGINT,
    IN p_reason VARCHAR,
    IN p_closed_by VARCHAR,
    OUT p_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_balance NUMERIC(18,2);
    v_open_txns BIGINT;
BEGIN
    SELECT balance INTO v_balance FROM public.accounts WHERE account_id = p_account_id FOR UPDATE;
    IF v_balance > 0 THEN
        p_status := 'ERR_NONZERO_BALANCE';
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_open_txns FROM public.transactions
    WHERE account_id = p_account_id AND status = 'PENDING';

    IF v_open_txns > 0 THEN
        p_status := 'ERR_PENDING_TXNS';
        RETURN;
    END IF;

    UPDATE public.accounts
    SET status = 'CLOSED',
        closed_at = CURRENT_TIMESTAMP,
        closure_reason = p_reason
    WHERE account_id = p_account_id;

    INSERT INTO public.audit_log(entity_type, entity_id, action, performed_by, "timestamp")
    VALUES ('ACCOUNT', p_account_id, 'CLOSE', p_closed_by, CURRENT_TIMESTAMP);

    p_status := 'SUCCESS';
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        p_status := 'ERR_NOT_FOUND';
    WHEN OTHERS THEN
        p_status := 'ERR_INTERNAL: ' || SQLERRM;
END;
$$;`,
        currentTargetCode: `CREATE OR REPLACE PROCEDURE banking_api.close_account(
    IN p_account_id BIGINT,
    IN p_reason VARCHAR,
    IN p_closed_by VARCHAR,
    OUT p_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_balance NUMERIC(18,2);
    v_open_txns BIGINT;
BEGIN
    SELECT balance INTO v_balance FROM public.accounts WHERE account_id = p_account_id FOR UPDATE;
    IF v_balance > 0 THEN
        p_status := 'ERR_NONZERO_BALANCE';
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_open_txns FROM public.transactions
    WHERE account_id = p_account_id AND status = 'PENDING';

    IF v_open_txns > 0 THEN
        p_status := 'ERR_PENDING_TXNS';
        RETURN;
    END IF;

    UPDATE public.accounts
    SET status = 'CLOSED',
        closed_at = CURRENT_TIMESTAMP,
        closure_reason = p_reason
    WHERE account_id = p_account_id;

    INSERT INTO public.audit_log(entity_type, entity_id, action, performed_by, "timestamp")
    VALUES ('ACCOUNT', p_account_id, 'CLOSE', p_closed_by, CURRENT_TIMESTAMP);

    p_status := 'SUCCESS';
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        p_status := 'ERR_NOT_FOUND';
    WHEN OTHERS THEN
        p_status := 'ERR_INTERNAL: ' || SQLERRM;
END;
$$;`,
        diagnostics: [
          {
            id: 'diag-1',
            severity: 'WARNING',
            line: 12,
            column: 17,
            construct: 'FOR UPDATE',
            message: 'Row lock semantics in PostgreSQL differ under REPEATABLE READ isolation.',
            recommendation: 'Verify target transaction isolation level in postgresql.conf.'
          },
          {
            id: 'diag-2',
            severity: 'INFO',
            line: 27,
            column: 9,
            construct: 'SYSDATE -> CURRENT_TIMESTAMP',
            message: 'Replaced Oracle SYSDATE with PostgreSQL standard CURRENT_TIMESTAMP.',
            recommendation: 'No manual intervention required.'
          }
        ],
        originalProposal: {
          targetCode: `CREATE OR REPLACE PROCEDURE banking_api.close_account(
    IN p_account_id BIGINT,
    IN p_reason VARCHAR,
    IN p_closed_by VARCHAR,
    OUT p_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_balance NUMERIC(18,2);
    v_open_txns BIGINT;
BEGIN
    SELECT balance INTO v_balance FROM public.accounts WHERE account_id = p_account_id FOR UPDATE;
    IF v_balance > 0 THEN
        p_status := 'ERR_NONZERO_BALANCE';
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_open_txns FROM public.transactions
    WHERE account_id = p_account_id AND status = 'PENDING';

    IF v_open_txns > 0 THEN
        p_status := 'ERR_PENDING_TXNS';
        RETURN;
    END IF;

    UPDATE public.accounts
    SET status = 'CLOSED',
        closed_at = CURRENT_TIMESTAMP,
        closure_reason = p_reason
    WHERE account_id = p_account_id;

    INSERT INTO public.audit_log(entity_type, entity_id, action, performed_by, "timestamp")
    VALUES ('ACCOUNT', p_account_id, 'CLOSE', p_closed_by, CURRENT_TIMESTAMP);

    p_status := 'SUCCESS';
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        p_status := 'ERR_NOT_FOUND';
    WHEN OTHERS THEN
        p_status := 'ERR_INTERNAL: ' || SQLERRM;
END;
$$;`
        }
      },
      {
        id: 'code-calc-fee',
        name: 'BANKING_API.CALC_FEE',
        category: 'FUNCTION',
        categoryLabel: 'Function',
        sourceLanguage: 'Oracle PL/SQL',
        targetLanguage: 'PostgreSQL PL/pgSQL',
        status: 'CONVERTED',
        lifecycleState: 'CONVERTED',
        sourceCode: `CREATE OR REPLACE FUNCTION calc_fee (
    p_amount IN NUMBER,
    p_tier IN VARCHAR2
) RETURN NUMBER IS
    v_rate NUMBER(5,4);
BEGIN
    IF p_tier = 'PLATINUM' THEN
        v_rate := 0.0010;
    ELSIF p_tier = 'GOLD' THEN
        v_rate := 0.0025;
    ELSE
        v_rate := 0.0050;
    END IF;
    RETURN ROUND(p_amount * v_rate, 2);
END calc_fee;`,
        proposedTargetCode: `CREATE OR REPLACE FUNCTION banking_api.calc_fee(
    p_amount NUMERIC,
    p_tier VARCHAR
) RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_rate NUMERIC(5,4);
BEGIN
    IF p_tier = 'PLATINUM' THEN
        v_rate := 0.0010;
    ELSIF p_tier = 'GOLD' THEN
        v_rate := 0.0025;
    ELSE
        v_rate := 0.0050;
    END IF;
    RETURN ROUND(p_amount * v_rate, 2);
END;
$$;`,
        currentTargetCode: `CREATE OR REPLACE FUNCTION banking_api.calc_fee(
    p_amount NUMERIC,
    p_tier VARCHAR
) RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_rate NUMERIC(5,4);
BEGIN
    IF p_tier = 'PLATINUM' THEN
        v_rate := 0.0010;
    ELSIF p_tier = 'GOLD' THEN
        v_rate := 0.0025;
    ELSE
        v_rate := 0.0050;
    END IF;
    RETURN ROUND(p_amount * v_rate, 2);
END;
$$;`,
        diagnostics: [],
        originalProposal: { targetCode: `CREATE OR REPLACE FUNCTION banking_api.calc_fee(...)` }
      }
    ];

    const compatibilityHelpers: CompatibilityHelperRef[] = [
      {
        name: 'akaal_nvl',
        category: 'NULL Handling',
        affectedRoutines: ['BANKING_API.CLOSE_ACCOUNT', 'CALC_FEE', 'GET_RATE'],
        rationale: 'Emulates Oracle NVL(expr1, expr2) with exact type coercion matching Oracle rules.',
        installSql: 'CREATE OR REPLACE FUNCTION public.nvl(anyelement, anyelement) RETURNS anyelement AS $$ SELECT COALESCE($1, $2); $$ LANGUAGE sql IMMUTABLE;'
      },
      {
        name: 'akaal_decode',
        category: 'Control Flow',
        affectedRoutines: ['CALC_FEE', 'AUDIT_CUSTOMER'],
        rationale: 'Emulates Oracle DECODE expression evaluation.',
        installSql: 'CREATE OR REPLACE FUNCTION public.decode(variadic text[]) RETURNS text AS $$ ... $$ LANGUAGE plpgsql;'
      },
      {
        name: 'akaal_instr',
        category: 'String Evaluation',
        affectedRoutines: ['BANKING_API.VALIDATE_IBAN'],
        rationale: 'Emulates 1-indexed Oracle INSTR substring search.',
        installSql: 'CREATE OR REPLACE FUNCTION public.instr(string text, substring text, position int default 1, occurrence int default 1) RETURNS int AS $$ ... $$ LANGUAGE plpgsql;'
      },
      {
        name: 'dbms_output_emulation',
        category: 'Diagnostics Logging',
        affectedRoutines: ['BANKING_API.CLOSE_ACCOUNT'],
        rationale: 'Routes DBMS_OUTPUT.PUT_LINE calls to PostgreSQL RAISE NOTICE.',
        installSql: 'CREATE SCHEMA IF NOT EXISTS dbms_output; CREATE OR REPLACE PROCEDURE dbms_output.put_line(msg text) AS $$ BEGIN RAISE NOTICE \'% \', msg; END; $$ LANGUAGE plpgsql;'
      }
    ];

    return {
      objects,
      namespaces,
      codeObjects,
      compatibilityHelpers,
      privacyItems,
      cleansingItems,
      filterItems,
      deduplicationItems,
      qualityItems,
      privacyOptions: this.defaultPrivacyOptions,
      cleansingOptions: this.defaultCleansingOptions,
      survivorPolicyOptions: this.defaultSurvivorPolicyOptions
    };
  }

  // =========================================================================
  // DECLARATIVE SNAPSHOT 2: DOCUMENT (MongoDB -> PostgreSQL / Kafka)
  // =========================================================================
  private createMongoDbSnapshot(target: PhysicalProviderId, mode: MigrationMode): Step5MappingPacket {
    const namespaces: NamespaceRoutingRule[] = [
      {
        sourceNamespace: 'storefront',
        proposedTargetNamespace: 'store_data',
        currentTargetNamespace: 'store_data',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        affectedObjectsCount: 2,
        originalProposal: { targetNamespace: 'store_data', prefix: '', suffix: '' }
      }
    ];

    const objects: ObjectMappingContract[] = [
      {
        id: 'obj-mongo-orders',
        sourceName: 'orders',
        sourceNamespace: 'storefront',
        sourceType: 'COLLECTION',
        sourceTypeLabel: 'Collection',
        proposedTargetNamespace: 'store_data',
        currentTargetNamespace: 'store_data',
        proposedTargetName: 'orders_collection',
        currentTargetName: 'orders_collection',
        isIncluded: true,
        rowFilterMode: 'ALL',
        deduplication: { enabled: false, keyFields: ['_id'], survivorPolicy: 'FIRST' },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 0,
          rewiredFkCount: 0,
          indexesCount: 2,
          dependentObjectsCount: 0,
          dependentObjects: []
        },
        originalProposal: {
          targetNamespace: 'store_data',
          targetName: 'orders_collection',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: { enabled: false, keyFields: ['_id'], survivorPolicy: 'FIRST' }
        },
        uiWorkState: 'AUTOMATIC',
        conversionSafety: 'COMPATIBLE_WITH_TRANSFORMATION',
        readiness: 'READY',
        status: 'AUTO_MAPPED',
        issues: [],
        columns: [
          {
            id: 'col-m-id',
            sourceField: '_id',
            sourceType: 'ObjectId',
            proposedTargetField: 'id',
            currentTargetField: 'id',
            proposedTargetType: 'VARCHAR(24)',
            currentTargetType: 'VARCHAR(24)',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'COMPATIBLE_WITH_TRANSFORMATION',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'id', targetType: 'VARCHAR(24)', isIncluded: true }
          },
          {
            id: 'col-m-doc',
            sourceField: 'payload',
            sourceType: 'BSON Document',
            proposedTargetField: 'data',
            currentTargetField: 'data',
            proposedTargetType: 'JSONB',
            currentTargetType: 'JSONB',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'data', targetType: 'JSONB', isIncluded: true }
          }
        ]
      }
    ];

    return {
      objects,
      namespaces,
      codeObjects: [],
      compatibilityHelpers: [],
      privacyItems: [],
      cleansingItems: [],
      filterItems: [],
      deduplicationItems: [],
      qualityItems: [],
      privacyOptions: this.defaultPrivacyOptions,
      cleansingOptions: this.defaultCleansingOptions,
      survivorPolicyOptions: this.defaultSurvivorPolicyOptions
    };
  }

  // =========================================================================
  // DECLARATIVE SNAPSHOT 3: STREAMING (Kafka -> S3 / PostgreSQL)
  // =========================================================================
  private createKafkaSnapshot(target: PhysicalProviderId, mode: MigrationMode): Step5MappingPacket {
    const namespaces: NamespaceRoutingRule[] = [
      {
        sourceNamespace: 'cluster-prod',
        proposedTargetNamespace: 'kafka_events',
        currentTargetNamespace: 'kafka_events',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        affectedObjectsCount: 1,
        originalProposal: { targetNamespace: 'kafka_events', prefix: '', suffix: '' }
      }
    ];

    const objects: ObjectMappingContract[] = [
      {
        id: 'obj-kafka-events',
        sourceName: 'payment-events',
        sourceNamespace: 'cluster-prod',
        sourceType: 'TOPIC',
        sourceTypeLabel: 'Topic',
        proposedTargetNamespace: 'kafka_events',
        currentTargetNamespace: 'kafka_events',
        proposedTargetName: 'payment_events_sink',
        currentTargetName: 'payment_events_sink',
        isIncluded: true,
        rowFilterMode: 'ALL',
        deduplication: { enabled: true, keyFields: ['event_id'], survivorPolicy: 'FIRST' },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 0,
          rewiredFkCount: 0,
          indexesCount: 0,
          dependentObjectsCount: 0,
          dependentObjects: []
        },
        originalProposal: {
          targetNamespace: 'kafka_events',
          targetName: 'payment_events_sink',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: { enabled: true, keyFields: ['event_id'], survivorPolicy: 'FIRST' }
        },
        uiWorkState: 'AUTOMATIC',
        conversionSafety: 'EXACT',
        readiness: 'READY',
        status: 'AUTO_MAPPED',
        issues: [],
        columns: [
          {
            id: 'col-k-key',
            sourceField: 'message.key',
            sourceType: 'BYTEA',
            proposedTargetField: 'key',
            currentTargetField: 'key',
            proposedTargetType: 'TEXT',
            currentTargetType: 'TEXT',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'key', targetType: 'TEXT', isIncluded: true }
          },
          {
            id: 'col-k-val',
            sourceField: 'message.value',
            sourceType: 'AVRO / JSON',
            proposedTargetField: 'payload',
            currentTargetField: 'payload',
            proposedTargetType: 'JSONB',
            currentTargetType: 'JSONB',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'payload', targetType: 'JSONB', isIncluded: true }
          }
        ]
      }
    ];

    return {
      objects,
      namespaces,
      codeObjects: [],
      compatibilityHelpers: [],
      privacyItems: [],
      cleansingItems: [],
      filterItems: [],
      deduplicationItems: [],
      qualityItems: [],
      privacyOptions: this.defaultPrivacyOptions,
      cleansingOptions: this.defaultCleansingOptions,
      survivorPolicyOptions: this.defaultSurvivorPolicyOptions
    };
  }

  // =========================================================================
  // DECLARATIVE SNAPSHOT 4: OBJECT STORAGE (Amazon S3 -> Snowflake)
  // =========================================================================
  private createS3StorageSnapshot(target: PhysicalProviderId, mode: MigrationMode): Step5MappingPacket {
    const namespaces: NamespaceRoutingRule[] = [
      {
        sourceNamespace: 'finance-lake',
        proposedTargetNamespace: 'landing_zone',
        currentTargetNamespace: 'landing_zone',
        origin: 'AUTOMATIC',
        prefix: '',
        suffix: '',
        affectedObjectsCount: 1,
        originalProposal: { targetNamespace: 'landing_zone', prefix: '', suffix: '' }
      }
    ];

    const objects: ObjectMappingContract[] = [
      {
        id: 'obj-s3-logs',
        sourceName: 'audit-logs/2026/',
        sourceNamespace: 'finance-lake',
        sourceType: 'BUCKET',
        sourceTypeLabel: 'Bucket',
        proposedTargetNamespace: 'landing_zone',
        currentTargetNamespace: 'landing_zone',
        proposedTargetName: 'audit_logs_landing',
        currentTargetName: 'audit_logs_landing',
        isIncluded: true,
        rowFilterMode: 'ALL',
        deduplication: { enabled: false, keyFields: [], survivorPolicy: 'FIRST' },
        originalProposal: {
          targetNamespace: 'landing_zone',
          targetName: 'audit_logs_landing',
          isIncluded: true,
          rowFilterMode: 'ALL',
          deduplication: { enabled: false, keyFields: [], survivorPolicy: 'FIRST' }
        },
        structuralImpact: {
          primaryKeyStatus: 'PRESERVED',
          foreignKeysCount: 0,
          rewiredFkCount: 0,
          indexesCount: 0,
          dependentObjectsCount: 0,
          dependentObjects: []
        },
        uiWorkState: 'AUTOMATIC',
        conversionSafety: 'EXACT',
        readiness: 'READY',
        status: 'AUTO_MAPPED',
        issues: [],
        columns: [
          {
            id: 'col-s3-key',
            sourceField: 's3_uri',
            sourceType: 'VARCHAR',
            proposedTargetField: 'file_path',
            currentTargetField: 'file_path',
            proposedTargetType: 'VARCHAR',
            currentTargetType: 'VARCHAR',
            isIncluded: true,
            uiWorkState: 'AUTOMATIC',
            conversionSafety: 'EXACT',
            readiness: 'READY',
            status: 'AUTO_MAPPED',
            originalProposal: { targetField: 'file_path', targetType: 'VARCHAR', isIncluded: true }
          }
        ]
      }
    ];

    return {
      objects,
      namespaces,
      codeObjects: [],
      compatibilityHelpers: [],
      privacyItems: [],
      cleansingItems: [],
      filterItems: [],
      deduplicationItems: [],
      qualityItems: [],
      privacyOptions: this.defaultPrivacyOptions,
      cleansingOptions: this.defaultCleansingOptions,
      survivorPolicyOptions: this.defaultSurvivorPolicyOptions
    };
  }
}
