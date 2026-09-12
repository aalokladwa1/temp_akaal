/**
 * AKAAL Administration — Enterprise Reactive Signals Store
 * Single source of truth for 5.1 Enterprise domains with bi-directional ContextService synchronization.
 */

import { Injectable, signal, computed, Optional } from '@angular/core';
import { ContextService } from '../../../core/services/context.service';
import {
  EnterpriseSettings,
  AdminOrganization,
  AdminWorkspace,
  AdminEnvironment,
  ProjectBoundary,
  ResourceOwnership,
  QuotaAllocation,
  AdminMetadataTag,
  OrgTier,
  WorkspaceTier,
  EnvironmentTier
} from '../models/enterprise.models';

@Injectable({
  providedIn: 'root'
})
export class EnterpriseService {
  // 1. Enterprise Root Settings
  public settings = signal<EnterpriseSettings>({
    id: 'ent-root-default',
    legalEntityName: 'Akaal Global Financial Technologies Inc.',
    enterpriseIdentifier: 'AKAAL-ENT-8849',
    primaryDomain: 'akaaltech.internal',
    secondaryDomains: ['cloud.akaal.corp', 'apac.akaal.internal'],
    rootOrgId: 'org-global-corp',
    rootOrgName: 'Akaal Corporate Global',
    globalComplianceTier: 'FINANCIAL_STRICT_SOC2_PCI',
    kmsKeyArn: 'arn:aws:kms:us-east-1:109923847120:key/akaal-master-hsm-2026',
    securityBaseline: {
      mfaEnforced: true,
      sessionTimeoutMinutes: 60,
      fourEyesQuorumThreshold: 2,
      auditLogRetentionDays: 365,
      ipAllowlistEnforced: true
    },
    maintenanceWindow: {
      preferredDay: 'SUNDAY',
      startUtc: '02:00',
      durationHours: 4,
      timeZone: 'UTC'
    },
    emergencyBreakGlass: {
      primaryContact: 'SecOps Incident Commander',
      emergencyEmail: 'secops-breakglass@akaaltech.internal',
      escalationPhone: '+1 (800) 555-0199',
      vaultEscrowReference: 'CYBER-VAULT-ESCROW-ALPHA-01'
    },
    updatedAt: '2026-03-01T00:00:00Z',
    updatedBy: 'system.bootstrap@akaaltech.internal'
  });

  // 2. Structure Signals
  public organizations = signal<AdminOrganization[]>([
    {
      id: 'org-global-corp',
      name: 'Akaal Corporate Global',
      code: 'GLOBAL-CORP',
      description: 'Primary corporate tenant encompassing enterprise banking, retail, and wealth management portfolios.',
      tier: 'GLOBAL_PARENT',
      status: 'ACTIVE',
      primaryContactName: 'Aalok Ladwa',
      primaryContactEmail: 'aalok.ladwa@akaaltech.internal',
      workspacesCount: 1,
      activeUsersCount: 1,
      defaultRegion: 'us-east-1',
      costCenterCode: 'CC-1000-GLOBAL',
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-03-01T00:00:00Z'
    }
  ]);

  public workspaces = signal<AdminWorkspace[]>([
    {
      id: 'ws-core-banking',
      orgId: 'org-global-corp',
      orgName: 'Akaal Corporate Global',
      name: 'Core Banking Modernization',
      code: 'WS-CORE-BANKING',
      description: 'Primary workspace executing multi-terabyte transactional ledger migration to distributed PostgreSQL.',
      tier: 'ENTERPRISE_PRODUCTION',
      status: 'ACTIVE',
      residencyRegion: 'us-east-1',
      environmentCount: 1,
      activeMemberCount: 1,
      activeInitiativesCount: 1,
      ownerName: 'Aalok Ladwa',
      ownerEmail: 'aalok.ladwa@akaaltech.internal',
      storageQuotaGb: 1024,
      storageUsedGb: 120,
      createdAt: '2026-01-10T00:00:00Z',
      updatedAt: '2026-03-01T00:00:00Z'
    }
  ]);

