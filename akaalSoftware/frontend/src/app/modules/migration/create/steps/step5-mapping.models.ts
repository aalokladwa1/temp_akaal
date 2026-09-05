import { PhysicalProviderId, MigrationMode } from '../../../../core/models/migration-view.models';

export type Step5WorkspaceTab = 'MAPPING' | 'TRANSPILER';

export type MappingSubWorkspace = 'OVERVIEW' | 'STRUCTURE' | 'FIELDS' | 'CONTROLS';

export type DataControlCategory = 'PRIVACY' | 'CLEANSING' | 'FILTERING' | 'DEDUPLICATION' | 'QUALITY';

export type MappingStatusBucket = 'ALL' | 'AUTO_MAPPED' | 'MODIFIED' | 'NEEDS_REVIEW' | 'BLOCKED';

export type CodeObjectCategory = 'PROCEDURE' | 'FUNCTION' | 'PACKAGE' | 'VIEW' | 'TRIGGER';

// =============================================================================
// THREE DECOUPLED STATUS DIMENSIONS (NON-NEGOTIABLE CANONICAL SPECIFICATION)
// =============================================================================

/** 1. UI Work State: tracks the operator's intervention state */
export type UiWorkState = 'AUTOMATIC' | 'MODIFIED' | 'NEEDS_REVIEW' | 'BLOCKED';

/** 2. Conversion Safety: tracks semantic datatype & transformation equivalence */
export type ConversionSafetyState =
  | 'EXACT'
  | 'SEMANTICALLY_EQUIVALENT'
  | 'COMPATIBLE_WITH_TRANSFORMATION'
  | 'COMPATIBILITY_LAYER_REQUIRED'
  | 'LOSSY'
  | 'UNSUPPORTED'
  | 'USER_DECISION_REQUIRED';

/** 3. Readiness: tracks migration execution gate state */
export type ReadinessState =
  | 'READY'
  | 'READY_WITH_WARNINGS'
  | 'WAIVER_REQUIRED'
  | 'BLOCKED';

// =============================================================================
// DATA CONTROLS CANONICAL DEFINITIONS
// =============================================================================

export type DeduplicationSurvivorPolicy =
  | 'FIRST'
  | 'LAST'
  | 'MIN_FIELD'
  | 'MAX_FIELD'
  | 'NEWEST'
  | 'OLDEST'
  | 'PRIORITY'
  | 'FAIL_ON_DUPLICATE'
  | 'REJECT_GROUP'
  | 'QUARANTINE_GROUP';

export type PrivacyStrategy =
  | 'STATIC_REDACT'
  | 'PARTIAL_MASK'
  | 'NULLIFY'
  | 'HASH'
  | 'KEYED_PSEUDONYM'
  | 'FORMAT_PRESERVING_MASK';

export type CleansingRuleType =
  | 'TRIM'
  | 'UPPERCASE'
  | 'LOWERCASE'
  | 'DEFAULT'
  | 'REGEX_REPLACE';

export type QualityRuleType =
  | 'NOT_NULL'
  | 'MAX_LENGTH'
  | 'NUMERIC_OVERFLOW'
  | 'VALUE_RANGE'
  | 'REGEX_MATCH'
  | 'ENUM_VALUES';

export type QualityDisposition =
  | 'FAIL_JOB'
  | 'REJECT_RECORD'
  | 'QUARANTINE_RECORD'
  | 'USE_DEFAULT'
  | 'USE_NULL'
  | 'EXPLICIT_TRUNCATE';

// =============================================================================
// CAPABILITY REFERENCES & ISSUES
// =============================================================================

export interface CapabilityOptionRef {
  id: string;
  label: string;
  description?: string;
  requiresParam?: boolean;
  paramLabel?: string;
  paramPlaceholder?: string;
}

export interface MappingIssue {
  id: string;
  severity: 'BLOCKED' | 'NEEDS_REVIEW';
  code: string;
  title: string;
  reason: string;
  recommendation?: string;
  affectedField?: string;
  targetObject?: string;
  lossinessReasons?: string[];
}

export interface DependencyObjectRef {
  type: 'FOREIGN_KEY' | 'VIEW' | 'TRIGGER' | 'PROCEDURE';
  name: string;
  relation?: string;
  impactDescription: string;
}

export interface StructuralImpact {
  primaryKeyStatus: 'PRESERVED' | 'REMOVED' | 'MODIFIED';
  foreignKeysCount: number;
  rewiredFkCount: number;
  indexesCount: number;
  dependentObjectsCount: number;
  requiresGovernanceWaiver?: boolean;
  dependentObjects: DependencyObjectRef[];
}

// =============================================================================
// COLUMN MAPPING CONTRACT
// =============================================================================

