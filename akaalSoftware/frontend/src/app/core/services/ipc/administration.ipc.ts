import { Injectable, inject } from '@angular/core';
import { IpcService } from '../ipc.service';
import type { IPCResponse } from '../../models/ipc.models';

@Injectable({ providedIn: 'root' })
export class AdministrationIpc {
  private ipc: IpcService;

  constructor(ipcService?: IpcService) {
    if (ipcService) {
      this.ipc = ipcService;
    } else {
      try {
        this.ipc = inject(IpcService, { optional: true }) || new IpcService();
      } catch {
        this.ipc = new IpcService();
      }
    }
  }

  // =========================================================================
  // 29 Administration Queries
  // =========================================================================

  // 1. Enterprise Hierarchy
  public async getEnterpriseHierarchy(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'enterprise.hierarchy', params);
  }

  // 2. Organizations
  public async listOrganizations(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'organization.list', params);
  }

  // 3. Workspaces
  public async listWorkspaces(orgId?: string): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'workspace.list', orgId ? { org_id: orgId } : {});
  }

  // 4. Environments
  public async listEnvironments(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'environment.list', params);
  }

  // 5. Cost Centers
  public async listCostCenters(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'cost_center.list', params);
  }

  // 6. Users
  public async listUsers(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'user.list', params);
  }

  // 7. Teams
  public async listTeams(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'team.list', params);
  }

  // 8. Contractors
  public async listContractors(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'contractor.list', params);
  }

  // 9. Service Accounts
  public async listServiceAccounts(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'service_account.list', params);
  }

  // 10. Governance Summary
  public async getGovernanceSummary(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'governance.summary', params);
  }

  // 11. Governance Exceptions
  public async listGovernanceExceptions(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'governance.exceptions', params);
  }

  // 12. Governance Gates
  public async listGovernanceGates(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'governance.gates', params);
  }

  // 13. Roles
  public async listRoles(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'role.list', params);
  }

  // 14. Directory Sync Status
  public async getDirectorySyncStatus(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'directory.sync_status', params);
  }

  // 15. Templates
  public async listTemplates(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'template.list', params);
  }

  // 16. Profiles
  public async listProfiles(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'profile.list', params);
  }

  // 17. Connectors
  public async listConnectors(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'connector.list', params);
  }

  // 18. Plugins
  public async listPlugins(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'plugin.list', params);
  }

  // 19. Infra Agents
  public async listInfraAgents(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'infra.agents', params);
  }

  // 20. Infra Endpoints
  public async listInfraEndpoints(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'infra.endpoints', params);
  }

  // 21. Compliance Frameworks
  public async listComplianceFrameworks(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'compliance.frameworks', params);
  }

  // 22. Compliance Evidence Retention
  public async getComplianceEvidenceRetention(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'compliance.evidence_retention', params);
  }

  // 23. Audit Ledger
  public async getAuditLedger(params: { limit?: number; offset?: number } = { limit: 50, offset: 0 }): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'audit.ledger', params);
  }

  // 24. Audit Sessions
  public async listAuditSessions(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'audit.sessions', params);
  }

  // 25. Platform License
  public async getPlatformLicense(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'platform.license', params);
  }

  // 26. Platform Health
  public async getPlatformHealth(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'platform.health', params);
  }

  // 27. Integration SIEM
  public async getIntegrationSiem(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'integration.siem', params);
  }

  // 28. Integration Webhooks
  public async listIntegrationWebhooks(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'integration.webhooks', params);
  }

  // 29. Integration Keys
  public async listIntegrationKeys(params: Record<string, unknown> = {}): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'integration.keys', params);
  }

  // =========================================================================
  // 16 Administration Commands
  // =========================================================================

  // 30. Create Organization
  public async createOrganization(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'organization.create', payload);
  }

  // 31. Update Organization
  public async updateOrganization(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'organization.update', payload);
  }

  // 32. Create Workspace
  public async createWorkspace(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'workspace.create', payload);
  }

  // 33. Update Workspace
  public async updateWorkspace(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'workspace.update', payload);
  }

  // 34. Create User
  public async createUser(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'user.create', payload);
  }

  // 35. Update User
  public async updateUser(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'user.update', payload);
  }

  // 36. Delete User
  public async deleteUser(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'user.delete', payload);
  }

  // 37. Create Role
  public async createRole(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'role.create', payload);
  }

  // 38. Update Role
  public async updateRole(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'role.update', payload);
  }

  // 39. Assign Role
  public async assignRole(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'role.assign', payload);
  }

  // 40. Request Governance Exception
  public async requestGovernanceException(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'governance.request_exception', payload);
  }

  // 41. Approve Governance Exception
  public async approveGovernanceException(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'governance.approve_exception', payload);
  }

  // 42. Rotate Key
  public async rotateKey(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'key.rotate', payload);
  }

  // 43. Enforce MFA
  public async enforceMfa(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'mfa.enforce', payload);
  }

  // 44. Install Plugin
  public async installPlugin(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'plugin.install', payload);
  }

  // 45. Create Connector
  public async createConnector(payload: Record<string, any>): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('admin', 'connector.create', payload);
  }

  // =========================================================================
  // Self-Service Account Commands & Queries
  // =========================================================================

  public async getCurrentAccount(): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('account', 'current.get', {});
  }

  public async updateSelfProfile(payload: { display_name?: string; name?: string; email?: string }): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('account', 'profile.update', payload);
  }

  public async updateSelfAvatar(avatarData: string): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('account', 'avatar.update', { avatar: avatarData });
  }

  public async removeSelfAvatar(): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('account', 'avatar.remove', {});
  }

  public async changeSelfPassword(currentPassword: string, newPassword: string): Promise<IPCResponse<any>> {
    return this.ipc.invoke<any>('account', 'password.change', {
      current_password: currentPassword,
      new_password: newPassword
    });
  }
}

// Backward compatibility alias for AdministrationIpcService
export type AdministrationIpcService = AdministrationIpc;
export const AdministrationIpcService = AdministrationIpc;
