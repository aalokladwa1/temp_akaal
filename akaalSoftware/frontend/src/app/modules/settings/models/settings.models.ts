/**
 * AKAAL Settings — Part 1 Models
 * Authoritative contracts for Workstation General Preferences and Composable Appearance Modes.
 */

export type ThemeOption = 'enterprise-blue' | 'dark' | 'system';
export type AccessibilityPaletteOption = 'standard' | 'color-vision-safe';
export type ContrastOption = 'standard' | 'high-contrast';

export interface AppearanceSettings {
  theme: ThemeOption;
  palette: AccessibilityPaletteOption;
  contrast: ContrastOption;
  reduceMotion: boolean;
  enhancedFocus: boolean;
}

export type LandingSurfaceOption =
  | 'dashboard'
  | 'migration'
  | 'monitoring'
  | 'reports'
  | 'administration';

export type TimezoneOption =
  | 'LOCAL'
  | 'UTC'
  | 'America/New_York'
  | 'Europe/London'
  | 'Asia/Kolkata'
  | 'Asia/Singapore'
  | 'Asia/Tokyo';

export type DateFormatOption = 'YYYY-MM-DD' | 'MM/DD/YYYY' | 'DD/MM/YYYY';
export type TimeFormatOption = '24h' | '12h';
export type DataUnitStandard = 'BINARY_IEC' | 'DECIMAL_SI';
export type NumberGroupingSeparator = 'COMMA' | 'PERIOD' | 'SPACE';

export interface GeneralSettings {
  defaultLandingSurface: LandingSurfaceOption;
  timezonePreference: TimezoneOption;
  dateFormat: DateFormatOption;
  timeFormat: TimeFormatOption;
  dataUnitStandard: DataUnitStandard;
  numberGroupingSeparator: NumberGroupingSeparator;
  defaultOrgId: string;
  defaultWorkspaceId: string;
  defaultEnvironmentId: string;
  confirmDestructiveActions: boolean; // Permanently enforced for enterprise safety
  warnUnsavedChanges: boolean;
  enableLocalCrashTelemetry: boolean;
}

export interface SettingsNavCategory {
  id: string;
  label: string;
  path: string;
  icon: string;
  description: string;
  status: 'ACTIVE' | 'FUTURE';
  badge?: string;
}

export interface SettingsNavSection {
  title: string;
  categories: SettingsNavCategory[];
}

// ============================================================================
// PART 2: RUNTIME & MIGRATION DEFAULTS
// ============================================================================

export type ExecutionProfileOption = 'BALANCED' | 'HIGH_THROUGHPUT' | 'MEMORY_CONSTRAINED' | 'LOW_IMPACT';
export type ExecutionGraphOption = 'DYNAMIC_DAG' | 'FIXED_LINEAR';
export type TablePartitionStrategy = 'AUTO_DETECT' | 'PRIMARY_KEY_RANGE' | 'MODULO_HASH' | 'KEYSET_PAGING';
export type ConflictResolutionOption = 'SOURCE_WINS' | 'TARGET_WINS' | 'MANUAL_HOLD';
export type ValidationAssuranceLevel = 'LEVEL_1_ROW_COUNT' | 'LEVEL_2_CHECKSUM' | 'LEVEL_3_FULL_DIFF';
export type RecoveryStrategyOption = 'RESUME_CHECKPOINT' | 'RESTART_STEP' | 'FAIL_CLOSED';

export interface RuntimeMigrationSettings {
  // 1. Runtime
  executionProfile: ExecutionProfileOption;
  taskTimeoutSeconds: number;
  graphStrategy: ExecutionGraphOption;

  // 2. Workers / Parallelism
  defaultStartingWorkers: number;
  minConcurrencyFloor: number;
  preferredMaxWorkers: number;
  adaptiveConcurrencyEnabled: boolean;
  governedMaxWorkerLimit: number; // 64 (Governed by Platform Administration)

  // 3. Batching
  defaultBatchSize: number;
  adaptiveBatchingEnabled: boolean;
  maxMemoryPerBatchMb: number;
  lobStreamingThresholdKb: number;