export interface ColumnMappingContract {
  id: string;
  sourceField: string;
  sourceType: string;
  proposedTargetField: string;
  currentTargetField: string;
  proposedTargetType: string;
  currentTargetType: string;
  targetTypeOptions?: string[];
  
  // Precision / Scale / Length overrides
  sourcePrecision?: number;
  sourceScale?: number;
  sourceLength?: number;
  proposedPrecision?: number;
  proposedScale?: number;
  proposedLength?: number;
  currentPrecision?: number;
  currentScale?: number;
  currentLength?: number;
  length?: number;
  precision?: number;
  scale?: number;

  defaultExpression?: string;
  currentDefaultExpression?: string;
  isDefaultExpressionOverridden?: boolean;
  
  // Data Controls associations
  privacyOptionId?: string | null;
  privacyParam?: string;
  cleansingOptionId?: string | null;
  
  isIncluded: boolean;
  isGenerated?: boolean;

  // The 3 Decoupled Status Dimensions
  uiWorkState: UiWorkState;
  conversionSafety: ConversionSafetyState;
  readiness: ReadinessState;
  
  // Compatibility with older views
  status: 'AUTO_MAPPED' | 'MODIFIED' | 'NEEDS_REVIEW' | 'BLOCKED';
  
  lossinessReasons?: string[];
  operatorReason?: string;
  issues?: MappingIssue[];
  isModified?: boolean;
  
  originalProposal: {
    targetField: string;
    targetType: string;
    isIncluded: boolean;
    precision?: number;
    scale?: number;
    length?: number;
    defaultExpression?: string;
  };
}

// =============================================================================
// OBJECT MAPPING CONTRACT
// =============================================================================

export interface DeduplicationConfig {
  enabled: boolean;
  keyFields: string[];
  survivorPolicy: DeduplicationSurvivorPolicy;
  survivorPolicyOptionId?: string | null;
  priorityField?: string;
  priorityOrder?: string[];
  duplicateDisposition?: 'LOG_AND_DISCARD' | 'REJECT_GROUP' | 'QUARANTINE_GROUP' | 'FAIL_JOB';
}

export interface ObjectMappingContract {
  id: string;
  sourceName: string;
  sourceNamespace: string;
  sourceType: 'TABLE' | 'COLLECTION' | 'TOPIC' | 'BUCKET' | 'VIEW';
  sourceTypeLabel: string;
  
  proposedTargetNamespace: string;
  currentTargetNamespace: string;
  proposedTargetName: string;
  currentTargetName: string;
  
  isIncluded: boolean;
  rowFilterMode: 'ALL' | 'CUSTOM';
  rowFilterPredicate?: string;
  
  deduplication: DeduplicationConfig;
  columns: ColumnMappingContract[];
  
  structuralImpact: StructuralImpact;

  // 3 Decoupled Status Dimensions
  uiWorkState: UiWorkState;
  conversionSafety: ConversionSafetyState;
  readiness: ReadinessState;

  // Older status property for compatibility
  status: 'AUTO_MAPPED' | 'MODIFIED' | 'NEEDS_REVIEW' | 'BLOCKED';
  issues: MappingIssue[];
  isModified?: boolean;
  
  secondaryTraits?: string[];
  estimatedRows?: number | null;
  estimatedSizeBytes?: number | null;
  
  originalProposal: {
    targetNamespace: string;
    targetName: string;
    isIncluded: boolean;
    rowFilterMode: 'ALL' | 'CUSTOM';
    rowFilterPredicate?: string;
    deduplication: DeduplicationConfig;
  };
}

// =============================================================================
// NAMESPACE ROUTING CONTRACT
// =============================================================================

export interface NamespaceRoutingRule {
  sourceNamespace: string;
  proposedTargetNamespace: string;
  currentTargetNamespace: string;
  origin: 'AUTOMATIC' | 'MODIFIED';
  prefix: string;
  suffix: string;
  advancedPattern?: string;
  advancedReplacement?: string;
  affectedObjectsCount: number;
  isModified?: boolean;
  originalProposal: {
    targetNamespace: string;
    prefix: string;
    suffix: string;
    advancedPattern?: string;
    advancedReplacement?: string;
  };
}

// =============================================================================
// DATA CONTROLS CONTRACTS (DEDICATED WORKSPACE)
// =============================================================================

export interface PrivacyItemContract {
  id: string;
  objectId: string;
  fieldId: string;
  objectName: string;
  fieldName: string;
  strategy: PrivacyStrategy;
  strategyLabel: string;
  configuration: string;
  secretReference?: string;
  status: 'READY' | 'CONFIGURED' | 'NEEDS_REVIEW';
  isModified?: boolean;
  originalProposal: {
    strategy: PrivacyStrategy;
    configuration: string;
    secretReference?: string;
  };
}

