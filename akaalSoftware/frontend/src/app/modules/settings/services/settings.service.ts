/**
 * AKAAL Settings — Settings Service
 * Authoritative client preference store with reactive signals, DOM theme/accessibility class synchronization,
 * and persistent local workstation storage.
 */

import { Injectable, signal, computed, effect } from '@angular/core';
import {
  AppearanceSettings,
  GeneralSettings,
  ThemeOption,
  AccessibilityPaletteOption,
  ContrastOption,
  LandingSurfaceOption,
  TimezoneOption,
  DateFormatOption,
  TimeFormatOption,
  DataUnitStandard,
  NumberGroupingSeparator,
  RuntimeMigrationSettings,
  ConnectorSettings,
  StorageRetentionSettings,
  ExecutionProfileOption,
  ExecutionGraphOption,
  TablePartitionStrategy,
  ConflictResolutionOption,
  ValidationAssuranceLevel,
  RecoveryStrategyOption,
  TLSEnforcementMode,
  CursorPaginationStrategy,
  NotificationSettings,
  IntegrationSettings,
  AiIntelligenceSettings,
  LoggingDiagnosticsSettings,
  AdvancedSettings,
  ClientLogLevel,
  EngineLogLevel,
  LogDestination
} from '../models/settings.models';

const STORAGE_KEY_APPEARANCE = 'akaal_settings_appearance';
const STORAGE_KEY_GENERAL = 'akaal_settings_general';

export const DEFAULT_APPEARANCE_SETTINGS: AppearanceSettings = {
  theme: 'enterprise-blue',
  palette: 'standard',
  contrast: 'standard',
  reduceMotion: false,
  enhancedFocus: false
};

export const DEFAULT_GENERAL_SETTINGS: GeneralSettings = {
  defaultLandingSurface: 'dashboard',
  timezonePreference: 'LOCAL',
  dateFormat: 'YYYY-MM-DD',
  timeFormat: '24h',
  dataUnitStandard: 'BINARY_IEC',
  numberGroupingSeparator: 'COMMA',
  defaultOrgId: 'org-enterprise',
  defaultWorkspaceId: 'ws-prod-migration',
  defaultEnvironmentId: 'env-prod-01',
  confirmDestructiveActions: true, // Safety-critical locked preference
  warnUnsavedChanges: true,
  enableLocalCrashTelemetry: true
};

export const DEFAULT_RUNTIME_MIGRATION_SETTINGS: RuntimeMigrationSettings = {
  executionProfile: 'BALANCED',
  taskTimeoutSeconds: 3600,
  graphStrategy: 'DYNAMIC_DAG',
  defaultStartingWorkers: 16,
  minConcurrencyFloor: 4,
  preferredMaxWorkers: 32,
  adaptiveConcurrencyEnabled: true,
  governedMaxWorkerLimit: 64,
  defaultBatchSize: 10000,
  adaptiveBatchingEnabled: true,
  maxMemoryPerBatchMb: 64,
  lobStreamingThresholdKb: 1024,
  defaultQueueCapacity: 50000,
  highWatermarkPercent: 85,
  lowWatermarkPercent: 50,
  governedMaxMemoryMb: 8192,
  governedMaxCpuMillicores: 4000,
  workerProcessPriority: 'Normal (0)',
  partitionStrategy: 'AUTO_DETECT',
  parallelChunksPerTable: 4,
  readFetchBufferSize: 5000,
  directPathBulkInsert: true,
  cdcBufferMemoryMb: 64,
  spillThresholdPercent: 80,
  cdcPollFrequencyMs: 250,
  transactionGroupingWindowMs: 500,
  pollingIntervalSeconds: 10,
  watermarkColumnStrategy: 'Auto-Detect (updated_at, mtime)',
  lookbackSafetyMarginSeconds: 60,
  maxRecordsPerPoll: 10000,
  reconciliationStrategy: 'Two-Way Keyset Diff',
  stateDriftSensitivity: 'Strict',
  conflictResolutionPreference: 'SOURCE_WINS',
  validationAssuranceLevel: 'LEVEL_2_CHECKSUM',
  sampleVerificationRatePercent: 100,
  postMigrationAutoValidation: true,
  recoveryStrategy: 'RESUME_CHECKPOINT',
  maxAutomaticRetries: 3,
  retryBackoffMultiplier: 'Exponential (5s initial, 60s max)',
  fencingEpochRollbackBarrier: true
};