  public environments = signal<AdminEnvironment[]>([
    {
      id: 'env-core-bank-prod',
      workspaceId: 'ws-core-banking',
      workspaceName: 'Core Banking Modernization',
      orgId: 'org-global-corp',
      name: 'Production Transaction Tier',
      tier: 'PRODUCTION',
      isProduction: true,
      isolationBarrierStatus: 'STRICT_ENFORCED',
      dataMaskingEnforced: true,
      maintenanceLock: false,
      activeConnectionsCount: 4,
      lastDeploymentAt: '2026-03-10T14:30:00Z',
      createdAt: '2026-01-10T00:00:00Z'
    }
  ]);

  // 3. Resource Governance Signals
  public boundaries = signal<ProjectBoundary[]>([
    {
      id: 'bnd-core-ledger',
      name: 'Core Ledger Isolation Boundary',
      code: 'BND-CORE-LEDGER',
      workspaceId: 'ws-core-banking',
      workspaceName: 'Core Banking Modernization',
      leadOwnerName: 'Aalok Ladwa',
      isolationPolicy: 'STRICT_ISOLATED',
      boundConnectionsCount: 2,
      crossBoundaryAllowed: false,
      dataClassification: 'RESTRICTED_CONFIDENTIAL',
      tags: ['PCI-DSS-SCOPE', 'TIER-0-MISSION-CRITICAL'],
      createdAt: '2026-01-15T00:00:00Z'
    }
  ]);

  public resourceOwnerships = signal<ResourceOwnership[]>([
    {
      id: 'own-01',
      resourceType: 'WORKSPACE',
      resourceId: 'ws-core-banking',
      resourceName: 'Core Banking Modernization',
      primaryOwnerName: 'Aalok Ladwa',
      primaryOwnerEmail: 'aalok.ladwa@akaaltech.internal',
      secondaryOwnerName: 'Priya Sharma',
      secondaryOwnerEmail: 'p.sharma@akaaltech.internal',
      assignedTeam: 'Core Infrastructure Guild',
      escalationContact: 'Platform Engineering Escalation',
      lastTransferDate: '2026-01-10T00:00:00Z',
      transferPending: false
    }
  ]);

  public quotaAllocations = signal<QuotaAllocation[]>([
    {
      id: 'quota-01',
      scopeType: 'ORGANIZATION',
      scopeId: 'org-global-corp',
      scopeName: 'Akaal Corporate Global',
      concurrentMigrationsLimit: 16,
      concurrentMigrationsUsed: 2,
      bandwidthMbpsLimit: 10000,
      bandwidthMbpsUsed: 1250,
      maxActiveConnectionsLimit: 64,
      activeConnectionsUsed: 8,
      storageQuotaGb: 8192,
      storageUsedGb: 1420,
      peakThroughputCapIops: 25000,
      rateLimitReqPerSec: 5000,
      lastUpdated: '2026-03-01T00:00:00Z'
    }
  ]);

  public metadataTags = signal<AdminMetadataTag[]>([
    {
      id: 'tag-01',
      key: 'CostCenter',
      valueSchema: 'STRING',
      category: 'COST_CENTER',
      isMandatory: true,
      allowedValues: ['CC-1000-GLOBAL', 'CC-2000-RETAIL', 'CC-3000-WEALTH'],
      appliedResourceCount: 3,
      description: 'Financial ledger billing allocation and chargeback reference.',
      createdAt: '2026-01-01T00:00:00Z'
    },
    {
      id: 'tag-02',
      key: 'DataClassification',
      valueSchema: 'ENUM',
      category: 'DATA_GOVERNANCE',
      isMandatory: true,
      allowedValues: ['RESTRICTED_CONFIDENTIAL', 'CONFIDENTIAL', 'INTERNAL', 'PUBLIC'],
      appliedResourceCount: 5,
      description: 'Regulatory data confidentiality and encryption baseline level.',
      createdAt: '2026-01-01T00:00:00Z'
    }
  ]);

  constructor(@Optional() private cs?: ContextService) {
    this.initializeFromContext();
    this.syncContextService();
  }