export interface CleansingItemContract {
  id: string;
  objectId: string;
  fieldId: string;
  objectName: string;
  fieldName: string;
  ruleType: CleansingRuleType;
  ruleTypeLabel: string;
  paramValue?: string;
  orderIndex: number;
  status: 'READY' | 'CONFIGURED';
  isModified?: boolean;
  originalProposal: {
    ruleType: CleansingRuleType;
    paramValue?: string;
  };
}

export interface FilterItemContract {
  id: string;
  objectId: string;
  objectName: string;
  mode: 'ALL' | 'CUSTOM';
  predicate?: string;
  status: 'READY' | 'CONFIGURED';
  isModified?: boolean;
  originalProposal: {
    mode: 'ALL' | 'CUSTOM';
    predicate?: string;
  };
}

export interface DeduplicationItemContract {
  id: string;
  objectId: string;
  objectName: string;
  enabled: boolean;
  keyFields: string[];
  survivorPolicy: DeduplicationSurvivorPolicy;
  survivorPolicyLabel: string;
  priorityField?: string;
  priorityOrder?: string[];
  disposition: string;
  status: 'READY' | 'CONFIGURED';
  isModified?: boolean;
  originalProposal: {
    enabled: boolean;
    keyFields: string[];
    survivorPolicy: DeduplicationSurvivorPolicy;
    priorityField?: string;
    priorityOrder?: string[];
    disposition: string;
  };
}

export interface QualityItemContract {
  id: string;
  objectId: string;
  fieldId?: string;
  objectName: string;
  fieldName?: string;
  ruleType: QualityRuleType;
  ruleLabel: string;
  constraintValue?: string;
  disposition: QualityDisposition;
  dispositionLabel: string;
  status: 'READY' | 'CONFIGURED';
  isModified?: boolean;
  originalProposal: {
    ruleType: QualityRuleType;
    constraintValue?: string;
    disposition: QualityDisposition;
  };
}

// =============================================================================
// PROCEDURAL TRANSPILER CONTRACTS
// =============================================================================

export interface TranspilerDiagnostic {
  id: string;
  severity: 'ERROR' | 'WARNING' | 'INFO';
  line?: number;
  column?: number;
  construct?: string;
  message: string;
  recommendation?: string;
}

export interface CompatibilityHelperRef {
  name: string;
  category: string;
  affectedRoutines: string[];
  rationale: string;
  installSql: string;
}

export interface TranspilerObjectContract {
  id: string;
  name: string;
  category: CodeObjectCategory;
  categoryLabel: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceCode: string;
  proposedTargetCode: string;
  currentTargetCode: string;
  status: 'CONVERTED' | 'MODIFIED' | 'NEEDS_REVIEW' | 'BLOCKED';
  lifecycleState: 'PARSED' | 'ANALYZED' | 'TRANSPILED' | 'SYNTACTICALLY_CHECKED' | 'COMPATIBILITY_WRAPPED' | 'MANUAL_REVIEW_REQUIRED' | 'MANUAL_REWRITE_REQUIRED' | 'CONVERTED' | 'FAILED';
  diagnostics: TranspilerDiagnostic[];
  isModified?: boolean;
  operatorReason?: string;
  originalProposal: {
    targetCode: string;
  };
}

// =============================================================================
// COMPLETE PACKET & SUMMARY METRICS
// =============================================================================

export interface Step5MappingPacket {
  objects: ObjectMappingContract[];
  namespaces: NamespaceRoutingRule[];
  codeObjects: TranspilerObjectContract[];
  compatibilityHelpers: CompatibilityHelperRef[];
  
  // Data Controls items
  privacyItems: PrivacyItemContract[];
  cleansingItems: CleansingItemContract[];
  filterItems: FilterItemContract[];
  deduplicationItems: DeduplicationItemContract[];
  qualityItems: QualityItemContract[];

  // Capability Options
  privacyOptions: CapabilityOptionRef[];
  cleansingOptions: CapabilityOptionRef[];
  survivorPolicyOptions: CapabilityOptionRef[];
  targetTypeCatalog?: { [providerCategory: string]: string[] };
}

export interface Step5SummaryMetrics {
  totalObjects: number;
  autoMappedCount: number;
  modifiedCount: number;
  needsReviewCount: number;
  blockedCount: number;
  governanceRequiredCount: number;
  
  totalCodeObjects: number;
  codeConvertedCount: number;
  codeModifiedCount: number;
  codeNeedsReviewCount: number;
  codeBlockedCount: number;

  totalPrivacyCount: number;
  totalCleansingCount: number;
  totalFilterCount: number;
  totalDedupCount: number;
  totalQualityCount: number;
}
