// ============================================================================
// AKAAL ENTERPRISE MIGRATION SUITE — PRESENTATION & INTEGRATION CONTRACTS
// ============================================================================

// ----------------------------------------------------------------------------
// 1. PHYSICAL PROVIDER CONTRACTS (EXACTLY 28 PHYSICAL PROVIDERS)
// ----------------------------------------------------------------------------
export type ProviderCategory =
  | 'RELATIONAL'
  | 'WAREHOUSE'
  | 'NOSQL_GRAPH_SEARCH'
  | 'STREAMING'
  | 'STORAGE';

export type PhysicalProviderId =
  // Relational (7)
  | 'Oracle'
  | 'PostgreSQL'
  | 'MySQL'
  | 'Microsoft SQL Server'
  | 'MariaDB'
  | 'SQLite'
  | 'IBM Db2'
  // Warehouses / Lakehouses (4)
  | 'Snowflake'
  | 'Google BigQuery'
  | 'Amazon Redshift'
  | 'Databricks / Delta Lake'
  // NoSQL / Graph / Search (8)
  | 'MongoDB'
  | 'Apache Cassandra'
  | 'ScyllaDB'
  | 'Neo4j'
  | 'Redis'
  | 'KeyDB'
  | 'Elasticsearch'
  | 'OpenSearch'
  // Streaming (4)
  | 'Apache Kafka'
  | 'Amazon Kinesis'
  | 'Azure Event Hubs'
  | 'Google Cloud Pub/Sub'
  // Storage (5)
  | 'Amazon S3'
  | 'Google Cloud Storage'
  | 'Azure Blob Storage'
  | 'MinIO'
  | 'Apache HDFS';

export interface PhysicalProviderMeta {
  id: PhysicalProviderId;
  name: string;
  category: ProviderCategory;
  defaultPort?: number;
  icon: string;
  description: string;
  supportedModes: MigrationMode[];
  isSourceSupported: boolean;
  isTargetSupported: boolean;
  capabilities: string[];
}

// ----------------------------------------------------------------------------
// 2. MIGRATION MODES & LIFECYCLE (EXACTLY 7 CREATION EXECUTION MODES)
// ----------------------------------------------------------------------------
export type MigrationMode =
  | 'M1_BULK'           // Bulk Migration
  | 'M2_BULK_CDC'       // Bulk + CDC
  | 'M3_CDC'            // CDC Only
  | 'M4_INCREMENTAL'    // Incremental Query
  | 'M5_STATE_SYNC'     // State Synchronization
  | 'M6_SCHEMA_ONLY'    // Schema Only
  | 'M7_DATA_ONLY';     // Data Only

export interface MigrationModeDefinition {
  id: MigrationMode;
  code: string;
  title: string;
  badge: string;
  shortDesc: string;
  detailedImpact: string;
  scopeTag: string;
  slaExpectation: string;
  requiredCapabilities: string[];
}

export type MigrationLifecycleState =
  | 'INITIALIZED'
  | 'ACTIVE'
  | 'RUNNING'
  | 'PAUSED'
  | 'GOVERNANCE_PENDING'
  | 'INTERRUPTED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'ARCHIVED';

export type OperationalHealth = 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'STALLED';

// ----------------------------------------------------------------------------
// 3. PORTFOLIO & HUB VIEW MODELS (2.1)
// ----------------------------------------------------------------------------
export interface PortfolioSummaryCounters {
  total: number;
  active: number;
  scheduled: number;
  attentionRequired: number;
  completed: number;
  failedInterrupted: number;
  archived: number;
}

export interface MigrationAttentionItem {
  id: string;
  migrationId: string;
  migrationName: string;
  severity: 'INFO' | 'WARNING' | 'ACTION_REQUIRED' | 'CRITICAL';
  title: string;
  description: string;
  actionLabel: string;
  actionType: 'APPROVE' | 'RETRY' | 'ADJUST_BUFFER' | 'RESOLVE_CONFLICT' | 'INSPECT';
  targetTab?: string;
  timestamp: string;
}