  // 4. Queues
  defaultQueueCapacity: number;
  highWatermarkPercent: number;
  lowWatermarkPercent: number;

  // 5. Resource Limits
  governedMaxMemoryMb: number; // 8192 (Platform policy limit)
  governedMaxCpuMillicores: number; // 4000 (Platform policy limit)
  workerProcessPriority: string; // 'Normal (0)'

  // 6. Bulk
  partitionStrategy: TablePartitionStrategy;
  parallelChunksPerTable: number;
  readFetchBufferSize: number;
  directPathBulkInsert: boolean;

  // 7. CDC
  cdcBufferMemoryMb: number; // 64 MB (akaalEngine backlog default)
  spillThresholdPercent: number; // 80%
  cdcPollFrequencyMs: number; // 250 ms
  transactionGroupingWindowMs: number; // 500 ms

  // 8. Incremental / Polling
  pollingIntervalSeconds: number; // 10 s
  watermarkColumnStrategy: string; // 'Auto-Detect (updated_at, mtime)'
  lookbackSafetyMarginSeconds: number; // 60 s
  maxRecordsPerPoll: number; // 10000

  // 9. State Synchronization
  reconciliationStrategy: string; // 'Two-Way Keyset Diff'
  stateDriftSensitivity: string; // 'Strict'
  conflictResolutionPreference: ConflictResolutionOption;

  // 10. Validation
  validationAssuranceLevel: ValidationAssuranceLevel;
  sampleVerificationRatePercent: number; // 100%
  postMigrationAutoValidation: boolean;

  // 11. Recovery
  recoveryStrategy: RecoveryStrategyOption;
  maxAutomaticRetries: number;
  retryBackoffMultiplier: string; // 'Exponential (5s initial, 60s max)'
  fencingEpochRollbackBarrier: boolean; // Locked true (Durability Authority #5)
}

// ============================================================================
// PART 2: CONNECTOR DEFAULTS
// ============================================================================

export type TLSEnforcementMode = 'VERIFY_FULL' | 'VERIFY_CA' | 'PREFERRED' | 'REQUIRED';
export type CursorPaginationStrategy = 'KEYSET_CURSOR' | 'LIMIT_OFFSET' | 'STREAMING_RESULTSET';

export interface ConnectorSettings {
  // Connection Behavior & Timeouts
  connectTimeoutMs: number; // 15000 ms (RouteSpec)
  socketTimeoutMs: number; // 30000 ms (RouteSpec)
  dnsTimeoutMs: number; // 5000 ms (RouteSpec)
  statementTimeoutMs: number; // 60000 ms (SessionRequest)
  lockTimeoutMs: number; // 10000 ms (SessionRequest)

  // Keep-Alive & Network Probes
  keepaliveEnabled: boolean; // true (RouteSpec)
  keepaliveIdleSeconds: number; // 60 s
  keepaliveIntervalSeconds: number; // 15 s
  keepaliveProbesCount: number; // 5

  // Fetch & Transfer
  defaultFetchSize: number; // 2000 rows
  maxReadBufferMb: number; // 16 MB
  paginationStrategy: CursorPaginationStrategy;
  encodingFallback: string; // 'UTF-8 (Strict)'

  // Security Baseline
  tlsMinVersion: string; // 'TLSv1.2'
  tlsMode: TLSEnforcementMode; // 'VERIFY_FULL'
  allowPermissiveSelfSigned: boolean; // false (Governed)
  credentialProtocol: string; // 'vault://'
}

// ============================================================================
// PART 2: STORAGE & RETENTION
// ============================================================================

export interface StorageRetentionSettings {
  // Checkpoints
  checkpointIntervalRows: number; // 1000 rows
  checkpointIntervalSeconds: number; // 30 s
  retainedCheckpointsCount: number; // 10 snapshots
  checkpointStorageEngine: string; // 'SQLite WAL Journal'
  mandatoryDurabilityEnforced: boolean; // Locked true

