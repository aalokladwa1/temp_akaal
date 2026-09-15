/**
 * AKAAL Create Template Domain & Draft Models
 * Governs the 6-Step Create Template transaction:
 * 1. Definition & Applicability (Name, Scope, Providers, M1-M7 Modes)
 * 2. Migration Defaults (Naming, Priority, Connection Policies, Required-at-Use Checklist)
 * 3. Scope, Mapping & Data Controls (Include/Exclude, Schema/Table, Column Types, Masking, Cleansing)
 * 4. Enterprise Configuration (Performance, Checkpointing, Dynamic Mode Tuning, Validation Presets)
 * 5. Governance & Reuse Rules (Overridability, Prerequisites, Approval, Secret Reference Guidance)
 * 6. Review & Create (Scannable Grouped Summary & Final Template Instantiation)
 *
 * OWNER-FROZEN BOUNDARY:
 * - Templates accelerate canonical Migration Creation (M1-M7 only).
 * - M8 (Validation Only) is STRICTLY FORBIDDEN anywhere in Templates.
 * - Standalone Validation Creation NEVER consumes Templates.
 * - Zero Plaintext Secrets: Templates NEVER capture or store raw credentials.
 */

import { TemplateMigrationMode, TemplateScope, TemplateItem, TEMPLATE_MODE_DESCRIPTORS } from '../templates.models';

export type CreateTemplateStepIndex = 1 | 2 | 3 | 4 | 5 | 6;

export interface CreateTemplateStepItem {
  index: CreateTemplateStepIndex;
  label: string;
  sublabel: string;
  description: string;
}

export const CREATE_TEMPLATE_STEPS: CreateTemplateStepItem[] = [
  {
    index: 1,
    label: 'Definition & Applicability',
    sublabel: 'Name, Scope & Modes',
    description: 'Define template identity, availability boundary, provider compatibility, and migration operational mode.'
  },
  {
    index: 2,
    label: 'Migration Defaults',
    sublabel: 'Naming & Policies',
    description: 'Establish default migration naming patterns, execution priorities, connection preferences, and operator requirements.'
  },
  {
    index: 3,
    label: 'Scope, Mapping & Controls',
    sublabel: 'Objects, Schema & Data',
    description: 'Configure object selection filters, schema/table transformations, column data type mappings, and privacy masking.'
  },
  {
    index: 4,
    label: 'Enterprise Configuration',
    sublabel: 'Performance & Mode Tuning',
    description: 'Set concurrency threads, batching, checkpointing, mode-specific engine parameters, and validation presets.'
  },
  {
    index: 5,
    label: 'Governance & Reuse Rules',
    sublabel: 'Policies & Prerequisites',
    description: 'Declare parameter overridability constraints, capability requirements, approval policies, and secret reference rules.'
  },
  {
    index: 6,
    label: 'Review & Create',
    sublabel: 'Summary & Instantiation',
    description: 'Review the cohesive configuration specification and instantiate the reusable migration template.'
  }
];

// =========================================================================
// STEP 1: DEFINITION & APPLICABILITY
// =========================================================================

export interface Step1DefinitionState {
  name: string;
  description: string;
  scope: TemplateScope;
  sourceProvider: string;
  targetProvider: string;
  mode: TemplateMigrationMode;
}

// =========================================================================
// STEP 2: MIGRATION DEFAULTS
// =========================================================================

export type ExecutionPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
export type ConnectionPolicy = 'REQUIRE_AT_CREATION' | 'PROJECT_POOL' | 'LOGICAL_TAG';

export interface RequiredAtUseChecklist {
  targetDatabaseRequired: boolean;
  scheduleRequired: boolean;
  secretBindingsRequired: boolean;
  workspaceSelectionRequired: boolean;
  notificationChannelsRequired: boolean;
}

export interface Step2DefaultsState {
  migrationNamePattern: string;
  executionPriority: ExecutionPriority;
  sourceConnectionPolicy: ConnectionPolicy;
  sourceConnectionTag: string;
  targetConnectionPolicy: ConnectionPolicy;
  targetConnectionTag: string;
  requiredAtUse: RequiredAtUseChecklist;
}

