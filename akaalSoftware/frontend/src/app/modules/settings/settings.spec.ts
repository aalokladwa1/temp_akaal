import '@angular/compiler';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  SettingsService,
  DEFAULT_APPEARANCE_SETTINGS,
  DEFAULT_GENERAL_SETTINGS,
  DEFAULT_NOTIFICATION_SETTINGS,
  DEFAULT_INTEGRATION_SETTINGS,
  DEFAULT_AI_INTELLIGENCE_SETTINGS,
  DEFAULT_LOGGING_DIAGNOSTICS_SETTINGS,
  DEFAULT_ADVANCED_SETTINGS
} from './services/settings.service';
import { SETTINGS_NAV_SECTIONS } from './settings-shell.component';
import { ContextService } from '../../core/services/context.service';

// Mock storage & DOM for Node environment in vitest
class MockLocalStorage {
  private store: Record<string, string> = {};

  getItem(key: string): string | null {
    return this.store[key] !== undefined ? this.store[key] : null;
  }

  setItem(key: string, value: string): void {
    this.store[key] = value;
  }

  removeItem(key: string): void {
    delete this.store[key];
  }

  clear(): void {
    this.store = {};
  }
}

class MockDOMElement {
  public classSet = new Set<string>();
  public attributes: Record<string, string> = {};

  public classList = {
    add: (cls: string) => { this.classSet.add(cls); },
    remove: (cls: string) => { this.classSet.delete(cls); },
    contains: (cls: string) => this.classSet.has(cls)
  };

  public setAttribute(key: string, val: string): void {
    this.attributes[key] = val;
  }

  public getAttribute(key: string): string | null {
    return this.attributes[key] !== undefined ? this.attributes[key] : null;
  }

  public removeAttribute(key: string): void {
    delete this.attributes[key];
  }

  public reset(): void {
    this.classSet.clear();
    this.attributes = {};
  }
}