  // CDC Buffers
  cdcStreamBufferMb: number; // 64 MB
  spillStorageLocation: string; // 'Local Encrypted Durability Scratch'
  governedSpillBudgetGb: number; // 100 GB (Platform quota)
  sourceRetentionWarningPercent: number; // 15% (SourceRetentionMonitor)

  // Reports & Evidence
  defaultReportRetentionDays: number; // 90 days
  sha256CryptographicAttestation: boolean; // Locked true
  exportFormatsEnabled: string[]; // ['JSON', 'CSV', 'ZIP']

  // Logs (Storage & Retention)
  diagnosticLogBudgetGb: number; // 10 GB
  logSegmentSizeMb: number; // 100 MB
  maxRetainedLogSegments: number; // 20 segments
  logArchivalCompression: string; // 'Gzip (Level 6)'

  // Retention Policies
  defaultJobHistoryRetentionDays: number; // 30 days
  enterpriseMinRetentionDays: number; // 30 days (Governed minimum)
  activeLegalHoldProtected: boolean; // Reference display (Domain 5.9 Audit)
}

// ============================================================================
// PART 3: NOTIFICATIONS
// ============================================================================

export type NotificationSeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type NotificationDigestFrequency = 'IMMEDIATE' | 'HOURLY_DIGEST' | 'DAILY_DIGEST';

export interface NotificationSettings {
  // Email
  emailEnabled: boolean;
  emailMinSeverity: NotificationSeverityLevel;
  emailDigestFrequency: NotificationDigestFrequency;
  emailNotifyOnMigrationFailure: boolean;
  emailNotifyOnSecurityAlert: boolean;
  emailNotifyOnGovernanceBarrier: boolean;

  // Slack
  slackEnabled: boolean;
  slackMinSeverity: NotificationSeverityLevel;
  slackThreadReplies: boolean;
  slackChannelId: string; // Dynamic reference to configured Slack channel in Admin 5.11

  // Microsoft Teams
  teamsEnabled: boolean;
  teamsMinSeverity: NotificationSeverityLevel;
  teamsChannelId: string; // Dynamic reference to configured Teams channel in Admin 5.11

  // Webhooks
  webhookEnabled: boolean;
  webhookPayloadFormat: 'STANDARD_JSON' | 'EXPANDED_JSON';
  webhookEndpointId: string; // Dynamic reference to configured Webhook endpoint in Admin 5.11

  // Escalation Defaults
  escalationEnabled: boolean;
  escalationTargetChannelId: string;
  personalAckWindowMinutes: number; // 5, 15, 30
  mandatoryCriticalEscalationLocked: boolean; // Locked true: Enterprise critical escalation cannot be suppressed

  // Quiet Hours
  quietHoursEnabled: boolean;
  quietHoursStart: string; // '22:00'
  quietHoursEnd: string; // '07:00'
  criticalBypassQuietHours: boolean; // Locked true: Critical alerts bypass quiet hours
}

// ============================================================================
// PART 3: INTEGRATIONS
// ============================================================================

export type TelemetryExportTarget = 'SPLUNK_HEC' | 'DATADOG_AGENT' | 'LOCAL_CONSOLE';
export type CatalogFormatType = 'OPEN_LINEAGE' | 'APACHE_ATLAS' | 'CUSTOM_CATALOG';

export interface IntegrationSettings {
  // Observability Integrations
  observabilityExportEnabled: boolean;
  telemetryDestination: TelemetryExportTarget;
  propagateTraceContext: boolean; // W3C traceparent header propagation
  autoExportCrashDiagnostics: boolean;

  // Notification Integrations
  defaultNotificationChannelId: string;
  fanOutCriticalFailures: boolean;

  // Catalog / Lineage Integrations
  lineagePublishingEnabled: boolean;
  catalogFormat: CatalogFormatType;
  autoExportLineageOnExecution: boolean;
  catalogEndpointConfigured: boolean; // Truthful: False indicates missing workspace configuration

  // Installed Enterprise Integrations
  suppressedIntegrations: Record<string, boolean>; // Local suppression per integration id
}

