import { PhysicalProviderId, MigrationMode } from '../../../../core/models/migration-view.models';

export type ConfigurationDepth = 'STANDARD' | 'ADVANCED';

export type StandardProfileId = 'PROTECTIVE' | 'BALANCED' | 'HIGH_THROUGHPUT';

export interface StandardProfileOption {
  id: StandardProfileId;
  title: string;
  badge?: string;
  description: string;
  workers: number;
  sourceImpact: string;
  targetImpact: string;
  batching: string;
  durability: string;
}

export type BandwidthPolicy = 'UNLIMITED' | 'LIMITED';
export type LobHandlingPolicy = 'AUTOMATIC' | 'INLINE' | 'STREAMING';
export type ResourceImpactPolicy = 'CONSERVATIVE' | 'BALANCED' | 'MAXIMUM';

export type RecoveryPolicy = 'RESUME_CHECKPOINT' | 'PAUSE_OPERATOR';
export type TransientFailurePolicy = 'RETRY_BACKOFF' | 'PAUSE_WORK';
export type FailedRecordsPolicy = 'QUARANTINE_CONTINUE' | 'STOP_WORK';

export type ValidationDepthOption = 'FAST_FULL' | 'EXACT_FULL' | 'DETERMINISTIC_SAMPLE' | 'STRUCTURE_ONLY';

export interface ValidationOptionDescriptor {
  id: ValidationDepthOption;
  title: string;
  badge?: string;
  description: string;
  coverage: string;
  relativeImpact: 'Low' | 'Moderate' | 'High';
}

export type ExecutionWindowChoice = 'ANYTIME' | 'RESTRICTED';

export type CustomActionHook = 'PRE_MIGRATION' | 'POST_SCHEMA' | 'POST_BULK' | 'POST_CUTOVER';

export interface CustomActionItem {
  id: string;
  hook: CustomActionHook;
  hookLabel: string;
  name: string;
  sql: string;
  timeoutSec: number;
  onFailure: 'ABORT_MIGRATION' | 'LOG_AND_CONTINUE';
  isEnabled: boolean;
}

// ----------------------------------------------------------------------------
// MODE-SPECIFIC CONFIGURATION CONTRACTS (M1 - M7)
// ----------------------------------------------------------------------------
export interface ModeM1Config {
  partitionStrategy: 'AUTOMATIC' | 'HASH' | 'RANGE';
  chunkSizeRows: number;
  directLoad: boolean;
  parallelWriters: number;
}

export interface ModeM2Config {
  catchupLagTargetSec: number;
  cutoverMaxLagSec: number;
  conflictPolicy: 'LATEST_WINS' | 'SOURCE_WINS' | 'FAIL_ON_CONFLICT';
  quiescenceTimeoutSec: number;
  enableCdcBufferSpill: boolean;
}

export interface ModeM3Config {
  startPosition: 'IMMEDIATE' | 'CURRENT_SCN' | 'TIMESTAMP';
  startPositionTimestamp?: string;
  batchWindowMs: number;
  applyConcurrency: number;
  eventBufferMb: number;
}

export interface ModeM4Config {
  watermarkColumn: string;
  pollingIntervalSec: number;
  lookbackWindowMin: number;
  cursorPageSize: number;
}

export interface ModeM5Config {
  reconciliationMode: 'ONE_WAY_ALIGN' | 'BIDIRECTIONAL_REPORT';
  divergencePosture: 'REPAIR_TARGET' | 'LOG_ONLY';
  syncIntervalSec: number;
  stateTolerancePercent: number;
}

export interface ModeM6Config {
  transactionalDdl: boolean;
  fkIndexTiming: 'DEFERRED' | 'INLINE';
  routineValidation: 'STRICT' | 'PERMISSIVE';
  dropExistingObjects: boolean;
}

export interface ModeM7Config {
  targetReadiness: 'TRUNCATE' | 'APPEND' | 'UPSERT';
  requireSchemaAttestation: boolean;
  batchCommitIntervalRows: number;
}

// ----------------------------------------------------------------------------
// ADVANCED 8 OPERATOR GROUPS
// ----------------------------------------------------------------------------
export type AdvancedGroupId =
  | 'EXECUTION_RESOURCES'
  | 'TRANSFER_BATCHING'
  | 'RESILIENCE_RECOVERY'
  | 'MODE_CONFIG'
  | 'VALIDATION_RECON'
  | 'SCHEMA_ACTIONS'
  | 'OBSERVABILITY_WINDOWS'
  | 'PROVIDER_OPTIONS';

export interface AdvancedGroupNavDescriptor {
  id: AdvancedGroupId;
  label: string;
  description: string;
  icon: string;
}

export type ProvenanceSource = 'PRESET' | 'INHERITED_POLICY' | 'USER_OVERRIDE';

export interface AdvancedFieldDescriptor {
  id: string;
  groupId: AdvancedGroupId;
  subGroup?: string;
  label: string;
  description: string;
  type: 'number' | 'string' | 'boolean' | 'select';
  options?: { label: string; value: any; desc?: string }[];
  defaultValue: any;
  effectiveValue: any;
  overriddenValue?: any;
  isOverridden: boolean;
  provenance: ProvenanceSource;
  provenanceDetail?: string;
  isPolicyLocked?: boolean;
  policyLockReason?: string;
  isMaterialChange?: boolean;
  materialChangeWarning?: string;
  providerEndpoint?: 'SOURCE' | 'TARGET';
  providerName?: string;
  min?: number;
  max?: number;
  unit?: string;
}

// ----------------------------------------------------------------------------
// COMPLETE STEP 6 DRAFT STATE CONTRACT
// ----------------------------------------------------------------------------
export interface Step6ConfigurationDraft {
  depth: ConfigurationDepth;
  profile: StandardProfileId;
  bandwidthPolicy: BandwidthPolicy;
  bandwidthLimitValue: number;
  bandwidthLimitUnit: 'MB/s' | 'Gb/s';
  lobPolicy: LobHandlingPolicy;
  resourceImpact: ResourceImpactPolicy;
  recoveryPolicy: RecoveryPolicy;
  transientFailurePolicy: TransientFailurePolicy;
  failedRecordsPolicy: FailedRecordsPolicy;
  
  modeM1: ModeM1Config;
  modeM2: ModeM2Config;
  modeM3: ModeM3Config;
  modeM4: ModeM4Config;
  modeM5: ModeM5Config;
  modeM6: ModeM6Config;
  modeM7: ModeM7Config;

  validationDepth: ValidationDepthOption;
  
  executionWindowChoice: ExecutionWindowChoice;
  executionWindowStart: string;
  executionWindowEnd: string;
  executionWindowDays: string[];
  
  customActions: CustomActionItem[];
  advancedOverrides: Record<string, any>;
}

export interface Step6SummaryMetrics {
  profileLabel: string;
  bandwidthSummary: string;
  recoverySummary: string;
  quarantineSummary: string;
  modeSummary: string;
  validationSummary: string;
  windowSummary: string;
  inheritedPoliciesCount: number;
  customOverridesCount: number;
  isCustomized: boolean;
}