// =========================================================================
// STEP 3: SCOPE, MAPPING & DATA CONTROLS
// =========================================================================

export type ScopeRuleType = 'INCLUDE' | 'EXCLUDE';
export type ScopeObjectType = 'TABLE' | 'VIEW' | 'SCHEMA' | 'SEQUENCE' | 'PROCEDURE';

export interface ObjectScopeRule {
  id: string;
  ruleType: ScopeRuleType;
  objectType: ScopeObjectType;
  pattern: string;
  description?: string;
}

export interface SchemaMappingRule {
  id: string;
  sourceSchema: string;
  targetSchema: string;
}

export type TableCaseTransformation = 'PRESERVE' | 'UPPERCASE' | 'LOWERCASE' | 'SNAKE_CASE';

export interface ColumnTypeOverride {
  id: string;
  sourceType: string;
  targetType: string;
  condition?: string;
}

export type NullabilityPolicy = 'PRESERVE' | 'ALLOW_NULL' | 'REPLACE_WITH_DEFAULT';

export type MaskingType = 'PII_REDACT' | 'HASH_SHA256' | 'MASK_EMAIL' | 'RANDOM_GENERATOR' | 'TOKENIZE';

export interface MaskingRule {
  id: string;
  targetPattern: string; // Column or field pattern, e.g. "*ssn*", "email", "*credit_card*"
  maskingType: MaskingType;
  note?: string;
}

export interface CleansingRules {
  trimWhitespace: boolean;
  emptyStringToNull: boolean;
  deduplicateOnPrimaryKey: boolean;
}

export interface Step3ScopeMappingState {
  objectScopeRules: ObjectScopeRule[];
  schemaMappings: SchemaMappingRule[];
  tableCaseTransformation: TableCaseTransformation;
  columnTypeOverrides: ColumnTypeOverride[];
  nullabilityPolicy: NullabilityPolicy;
  maskingRules: MaskingRule[];
  cleansing: CleansingRules;
}

// =========================================================================
// STEP 4: ENTERPRISE CONFIGURATION
// =========================================================================

export interface PerformanceConfig {
  extractThreads: number;      // 1 to 32
  batchSize: number;           // rows (e.g. 10000)
  bufferMemoryMb: number;      // MB (e.g. 1024)
  maxThroughputMbps: number;   // 0 = unlimited
}

export type ErrorHandlingPolicy = 'ABORT_IMMEDIATELY' | 'SKIP_AND_LOG_DLQ' | 'RETRY_EXPONENTIAL';

export interface CheckpointRecoveryConfig {
  commitIntervalRows: number;
  commitIntervalSec: number;
  retryCount: number;          // 0 to 5
  errorHandlingPolicy: ErrorHandlingPolicy;
  maxSkippedErrors: number;
}

// Mode-Specific Dynamic Configurations
export type CdcEngineType = 'DATABASE_LOG_MINER' | 'DEBEZIUM_STREAM' | 'WAL2JSON' | 'BINLOG_REPLICATION';
export type StreamHandoffPolicy = 'SEAMLESS_LOCKLESS' | 'QUIESCE_REQUIRED';

export interface CdcModeConfig {
  cdcEngine: CdcEngineType;
  maxLagAlertSec: number;
  heartbeatTracking: boolean;
  snapshotToStreamHandoff: StreamHandoffPolicy;
}

export interface IncrementalModeConfig {
  watermarkColumn: string;
  pollingIntervalSec: number;
  lookbackWindowMinutes: number;
}

export type ConflictResolutionPolicy = 'SOURCE_WINS' | 'TARGET_WINS' | 'LATEST_TIMESTAMP' | 'MANUAL_QUEUE';

export interface StateSyncModeConfig {
  conflictResolution: ConflictResolutionPolicy;
  biDirectionalEnabled: boolean;
}

export type ForeignKeyOrderPolicy = 'PRE_LOAD' | 'POST_LOAD' | 'NONE';

