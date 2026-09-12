/**
 * AKAAL Administration Module & 5.1 Enterprise Domain Test Suite
 * Exhaustive coverage of reactive signals store, mutations, and structural contracts.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { EnterpriseService } from './services/enterprise.service';
import { ContextService } from '../../core/services/context.service';

describe('AKAAL Administration — 5.1 Enterprise Domain Suite', () => {
  let enterpriseService: EnterpriseService;
  let contextService: ContextService;

  beforeEach(() => {
    contextService = new ContextService();
    enterpriseService = new EnterpriseService(contextService);
  });

  describe('1. Enterprise Settings', () => {
    it('should initialize with canonical settings state', () => {
      const s = enterpriseService.settings();
      expect(s.legalEntityName).toBe('Akaal Global Financial Technologies Inc.');
      expect(s.enterpriseIdentifier).toBe('AKAAL-ENT-8849');
      expect(s.globalComplianceTier).toBe('FINANCIAL_STRICT_SOC2_PCI');
      expect(s.securityBaseline.mfaEnforced).toBe(true);
      expect(s.securityBaseline.sessionTimeoutMinutes).toBe(60);
    });

    it('should update enterprise settings immutably', () => {
      enterpriseService.updateSettings({
        legalEntityName: 'Akaal Global Enterprises LLC',
        securityBaseline: {
          ...enterpriseService.settings().securityBaseline,
          sessionTimeoutMinutes: 30
        }
      });
      const s = enterpriseService.settings();
      expect(s.legalEntityName).toBe('Akaal Global Enterprises LLC');
      expect(s.securityBaseline.sessionTimeoutMinutes).toBe(30);
    });
  });

  describe('2. Structure — Organizations', () => {
    it('should initialize with default global parent organization', () => {
      const orgs = enterpriseService.organizations();
      expect(orgs.length).toBeGreaterThanOrEqual(1);
      expect(orgs[0].code).toBe('GLOBAL-CORP');
      expect(orgs[0].tier).toBe('GLOBAL_PARENT');
    });

    it('should create and retrieve new organization', () => {
      const newOrg = enterpriseService.createOrganization({
        name: 'Akaal EMEA Holding',
        code: 'EMEA-HOLDING',
        description: 'European operating division',
        tier: 'REGIONAL_SUBSIDIARY',
        primaryContactName: 'John Doe',
        primaryContactEmail: 'john.doe@akaal.corp',
        defaultRegion: 'eu-west-1',
        costCenterCode: 'CC-EMEA-01'
      });

      expect(newOrg.id).toBeDefined();
      expect(enterpriseService.getOrganization(newOrg.id)).toBeDefined();
      expect(enterpriseService.getOrganization(newOrg.id)?.name).toBe('Akaal EMEA Holding');
    });

    it('should update organization fields', () => {
      const org = enterpriseService.organizations()[0];
      enterpriseService.updateOrganization(org.id, {
        description: 'Updated description for global tenant'
      });
      expect(enterpriseService.getOrganization(org.id)?.description).toBe('Updated description for global tenant');
    });

    it('should delete organization', () => {
      const newOrg = enterpriseService.createOrganization({
        name: 'Temp Org',
        code: 'TEMP',
        description: 'Temp',
        tier: 'SANDBOX_TENANT',
        primaryContactName: 'Temp',
        primaryContactEmail: 'temp@akaal.corp'
      });
      const initialCount = enterpriseService.organizations().length;
      enterpriseService.deleteOrganization(newOrg.id);
      expect(enterpriseService.organizations().length).toBe(initialCount - 1);
      expect(enterpriseService.getOrganization(newOrg.id)).toBeUndefined();
    });
  });

  describe('3. Structure — Workspaces', () => {
    it('should initialize with default workspace and query by organization', () => {
      const org = enterpriseService.organizations()[0];
      const ws = enterpriseService.getWorkspacesByOrg(org.id);
      expect(ws.length).toBeGreaterThanOrEqual(1);
      expect(ws[0].code).toBe('WS-CORE-BANKING');
    });

    it('should create workspace and auto-generate initial development environment', () => {
      const org = enterpriseService.organizations()[0];
      const initialEnvCount = enterpriseService.environments().length;
      const newWs = enterpriseService.createWorkspace({
        orgId: org.id,
        name: 'Wealth Analytics Hub',
        code: 'WS-WEALTH-ANALYTICS',
        description: 'Portfolio analytics replication pipeline',
        tier: 'ENTERPRISE_PRODUCTION',
        residencyRegion: 'us-east-1',
        ownerName: 'Aalok Ladwa',
        ownerEmail: 'aalok@akaal.corp'
      });

      expect(newWs.id).toBeDefined();
      expect(enterpriseService.getWorkspace(newWs.id)).toBeDefined();
      expect(enterpriseService.environments().length).toBe(initialEnvCount + 1);
    });

    it('should delete workspace and cascadingly remove associated environments', () => {
      const org = enterpriseService.organizations()[0];
      const newWs = enterpriseService.createWorkspace({
        orgId: org.id,
        name: 'Disposal WS',
        code: 'DISPOSAL-WS',
        description: 'To be deleted',
        tier: 'DEVELOPMENT_SANDBOX',
        residencyRegion: 'us-east-1',
        ownerName: 'Admin',
        ownerEmail: 'admin@akaal.corp'
      });

      expect(enterpriseService.getEnvironmentsByWorkspace(newWs.id).length).toBe(1);
      enterpriseService.deleteWorkspace(newWs.id);
      expect(enterpriseService.getWorkspace(newWs.id)).toBeUndefined();
      expect(enterpriseService.getEnvironmentsByWorkspace(newWs.id).length).toBe(0);
    });
  });

  describe('4. Structure — Environments', () => {
    it('should create new environment under a workspace', () => {
      const ws = enterpriseService.workspaces()[0];
      const newEnv = enterpriseService.createEnvironment({
        workspaceId: ws.id,
        name: 'Staging Integration Cluster',
        tier: 'STAGING',
        isProduction: false,
        isolationBarrierStatus: 'STANDARD_ISOLATED',
        dataMaskingEnforced: true
      });

      expect(newEnv.id).toBeDefined();
      expect(enterpriseService.getEnvironment(newEnv.id)).toBeDefined();
      expect(enterpriseService.getEnvironment(newEnv.id)?.isProduction).toBe(false);
    });

    it('should toggle maintenance lock on environment', () => {
      const env = enterpriseService.environments()[0];
      const initialLock = env.maintenanceLock;
      enterpriseService.toggleEnvironmentLock(env.id);
      expect(enterpriseService.getEnvironment(env.id)?.maintenanceLock).toBe(!initialLock);
    });

    it('should delete environment', () => {
      const ws = enterpriseService.workspaces()[0];
      const newEnv = enterpriseService.createEnvironment({
        workspaceId: ws.id,
        name: 'Temp Env',
        tier: 'DEVELOPMENT',
        isProduction: false,
        isolationBarrierStatus: 'SHARED_DEVELOPMENT',
        dataMaskingEnforced: false
      });
      enterpriseService.deleteEnvironment(newEnv.id);
      expect(enterpriseService.getEnvironment(newEnv.id)).toBeUndefined();
    });
  });

  describe('5. Resource Governance — Boundaries', () => {
    it('should create and retrieve project boundary', () => {
      const ws = enterpriseService.workspaces()[0];
      const newB = enterpriseService.createBoundary({
        name: 'Treasury Isolation Enclave',
        code: 'BND-TREASURY',
        workspaceId: ws.id,
        leadOwnerName: 'Chief Security Officer',
        isolationPolicy: 'STRICT_ISOLATED',
        dataClassification: 'RESTRICTED_CONFIDENTIAL',
        crossBoundaryAllowed: false,
        tags: ['PCI-DSS-SCOPE', 'TREASURY-01']
      });

      expect(newB.id).toBeDefined();
      expect(enterpriseService.getBoundary(newB.id)).toBeDefined();
      expect(enterpriseService.getBoundary(newB.id)?.isolationPolicy).toBe('STRICT_ISOLATED');
    });

    it('should update and delete boundary', () => {
      const ws = enterpriseService.workspaces()[0];
      const newB = enterpriseService.createBoundary({
        name: 'Temp Bnd',
        code: 'TEMP-BND',
        workspaceId: ws.id,
        leadOwnerName: 'SecOps',
        isolationPolicy: 'CROSS_TENANT_READ',
        dataClassification: 'CONFIDENTIAL',
        crossBoundaryAllowed: true,
        tags: ['TEMP']
      });

      enterpriseService.updateBoundary(newB.id, { leadOwnerName: 'Updated Lead' });
      expect(enterpriseService.getBoundary(newB.id)?.leadOwnerName).toBe('Updated Lead');

      enterpriseService.deleteBoundary(newB.id);
      expect(enterpriseService.getBoundary(newB.id)).toBeUndefined();
    });
  });

  describe('6. Resource Governance — Ownership', () => {
    it('should list resource ownership records and execute transfer', () => {
      const ownerships = enterpriseService.resourceOwnerships();
      expect(ownerships.length).toBeGreaterThanOrEqual(1);

      const target = ownerships[0];
      enterpriseService.transferOwnership(
        target.id,
        'Senior Custodian',
        'custodian@akaal.corp',
        'Standby Custodian',
        'standby@akaal.corp',
        'Core SRE Guild'
      );

      const updated = enterpriseService.getOwnership(target.id);
      expect(updated?.primaryOwnerName).toBe('Senior Custodian');
      expect(updated?.primaryOwnerEmail).toBe('custodian@akaal.corp');
      expect(updated?.assignedTeam).toBe('Core SRE Guild');
    });
  });

  describe('7. Resource Governance — Quotas', () => {
    it('should create and update quota allocations', () => {
      const newQuota = enterpriseService.createQuota({
        scopeType: 'WORKSPACE',
        scopeId: 'ws-test',
        scopeName: 'Test WS',
        concurrentMigrationsLimit: 8,
        bandwidthMbpsLimit: 5000,
        maxActiveConnectionsLimit: 32,
        storageQuotaGb: 4096,
        peakThroughputCapIops: 10000,
        rateLimitReqPerSec: 2500
      });

      expect(newQuota.id).toBeDefined();
      expect(enterpriseService.getQuota(newQuota.id)).toBeDefined();

      enterpriseService.updateQuotas(newQuota.id, {
        concurrentMigrationsLimit: 12
      });
      expect(enterpriseService.getQuota(newQuota.id)?.concurrentMigrationsLimit).toBe(12);
    });
  });

  describe('8. Resource Governance — Administrative Metadata & Tags', () => {
    it('should create, update, and delete tag definitions', () => {
      const newTag = enterpriseService.createMetadataTag({
        key: 'EnvironmentOwner',
        valueSchema: 'STRING',
        category: 'OPERATIONAL_TIER',
        isMandatory: true,
        allowedValues: ['PROD-TEAM', 'STAGE-TEAM'],
        description: 'Operational team responsible for environment triage.'
      });

      expect(newTag.id).toBeDefined();
      expect(enterpriseService.getTag(newTag.id)).toBeDefined();
      expect(enterpriseService.getTag(newTag.id)?.isMandatory).toBe(true);

      enterpriseService.updateMetadataTag(newTag.id, {
        description: 'Updated operational tag description'
      });
      expect(enterpriseService.getTag(newTag.id)?.description).toBe('Updated operational tag description');

      enterpriseService.deleteMetadataTag(newTag.id);
      expect(enterpriseService.getTag(newTag.id)).toBeUndefined();
    });
  });

  describe('9. Component Search & Filtering Logic', () => {
    it('should filter organizations by search query and tier', () => {
      const orgs = enterpriseService.organizations();
      const filtered = orgs.filter(o => o.tier === 'GLOBAL_PARENT' && o.name.toLowerCase().includes('akaal'));
      expect(filtered.length).toBe(1);
      expect(filtered[0].code).toBe('GLOBAL-CORP');
    });

    it('should filter workspaces by search query and orgId', () => {
      const wsList = enterpriseService.workspaces();
      const org = enterpriseService.organizations()[0];
      const filtered = wsList.filter(w => w.orgId === org.id && w.name.toLowerCase().includes('core'));
      expect(filtered.length).toBe(1);
      expect(filtered[0].code).toBe('WS-CORE-BANKING');
    });

    it('should filter environments by workspace and lifecycle tier', () => {
      const envs = enterpriseService.environments();
      const ws = enterpriseService.workspaces()[0];
      const filtered = envs.filter(e => e.workspaceId === ws.id);
      expect(filtered.length).toBeGreaterThanOrEqual(1);
    });

    it('should filter resource boundaries by classification', () => {
      const boundaries = enterpriseService.boundaries();
      const filtered = boundaries.filter(b => b.dataClassification === 'RESTRICTED_CONFIDENTIAL');
      expect(filtered.length).toBeGreaterThanOrEqual(1);
    });
  });
});