export interface MigrationPortfolioItem {
  id: string;
  name: string;
  projectId?: string;
  projectName?: string;
  sourceEngine: PhysicalProviderId;
  sourceInstance: string;
  targetEngine: PhysicalProviderId;
  targetInstance: string;
  mode: MigrationMode;
  environment: string;
  lifecycleState: MigrationLifecycleState;
  currentStage: string;
  progressPercent: number;
  throughputRowsSec?: number;
  cdcLagMs?: number;
  watermarkTimestamp?: string;
  merkleDifferencesCount?: number;
  objectsCompletedCount?: number;
  objectsTotalCount?: number;
  etaString: string;
  health: OperationalHealth;
  attentionCount: number;
  requiresApproval: boolean;
  activeBarrierId?: string;
  planVersion: string;
  planFingerprint: string;
  updatedAt: string;
}

export interface ActivityEventItem {
  id: string;
  timestamp: string;
  type: 'APPROVAL_GRANTED' | 'APPROVAL_REVOKED' | 'CUTOVER_EXECUTED' | 'RECOVERY_SUCCEEDED' | 'COMPLETED' | 'CERTIFIED' | 'GOVERNED_REPAIR';
  title: string;
  description: string;
  migrationId?: string;
  migrationName?: string;
  projectId?: string;
  operator: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'CRITICAL';
}

// ----------------------------------------------------------------------------
// 4. CONNECTIONS VAULT (2.3)
// ----------------------------------------------------------------------------
export type NetworkRouteType = 'DIRECT' | 'SSH_BASTION' | 'PROXY' | 'PRIVATE_ENDPOINT' | 'CUSTOM';
export type ConnectionHealthStatus = 'CONNECTED' | 'DEGRADED' | 'UNREACHABLE' | 'AUTH_FAILED' | 'UNKNOWN';

export type ProbeStageName = 'NETWORK' | 'TLS' | 'AUTHENTICATION' | 'IDENTITY' | 'PERMISSIONS' | 'PREREQUISITES' | 'CAPABILITIES';
export type ProbeStageStatus = 'NOT_TESTED' | 'TESTING' | 'PASSED' | 'FAILED' | 'WARNING' | 'SKIPPED';

export interface ProbeStageResult {
  stage: ProbeStageName;
  label: string;
  status: ProbeStageStatus;
  detail: string;
  latencyMs?: number;
}

export interface ConnectionItem {
  id: string;
  name: string;
  provider: PhysicalProviderId;
  category: ProviderCategory;
  environment: string;
  host: string;
  port: number;
  databaseName?: string;
  username: string;
  secretRef: string; // e.g. "vault://secret/prod/db"
  tlsEnabled: boolean;
  networkRoute: NetworkRouteType;
  bastionHost?: string;
  proxyUrl?: string;
  privateEndpointId?: string;
  status: ConnectionHealthStatus;
  verificationFreshness: string;
  latencyMs?: number;
  capabilities: string[];
  assignedMigrationCount: number;
  assignedProjectCount: number;
  createdAt: string;
  updatedAt: string;
  probeStages?: ProbeStageResult[];
}

export type CompatibilityRating = 'SUPPORTED' | 'PARTIAL' | 'UNKNOWN' | 'UNAVAILABLE' | 'REVIEW_REQUIRED';

export interface RouteCompatibilityMatrix {
  sourceProvider: PhysicalProviderId;
  targetProvider: PhysicalProviderId;
  overallRating: CompatibilityRating;
  supportedModes: MigrationMode[];
  typeMappingFidelity: 'EXACT_1_TO_1' | 'HIGH_WITH_COERCION' | 'COMPLEX_TRANSFORMS_REQUIRED' | 'UNSUPPORTED';
  cdcCaptureSupport: boolean;
  transactionalApplySupport: boolean;
  notes: string[];
  prerequisites: string[];
}