export const DEFAULT_CONNECTOR_SETTINGS: ConnectorSettings = {
  connectTimeoutMs: 15000,
  socketTimeoutMs: 30000,
  dnsTimeoutMs: 5000,
  statementTimeoutMs: 60000,
  lockTimeoutMs: 10000,
  keepaliveEnabled: true,
  keepaliveIdleSeconds: 60,
  keepaliveIntervalSeconds: 15,
  keepaliveProbesCount: 5,
  defaultFetchSize: 2000,
  maxReadBufferMb: 16,
  paginationStrategy: 'KEYSET_CURSOR',
  encodingFallback: 'UTF-8 (Strict)',
  tlsMinVersion: 'TLSv1.2',
  tlsMode: 'VERIFY_FULL',
  allowPermissiveSelfSigned: false,
  credentialProtocol: 'vault://'
};

export const DEFAULT_STORAGE_RETENTION_SETTINGS: StorageRetentionSettings = {
  checkpointIntervalRows: 1000,
  checkpointIntervalSeconds: 30,
  retainedCheckpointsCount: 10,
  checkpointStorageEngine: 'SQLite WAL Journal',
  mandatoryDurabilityEnforced: true,
  cdcStreamBufferMb: 64,
  spillStorageLocation: 'Local Encrypted Durability Scratch',
  governedSpillBudgetGb: 100,
  sourceRetentionWarningPercent: 15,
  defaultReportRetentionDays: 90,
  sha256CryptographicAttestation: true,
  exportFormatsEnabled: ['JSON', 'CSV', 'ZIP'],
  diagnosticLogBudgetGb: 10,
  logSegmentSizeMb: 100,
  maxRetainedLogSegments: 20,
  logArchivalCompression: 'Gzip (Level 6)',
  defaultJobHistoryRetentionDays: 30,
  enterpriseMinRetentionDays: 30,
  activeLegalHoldProtected: true
};

export const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  emailEnabled: true,
  emailMinSeverity: 'HIGH',
  emailDigestFrequency: 'IMMEDIATE',
  emailNotifyOnMigrationFailure: true,
  emailNotifyOnSecurityAlert: true,
  emailNotifyOnGovernanceBarrier: true,
  slackEnabled: true,
  slackMinSeverity: 'CRITICAL',
  slackThreadReplies: true,
  slackChannelId: 'chan-slack-01',
  teamsEnabled: false,
  teamsMinSeverity: 'CRITICAL',
  teamsChannelId: '',
  webhookEnabled: false,
  webhookPayloadFormat: 'STANDARD_JSON',
  webhookEndpointId: '',
  escalationEnabled: true,
  escalationTargetChannelId: 'chan-pagerduty-01',
  personalAckWindowMinutes: 15,
  mandatoryCriticalEscalationLocked: true,
  quietHoursEnabled: true,
  quietHoursStart: '22:00',
  quietHoursEnd: '07:00',
  criticalBypassQuietHours: true
};

export const DEFAULT_INTEGRATION_SETTINGS: IntegrationSettings = {
  observabilityExportEnabled: true,
  telemetryDestination: 'SPLUNK_HEC',
  propagateTraceContext: true,
  autoExportCrashDiagnostics: true,
  defaultNotificationChannelId: 'chan-slack-01',
  fanOutCriticalFailures: true,
  lineagePublishingEnabled: false,
  catalogFormat: 'OPEN_LINEAGE',
  autoExportLineageOnExecution: false,
  catalogEndpointConfigured: false,
  suppressedIntegrations: {}
};

export const DEFAULT_AI_INTELLIGENCE_SETTINGS: AiIntelligenceSettings = {
  assistantEnabled: true,
  proactivityMode: 'ADVISORY',
  governedProviderDisplay: 'Platform Governed Service Gateway (Isolated Engine Endpoint)',
  strictCredentialSanitization: true,
  defaultRequestTokenBudget: 4000,
  workspaceMonthlyCostCapDisplay: '$500.00 / mo (Enforced by Admin Policy)',
  planSynthesisAssistance: true,
  partitionStrategyRecommendation: true,
  advisoryPlanConfirmationRequired: true,
  workloadAutoTuningSuggestions: true,
  concurrencyRecommendationAdvisory: true,
  failureRcaEnabled: true,
  redactSensitiveDataInTraces: true,
  recommendationConfidenceLevel: 'HIGH',
  mandatoryHumanReviewEnforced: true,
  cdcBufferSaturationPrediction: true,
  throughputAnomalyDetection: true
};