// ============================================================================
// PART 3: AI & INTELLIGENCE
// ============================================================================

export type AssistanceProactivityMode = 'ON_DEMAND' | 'ADVISORY';
export type RecommendationConfidenceLevel = 'HIGH' | 'STANDARD';

export interface AiIntelligenceSettings {
  // Assistant Configuration
  assistantEnabled: boolean;
  proactivityMode: AssistanceProactivityMode;
  governedProviderDisplay: string; // 'Platform Governed Service Gateway'
  strictCredentialSanitization: boolean; // Locked true: Sanitizes secrets and credentials before model inference
  defaultRequestTokenBudget: number; // 4000 tokens (bounded preference)
  workspaceMonthlyCostCapDisplay: string; // Read-only governed indicator

  // Planning Assistance
  planSynthesisAssistance: boolean;
  partitionStrategyRecommendation: boolean;
  advisoryPlanConfirmationRequired: boolean; // Locked true: AI suggestions require human approval

  // Optimization
  workloadAutoTuningSuggestions: boolean;
  concurrencyRecommendationAdvisory: boolean;

  // RCA / Diagnostics
  failureRcaEnabled: boolean;
  redactSensitiveDataInTraces: boolean; // Locked true: Error traces scrubbed before model analysis

  // Recommendation Policies
  recommendationConfidenceLevel: RecommendationConfidenceLevel;
  mandatoryHumanReviewEnforced: boolean; // Locked true: Autonomous execution disabled

  // Predictive Operations
  cdcBufferSaturationPrediction: boolean;
  throughputAnomalyDetection: boolean;
}

// ============================================================================
// PART 4: LOGGING & DIAGNOSTICS
// ============================================================================

export type ClientLogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
export type EngineLogLevel = 'DEBUG' | 'INFO';
export type LogDestination = 'CONSOLE_AND_DISK' | 'DISK_ONLY' | 'CONSOLE_ONLY';

export interface LoggingDiagnosticsSettings {
  // Log Levels
  clientLogLevel: ClientLogLevel;
  engineLogLevel: EngineLogLevel;
  logDestination: LogDestination;
  maxActiveLogSizeMb: number; // 50 MB (10 - 500)

  // Diagnostics
  crashDiagnosticCapture: boolean; // default true
  engineStateSnapshotOnAnomaly: boolean; // default false
  anomalyDumpDirectory: string; // read-only reference indicator

  // Tracing
  traceContextPropagation: boolean; // default true (W3C traceparent)
  localSpanBufferLimit: number; // 10000 spans (1000 - 50000)
  tracingSamplingRatePercent: number; // 100% (1 - 100)

  // Support Bundles (Defaults for diagnostic packages)
  bundleIncludeSanitizedConfig: boolean; // default true
  bundleIncludeEngineStatus: boolean; // default true
  bundleIncludeScrubbedLogs: boolean; // default true
  bundleScrubSecretsAndPii: boolean; // Locked true: Mandatory cryptographic and secret scrubbing
}

// ============================================================================
// PART 4: ADVANCED
// ============================================================================

export interface AdvancedSettings {
  // Capability Controls
  clientMemoryCacheLimitMb: number; // 512 MB (128 - 4096)
  parallelSchemaInspectionThreads: number; // 4 (1 - 16)
  ipcResponseTimeoutSeconds: number; // 30 s (5 - 120)
  localDiskIoThrottleMb: number; // 0 = Unlimited (0 - 500)

  // Experimental Capabilities
  experimentalCapabilitiesAcknowledged: boolean; // default false

  // Developer Options
  ipcDebugLogging: boolean; // default false
  uiBoundingBoxInspection: boolean; // default false
  extendedErrorStackTraces: boolean; // default false

  // Internal Diagnostics
  sqliteWalDiagnosticJournaling: boolean; // default true
  corruptBlockSelfCheckOnStartup: boolean; // default true

  // Fail-closed governance law
  failClosedGovernanceEnforced: boolean; // Locked true: Non-bypassable platform security gate
}

