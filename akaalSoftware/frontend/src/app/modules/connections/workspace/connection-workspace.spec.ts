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
    ws.loadFixtureForTesting('conn-ora-rac-01', 'overview');
  });

  // =========================================================================
  // 1. WORKSPACE INITIALIZATION, NOT_FOUND & TAB SWITCHING
  // =========================================================================
  describe('Workspace Shell & Tab Navigation', () => {
    it('should initialize in NOT_CONNECTED state with null connection before loading (B-2.2-01)', () => {
      const freshWs = new ConnectionWorkspaceService(routerMock as any);
      expect(freshWs.connection()).toBeNull();
      expect(freshWs.availabilityState()).toBe('NOT_CONNECTED');
    });

    it('should transition to NOT_FOUND state when an unknown ID is requested without falling back to Oracle (B-2.2-02)', () => {
      const freshWs = new ConnectionWorkspaceService(routerMock as any);
      freshWs.loadConnection('unknown-non-existent-id');
      expect(freshWs.connection()).toBeNull();
      expect(freshWs.availabilityState()).toBe('NOT_FOUND');
    });

    it('should load fixture in Overview tab when explicitly loaded for test suite', () => {
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
      ws.loadFixtureForTesting('conn-ora-rac-01');
      expect(ws.connection()?.endpointConfig.serviceName).toBe('FINANCE_PRD.CORP');
      expect(ws.connection()?.endpointConfig.driverMode).toBe('THIN');

      // Kafka Cluster
      ws.loadFixtureForTesting('conn-kafka-prod-01');
      expect(ws.connection()?.endpointConfig.bootstrapServers).toContain('kafka-broker-01.corp.internal:9092');
      expect(ws.connection()?.endpointConfig.securityProtocol).toBe('SASL_SSL');

      // S3 Bucket
      ws.loadFixtureForTesting('conn-s3-lake-01');
      expect(ws.connection()?.endpointConfig.bucketName).toBe('prod-emea-compliance-archive');
      expect(ws.connection()?.endpointConfig.region).toBe('eu-central-1');
    });

    it('should safely redact secret references in overview security summary', () => {
      ws.loadFixtureForTesting('conn-ora-rac-01');
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
    beforeEach(() => {
      ws.loadFixtureForTesting('conn-ora-rac-01', 'configuration');
    });

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

    it('should fail closed on saveConfigChanges without mutating connection signal or activities (B-2.2-07)', async () => {
      const originalPort = ws.connection()?.endpointConfig.port;
      const originalActivitiesLength = ws.connection()?.activities.length || 0;
      ws.startEditingConfig();
      ws.configDraft.update(d => ({ ...d, port: 1522 })); // Material port mutation
      ws.saveConfigChanges();

      // Form buffer preserves edited draft
      expect(ws.configDraft().port).toBe(1522);
      // Connection signal is NOT mutated
      expect(ws.connection()?.endpointConfig.port).toBe(originalPort);
      expect(ws.connection()?.activities.length).toBe(originalActivitiesLength);

      await new Promise(r => setTimeout(r, 350));
      expect(ws.configNotice()).toBe('Configuration saving is unavailable while connection service is disconnected.');
    });

    it('should handle point-in-time test probe with truthful notice', async () => {
      ws.testConnection();
      expect(ws.isRunningTest()).toBe(true);
      await new Promise(r => setTimeout(r, 350));
      expect(ws.isRunningTest()).toBe(false);
      expect(ws.testResultMessage()).toContain('Live connection testing is unavailable');
    });
  });

  // =========================================================================
  // 4. CAPABILITIES TAB: PROBES, CDC TRUTH & PROOF LEVELS
  // =========================================================================
  describe('Tab 3: Capabilities, Truthful CDC & Proof Attestation', () => {
    beforeEach(() => {
      ws.loadFixtureForTesting('conn-ora-rac-01', 'capabilities');
    });

    it('should introspect permissions through PermissionProbe', () => {
      const conn = ws.connection()!;
      expect(conn.capabilities.permissionChecks.length).toBeGreaterThan(0);
      const logmnr = conn.capabilities.permissionChecks.find(p => p.permission === 'EXECUTE ON DBMS_LOGMNR');
      expect(logmnr?.status).toBe('VERIFIED');
    });

    it('should truthfully classify Kafka as Stream Offset Consumption and NOT database CDC', () => {
      ws.loadFixtureForTesting('conn-kafka-prod-01', 'capabilities');
      const conn = ws.connection()!;
      expect(conn.capabilities.cdcCapability.type).toBe('STREAM_OFFSET');
      expect(conn.capabilities.cdcCapability.label).toContain('Stream Offset Consumption (Not Database CDC)');
      expect(conn.capabilities.targetCapability.acidCompliant).toBe(false);
    });

    it('should classify Oracle as native LogMiner CDC', () => {
      ws.loadFixtureForTesting('conn-ora-rac-01', 'capabilities');
      const conn = ws.connection()!;
      expect(conn.capabilities.cdcCapability.type).toBe('LOGMINER');
      expect(conn.capabilities.proofLevel).toBe('INTEGRATION_PROVEN');
    });

    it('should classify Aurora PostgreSQL as Logical Decoding CDC', () => {
      ws.loadFixtureForTesting('conn-pg-aurora-01', 'capabilities');
      const conn = ws.connection()!;
      expect(conn.capabilities.cdcCapability.type).toBe('LOGICAL_DECODING');
      expect(conn.capabilities.proofLevel).toBe('LIVE_PROVEN');
    });
  });

  // =========================================================================
  // 5. USAGE TAB: PROJECT-ORIENTED REUSABLE RESOURCE CONTEXT
  // =========================================================================
  describe('Tab 4: Usage & Dependency Awareness', () => {
    beforeEach(() => {
      ws.loadFixtureForTesting('conn-ora-rac-01', 'usage');
    });

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
      ws.loadFixtureForTesting('conn-unused-test-01', 'usage');
      const conn = ws.connection()!;
      expect(conn.usage.projects.length).toBe(0);
      expect(conn.usage.migrations.length).toBe(0);
      expect(conn.usage.referenceProtection.canDelete).toBe(true);
      expect(conn.usage.referenceProtection.isReferenced).toBe(false);
    });
  });

  // =========================================================================
  // 6. ACTIVITY TAB: TRUTHFUL UNAVAILABLE STATE (B-2.2-08)
  // =========================================================================
  describe('Tab 5: Activity & Governance Audit Log', () => {
    beforeEach(() => {
      ws.loadFixtureForTesting('conn-ora-rac-01', 'activity');
    });

    it('should show truthful empty activity without fabricated timeline events', () => {
      const conn = ws.connection()!;
      expect(conn.activities).toEqual([]);
      expect(ws.filteredActivities()).toEqual([]);
    });
  });

  // =========================================================================
  // 7. SETTINGS TAB: METADATA, DISABLE & ARCHIVE GOVERNANCE (FAIL-CLOSED B-2.2-07)
  // =========================================================================
  describe('Tab 6: Settings, Metadata & Governed Lifecycle', () => {
    beforeEach(() => {
      ws.loadFixtureForTesting('conn-ora-rac-01', 'settings');
    });

    it('should handle rename with truthful fail-closed notice without mutating name', () => {
      const originalName = ws.connection()?.name;
      ws.saveMetadata('Renamed Core Banking RAC', 'Updated production description', ['Core', 'Tier-0']);
      expect(ws.connection()?.name).toBe(originalName);
      expect(ws.configNotice()).toBe('Connection renaming is unavailable while connection service is disconnected.');
    });

    it('should handle disable/enable with truthful fail-closed notice without mutating state', () => {
      const originalState = ws.connection()?.lifecycleState;
      ws.toggleDisableConnection();
      expect(ws.connection()?.lifecycleState).toBe(originalState);
      expect(ws.configNotice()).toBe('Connection lifecycle changes are unavailable while connection service is disconnected.');
    });

    it('should handle archive with truthful fail-closed notice without mutating state', () => {
      const originalState = ws.connection()?.lifecycleState;
      ws.archiveConnection();
      expect(ws.connection()?.lifecycleState).toBe(originalState);
      expect(ws.configNotice()).toBe('Connection archiving is unavailable while connection service is disconnected.');
    });

    it('should handle delete with truthful fail-closed notice without deleting or navigating', () => {
      const originalConn = ws.connection();
      ws.deleteConnection();
      expect(ws.connection()).toBe(originalConn);
      expect(ws.configNotice()).toBe('Connection deletion is unavailable while connection service is disconnected.');
    });
  });
});