// ----------------------------------------------------------------------------
// 5. PROJECTS & WORKSPACES (2.4)
// ----------------------------------------------------------------------------
export interface ProjectItem {
  id: string;
  key: string;
  name: string;
  description: string;
  defaultEnvironment: string;
  owner: string;
  targetMilestone?: string;
  health: OperationalHealth;
  migrationIds: string[];
  activeMigrationsCount: number;
  attentionCount: number;
  scheduledCount: number;
  membersCount: number;
  progressPercent: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectCoordinationNode {
  id: string;
  migrationId: string;
  name: string;
  mode: MigrationMode;
  status: MigrationLifecycleState;
  progress: number;
}

export interface ProjectCoordinationEdge {
  id: string;
  source: string;
  target: string;
  relationship: 'MUST_COMPLETE_BEFORE' | 'MUST_REACH_STATE_BEFORE' | 'MUST_VALIDATE_BEFORE' | 'MUST_BE_CAUGHT_UP_BEFORE' | 'COORDINATED_CUTOVER_GROUP';
  isSatisfied: boolean;
}

export interface ProjectMember {
  id: string;
  name: string;
  email: string;
  principalType: 'USER' | 'DIRECTORY_GROUP';
  roles: string[];
  effectiveGrants: string[];
  soDConflicts: string[];
  jitStatus?: 'ACTIVE' | 'REQUESTED' | 'EXPIRED';
}

// ----------------------------------------------------------------------------
// 6. DISCOVERY, SCOPE & TOPOLOGY (STEP 4)
// ----------------------------------------------------------------------------
export type DiscoveryDepth = 'QUICK' | 'STANDARD' | 'DEEP' | 'COMPLIANCE';

export interface TopologyNode {
  id: string;
  label: string;
  type: 'DATABASE' | 'SCHEMA' | 'OBJECT_GROUP' | 'TABLE' | 'VIEW' | 'COLLECTION' | 'TOPIC' | 'BUCKET' | 'PATH';
  objectCount?: number;
  estimatedRows?: number;
  estimatedSizeBytes?: number;
  isSelected?: boolean;
  isPartial?: boolean;
  children?: TopologyNode[];
}

export interface SelectedScopeRule {
  id: string;
  type: 'INCLUDE' | 'EXCLUDE' | 'PATTERN' | 'PREDICATE' | 'PROJECTION' | 'PARTITION_RANGE';
  targetPattern: string;
  predicate?: string;
  columns?: string[];
  affectedObjectsCount: number;
}

// ----------------------------------------------------------------------------
// 7. STEP 5 — DUAL STUDIOS: MAPPING & SCT WORKBENCH
// ----------------------------------------------------------------------------
export type ColumnMappingStatus = 'MAPPED' | 'PARTIAL' | 'REVIEW_REQUIRED' | 'STALE' | 'UNSUPPORTED';

export interface ColumnMappingRow {
  id: string;
  sourceColumn: string;
  sourceType: string;
  targetColumn: string;
  targetType: string;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  isNullable: boolean;
  transformation?: string;
  piiSensitivity?: 'NONE' | 'PCI' | 'GDPR_NAME' | 'SSN' | 'EMAIL' | 'CUSTOM';
  piiMaskingPolicy?: string;
  status: ColumnMappingStatus;
  notes?: string;
}

export interface TableMappingItem {
  id: string;
  sourceSchema: string;
  sourceTable: string;
  targetSchema: string;
  targetTable: string;
  columnsCount: number;
  mappedColumnsCount: number;
  isComplete: boolean;
  piiRulesCount: number;
  dedupEnabled: boolean;
  dedupCandidateKeys: string[];
  dedupSurvivorRule: 'LATEST_TIMESTAMP' | 'HIGHEST_SEQUENCE' | 'SOURCE_PRIORITY';
  preOperationHookSql?: string;
  postOperationHookSql?: string;
  conflictPolicy: 'OVERWRITE' | 'IGNORE' | 'FAIL_ON_CONFLICT';
  columns: ColumnMappingRow[];
}

export type ConversionStatus =
  | 'NOT_EVALUATED'
  | 'CONVERSION_PROPOSED'
  | 'NEEDS_REVIEW'
  | 'UNSUPPORTED_CONSTRUCT'
  | 'READY_FOR_BACKEND_VALIDATION';

export interface CodeTranspilerItem {
  id: string;
  schema: string;
  name: string;
  objectType: 'PACKAGE' | 'PROCEDURE' | 'FUNCTION' | 'TRIGGER' | 'SEQUENCE' | 'TYPE' | 'VIEW';
  sourceLanguage: string;
  targetLanguage: string;
  sourceSql: string;
  targetSql: string;
  conversionStatus: ConversionStatus;
  findings: {
    line: number;
    severity: 'INFO' | 'WARNING' | 'ERROR';
    code: string;
    message: string;
    suggestedFix?: string;
  }[];
  parametersCount: number;
  complexityScore: number;
}

// ----------------------------------------------------------------------------
// 8. STEP 6 — ENTERPRISE CONFIGURATION TAXONOMY (DOMAINS A..AC)
// ----------------------------------------------------------------------------
export type ConfigDomainId =
  | 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I' | 'J' | 'K' | 'L' | 'M'
  | 'N' | 'O' | 'P' | 'Q' | 'R' | 'S' | 'T' | 'U' | 'V' | 'W' | 'X' | 'Y' | 'Z'
  | 'AA' | 'AB' | 'AC';

export interface ConfigFieldDescriptor {
  id: string;
  label: string;
  description: string;
  domainId: ConfigDomainId;
  type: 'number' | 'string' | 'boolean' | 'select' | 'duration' | 'bytes';
  options?: { label: string; value: any }[];
  defaultValue: any;
  effectiveValue: any;
  recommendation?: string;
  scope: 'MIGRATION' | 'NODE' | 'OBJECT' | 'PARTITION' | 'CONNECTOR';
  isOverridden: boolean;
  isBasicVisible: boolean;
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  restartRequired: boolean;
  recompileRequired?: boolean;
}

export interface ConfigDomainGroup {
  id: ConfigDomainId;
  name: string;
  description: string;
  applicableModes: MigrationMode[];
  fields: ConfigFieldDescriptor[];
}

export type BasicPerformancePreset = 'CONSERVATIVE' | 'BALANCED' | 'HIGH_THROUGHPUT';

export interface BasicConfigurationView {
  performancePreset: BasicPerformancePreset;
  derivedMinWorkers: number;
  derivedMaxWorkers: number;
  derivedBatchMb: number;
  durabilityLevel: 'STANDARD' | 'MAXIMUM';
  spillHeadroomGb: number;
  cdcLagObjectiveMs?: number;
  watermarkFreshnessSec?: number;
  validationDepth: 'QUICK' | 'STANDARD' | 'DEEP';
}

// ----------------------------------------------------------------------------
// 9. STEP 7 — EXECUTION PLAN & APPROVAL BARRIER (CYTOSCAPE DAG)
// ----------------------------------------------------------------------------
export type PlanNodeState = 'QUEUED' | 'READY' | 'RUNNING' | 'COMPLETED' | 'BLOCKED' | 'FAILED' | 'BARRIER_WAITING';

export interface DagNodeViewModel {
  id: string;
  label: string;
  type: 'STAGE' | 'DISCOVERY' | 'SCHEMA' | 'BULK_TRANSFER' | 'CDC_CATCHUP' | 'VALIDATION' | 'APPROVAL_BARRIER' | 'CUTOVER' | 'REPAIR';
  state: PlanNodeState;
  progressPercent: number;
  workerCount?: number;
  throughput?: string;
  isBarrier?: boolean;
  barrierType?: 'MANDATORY_FOUR_EYES' | 'QUORUM_APPROVAL' | 'MAKER_CHECKER' | 'CUSTOM_SIGN_OFF';
  approverRoles?: string[];
  requiredSignatures?: number;
  currentSignatures?: number;
  isApproved?: boolean;
}

export interface DagEdgeViewModel {
  id: string;
  source: string;
  target: string;
  label?: string;
  isCrossCutting?: boolean;
  canInsertBarrier?: boolean;
}

export interface ExecutionPlanViewModel {
  planId: string;
  migrationId: string;
  version: number;
  fingerprint: string;
  mode: MigrationMode;
  isStale: boolean;
  estimatedDurationMin: number;
  totalWorkItems: number;
  nodes: DagNodeViewModel[];
  edges: DagEdgeViewModel[];
  risks: string[];
  warnings: string[];
}

// ----------------------------------------------------------------------------
// 10. STEP 8 — GOVERNANCE & READINESS
// ----------------------------------------------------------------------------
export type ReadinessVerdict = 'READY_TO_INITIALIZE' | 'BLOCKED';

export interface ReadinessCheckItem {
  id: string;
  category: 'CONNECTION' | 'PREREQUISITES' | 'NETWORK' | 'STORAGE' | 'SCHEMA' | 'CONFIGURATION' | 'GOVERNANCE';
  title: string;
  status: 'PASSED' | 'FAILED' | 'WARNING' | 'REQUIRES_ACTION';
  detail: string;
  remediation?: string;
}

// ----------------------------------------------------------------------------
// 11. VALIDATION OPERATIONS (2.6 — DATA SYNCHRONIZATION ASSURANCE)
// ----------------------------------------------------------------------------
export type ValidationSyncVerdict =
  | 'VALIDATING'
  | 'SYNCED'
  | 'NOT_SYNCED'
  | 'INCONCLUSIVE'
  | 'BLOCKED'
  | 'RECONCILING'
  | 'REPAIRING'
  | 'REVALIDATING'
  | 'SYNCED_CERTIFIED';

export type ValidationPurpose =
  | 'PRE_MIGRATION_BASELINE'
  | 'POST_MIGRATION_VERIFICATION'
  | 'CONTINUOUS_SYNCHRONIZATION_ASSURANCE'
  | 'INDEPENDENT_AUDIT'
  | 'REVALIDATION'
  | 'CERTIFICATION'
  | 'INVESTIGATION';

export type ValidationProfile = 'QUICK' | 'STANDARD' | 'DEEP' | 'FULL_CERTIFICATION';

export interface ValidationItem {
  id: string;
  name: string;
  purpose: ValidationPurpose;
  migrationId?: string;
  migrationName?: string;
  sourceEngine: PhysicalProviderId;
  sourceInstance: string;
  targetEngine: PhysicalProviderId;
  targetInstance: string;
  verdict: ValidationSyncVerdict;
  profile: ValidationProfile;
  scopeType: 'FULL' | 'PARTITIONED' | 'SAMPLED';
  objectsExpected: number;
  objectsValidated: number;
  objectsDivergent: number;
  rowsExpected: number;
  rowsValidated: number;
  rowsMatched: number;
  rowsMismatched: number;
  rowsMissingInTarget: number;
  rowsExtraInTarget: number;
  cellDifferencesCount: number;
  durationSec: number;
  isRepairEligible: boolean;
  isCertified: boolean;
  runFingerprint: string;
  startedAt: string;
  completedAt?: string;
}

export interface DifferenceFunnelLevel {
  label: string;
  totalCount: number;
  matchedCount: number;
  mismatchedCount: number;
  unit: string;
  percentMatched: number;
}

export interface SchemaDiffItem {
  objectName: string;
  sourceType: string;
  targetType: string;
  status: 'MATCH' | 'TYPE_COERCION' | 'MISSING_IN_TARGET' | 'EXTRA_IN_TARGET' | 'CONSTRAINT_MISMATCH';
  detail: string;
}

export interface PartitionHeatmapCell {
  partitionId: string;
  keyRange: string;
  status: 'IDENTICAL' | 'LOW_DIFF' | 'HIGH_DIFF' | 'UNCHECKED';
  divergentRows: number;
  totalRows: number;
}

export interface MerkleNodeItem {
  id: string;
  range: string;
  sourceHash: string;
  targetHash: string;
  isMatched: boolean;
  children?: MerkleNodeItem[];
}

export interface DisputedRowItem {
  primaryKey: string;
  tableName: string;
  differenceType: 'VALUE_MISMATCH' | 'MISSING_IN_TARGET' | 'EXTRA_IN_TARGET';
  sourceFields: Record<string, any>;
  targetFields: Record<string, any>;
  disputedColumns: string[];
}

export interface GovernedRepairPlan {
  repairPlanId: string;
  validationRunId: string;
  fingerprint: string;
  proposedInserts: number;
  proposedUpdates: number;
  proposedDeletes: number;
  affectedObjects: string[];
  safetyClassification: 'TARGET_MUTATION_REVERSIBLE' | 'TARGET_MUTATION_HIGH_IMPACT';
  approvalRequired: boolean;
  approvalStatus: 'PENDING' | 'APPROVED' | 'REJECTED';
  approverRoles: string[];
  requiresMandatoryRevalidation: boolean;
  executionState: 'IDLE' | 'EXECUTING' | 'COMPLETED' | 'FAILED';
}

// ----------------------------------------------------------------------------
// 12. HISTORY & EVIDENCE LEDGER (2.7)
// ----------------------------------------------------------------------------
export type EvidenceSealingState = 'SEALED' | 'PENDING' | 'NOT_REQUESTED' | 'INVALIDATED';

export interface HistoryLedgerItem {
  executionId: string;
  migrationId: string;
  migrationName: string;
  sourceEngine: PhysicalProviderId;
  targetEngine: PhysicalProviderId;
  mode: MigrationMode;
  environment: string;
  startedAt: string;
  completedAt: string;
  durationString: string;
  lifecycleState: MigrationLifecycleState;
  validationVerdict: ValidationSyncVerdict;
  evidenceState: EvidenceSealingState;
  operator: string;
  planVersion: string;
  planFingerprint: string;
  rowsTransferred: number;
  throughputAvg: number;
}

export interface MultiRunComparisonMetric {
  dimension: string;
  runValues: Record<string, any>;
  hasVariance: boolean;
}

// ----------------------------------------------------------------------------
// 13. MIGRATION TEMPLATES (2.8)
// ----------------------------------------------------------------------------
export type TemplateStrength = 'RECOMMENDATION' | 'DEFAULT' | 'ENFORCED_POLICY';
export type TemplateCompatibilityVerdict = 'COMPATIBLE' | 'COMPATIBLE_WITH_ADJUSTMENTS' | 'REVIEW_REQUIRED' | 'INCOMPATIBLE' | 'UNKNOWN';

export interface MigrationTemplateItem {
  id: string;
  title: string;
  version: string;
  category: 'ORGANIZATION_STANDARD' | 'RECOMMENDED' | 'TEAM' | 'PROJECT' | 'DRAFT';
  description: string;
  sourceTypes: PhysicalProviderId[];
  targetTypes: PhysicalProviderId[];
  compatibleModes: MigrationMode[];
  strength: TemplateStrength;
  defaultConfigPreset: BasicPerformancePreset;
  recommendedWorkers: number;
  provenance: string;
  tags: string[];
  usageCount: number;
  lastUpdated: string;
  author: string;
}