export interface SchemaOnlyModeConfig {
  dropTargetObjectsFirst: boolean;
  createForeignKeys: ForeignKeyOrderPolicy;
  includeIndexes: boolean;
}

export interface DataOnlyModeConfig {
  requireTargetTableExists: boolean;
  truncateTargetBeforeLoad: boolean;
  disableForeignKeysDuringLoad: boolean;
}

export type SampleHashRate = 'NONE' | 'SAMPLE_0_1_PCT' | 'SAMPLE_1_PCT' | 'SAMPLE_10_PCT' | 'FULL_100_PCT';

export interface ValidationPresetsConfig {
  rowCountReconciliation: boolean;
  schemaChecksumCheck: boolean;
  sampleDataHashRate: SampleHashRate;
}

export interface Step4EnterpriseConfigState {
  performance: PerformanceConfig;
  checkpointRecovery: CheckpointRecoveryConfig;
  cdcConfig: CdcModeConfig;
  incrementalConfig: IncrementalModeConfig;
  stateSyncConfig: StateSyncModeConfig;
  schemaOnlyConfig: SchemaOnlyModeConfig;
  dataOnlyConfig: DataOnlyModeConfig;
  validationPresets: ValidationPresetsConfig;
}

// =========================================================================
// STEP 5: GOVERNANCE & REUSE RULES
// =========================================================================

export type OverridabilityLevel = 'FULL_OVERRIDE' | 'RESTRICTED' | 'LOCKED';
export type MappingOverrideLevel = 'ALLOWED' | 'REQUIRES_APPROVAL' | 'LOCKED';
export type ScopeOverrideLevel = 'UNRESTRICTED' | 'SUBSET_ONLY' | 'LOCKED';

export interface OverridabilityRules {
  performanceSettings: OverridabilityLevel;
  mappingRules: MappingOverrideLevel;
  scopeObjects: ScopeOverrideLevel;
}

export interface RequiredCapabilities {
  sourcePrivileges: string[];
  targetPrivileges: string[];
  networkRequirements: string[];
}

export type AuditLogLevel = 'STANDARD' | 'VERBOSE' | 'COMPLIANCE';

export interface ApprovalAndPolicy {
  requirePeerReview: boolean;
  enforceChangeFreezeWindow: boolean;
  auditLogLevel: AuditLogLevel;
}

export type SecretVaultProvider = 'HASHICORP_VAULT' | 'AWS_SECRETS_MANAGER' | 'AZURE_KEY_VAULT' | 'ENVIRONMENT_VAULT';

export interface SecretReferenceRules {
  vaultProvider: SecretVaultProvider;
  keyPathPrefix: string;
  guidanceNote: string;
}

export interface Step5GovernanceState {
  overridability: OverridabilityRules;
  requiredCapabilities: RequiredCapabilities;
  approvalAndPolicy: ApprovalAndPolicy;
  secretReferenceRules: SecretReferenceRules;
}

// =========================================================================
// ROOT DRAFT STATE
// =========================================================================

export interface CreateTemplateDraftState {
  definition: Step1DefinitionState;
  migrationDefaults: Step2DefaultsState;
  scopeMapping: Step3ScopeMappingState;
  enterpriseConfig: Step4EnterpriseConfigState;
  governance: Step5GovernanceState;
}