  // ==========================================
  // CONTEXT SYNCHRONIZATION
  // ==========================================
  private initializeFromContext(): void {
    if (!this.cs) return;

    const existingOrgs = this.cs.organizations();
    if (existingOrgs && existingOrgs.length > 0) {
      const currentOrgs = this.organizations();
      existingOrgs.forEach(o => {
        if (!currentOrgs.some(co => co.id === o.id)) {
          currentOrgs.push({
            id: o.id,
            name: o.name,
            code: o.id.toUpperCase(),
            description: o.description || 'Enterprise tenant scope',
            tier: 'GLOBAL_PARENT',
            status: 'ACTIVE',
            primaryContactName: 'Administrator',
            primaryContactEmail: 'admin@enterprise.internal',
            workspacesCount: 0,
            activeUsersCount: 0,
            defaultRegion: 'us-east-1',
            costCenterCode: 'CC-DEFAULT',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          });
        }
      });
      this.organizations.set([...currentOrgs]);
    }

    const existingWorkspaces = this.cs.workspaces();
    if (existingWorkspaces && existingWorkspaces.length > 0) {
      const currentWs = this.workspaces();
      existingWorkspaces.forEach(w => {
        if (!currentWs.some(cw => cw.id === w.id)) {
          const org = this.organizations().find(o => o.id === w.orgId);
          currentWs.push({
            id: w.id,
            orgId: w.orgId,
            orgName: org?.name || 'Enterprise Org',
            name: w.name,
            code: w.id.toUpperCase(),
            description: w.description || 'Enterprise workspace boundary',
            tier: 'ENTERPRISE_PRODUCTION',
            status: 'ACTIVE',
            residencyRegion: 'us-east-1',
            environmentCount: 1,
            activeMemberCount: 1,
            activeInitiativesCount: 0,
            ownerName: 'Platform Administrator',
            ownerEmail: 'admin@enterprise.internal',
            storageQuotaGb: 1024,
            storageUsedGb: 0,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          });
        }
      });
      this.workspaces.set([...currentWs]);
    }
  }

  private syncContextService(): void {
    if (!this.cs) return;

    const orgs = this.organizations().map(o => ({
      id: o.id,
      name: o.name,
      description: o.description
    }));
    this.cs.organizations.set(orgs);

    const workspaces = this.workspaces().map(w => ({
      id: w.id,
      orgId: w.orgId,
      name: w.name,
      description: w.description
    }));
    this.cs.workspaces.set(workspaces);

    const envs = this.environments().map(e => ({
      id: e.id,
      workspaceId: e.workspaceId,
      name: e.name,
      isProduction: e.isProduction
    }));
    this.cs.environments.set(envs);

    if (!this.cs.selectedOrg() && orgs.length > 0) {
      this.cs.selectOrganization(orgs[0]);
    }
    if (!this.cs.selectedWorkspace() && workspaces.length > 0) {
      this.cs.selectWorkspace(workspaces[0]);
    }
    if (!this.cs.selectedEnvironment() && envs.length > 0) {
      this.cs.selectEnvironment(envs[0]);
    }
  }

  // ==========================================
  // GETTER HELPERS
  // ==========================================
  public getOrganization(id: string): AdminOrganization | undefined {
    return this.organizations().find(o => o.id === id);
  }

  public getWorkspacesByOrg(orgId: string): AdminWorkspace[] {
    return this.workspaces().filter(w => w.orgId === orgId);
  }

  public getWorkspace(id: string): AdminWorkspace | undefined {
    return this.workspaces().find(w => w.id === id);
  }

  public getEnvironmentsByWorkspace(workspaceId: string): AdminEnvironment[] {
    return this.environments().filter(e => e.workspaceId === workspaceId);
  }

  public getEnvironment(id: string): AdminEnvironment | undefined {
    return this.environments().find(e => e.id === id);
  }

  public getBoundary(id: string): ProjectBoundary | undefined {
    return this.boundaries().find(b => b.id === id);
  }