describe('AKAAL Settings — Master Test Suite', () => {
  let service: SettingsService;
  let mockStorage: MockLocalStorage;
  let mockElement: MockDOMElement;

  beforeEach(() => {
    mockStorage = new MockLocalStorage();
    mockElement = new MockDOMElement();

    (globalThis as any).localStorage = mockStorage;
    (globalThis as any).window = {
      matchMedia: () => ({ matches: false, addEventListener: () => {} })
    };
    (globalThis as any).document = {
      documentElement: mockElement
    };

    service = new SettingsService();
  });

  afterEach(() => {
    mockStorage.clear();
    mockElement.reset();
  });

  describe('1. Default Settings & Initialization', () => {
    it('should initialize appearance settings with enterprise defaults', () => {
      const app = service.appearanceSettings();
      expect(app.theme).toBe('enterprise-blue');
      expect(app.palette).toBe('standard');
      expect(app.contrast).toBe('standard');
      expect(app.reduceMotion).toBe(false);
      expect(app.enhancedFocus).toBe(false);
    });

    it('should initialize general settings with enterprise defaults', () => {
      const gen = service.generalSettings();
      expect(gen.defaultLandingSurface).toBe('dashboard');
      expect(gen.timezonePreference).toBe('LOCAL');
      expect(gen.dateFormat).toBe('YYYY-MM-DD');
      expect(gen.timeFormat).toBe('24h');
      expect(gen.dataUnitStandard).toBe('BINARY_IEC');
      expect(gen.numberGroupingSeparator).toBe('COMMA');
      expect(gen.confirmDestructiveActions).toBe(true);
      expect(gen.warnUnsavedChanges).toBe(true);
      expect(gen.enableLocalCrashTelemetry).toBe(true);
    });

    it('should apply initial DOM classes and attributes correctly', () => {
      service.applyAppearanceToDOM();
      expect(mockElement.classList.contains('dark')).toBe(false);
      expect(mockElement.getAttribute('data-theme')).toBe('enterprise-blue');
      expect(mockElement.getAttribute('data-palette')).toBe('standard');
      expect(mockElement.getAttribute('data-contrast')).toBe('standard');
      expect(mockElement.getAttribute('data-motion')).toBe('normal');
      expect(mockElement.getAttribute('data-focus')).toBe('standard');
    });
  });

  describe('2. Appearance Preferences & Composable DOM Layers', () => {
    it('should update theme to dark and synchronize DOM and localStorage', () => {
      service.updateAppearance({ theme: 'dark' });

      expect(service.appearanceSettings().theme).toBe('dark');
      expect(service.effectiveTheme()).toBe('dark');
      expect(mockElement.classList.contains('dark')).toBe(true);
      expect(mockElement.getAttribute('data-theme')).toBe('dark');

      const stored = JSON.parse(mockStorage.getItem('akaal_settings_appearance') || '{}');
      expect(stored.theme).toBe('dark');
    });

    it('should update palette to color-vision-safe and synchronize DOM and localStorage', () => {
      service.updateAppearance({ palette: 'color-vision-safe' });

      expect(service.appearanceSettings().palette).toBe('color-vision-safe');
      expect(mockElement.classList.contains('color-vision-safe')).toBe(true);
      expect(mockElement.getAttribute('data-palette')).toBe('color-vision-safe');

      const stored = JSON.parse(mockStorage.getItem('akaal_settings_appearance') || '{}');
      expect(stored.palette).toBe('color-vision-safe');
    });

    it('should update contrast to high-contrast and synchronize DOM and localStorage', () => {
      service.updateAppearance({ contrast: 'high-contrast' });

      expect(service.appearanceSettings().contrast).toBe('high-contrast');
      expect(mockElement.classList.contains('high-contrast')).toBe(true);
      expect(mockElement.getAttribute('data-contrast')).toBe('high-contrast');

      const stored = JSON.parse(mockStorage.getItem('akaal_settings_appearance') || '{}');
      expect(stored.contrast).toBe('high-contrast');
    });

    it('should toggle reduceMotion and synchronize DOM', () => {
      service.updateAppearance({ reduceMotion: true });

      expect(service.appearanceSettings().reduceMotion).toBe(true);
      expect(mockElement.classList.contains('reduce-motion')).toBe(true);
      expect(mockElement.getAttribute('data-motion')).toBe('reduced');

      service.updateAppearance({ reduceMotion: false });
      expect(service.appearanceSettings().reduceMotion).toBe(false);
      expect(mockElement.classList.contains('reduce-motion')).toBe(false);
      expect(mockElement.getAttribute('data-motion')).toBe('normal');
    });

    it('should toggle enhancedFocus and synchronize DOM', () => {
      service.updateAppearance({ enhancedFocus: true });

      expect(service.appearanceSettings().enhancedFocus).toBe(true);
      expect(mockElement.classList.contains('enhanced-focus')).toBe(true);
      expect(mockElement.getAttribute('data-focus')).toBe('enhanced');

      service.updateAppearance({ enhancedFocus: false });
      expect(service.appearanceSettings().enhancedFocus).toBe(false);
      expect(mockElement.classList.contains('enhanced-focus')).toBe(false);
      expect(mockElement.getAttribute('data-focus')).toBe('standard');
    });

    it('should support orthogonal composition of multiple appearance layers simultaneously', () => {
      service.updateAppearance({
        theme: 'dark',
        palette: 'color-vision-safe',
        contrast: 'high-contrast',
        reduceMotion: true,
        enhancedFocus: true
      });

      expect(mockElement.classList.contains('dark')).toBe(true);
      expect(mockElement.classList.contains('color-vision-safe')).toBe(true);
      expect(mockElement.classList.contains('high-contrast')).toBe(true);
      expect(mockElement.classList.contains('reduce-motion')).toBe(true);
      expect(mockElement.classList.contains('enhanced-focus')).toBe(true);
    });

    it('should reset appearance settings to default values', () => {
      service.updateAppearance({
        theme: 'dark',
        contrast: 'high-contrast',
        reduceMotion: true
      });

      service.resetAppearance();

      expect(service.appearanceSettings()).toEqual(DEFAULT_APPEARANCE_SETTINGS);
      expect(mockElement.classList.contains('dark')).toBe(false);
      expect(mockElement.classList.contains('high-contrast')).toBe(false);
    });
  });

  describe('3. General Preferences & Safety Enforcement', () => {
    it('should update default landing surface and persist in localStorage', () => {
      service.updateGeneral({ defaultLandingSurface: 'migration' });

      expect(service.generalSettings().defaultLandingSurface).toBe('migration');
      const stored = JSON.parse(mockStorage.getItem('akaal_settings_general') || '{}');
      expect(stored.defaultLandingSurface).toBe('migration');
    });

    it('should strictly preserve destructive actions confirmation as locked true', () => {
      service.updateGeneral({ confirmDestructiveActions: false as any });

      expect(service.generalSettings().confirmDestructiveActions).toBe(true);
    });

    it('should update temporal formats and grouping preferences', () => {
      service.updateGeneral({
        timezonePreference: 'UTC',
        dateFormat: 'DD/MM/YYYY',
        timeFormat: '12h',
        dataUnitStandard: 'DECIMAL_SI',
        numberGroupingSeparator: 'PERIOD'
      });

      const gen = service.generalSettings();
      expect(gen.timezonePreference).toBe('UTC');
      expect(gen.dateFormat).toBe('DD/MM/YYYY');
      expect(gen.timeFormat).toBe('12h');
      expect(gen.dataUnitStandard).toBe('DECIMAL_SI');
      expect(gen.numberGroupingSeparator).toBe('PERIOD');
    });

    it('should reset general settings to enterprise defaults', () => {
      service.updateGeneral({
        defaultLandingSurface: 'reports',
        timezonePreference: 'UTC',
        warnUnsavedChanges: false
      });

      service.resetGeneral();

      expect(service.generalSettings()).toEqual(DEFAULT_GENERAL_SETTINGS);
    });
  });

  describe('4. Value Formatters & Previews', () => {
    it('should format bytes correctly under BINARY_IEC (1024 base)', () => {
      expect(service.formatBytes(1024, 'BINARY_IEC')).toBe('1 KiB');
      expect(service.formatBytes(1048576, 'BINARY_IEC')).toBe('1 MiB');
      expect(service.formatBytes(1073741824, 'BINARY_IEC')).toBe('1 GiB');
    });

    it('should format bytes correctly under DECIMAL_SI (1000 base)', () => {
      expect(service.formatBytes(1000, 'DECIMAL_SI')).toBe('1 KB');
      expect(service.formatBytes(1000000, 'DECIMAL_SI')).toBe('1 MB');
      expect(service.formatBytes(1000000000, 'DECIMAL_SI')).toBe('1 GB');
    });

    it('should format numbers with comma separator', () => {
      expect(service.formatNumber(1234567, 'COMMA')).toBe('1,234,567');
      expect(service.formatNumber(1234.56, 'COMMA')).toBe('1,234.56');
    });

    it('should format numbers with period separator', () => {
      expect(service.formatNumber(1234567, 'PERIOD')).toBe('1.234.567');
      expect(service.formatNumber(1234.56, 'PERIOD')).toBe('1.234,56');
    });

    it('should format numbers with space separator', () => {
      expect(service.formatNumber(1234567, 'SPACE')).toBe('1 234 567');
    });

    it('should generate formatted date preview string', () => {
      service.updateGeneral({
        dateFormat: 'YYYY-MM-DD',
        timeFormat: '24h',
        timezonePreference: 'UTC'
      });

      const fixedDate = new Date(2026, 8, 11, 14, 30, 0);
      const preview = service.formatDatePreview(fixedDate);

      expect(preview).toContain('2026-09-11');
      expect(preview).toContain('14:30:00');
      expect(preview).toContain('(UTC)');
    });
  });

  describe('5. Settings Navigation Structure & Category Status', () => {
    it('should define exactly 3 navigation sections with all 10 structural categories as ACTIVE', () => {
      expect(SETTINGS_NAV_SECTIONS.length).toBe(3);

      const allCategories = SETTINGS_NAV_SECTIONS.flatMap(s => s.categories);
      expect(allCategories.length).toBe(10);

      // Verify all 10 categories across Parts 1-4 are ACTIVE
      const allCategoryIds = [
        'general',
        'appearance',
        'runtime-migration',
        'connectors',
        'storage',
        'notifications',
        'integrations',
        'ai-intelligence',
        'logging',
        'advanced'
      ];
      for (const id of allCategoryIds) {
        const cat = allCategories.find(c => c.id === id);
        expect(cat).toBeDefined();
        expect(cat?.status).toBe('ACTIVE');
        expect(cat?.path).toMatch(/^\/settings\//);
      }

      // Verify 0 future/planned categories remain
      const futureCategories = allCategories.filter(c => c.status === 'FUTURE');
      expect(futureCategories.length).toBe(0);
    });
  });

  describe('6. Runtime & Migration Defaults', () => {
    it('should initialize with canonical pipeline and engine defaults', () => {
      const rt = service.runtimeMigrationSettings();
      expect(rt.executionProfile).toBe('BALANCED');
      expect(rt.defaultStartingWorkers).toBe(16);
      expect(rt.minConcurrencyFloor).toBe(4);
      expect(rt.preferredMaxWorkers).toBe(32);
      expect(rt.governedMaxWorkerLimit).toBe(64);
      expect(rt.defaultBatchSize).toBe(10000);
      expect(rt.cdcBufferMemoryMb).toBe(64);
      expect(rt.pollingIntervalSeconds).toBe(10);
      expect(rt.conflictResolutionPreference).toBe('SOURCE_WINS');
      expect(rt.validationAssuranceLevel).toBe('LEVEL_2_CHECKSUM');
      expect(rt.recoveryStrategy).toBe('RESUME_CHECKPOINT');
      expect(rt.fencingEpochRollbackBarrier).toBe(true);
    });

    it('should update configurable runtime settings while locking governed invariants', () => {
      service.updateRuntimeMigration({
        defaultStartingWorkers: 24,
        defaultBatchSize: 15000,
        fencingEpochRollbackBarrier: false as any,
        governedMaxWorkerLimit: 128 as any
      });

      const rt = service.runtimeMigrationSettings();
      expect(rt.defaultStartingWorkers).toBe(24);
      expect(rt.defaultBatchSize).toBe(15000);
      expect(rt.fencingEpochRollbackBarrier).toBe(true);
      expect(rt.governedMaxWorkerLimit).toBe(64);
    });

    it('should reset runtime migration defaults correctly', () => {
      service.updateRuntimeMigration({ defaultStartingWorkers: 8 });
      expect(service.runtimeMigrationSettings().defaultStartingWorkers).toBe(8);

      service.resetRuntimeMigration();
      expect(service.runtimeMigrationSettings().defaultStartingWorkers).toBe(16);
    });
  });

  describe('7. Connector Defaults', () => {
    it('should initialize with canonical RouteSpec and SessionRequest defaults', () => {
      const conn = service.connectorSettings();
      expect(conn.connectTimeoutMs).toBe(15000);
      expect(conn.socketTimeoutMs).toBe(30000);
      expect(conn.dnsTimeoutMs).toBe(5000);
      expect(conn.statementTimeoutMs).toBe(60000);
      expect(conn.lockTimeoutMs).toBe(10000);
      expect(conn.keepaliveEnabled).toBe(true);
      expect(conn.defaultFetchSize).toBe(2000);
      expect(conn.paginationStrategy).toBe('KEYSET_CURSOR');
      expect(conn.tlsMinVersion).toBe('TLSv1.2');
      expect(conn.tlsMode).toBe('VERIFY_FULL');
      expect(conn.allowPermissiveSelfSigned).toBe(false);
      expect(conn.credentialProtocol).toBe('vault://');
    });

    it('should update configurable connector settings while locking security baselines', () => {
      service.updateConnector({
        connectTimeoutMs: 20000,
        defaultFetchSize: 5000,
        allowPermissiveSelfSigned: true as any,
        credentialProtocol: 'plaintext://' as any
      });

      const conn = service.connectorSettings();
      expect(conn.connectTimeoutMs).toBe(20000);
      expect(conn.defaultFetchSize).toBe(5000);
      expect(conn.allowPermissiveSelfSigned).toBe(false);
      expect(conn.credentialProtocol).toBe('vault://');
    });

    it('should reset connector defaults correctly', () => {
      service.updateConnector({ connectTimeoutMs: 25000 });
      expect(service.connectorSettings().connectTimeoutMs).toBe(25000);

      service.resetConnector();
      expect(service.connectorSettings().connectTimeoutMs).toBe(15000);
    });
  });

  describe('8. Storage & Retention Defaults', () => {
    it('should initialize with canonical durability and audit defaults', () => {
      const stor = service.storageRetentionSettings();
      expect(stor.checkpointIntervalRows).toBe(1000);
      expect(stor.checkpointIntervalSeconds).toBe(30);
      expect(stor.retainedCheckpointsCount).toBe(10);
      expect(stor.mandatoryDurabilityEnforced).toBe(true);
      expect(stor.cdcStreamBufferMb).toBe(64);
      expect(stor.governedSpillBudgetGb).toBe(100);
      expect(stor.defaultReportRetentionDays).toBe(90);
      expect(stor.sha256CryptographicAttestation).toBe(true);
      expect(stor.diagnosticLogBudgetGb).toBe(10);
      expect(stor.defaultJobHistoryRetentionDays).toBe(30);
      expect(stor.enterpriseMinRetentionDays).toBe(30);
      expect(stor.activeLegalHoldProtected).toBe(true);
    });

    it('should update configurable storage settings while locking durability and legal hold invariants', () => {
      service.updateStorageRetention({
        checkpointIntervalRows: 2000,
        defaultReportRetentionDays: 120,
        mandatoryDurabilityEnforced: false as any,
        sha256CryptographicAttestation: false as any
      });

      const stor = service.storageRetentionSettings();
      expect(stor.checkpointIntervalRows).toBe(2000);
      expect(stor.defaultReportRetentionDays).toBe(120);
      expect(stor.mandatoryDurabilityEnforced).toBe(true);
      expect(stor.sha256CryptographicAttestation).toBe(true);
    });

    it('should reset storage retention defaults correctly', () => {
      service.updateStorageRetention({ checkpointIntervalRows: 500 });
      expect(service.storageRetentionSettings().checkpointIntervalRows).toBe(500);

      service.resetStorageRetention();
      expect(service.storageRetentionSettings().checkpointIntervalRows).toBe(1000);
    });
  });

  describe('9. Notifications Defaults (Part 3)', () => {
    it('should initialize with canonical notification preferences', () => {
      const notif = service.notificationSettings();
      expect(notif.emailEnabled).toBe(true);
      expect(notif.emailMinSeverity).toBe('HIGH');
      expect(notif.emailDigestFrequency).toBe('IMMEDIATE');
      expect(notif.emailNotifyOnMigrationFailure).toBe(true);
      expect(notif.slackEnabled).toBe(true);
      expect(notif.slackChannelId).toBe('chan-slack-01');
      expect(notif.teamsEnabled).toBe(false);
      expect(notif.escalationEnabled).toBe(true);
      expect(notif.escalationTargetChannelId).toBe('chan-pagerduty-01');
      expect(notif.personalAckWindowMinutes).toBe(15);
      expect(notif.mandatoryCriticalEscalationLocked).toBe(true);
      expect(notif.quietHoursEnabled).toBe(true);
      expect(notif.criticalBypassQuietHours).toBe(true);
    });

    it('should update configurable notification settings while locking safety bypass invariants', () => {
      service.updateNotification({
        emailMinSeverity: 'CRITICAL',
        personalAckWindowMinutes: 30,
        mandatoryCriticalEscalationLocked: false as any,
        criticalBypassQuietHours: false as any
      });

      const notif = service.notificationSettings();
      expect(notif.emailMinSeverity).toBe('CRITICAL');
      expect(notif.personalAckWindowMinutes).toBe(30);
      // Locked invariants remain enforced
      expect(notif.mandatoryCriticalEscalationLocked).toBe(true);
      expect(notif.criticalBypassQuietHours).toBe(true);
    });

    it('should reset notification defaults correctly', () => {
      service.updateNotification({ emailMinSeverity: 'LOW', quietHoursEnabled: false });
      expect(service.notificationSettings().emailMinSeverity).toBe('LOW');

      service.resetNotifications();
      expect(service.notificationSettings().emailMinSeverity).toBe('HIGH');
      expect(service.notificationSettings().quietHoursEnabled).toBe(true);
    });
  });

  describe('10. Integrations Defaults (Part 3)', () => {
    it('should initialize with canonical observability and integration settings', () => {
      const integ = service.integrationSettings();
      expect(integ.observabilityExportEnabled).toBe(true);
      expect(integ.telemetryDestination).toBe('SPLUNK_HEC');
      expect(integ.propagateTraceContext).toBe(true);
      expect(integ.autoExportCrashDiagnostics).toBe(true);
      expect(integ.fanOutCriticalFailures).toBe(true);
      expect(integ.catalogFormat).toBe('OPEN_LINEAGE');
      expect(integ.catalogEndpointConfigured).toBe(false); // Truthful: unconfigured in workspace
    });

    it('should update configurable integration settings while preserving unconfigured catalog truth', () => {
      service.updateIntegration({
        telemetryDestination: 'DATADOG_AGENT',
        propagateTraceContext: false,
        catalogEndpointConfigured: true as any // Attempt to claim fake catalog endpoint
      });

      const integ = service.integrationSettings();
      expect(integ.telemetryDestination).toBe('DATADOG_AGENT');
      expect(integ.propagateTraceContext).toBe(false);
      // Truthful unconfigured state preserved
      expect(integ.catalogEndpointConfigured).toBe(false);
    });

    it('should reset integration defaults correctly', () => {
      service.updateIntegration({ telemetryDestination: 'LOCAL_CONSOLE' });
      expect(service.integrationSettings().telemetryDestination).toBe('LOCAL_CONSOLE');

      service.resetIntegrations();
      expect(service.integrationSettings().telemetryDestination).toBe('SPLUNK_HEC');
    });
  });

  describe('11. AI & Intelligence Defaults (Part 3)', () => {
    it('should initialize with canonical AI assistant and recommendation policies', () => {
      const ai = service.aiIntelligenceSettings();
      expect(ai.assistantEnabled).toBe(true);
      expect(ai.proactivityMode).toBe('ADVISORY');
      expect(ai.strictCredentialSanitization).toBe(true);
      expect(ai.defaultRequestTokenBudget).toBe(4000);
      expect(ai.planSynthesisAssistance).toBe(true);
      expect(ai.advisoryPlanConfirmationRequired).toBe(true);
      expect(ai.workloadAutoTuningSuggestions).toBe(true);
      expect(ai.failureRcaEnabled).toBe(true);
      expect(ai.redactSensitiveDataInTraces).toBe(true);
      expect(ai.recommendationConfidenceLevel).toBe('HIGH');
      expect(ai.mandatoryHumanReviewEnforced).toBe(true);
      expect(ai.cdcBufferSaturationPrediction).toBe(true);
      expect(ai.throughputAnomalyDetection).toBe(true);
    });

    it('should update configurable AI settings while locking governance and redaction invariants', () => {
      service.updateAiIntelligence({
        proactivityMode: 'ON_DEMAND',
        defaultRequestTokenBudget: 8000,
        recommendationConfidenceLevel: 'STANDARD',
        strictCredentialSanitization: false as any,
        advisoryPlanConfirmationRequired: false as any,
        mandatoryHumanReviewEnforced: false as any,
        redactSensitiveDataInTraces: false as any
      });

      const ai = service.aiIntelligenceSettings();
      expect(ai.proactivityMode).toBe('ON_DEMAND');
      expect(ai.defaultRequestTokenBudget).toBe(8000);
      expect(ai.recommendationConfidenceLevel).toBe('STANDARD');

      // Locked governance & safety invariants remain enforced
      expect(ai.strictCredentialSanitization).toBe(true);
      expect(ai.advisoryPlanConfirmationRequired).toBe(true);
      expect(ai.mandatoryHumanReviewEnforced).toBe(true);
      expect(ai.redactSensitiveDataInTraces).toBe(true);
    });

    it('should reset AI intelligence defaults correctly', () => {
      service.updateAiIntelligence({ proactivityMode: 'ON_DEMAND', defaultRequestTokenBudget: 1000 });
      expect(service.aiIntelligenceSettings().proactivityMode).toBe('ON_DEMAND');

      service.resetAiIntelligence();
      expect(service.aiIntelligenceSettings().proactivityMode).toBe('ADVISORY');
      expect(service.aiIntelligenceSettings().defaultRequestTokenBudget).toBe(4000);
    });
  });

  describe('12. Zero-Fake Session Persistence Guarantee', () => {
    it('should not persist Part 2, Part 3, or Part 4 operational defaults into browser localStorage', () => {
      service.updateRuntimeMigration({ defaultStartingWorkers: 20 });
      service.updateConnector({ connectTimeoutMs: 18000 });
      service.updateStorageRetention({ checkpointIntervalRows: 1500 });
      service.updateNotification({ emailMinSeverity: 'CRITICAL' });
      service.updateIntegration({ telemetryDestination: 'DATADOG_AGENT' });
      service.updateAiIntelligence({ defaultRequestTokenBudget: 2000 });
      service.updateLogging({ clientLogLevel: 'DEBUG' });
      service.updateAdvanced({ clientMemoryCacheLimitMb: 1024 });

      // Only Part 1 keys (appearance, general) exist in localStorage
      expect(mockStorage.getItem('akaal_settings_runtime')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_connectors')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_storage')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_notifications')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_integrations')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_ai_intelligence')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_logging')).toBeNull();
      expect(mockStorage.getItem('akaal_settings_advanced')).toBeNull();
    });
  });

  describe('13. Logging & Diagnostics Defaults (Part 4)', () => {
    it('should initialize with canonical log levels, diagnostics, and support bundle defaults', () => {
      const log = service.loggingSettings();
      expect(log.clientLogLevel).toBe('INFO');
      expect(log.engineLogLevel).toBe('INFO');
      expect(log.logDestination).toBe('CONSOLE_AND_DISK');
      expect(log.maxActiveLogSizeMb).toBe(50);
      expect(log.crashDiagnosticCapture).toBe(true);
      expect(log.engineStateSnapshotOnAnomaly).toBe(false);
      expect(log.traceContextPropagation).toBe(true);
      expect(log.localSpanBufferLimit).toBe(10000);
      expect(log.tracingSamplingRatePercent).toBe(100);
      expect(log.bundleIncludeSanitizedConfig).toBe(true);
      expect(log.bundleIncludeEngineStatus).toBe(true);
      expect(log.bundleIncludeScrubbedLogs).toBe(true);
      expect(log.bundleScrubSecretsAndPii).toBe(true);
    });

    it('should update configurable logging settings while locking PII and secret scrubbing', () => {
      service.updateLogging({
        clientLogLevel: 'DEBUG',
        engineLogLevel: 'DEBUG',
        maxActiveLogSizeMb: 100,
        bundleScrubSecretsAndPii: false as any // Attempt to bypass scrubbing
      });

      const log = service.loggingSettings();
      expect(log.clientLogLevel).toBe('DEBUG');
      expect(log.engineLogLevel).toBe('DEBUG');
      expect(log.maxActiveLogSizeMb).toBe(100);
      // Locked security requirement remains enforced
      expect(log.bundleScrubSecretsAndPii).toBe(true);
    });

    it('should reset logging defaults correctly', () => {
      service.updateLogging({ clientLogLevel: 'ERROR', maxActiveLogSizeMb: 250 });
      expect(service.loggingSettings().clientLogLevel).toBe('ERROR');

      service.resetLogging();
      expect(service.loggingSettings().clientLogLevel).toBe('INFO');
      expect(service.loggingSettings().maxActiveLogSizeMb).toBe(50);
    });
  });

  describe('14. Advanced Defaults (Part 4)', () => {
    it('should initialize with canonical capability controls, developer options, and safety laws', () => {
      const adv = service.advancedSettings();
      expect(adv.clientMemoryCacheLimitMb).toBe(512);
      expect(adv.parallelSchemaInspectionThreads).toBe(4);
      expect(adv.ipcResponseTimeoutSeconds).toBe(30);
      expect(adv.localDiskIoThrottleMb).toBe(0); // 0 = unlimited
      expect(adv.ipcDebugLogging).toBe(false);
      expect(adv.uiBoundingBoxInspection).toBe(false);
      expect(adv.extendedErrorStackTraces).toBe(false);
      expect(adv.sqliteWalDiagnosticJournaling).toBe(true);
      expect(adv.corruptBlockSelfCheckOnStartup).toBe(true);
      expect(adv.failClosedGovernanceEnforced).toBe(true);
    });

    it('should update configurable advanced settings while locking fail-closed governance law', () => {
      service.updateAdvanced({
        clientMemoryCacheLimitMb: 1024,
        parallelSchemaInspectionThreads: 8,
        ipcDebugLogging: true,
        failClosedGovernanceEnforced: false as any // Attempt to bypass governance
      });

      const adv = service.advancedSettings();
      expect(adv.clientMemoryCacheLimitMb).toBe(1024);
      expect(adv.parallelSchemaInspectionThreads).toBe(8);
      expect(adv.ipcDebugLogging).toBe(true);
      // Fail-closed governance law remains locked
      expect(adv.failClosedGovernanceEnforced).toBe(true);
    });

    it('should reset advanced defaults correctly', () => {
      service.updateAdvanced({ clientMemoryCacheLimitMb: 2048, parallelSchemaInspectionThreads: 16 });
      expect(service.advancedSettings().clientMemoryCacheLimitMb).toBe(2048);

      service.resetAdvanced();
      expect(service.advancedSettings().clientMemoryCacheLimitMb).toBe(512);
      expect(service.advancedSettings().parallelSchemaInspectionThreads).toBe(4);
    });
  });
});
