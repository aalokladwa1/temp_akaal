import { describe, it, expect, beforeEach } from 'vitest';
import { ContextService, Organization, Workspace, Environment } from './context.service';

class MockDashboardService {
  public refreshCount = 0;
  refreshDashboard() {
    this.refreshCount++;
  }
}

describe('ContextService & Operational Context Switching', () => {
  let service: ContextService;
  let mockDs: MockDashboardService;

  const mockOrgA: Organization = { id: 'org-a', name: 'Global Finance Corp' };
  const mockOrgB: Organization = { id: 'org-b', name: 'Retail Logistics' };

  const mockWsA1: Workspace = { id: 'ws-a1', orgId: 'org-a', name: 'Core Payments' };
  const mockWsA2: Workspace = { id: 'ws-a2', orgId: 'org-a', name: 'Settlement' };
  const mockWsB1: Workspace = { id: 'ws-b1', orgId: 'org-b', name: 'Supply Chain' };

  const mockEnvProd: Environment = { id: 'env-prod', workspaceId: 'ws-a1', name: 'Production Cluster', isProduction: true };
  const mockEnvStaging: Environment = { id: 'env-stg', workspaceId: 'ws-a1', name: 'Staging Tier', isProduction: false };
  const mockEnvB: Environment = { id: 'env-b', workspaceId: 'ws-b1', name: 'Dev', isProduction: false };

  beforeEach(() => {
    mockDs = new MockDashboardService();
    // Instantiate ContextService
    service = new ContextService();
    (service as any).ds = mockDs;

    service.organizations.set([mockOrgA, mockOrgB]);
    service.workspaces.set([mockWsA1, mockWsA2, mockWsB1]);
    service.environments.set([mockEnvProd, mockEnvStaging, mockEnvB]);
  });

  it('should initialize with null selections and false production state', () => {
    expect(service.selectedOrg()).toBeNull();
    expect(service.selectedWorkspace()).toBeNull();
    expect(service.selectedEnvironment()).toBeNull();
    expect(service.isProduction()).toBe(false);
  });

  it('should filter workspaces based on selected organization', () => {
    service.selectOrganization(mockOrgA);
    expect(service.selectedOrg()?.id).toBe('org-a');
    expect(service.availableWorkspacesForOrg().length).toBe(2);
    expect(service.availableWorkspacesForOrg().map(w => w.id)).toEqual(['ws-a1', 'ws-a2']);
  });

  it('should invalidate child workspace and environment when organization changes', () => {
    service.selectOrganization(mockOrgA);
    service.selectWorkspace(mockWsA1);
    service.selectEnvironment(mockEnvProd);

    expect(service.isProduction()).toBe(true);

    // Change to Org B
    service.selectOrganization(mockOrgB);
    expect(service.selectedOrg()?.id).toBe('org-b');
    expect(service.selectedWorkspace()).toBeNull();
    expect(service.selectedEnvironment()).toBeNull();
    expect(service.isProduction()).toBe(false);
  });

  it('should invalidate child environment when workspace changes', () => {
    service.selectOrganization(mockOrgA);
    service.selectWorkspace(mockWsA1);
    service.selectEnvironment(mockEnvProd);

    expect(service.selectedEnvironment()?.id).toBe('env-prod');

    // Switch to Workspace A2
    service.selectWorkspace(mockWsA2);
    expect(service.selectedWorkspace()?.id).toBe('ws-a2');
    expect(service.selectedEnvironment()).toBeNull();
    expect(service.isProduction()).toBe(false);
  });

  it('should correctly detect production environment tier', () => {
    service.selectOrganization(mockOrgA);
    service.selectWorkspace(mockWsA1);
    
    service.selectEnvironment(mockEnvProd);
    expect(service.isProduction()).toBe(true);

    service.selectEnvironment(mockEnvStaging);
    expect(service.isProduction()).toBe(false);
  });
});