export const INITIAL_CREATE_TEMPLATE_DRAFT: CreateTemplateDraftState = {
  definition: {
    name: '',
    description: '',
    scope: 'ORGANIZATION',
    sourceProvider: 'oracle',
    targetProvider: 'postgresql',
    mode: 'M2_BULK_CDC'
  },
  migrationDefaults: {
    migrationNamePattern: 'MIG-{{PROJECT}}-{{ENV}}-{{SEQ}}',
    executionPriority: 'NORMAL',
    sourceConnectionPolicy: 'REQUIRE_AT_CREATION',
    sourceConnectionTag: 'production-primary',
    targetConnectionPolicy: 'REQUIRE_AT_CREATION',
    targetConnectionTag: 'analytics-target',
    requiredAtUse: {
      targetDatabaseRequired: true,
      scheduleRequired: false,
      secretBindingsRequired: true,
      workspaceSelectionRequired: true,
      notificationChannelsRequired: false
    }
  },
  scopeMapping: {
    objectScopeRules: [
      { id: 'rule-1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'public.*', description: 'Include all default public tables' },
      { id: 'rule-2', ruleType: 'EXCLUDE', objectType: 'TABLE', pattern: '*_tmp, *_bak', description: 'Exclude temporary and backup tables' }
    ],
    schemaMappings: [
      { id: 'sm-1', sourceSchema: 'app_prod', targetSchema: 'app_migrated' }
    ],
    tableCaseTransformation: 'LOWERCASE',
    columnTypeOverrides: [
      { id: 'co-1', sourceType: 'VARCHAR2(n)', targetType: 'VARCHAR(n)' },
      { id: 'co-2', sourceType: 'NUMBER(p,s)', targetType: 'NUMERIC(p,s)' },
      { id: 'co-3', sourceType: 'DATE', targetType: 'TIMESTAMP' }
    ],
    nullabilityPolicy: 'PRESERVE',
    maskingRules: [
      { id: 'mr-1', targetPattern: '*ssn*, *social_security*', maskingType: 'PII_REDACT', note: 'Redact social security numbers' },
      { id: 'mr-2', targetPattern: '*email*, *contact_email*', maskingType: 'MASK_EMAIL', note: 'Obfuscate email domain' }
    ],
    cleansing: {
      trimWhitespace: true,
      emptyStringToNull: true,
      deduplicateOnPrimaryKey: true
    }
  },
  enterpriseConfig: {
    performance: {
      extractThreads: 4,
      batchSize: 10000,
      bufferMemoryMb: 1024,
      maxThroughputMbps: 0 // Unlimited
    },
    checkpointRecovery: {
      commitIntervalRows: 10000,
      commitIntervalSec: 30,
      retryCount: 3,
      errorHandlingPolicy: 'SKIP_AND_LOG_DLQ',
      maxSkippedErrors: 100
    },
    cdcConfig: {
      cdcEngine: 'DATABASE_LOG_MINER',
      maxLagAlertSec: 60,
      heartbeatTracking: true,
      snapshotToStreamHandoff: 'SEAMLESS_LOCKLESS'
    },
    incrementalConfig: {
      watermarkColumn: 'updated_at',
      pollingIntervalSec: 300,
      lookbackWindowMinutes: 15
    },
    stateSyncConfig: {
      conflictResolution: 'SOURCE_WINS',
      biDirectionalEnabled: false
    },
    schemaOnlyConfig: {
      dropTargetObjectsFirst: false,
      createForeignKeys: 'POST_LOAD',
      includeIndexes: true
    },
    dataOnlyConfig: {
      requireTargetTableExists: true,
      truncateTargetBeforeLoad: false,
      disableForeignKeysDuringLoad: true
    },
    validationPresets: {
      rowCountReconciliation: true,
      schemaChecksumCheck: true,
      sampleDataHashRate: 'SAMPLE_1_PCT'
    }
  },
  governance: {
    overridability: {
      performanceSettings: 'FULL_OVERRIDE',
      mappingRules: 'REQUIRES_APPROVAL',
      scopeObjects: 'SUBSET_ONLY'
    },
    requiredCapabilities: {
      sourcePrivileges: ['SELECT', 'FLASHBACK', 'LOGMINING'],
      targetPrivileges: ['CREATE TABLE', 'INSERT', 'UPDATE', 'INDEX'],
      networkRequirements: ['TLS 1.3 Encryption', 'VPC Direct Peering']
    },
    approvalAndPolicy: {
      requirePeerReview: false,
      enforceChangeFreezeWindow: true,
      auditLogLevel: 'STANDARD'
    },
    secretReferenceRules: {
      vaultProvider: 'HASHICORP_VAULT',
      keyPathPrefix: 'secret/data/akaal/migration/',
      guidanceNote: 'Never store plain credentials in template definitions. Reference vault paths.'
    }
  }
};
