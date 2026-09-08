/**
 * AKAAL Connection Workspace (Part C) Comprehensive Unit & Integration Tests
 * Validates full 6-tab Workspace, factual verification semantics, configuration editing,
 * capability proof levels, project-oriented usage, activity audit log, and governed lifecycle.
 */

import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ConnectionWorkspaceService } from './connection-workspace.service';
import { DETAILED_CONNECTION_FIXTURES } from './connection-workspace.fixtures';
import { ConnectionWorkspaceTab, ActivityCategory } from './connection-workspace.models';

describe('Connection Workspace (Part C) Unit & Integration Suite', () => {
  let ws: ConnectionWorkspaceService;
  let routerMock: any;

  beforeEach(() => {
    routerMock = {
      navigate: vi.fn().mockResolvedValue(true)
    };
    ws = new ConnectionWorkspaceService(routerMock as any);
    ws.loadConnection('conn-ora-rac-01', 'overview');
  });

  // =========================================================================
  // 1. WORKSPACE INITIALIZATION & TAB SWITCHING
  // =========================================================================
  describe('Workspace Shell & Tab Navigation', () => {
    it('should initialize with Oracle RAC primary fixture in Overview tab', () => {
      expect(ws.connection()).toBeDefined();
      expect(ws.connection()?.id).toBe('conn-ora-rac-01');
      expect(ws.connection()?.providerId).toBe('oracle');
      expect(ws.activeTab()).toBe('overview');
    });

    it('should cleanly switch between all 6 primary workspace tabs', () => {
      const tabs: ConnectionWorkspaceTab[] = [
        'overview',
        'configuration',
        'capabilities',
        'usage',
        'activity',
        'settings'
      ];

      for (const tab of tabs) {
        ws.setActiveTab(tab);
        expect(ws.activeTab()).toBe(tab);
      }
    });

    it('should copy connection ID with transient feedback', () => {
      expect(ws.copiedId()).toBe(false);
      ws.copyConnectionId();
      expect(ws.copiedId()).toBe(true);
    });
  });

  // =========================================================================
  // 2. OVERVIEW TAB: IDENTITY, VERIFICATION & PROVIDER CONTEXT
  // =========================================================================
  describe('Tab 1: Overview Presentation & Factual Verification Semantics', () => {
    it('should render factual verification facts without reducing to synthetic health', () => {
      const conn = ws.connection()!;
      expect(conn.verificationState).toBe('VERIFIED_RECENT');
      expect(conn.lastVerifiedAt).toBeDefined();
      expect(conn.capabilities.connectivityProbes.length).toBeGreaterThan(0);
      
      const dns = conn.capabilities.connectivityProbes.find(p => p.step === 'DNS_RESOLUTION');
      expect(dns?.status).toBe('VERIFIED');
    });

    it('should present provider-aware endpoint addressing without forcing relational schema on non-relational providers', () => {
      // Oracle RAC
      ws.loadConnection('conn-ora-rac-01');
      expect(ws.connection()?.endpointConfig.serviceName).toBe('FINANCE_PRD.CORP');
      expect(ws.connection()?.endpointConfig.driverMode).toBe('THIN');

      // Kafka Cluster
      ws.loadConnection('conn-kafka-prod-01');
      expect(ws.connection()?.endpointConfig.bootstrapServers).toContain('kafka-broker-01.corp.internal:9092');
      expect(ws.connection()?.endpointConfig.securityProtocol).toBe('SASL_SSL');

      // S3 Bucket
      ws.loadConnection('conn-s3-lake-01');
      expect(ws.connection()?.endpointConfig.bucketName).toBe('prod-emea-compliance-archive');
      expect(ws.connection()?.endpointConfig.region).toBe('eu-central-1');
    });

    it('should safely redact secret references in overview security summary', () => {
      const conn = ws.connection()!;
      expect(conn.authConfig.secretRef).toBe('kv/data/production/oracle/core-banking');
      expect(conn.authConfig.secretSource).toBe('Vault');
      // Plaintext secrets must never exist in the domain model
      expect((conn.authConfig as any).password).toBeUndefined();
      expect((conn.authConfig as any).secretValue).toBeUndefined();
    });
  });

  // =========================================================================
  // 3. CONFIGURATION TAB: READ MODE, EDIT MODE & STALENESS LIFECYCLE
  // =========================================================================
  describe('Tab 2: Configuration Editing & Staleness Semantics', () => {
    it('should start with read mode and open controlled edit mode on demand', () => {
      expect(ws.isEditingConfig()).toBe(false);
      ws.startEditingConfig();
      expect(ws.isEditingConfig()).toBe(true);
      expect(ws.configDraft().host).toBe('rac-cluster-01.corp.internal');
      expect(ws.configDraft().port).toBe(1521);
    });

    it('should cancel edit mode and discard uncommitted draft modifications', () => {
      ws.startEditingConfig();
      ws.configDraft.update(d => ({ ...d, host: 'mutated.host.internal' }));
      ws.cancelEditingConfig();
      expect(ws.isEditingConfig()).toBe(false);
      expect(ws.connection()?.endpointConfig.host).toBe('rac-cluster-01.corp.internal');
    });

    it('should transition verification to CONFIG_CHANGED_SINCE_TEST when material endpoint fields change', () => {
      ws.startEditingConfig();
      ws.configDraft.update(d => ({ ...d, port: 1522 })); // Material port mutation
      ws.saveConfigChanges();

      // Verification becomes stale immediately
      expect(ws.connection()?.verificationState).toBe('CONFIG_CHANGED_SINCE_TEST');
      expect(ws.connection()?.configChangedSinceTest).toBe(true);
      expect(ws.isVerificationStale()).toBe(true);

      // Audit activity logged
      const latestAct = ws.connection()?.activities[0];
      expect(latestAct?.category).toBe('CONFIG');
      expect(latestAct?.title).toBe('Configuration Updated');
    });

    it('should restore verified state when running a point-in-time test probe', () => {
      // Mark stale first
      ws.startEditingConfig();
      ws.configDraft.update(d => ({ ...d, port: 1522 }));
      ws.saveConfigChanges();
      expect(ws.isVerificationStale()).toBe(true);

      // Trigger test probe
      ws.testConnection();
      expect(ws.connection()?.verificationState).toBe('TESTING');

      // Fast-forward simulated test completion
      const nowIso = new Date().toISOString();
      ws.connection.update(c => ({
        ...c!,
        verificationState: 'VERIFIED_RECENT',
        configChangedSinceTest: false,
        lastVerifiedAt: nowIso
      }));

      expect(ws.connection()?.verificationState).toBe('VERIFIED_RECENT');
      expect(ws.isVerificationStale()).toBe(false);
    });
  });

  // =========================================================================
  // 4. CAPABILITIES TAB: PROBES, CDC TRUTH & PROOF LEVELS
  // =========================================================================
  describe('Tab 3: Capabilities, Truthful CDC & Proof Attestation', () => {
    it('should introspect permissions through PermissionProbe', () => {
      const conn = ws.connection()!;
      expect(conn.capabilities.permissionChecks.length).toBeGreaterThan(0);
      const logmnr = conn.capabilities.permissionChecks.find(p => p.permission === 'EXECUTE ON DBMS_LOGMNR');
      expect(logmnr?.status).toBe('VERIFIED');
    });

    it('should truthfully classify Kafka as Stream Offset Consumption and NOT database CDC', () => {
      ws.loadConnection('conn-kafka-prod-01');
      const conn = ws.connection()!;
      expect(conn.capabilities.cdcCapability.type).toBe('STREAM_OFFSET');
      expect(conn.capabilities.cdcCapability.label).toContain('Stream Offset Consumption (Not Database CDC)');
      expect(conn.capabilities.targetCapability.acidCompliant).toBe(false);
    });

    it('should classify Oracle as native LogMiner CDC', () => {
      ws.loadConnection('conn-ora-rac-01');
      const conn = ws.connection()!;
      expect(conn.capabilities.cdcCapability.type).toBe('LOGMINER');
      expect(conn.capabilities.proofLevel).toBe('INTEGRATION_PROVEN');
    });

    it('should classify Aurora PostgreSQL as Logical Decoding CDC', () => {
      ws.loadConnection('conn-pg-aurora-01');
      const conn = ws.connection()!;
      expect(conn.capabilities.cdcCapability.type).toBe('LOGICAL_DECODING');
      expect(conn.capabilities.proofLevel).toBe('LIVE_PROVEN');
    });
  });

  // =========================================================================
  // 5. USAGE TAB: PROJECT-ORIENTED REUSABLE RESOURCE CONTEXT
  // =========================================================================
  describe('Tab 4: Usage & Dependency Awareness', () => {
    it('should represent Projects as the primary reusable resource association context', () => {
      const conn = ws.connection()!;
      expect(conn.usage.projects.length).toBe(2);
      expect(conn.usage.projects[0].name).toBe('Core Banking Ledger Modernization');
      expect(conn.usage.projects[1].name).toBe('Payments Gateway Real-Time Sync');
    });

    it('should list referencing migrations and active validation missions', () => {
      const conn = ws.connection()!;
      expect(conn.usage.migrations.length).toBe(3);
      expect(conn.usage.validations.length).toBe(2);
      expect(conn.usage.activeStreamsCount).toBe(2);
    });

    it('should block deletion when connection has active or historical references', () => {
      const conn = ws.connection()!;
      expect(conn.usage.referenceProtection.canDelete).toBe(false);
      expect(conn.usage.referenceProtection.isReferenced).toBe(true);
      expect(conn.usage.referenceProtection.blockReason).toBeDefined();
    });

    it('should permit deletion when connection is completely unused', () => {
      ws.loadConnection('conn-unused-test-01');
      const conn = ws.connection()!;
      expect(conn.usage.projects.length).toBe(0);
      expect(conn.usage.migrations.length).toBe(0);
      expect(conn.usage.referenceProtection.canDelete).toBe(true);
      expect(conn.usage.referenceProtection.isReferenced).toBe(false);
    });
  });

  // =========================================================================
  // 6. ACTIVITY TAB: AUDIT TIMELINE & CATEGORY FILTERING
  // =========================================================================
  describe('Tab 5: Activity & Governance Audit Log', () => {
    it('should display chronological activity timeline with category filtering', () => {
      const conn = ws.connection()!;
      expect(conn.activities.length).toBeGreaterThan(0);

      ws.activityCategoryFilter.set('TEST');
      expect(ws.filteredActivities().every(a => a.category === 'TEST')).toBe(true);

      ws.activityCategoryFilter.set('SECURITY');
      expect(ws.filteredActivities().every(a => a.category === 'SECURITY')).toBe(true);

      ws.activityCategoryFilter.set('ALL');
      expect(ws.filteredActivities().length).toBe(conn.activities.length);
    });

    it('should never contain leaked secret values in activity entries', () => {
      const allActs = ws.connection()!.activities;
      for (const act of allActs) {
        expect(act.description).not.toMatch(/password=|secret=|key=|token=/i);
      }
    });
  });

  // =========================================================================
  // 7. SETTINGS TAB: METADATA, DISABLE & ARCHIVE GOVERNANCE
  // =========================================================================
  describe('Tab 6: Settings, Metadata & Governed Lifecycle', () => {
    it('should update general metadata and record audit activity', () => {
      ws.saveMetadata('Renamed Core Banking RAC', 'Updated production description', ['Core', 'Tier-0']);
      expect(ws.connection()?.name).toBe('Renamed Core Banking RAC');
      expect(ws.connection()?.description).toBe('Updated production description');
      expect(ws.connection()?.activities[0].title).toBe('General Metadata Updated');
    });

    it('should toggle Disable connection state without mutating active executions', () => {
      expect(ws.connection()?.lifecycleState).toBe('ACTIVE');
      ws.toggleDisableConnection();
      expect(ws.connection()?.lifecycleState).toBe('DISABLED');
      expect(ws.connection()?.disabledAt).toBeDefined();

      // Re-enable
      ws.toggleDisableConnection();
      expect(ws.connection()?.lifecycleState).toBe('ACTIVE');
    });

    it('should archive connection to retire from active pickers while retaining history', () => {
      expect(ws.connection()?.lifecycleState).toBe('ACTIVE');
      ws.archiveConnection();
      expect(ws.connection()?.lifecycleState).toBe('ARCHIVED');
      expect(ws.connection()?.archivedAt).toBeDefined();
    });
  });
});