  public getOwnership(id: string): ResourceOwnership | undefined {
    return this.resourceOwnerships().find(r => r.id === id);
  }

  public getQuota(id: string): QuotaAllocation | undefined {
    return this.quotaAllocations().find(q => q.id === id);
  }

  public getTag(id: string): AdminMetadataTag | undefined {
    return this.metadataTags().find(t => t.id === id);
  }

  // ==========================================
  // ENTERPRISE SETTINGS MUTATIONS
  // ==========================================
  public updateSettings(updates: Partial<EnterpriseSettings>): void {
    this.settings.update(current => ({
      ...current,
      ...updates,
      updatedAt: new Date().toISOString(),
      updatedBy: 'Platform Administrator'
    }));
  }

  // ==========================================
  // STRUCTURE MUTATIONS
  // ==========================================
  public createOrganization(data: {
    name: string;
    code: string;
    description: string;
    tier: OrgTier;
    primaryContactName: string;
    primaryContactEmail: string;
    defaultRegion?: string;
    costCenterCode?: string;
  }): AdminOrganization {
    const newOrg: AdminOrganization = {
      id: `org-${data.code.toLowerCase()}-${Date.now().toString().slice(-4)}`,
      name: data.name,
      code: data.code.toUpperCase(),
      description: data.description,
      tier: data.tier || 'GLOBAL_PARENT',
      status: 'ACTIVE',
      primaryContactName: data.primaryContactName,
      primaryContactEmail: data.primaryContactEmail,
      workspacesCount: 0,
      activeUsersCount: 1,
      defaultRegion: data.defaultRegion || 'us-east-1',
      costCenterCode: data.costCenterCode || 'CC-DEFAULT',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    this.organizations.update(list => [newOrg, ...list]);
    this.syncContextService();
    return newOrg;
  }

  public updateOrganization(orgId: string, updates: Partial<AdminOrganization>): void {
    this.organizations.update(list => list.map(o => {
      if (o.id === orgId) {
        return { ...o, ...updates, updatedAt: new Date().toISOString() };
      }
      return o;
    }));
    this.syncContextService();
  }

  public deleteOrganization(orgId: string): void {
    this.organizations.update(list => list.filter(o => o.id !== orgId));
    this.syncContextService();
  }

  public createWorkspace(data: {
    orgId: string;
    name: string;
    code: string;
    description: string;
    tier: WorkspaceTier;
    residencyRegion: string;
    ownerName: string;
    ownerEmail: string;
    storageQuotaGb?: number;
  }): AdminWorkspace {
    const org = this.organizations().find(o => o.id === data.orgId);
    const newWs: AdminWorkspace = {
      id: `ws-${data.code.toLowerCase()}-${Date.now().toString().slice(-4)}`,
      orgId: data.orgId,
      orgName: org?.name || 'Enterprise Org',
      name: data.name,
      code: data.code.toUpperCase(),
      description: data.description,
      tier: data.tier || 'ENTERPRISE_PRODUCTION',
      status: 'ACTIVE',
      residencyRegion: data.residencyRegion,
      environmentCount: 1,
      activeMemberCount: 1,
      activeInitiativesCount: 0,
      ownerName: data.ownerName,
      ownerEmail: data.ownerEmail,
      storageQuotaGb: data.storageQuotaGb || 1024,
      storageUsedGb: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    this.workspaces.update(list => [newWs, ...list]);

    // Add initial environment
    const newEnv: AdminEnvironment = {
      id: `env-${newWs.code.toLowerCase()}-dev`,
      workspaceId: newWs.id,
      workspaceName: newWs.name,
      orgId: newWs.orgId,
      name: 'Development Tier',
      tier: 'DEVELOPMENT',
      isProduction: false,
      isolationBarrierStatus: 'SHARED_DEVELOPMENT',
      dataMaskingEnforced: false,
      maintenanceLock: false,
      activeConnectionsCount: 0,
      lastDeploymentAt: 'Never',
      createdAt: new Date().toISOString()
    };
    this.environments.update(list => [newEnv, ...list]);

    this.organizations.update(list => list.map(o => o.id === data.orgId ? { ...o, workspacesCount: o.workspacesCount + 1 } : o));
    this.syncContextService();
    return newWs;
  }

  public updateWorkspace(workspaceId: string, updates: Partial<AdminWorkspace>): void {
    this.workspaces.update(list => list.map(w => {
      if (w.id === workspaceId) {
        return { ...w, ...updates, updatedAt: new Date().toISOString() };
      }
      return w;
    }));
    this.syncContextService();
  }

  public deleteWorkspace(workspaceId: string): void {
    const ws = this.workspaces().find(w => w.id === workspaceId);
    if (ws) {
      this.organizations.update(list => list.map(o => o.id === ws.orgId ? { ...o, workspacesCount: Math.max(0, o.workspacesCount - 1) } : o));
    }
    this.workspaces.update(list => list.filter(w => w.id !== workspaceId));
    this.environments.update(list => list.filter(e => e.workspaceId !== workspaceId));
    this.syncContextService();
  }

  public createEnvironment(data: {
    workspaceId: string;
    name: string;
    tier: EnvironmentTier;
    isProduction: boolean;
    isolationBarrierStatus: any;
    dataMaskingEnforced: boolean;
  }): AdminEnvironment {
    const ws = this.workspaces().find(w => w.id === data.workspaceId);
    const newEnv: AdminEnvironment = {
      id: `env-${Date.now().toString().slice(-6)}`,
      workspaceId: data.workspaceId,
      workspaceName: ws?.name || 'Workspace',
      orgId: ws?.orgId || 'org-root',
      name: data.name,
      tier: data.tier,
      isProduction: data.isProduction,
      isolationBarrierStatus: data.isolationBarrierStatus,
      dataMaskingEnforced: data.dataMaskingEnforced,
      maintenanceLock: false,
      activeConnectionsCount: 0,
      lastDeploymentAt: 'Never',
      createdAt: new Date().toISOString()
    };
    this.environments.update(list => [newEnv, ...list]);
    this.workspaces.update(list => list.map(w => w.id === data.workspaceId ? { ...w, environmentCount: w.environmentCount + 1 } : w));
    this.syncContextService();
    return newEnv;
  }

  public updateEnvironment(envId: string, updates: Partial<AdminEnvironment>): void {
    this.environments.update(list => list.map(e => {
      if (e.id === envId) {
        return { ...e, ...updates };
      }
      return e;
    }));
    this.syncContextService();
  }

  public toggleEnvironmentLock(envId: string): void {
    this.environments.update(list => list.map(e => {
      if (e.id === envId) {
        return { ...e, maintenanceLock: !e.maintenanceLock };
      }
      return e;
    }));
  }

  public deleteEnvironment(envId: string): void {
    const env = this.environments().find(e => e.id === envId);
    if (env) {
      this.workspaces.update(list => list.map(w => w.id === env.workspaceId ? { ...w, environmentCount: Math.max(0, w.environmentCount - 1) } : w));
    }
    this.environments.update(list => list.filter(e => e.id !== envId));
    this.syncContextService();
  }

  // ==========================================
  // RESOURCE GOVERNANCE MUTATIONS
  // ==========================================
  public createBoundary(data: {
    name: string;
    code: string;
    workspaceId: string;
    leadOwnerName: string;
    isolationPolicy: any;
    dataClassification: any;
    crossBoundaryAllowed: boolean;
    tags: string[];
  }): ProjectBoundary {
    const ws = this.workspaces().find(w => w.id === data.workspaceId);
    const newBoundary: ProjectBoundary = {
      id: `bnd-${data.code.toLowerCase()}-${Date.now().toString().slice(-4)}`,
      name: data.name,
      code: data.code.toUpperCase(),
      workspaceId: data.workspaceId,
      workspaceName: ws?.name || 'Workspace',
      leadOwnerName: data.leadOwnerName,
      isolationPolicy: data.isolationPolicy,
      boundConnectionsCount: 0,
      crossBoundaryAllowed: data.crossBoundaryAllowed,
      dataClassification: data.dataClassification,
      tags: data.tags,
      createdAt: new Date().toISOString()
    };
    this.boundaries.update(list => [newBoundary, ...list]);
    return newBoundary;
  }

  public updateBoundary(boundaryId: string, updates: Partial<ProjectBoundary>): void {
    this.boundaries.update(list => list.map(b => {
      if (b.id === boundaryId) {
        return { ...b, ...updates };
      }
      return b;
    }));
  }

  public deleteBoundary(boundaryId: string): void {
    this.boundaries.update(list => list.filter(b => b.id !== boundaryId));
  }

  public transferOwnership(resourceId: string, newOwnerName: string, newOwnerEmail: string, newSecondaryName?: string, newSecondaryEmail?: string, newTeam?: string): void {
    this.resourceOwnerships.update(list => list.map(r => {
      if (r.id === resourceId || r.resourceId === resourceId) {
        return {
          ...r,
          primaryOwnerName: newOwnerName,
          primaryOwnerEmail: newOwnerEmail,
          secondaryOwnerName: newSecondaryName || r.secondaryOwnerName,
          secondaryOwnerEmail: newSecondaryEmail || r.secondaryOwnerEmail,
          assignedTeam: newTeam || r.assignedTeam,
          lastTransferDate: new Date().toISOString(),
          transferPending: false,
          pendingTransferTo: undefined
        };
      }
      return r;
    }));
  }

  public updateQuotas(quotaId: string, updates: Partial<QuotaAllocation>): void {
    this.quotaAllocations.update(list => list.map(q => {
      if (q.id === quotaId) {
        return { ...q, ...updates, lastUpdated: new Date().toISOString() };
      }
      return q;
    }));
  }

  public createQuota(data: {
    scopeType: any;
    scopeId: string;
    scopeName: string;
    concurrentMigrationsLimit: number;
    bandwidthMbpsLimit: number;
    maxActiveConnectionsLimit: number;
    storageQuotaGb: number;
    peakThroughputCapIops: number;
    rateLimitReqPerSec: number;
  }): QuotaAllocation {
    const newQuota: QuotaAllocation = {
      id: `quota-${Date.now().toString().slice(-6)}`,
      scopeType: data.scopeType,
      scopeId: data.scopeId,
      scopeName: data.scopeName,
      concurrentMigrationsLimit: data.concurrentMigrationsLimit,
      concurrentMigrationsUsed: 0,
      bandwidthMbpsLimit: data.bandwidthMbpsLimit,
      bandwidthMbpsUsed: 0,
      maxActiveConnectionsLimit: data.maxActiveConnectionsLimit,
      activeConnectionsUsed: 0,
      storageQuotaGb: data.storageQuotaGb,
      storageUsedGb: 0,
      peakThroughputCapIops: data.peakThroughputCapIops,
      rateLimitReqPerSec: data.rateLimitReqPerSec,
      lastUpdated: new Date().toISOString()
    };
    this.quotaAllocations.update(list => [newQuota, ...list]);
    return newQuota;
  }

  public createMetadataTag(data: {
    key: string;
    valueSchema: string;
    category: any;
    isMandatory: boolean;
    allowedValues?: string[];
    description: string;
  }): AdminMetadataTag {
    const newTag: AdminMetadataTag = {
      id: `tag-${Date.now().toString().slice(-6)}`,
      key: data.key,
      valueSchema: data.valueSchema,
      category: data.category,
      isMandatory: data.isMandatory,
      allowedValues: data.allowedValues || [],
      appliedResourceCount: 0,
      description: data.description,
      createdAt: new Date().toISOString()
    };
    this.metadataTags.update(list => [newTag, ...list]);
    return newTag;
  }

  public updateMetadataTag(tagId: string, updates: Partial<AdminMetadataTag>): void {
    this.metadataTags.update(list => list.map(t => {
      if (t.id === tagId) {
        return { ...t, ...updates };
      }
      return t;
    }));
  }

  public deleteMetadataTag(tagId: string): void {
    this.metadataTags.update(list => list.filter(t => t.id !== tagId));
  }
}