export const DEFAULT_LOGGING_DIAGNOSTICS_SETTINGS: LoggingDiagnosticsSettings = {
  clientLogLevel: 'INFO',
  engineLogLevel: 'INFO',
  logDestination: 'CONSOLE_AND_DISK',
  maxActiveLogSizeMb: 50,
  crashDiagnosticCapture: true,
  engineStateSnapshotOnAnomaly: false,
  anomalyDumpDirectory: 'AppData/Local/AKAAL/diagnostics',
  traceContextPropagation: true,
  localSpanBufferLimit: 10000,
  tracingSamplingRatePercent: 100,
  bundleIncludeSanitizedConfig: true,
  bundleIncludeEngineStatus: true,
  bundleIncludeScrubbedLogs: true,
  bundleScrubSecretsAndPii: true
};

export const DEFAULT_ADVANCED_SETTINGS: AdvancedSettings = {
  clientMemoryCacheLimitMb: 512,
  parallelSchemaInspectionThreads: 4,
  ipcResponseTimeoutSeconds: 30,
  localDiskIoThrottleMb: 0,
  experimentalCapabilitiesAcknowledged: false,
  ipcDebugLogging: false,
  uiBoundingBoxInspection: false,
  extendedErrorStackTraces: false,
  sqliteWalDiagnosticJournaling: true,
  corruptBlockSelfCheckOnStartup: true,
  failClosedGovernanceEnforced: true
};

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  public appearanceSettings = signal<AppearanceSettings>(this.loadAppearanceSettings());
  public generalSettings = signal<GeneralSettings>(this.loadGeneralSettings());
  public systemPrefersDark = signal<boolean>(this.detectSystemDarkPreference());

  // Operational Defaults (Part 2: in-memory workstation defaults for new pipelines)
  public runtimeMigrationSettings = signal<RuntimeMigrationSettings>({ ...DEFAULT_RUNTIME_MIGRATION_SETTINGS });
  public connectorSettings = signal<ConnectorSettings>({ ...DEFAULT_CONNECTOR_SETTINGS });
  public storageRetentionSettings = signal<StorageRetentionSettings>({ ...DEFAULT_STORAGE_RETENTION_SETTINGS });

  // Operational Defaults (Part 3: in-memory workstation defaults)
  public notificationSettings = signal<NotificationSettings>({ ...DEFAULT_NOTIFICATION_SETTINGS });
  public integrationSettings = signal<IntegrationSettings>({ ...DEFAULT_INTEGRATION_SETTINGS });
  public aiIntelligenceSettings = signal<AiIntelligenceSettings>({ ...DEFAULT_AI_INTELLIGENCE_SETTINGS });

  // Operational Defaults (Part 4: in-memory workstation defaults)
  public loggingSettings = signal<LoggingDiagnosticsSettings>({ ...DEFAULT_LOGGING_DIAGNOSTICS_SETTINGS });
  public advancedSettings = signal<AdvancedSettings>({ ...DEFAULT_ADVANCED_SETTINGS });

  /**
   * Resolves the active theme considering system OS preference if theme is 'system'
   */
  public effectiveTheme = computed<'enterprise-blue' | 'dark'>(() => {
    const currentTheme = this.appearanceSettings().theme;
    if (currentTheme === 'system') {
      return this.systemPrefersDark() ? 'dark' : 'enterprise-blue';
    }
    return currentTheme;
  });

  constructor() {
    this.initSystemThemeListener();
    this.applyAppearanceToDOM();
  }

  // =========================================================================
  // Appearance Preferences
  // =========================================================================

  public updateAppearance(changes: Partial<AppearanceSettings>): void {
    this.appearanceSettings.update(prev => {
      const updated: AppearanceSettings = { ...prev, ...changes };
      this.saveAppearanceSettings(updated);
      return updated;
    });
    this.applyAppearanceToDOM();
  }

  public resetAppearance(): void {
    this.appearanceSettings.set({ ...DEFAULT_APPEARANCE_SETTINGS });
    this.saveAppearanceSettings(DEFAULT_APPEARANCE_SETTINGS);
    this.applyAppearanceToDOM();
  }

  // =========================================================================
  // General Preferences
  // =========================================================================

  public updateGeneral(changes: Partial<GeneralSettings>): void {
    this.generalSettings.update(prev => {
      const updated: GeneralSettings = {
        ...prev,
        ...changes,
        // Ensure safety-critical setting remains locked
        confirmDestructiveActions: true
      };
      this.saveGeneralSettings(updated);
      return updated;
    });
  }

  public resetGeneral(): void {
    this.generalSettings.set({ ...DEFAULT_GENERAL_SETTINGS });
    this.saveGeneralSettings(DEFAULT_GENERAL_SETTINGS);
  }

  // =========================================================================
  // Operational Defaults: Runtime & Migration Defaults
  // =========================================================================

  public updateRuntimeMigration(changes: Partial<RuntimeMigrationSettings>): void {
    this.runtimeMigrationSettings.update(prev => ({
      ...prev,
      ...changes,
      // Governed safety invariants remain locked
      fencingEpochRollbackBarrier: true,
      governedMaxWorkerLimit: DEFAULT_RUNTIME_MIGRATION_SETTINGS.governedMaxWorkerLimit,
      governedMaxMemoryMb: DEFAULT_RUNTIME_MIGRATION_SETTINGS.governedMaxMemoryMb,
      governedMaxCpuMillicores: DEFAULT_RUNTIME_MIGRATION_SETTINGS.governedMaxCpuMillicores
    }));
  }

  public resetRuntimeMigration(): void {
    this.runtimeMigrationSettings.set({ ...DEFAULT_RUNTIME_MIGRATION_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: Connector Defaults
  // =========================================================================

  public updateConnector(changes: Partial<ConnectorSettings>): void {
    this.connectorSettings.update(prev => ({
      ...prev,
      ...changes,
      // Governed security baseline remains locked
      allowPermissiveSelfSigned: false,
      credentialProtocol: 'vault://'
    }));
  }

  public resetConnector(): void {
    this.connectorSettings.set({ ...DEFAULT_CONNECTOR_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: Storage & Retention
  // =========================================================================

  public updateStorageRetention(changes: Partial<StorageRetentionSettings>): void {
    this.storageRetentionSettings.update(prev => ({
      ...prev,
      ...changes,
      // Governed durability and audit compliance invariants remain locked
      mandatoryDurabilityEnforced: true,
      sha256CryptographicAttestation: true,
      enterpriseMinRetentionDays: DEFAULT_STORAGE_RETENTION_SETTINGS.enterpriseMinRetentionDays,
      activeLegalHoldProtected: true
    }));
  }

  public resetStorageRetention(): void {
    this.storageRetentionSettings.set({ ...DEFAULT_STORAGE_RETENTION_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: Notifications
  // =========================================================================

  public updateNotification(changes: Partial<NotificationSettings>): void {
    this.notificationSettings.update(prev => ({
      ...prev,
      ...changes,
      mandatoryCriticalEscalationLocked: true,
      criticalBypassQuietHours: true
    }));
  }

  public resetNotifications(): void {
    this.notificationSettings.set({ ...DEFAULT_NOTIFICATION_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: Integrations
  // =========================================================================

  public updateIntegration(changes: Partial<IntegrationSettings>): void {
    this.integrationSettings.update(prev => ({
      ...prev,
      ...changes,
      catalogEndpointConfigured: false
    }));
  }

  public resetIntegrations(): void {
    this.integrationSettings.set({ ...DEFAULT_INTEGRATION_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: AI & Intelligence
  // =========================================================================

  public updateAiIntelligence(changes: Partial<AiIntelligenceSettings>): void {
    this.aiIntelligenceSettings.update(prev => ({
      ...prev,
      ...changes,
      strictCredentialSanitization: true,
      advisoryPlanConfirmationRequired: true,
      redactSensitiveDataInTraces: true,
      mandatoryHumanReviewEnforced: true,
      governedProviderDisplay: DEFAULT_AI_INTELLIGENCE_SETTINGS.governedProviderDisplay,
      workspaceMonthlyCostCapDisplay: DEFAULT_AI_INTELLIGENCE_SETTINGS.workspaceMonthlyCostCapDisplay
    }));
  }

  public resetAiIntelligence(): void {
    this.aiIntelligenceSettings.set({ ...DEFAULT_AI_INTELLIGENCE_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: Logging & Diagnostics
  // =========================================================================

  public updateLogging(changes: Partial<LoggingDiagnosticsSettings>): void {
    this.loggingSettings.update(prev => ({
      ...prev,
      ...changes,
      bundleScrubSecretsAndPii: true // Enterprise mandatory safety invariant
    }));
  }

  public resetLogging(): void {
    this.loggingSettings.set({ ...DEFAULT_LOGGING_DIAGNOSTICS_SETTINGS });
  }

  // =========================================================================
  // Operational Defaults: Advanced
  // =========================================================================

  public updateAdvanced(changes: Partial<AdvancedSettings>): void {
    this.advancedSettings.update(prev => ({
      ...prev,
      ...changes,
      failClosedGovernanceEnforced: true // Fail-closed governance law cannot be modified
    }));
  }

  public resetAdvanced(): void {
    this.advancedSettings.set({ ...DEFAULT_ADVANCED_SETTINGS });
  }

  // =========================================================================
  // DOM Theme & Accessibility Class Synchronization
  // =========================================================================

  public applyAppearanceToDOM(): void {
    if (typeof document === 'undefined') return;

    const root = document.documentElement;
    const appearance = this.appearanceSettings();
    const effective = this.effectiveTheme();

    // 1. Dark Theme
    if (effective === 'dark') {
      root.classList.add('dark');
      root.setAttribute('data-theme', 'dark');
    } else {
      root.classList.remove('dark');
      root.setAttribute('data-theme', 'enterprise-blue');
    }

    // 2. Color Vision Safe Palette
    if (appearance.palette === 'color-vision-safe') {
      root.classList.add('color-vision-safe');
      root.setAttribute('data-palette', 'color-vision-safe');
    } else {
      root.classList.remove('color-vision-safe');
      root.setAttribute('data-palette', 'standard');
    }

    // 3. High Contrast Mode
    if (appearance.contrast === 'high-contrast') {
      root.classList.add('high-contrast');
      root.setAttribute('data-contrast', 'high-contrast');
    } else {
      root.classList.remove('high-contrast');
      root.setAttribute('data-contrast', 'standard');
    }

    // 4. Reduce Motion
    if (appearance.reduceMotion) {
      root.classList.add('reduce-motion');
      root.setAttribute('data-motion', 'reduced');
    } else {
      root.classList.remove('reduce-motion');
      root.setAttribute('data-motion', 'normal');
    }

    // 5. Enhanced Focus Visibility
    if (appearance.enhancedFocus) {
      root.classList.add('enhanced-focus');
      root.setAttribute('data-focus', 'enhanced');
    } else {
      root.classList.remove('enhanced-focus');
      root.setAttribute('data-focus', 'standard');
    }
  }

  // =========================================================================
  // Value Formatters & Previews
  // =========================================================================

  public formatBytes(bytes: number, standard?: DataUnitStandard): string {
    const std = standard || this.generalSettings().dataUnitStandard;
    const isBinary = std === 'BINARY_IEC';
    const thresh = isBinary ? 1024 : 1000;

    if (Math.abs(bytes) < thresh) {
      return bytes + ' B';
    }

    const units = isBinary
      ? ['KiB', 'MiB', 'GiB', 'TiB', 'PiB']
      : ['KB', 'MB', 'GB', 'TB', 'PB'];
    let u = -1;
    const r = 10;

    do {
      bytes /= thresh;
      ++u;
    } while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);

    const formattedNum = this.formatNumber(parseFloat(bytes.toFixed(2)));
    return `${formattedNum} ${units[u]}`;
  }

  public formatNumber(value: number, separator?: NumberGroupingSeparator): string {
    const sep = separator || this.generalSettings().numberGroupingSeparator;
    const parts = value.toString().split('.');
    const integerPart = parts[0];
    const decimalPart = parts.length > 1 ? parts[1] : null;

    let sepChar = ',';
    let decChar = '.';
    if (sep === 'PERIOD') {
      sepChar = '.';
      decChar = ',';
    } else if (sep === 'SPACE') {
      sepChar = ' ';
      decChar = '.';
    }

    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, sepChar);
    return decimalPart !== null ? `${formattedInteger}${decChar}${decimalPart}` : formattedInteger;
  }

  public getDetectedLocalTimezone(): string {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local System';
    } catch {
      return 'Local System';
    }
  }

  public formatDatePreview(date: Date = new Date()): string {
    const gen = this.generalSettings();
    const pad = (n: number) => (n < 10 ? '0' + n : '' + n);

    let year = date.getFullYear();
    let month = pad(date.getMonth() + 1);
    let day = pad(date.getDate());
    let hours = date.getHours();
    let minutes = pad(date.getMinutes());
    let seconds = pad(date.getSeconds());

    let dateStr = '';
    if (gen.dateFormat === 'YYYY-MM-DD') {
      dateStr = `${year}-${month}-${day}`;
    } else if (gen.dateFormat === 'MM/DD/YYYY') {
      dateStr = `${month}/${day}/${year}`;
    } else {
      dateStr = `${day}/${month}/${year}`;
    }

    let timeStr = '';
    if (gen.timeFormat === '24h') {
      timeStr = `${pad(hours)}:${minutes}:${seconds}`;
    } else {
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12;
      timeStr = `${pad(hours)}:${minutes}:${seconds} ${ampm}`;
    }

    const tzLabel = gen.timezonePreference === 'UTC' ? 'UTC' : gen.timezonePreference === 'LOCAL' ? 'Local' : gen.timezonePreference;
    return `${dateStr} ${timeStr} (${tzLabel})`;
  }

  // =========================================================================
  // Private Helpers & Storage
  // =========================================================================

  private loadAppearanceSettings(): AppearanceSettings {
    if (typeof window === 'undefined') return { ...DEFAULT_APPEARANCE_SETTINGS };
    try {
      const raw = localStorage.getItem(STORAGE_KEY_APPEARANCE);
      if (raw) {
        const parsed = JSON.parse(raw);
        return {
          theme: parsed.theme || DEFAULT_APPEARANCE_SETTINGS.theme,
          palette: parsed.palette || DEFAULT_APPEARANCE_SETTINGS.palette,
          contrast: parsed.contrast || DEFAULT_APPEARANCE_SETTINGS.contrast,
          reduceMotion: !!parsed.reduceMotion,
          enhancedFocus: !!parsed.enhancedFocus
        };
      }
    } catch {
      // Ignore storage read error and return defaults
    }
    return { ...DEFAULT_APPEARANCE_SETTINGS };
  }

  private saveAppearanceSettings(settings: AppearanceSettings): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_KEY_APPEARANCE, JSON.stringify(settings));
    } catch {
      // Ignore storage write error
    }
  }

  private loadGeneralSettings(): GeneralSettings {
    if (typeof window === 'undefined') return { ...DEFAULT_GENERAL_SETTINGS };
    try {
      const raw = localStorage.getItem(STORAGE_KEY_GENERAL);
      if (raw) {
        const parsed = JSON.parse(raw);
        return {
          defaultLandingSurface: parsed.defaultLandingSurface || DEFAULT_GENERAL_SETTINGS.defaultLandingSurface,
          timezonePreference: parsed.timezonePreference || DEFAULT_GENERAL_SETTINGS.timezonePreference,
          dateFormat: parsed.dateFormat || DEFAULT_GENERAL_SETTINGS.dateFormat,
          timeFormat: parsed.timeFormat || DEFAULT_GENERAL_SETTINGS.timeFormat,
          dataUnitStandard: parsed.dataUnitStandard || DEFAULT_GENERAL_SETTINGS.dataUnitStandard,
          numberGroupingSeparator: parsed.numberGroupingSeparator || DEFAULT_GENERAL_SETTINGS.numberGroupingSeparator,
          defaultOrgId: parsed.defaultOrgId || DEFAULT_GENERAL_SETTINGS.defaultOrgId,
          defaultWorkspaceId: parsed.defaultWorkspaceId || DEFAULT_GENERAL_SETTINGS.defaultWorkspaceId,
          defaultEnvironmentId: parsed.defaultEnvironmentId || DEFAULT_GENERAL_SETTINGS.defaultEnvironmentId,
          confirmDestructiveActions: true,
          warnUnsavedChanges: parsed.warnUnsavedChanges !== undefined ? !!parsed.warnUnsavedChanges : DEFAULT_GENERAL_SETTINGS.warnUnsavedChanges,
          enableLocalCrashTelemetry: parsed.enableLocalCrashTelemetry !== undefined ? !!parsed.enableLocalCrashTelemetry : DEFAULT_GENERAL_SETTINGS.enableLocalCrashTelemetry
        };
      }
    } catch {
      // Ignore storage read error and return defaults
    }
    return { ...DEFAULT_GENERAL_SETTINGS };
  }

  private saveGeneralSettings(settings: GeneralSettings): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_KEY_GENERAL, JSON.stringify(settings));
    } catch {
      // Ignore storage write error
    }
  }

  private detectSystemDarkPreference(): boolean {
    if (typeof window === 'undefined') return false;
    return !!window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  }

  private initSystemThemeListener(): void {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (e: MediaQueryListEvent) => {
      this.systemPrefersDark.set(e.matches);
      if (this.appearanceSettings().theme === 'system') {
        this.applyAppearanceToDOM();
      }
    };
    if (media.addEventListener) {
      media.addEventListener('change', listener);
    } else if ((media as any).addListener) {
      (media as any).addListener(listener);
    }
  }
}
