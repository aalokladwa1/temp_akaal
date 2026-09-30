/**
 * AKAAL Administration — 5.2 People & Access Reactive Signals Store
 */

import { Injectable, signal, computed, Optional, inject } from '@angular/core';
import { AdministrationIpcService } from '../../../core/services/ipc/administration.ipc';
import { IpcService } from '../../../core/services/ipc.service';
import {
  AdminUser,
  AdminTeam,
  AdminServiceAccount,
  AdminRole,
  AccessAssignment,
  ConditionalAccessRule,
  JitRequest,
  AccessConflictRecord,
  AdminSessionRecord,
  AccessReviewCampaign
} from '../models/people.models';

@Injectable({
  providedIn: 'root'
})
export class PeopleService {
  private adminIpc?: AdministrationIpcService;
  private ipc?: IpcService;

  constructor(
    @Optional() adminIpc?: AdministrationIpcService,
    @Optional() ipcService?: IpcService
  ) {
    if (adminIpc) {
      this.adminIpc = adminIpc;
    } else {
      try {
        this.adminIpc = inject(AdministrationIpcService, { optional: true }) || undefined;
      } catch {
        this.adminIpc = undefined;
      }
    }

    if (ipcService) {
      this.ipc = ipcService;
    } else {
      try {
        this.ipc = inject(IpcService, { optional: true }) || undefined;
      } catch {
        this.ipc = undefined;
      }
    }

    if (this.ipc && typeof this.ipc.subscribe === 'function') {
      this.ipc.subscribe('akaal:engine:connected', () => {
        this.loadFromBackend();
      });
      this.ipc.subscribe('akaal:governance:event', () => {
        this.loadFromBackend();
      });
    }

    this.loadFromBackend();
  }

  public async loadFromBackend(): Promise<void> {
    if (!this.adminIpc) return;
    try {
      const resp = await this.adminIpc.listUsers();
      if (resp.status === 'SUCCESS' && resp.data) {
        const users = Array.isArray(resp.data) ? resp.data : (resp.data.users || []);
        const loadedUsers: AdminUser[] = users.map((u: any) => {
          const uId = u.principal_id || u.id;
          return {
            id: uId,
            name: u.display_name || u.name || uId,
            email: u.email || `${uId}@akaaltech.corp`,
            title: u.title || 'Staff Engineer',
            department: u.department || 'Platform Engineering',
            type: u.type || 'EMPLOYEE',
            status: (u.is_active === 0 || u.status === 'SUSPENDED' ? 'DEACTIVATED' : 'ACTIVE') as any,
            primaryOrgId: u.tenant_id || u.primaryOrgId || 'org-primary',
            primaryOrgName: u.primaryOrgName || 'Primary Organization',
            assignedRolesCount: u.assignedRolesCount || 1,
            teamsCount: u.teamsCount || 1,
            lastActive: u.lastActive || 'Active now',
            mfaEnforced: u.mfaEnforced ?? true,
            createdAt: u.created_at || u.createdAt || new Date().toISOString()
          };
        });
        this.users.set(loadedUsers);
      }

      const roleResp = await this.adminIpc.listRoles();
      if (roleResp.status === 'SUCCESS' && roleResp.data) {
        const roles = Array.isArray(roleResp.data) ? roleResp.data : (roleResp.data.roles || []);
        const loadedRoles: AdminRole[] = roles.map((r: any) => {
          const rId = r.id || r.role_id;
          return {
            id: rId,
            name: r.name || r.role_name || rId,
            code: r.code || (rId ? rId.toUpperCase() : 'ROLE-CUSTOM'),
            description: r.description || '',
            domainScope: r.domainScope || 'WORKSPACE',
            isSystemRole: !!r.isBuiltIn,
            assignedPrincipalsCount: r.assignedCount || 0,
            permissionsCount: r.permissions?.length || 0,
            permissions: r.permissions || [],
            createdAt: r.createdAt || r.created_at || new Date().toISOString()
          };
        });
        this.roles.set(loadedRoles);
      }

      const teamResp = await this.adminIpc.listTeams();
      if (teamResp.status === 'SUCCESS' && teamResp.data) {
        const teams = Array.isArray(teamResp.data) ? teamResp.data : (teamResp.data.teams || []);
        const loadedTeams: AdminTeam[] = teams.map((t: any) => {
          const tId = t.id || t.team_id;
          return {
            id: tId,
            name: t.name || tId,
            code: t.code || 'TEAM-CUSTOM',
            description: t.description || '',
            leadOwnerName: t.leadOwnerName || t.owner || '',
            leadOwnerEmail: t.leadOwnerEmail || '',
            orgId: t.orgId || 'org-primary',
            orgName: t.orgName || 'Primary Organization',
            membersCount: t.membersCount || 1,
            assignedRolesCount: 1,
            status: 'ACTIVE',
            createdAt: t.createdAt || new Date().toISOString()
          };
        });
        this.teams.set(loadedTeams);
      }

      const saResp = await this.adminIpc.listServiceAccounts();
      if (saResp.status === 'SUCCESS' && saResp.data) {
        const saList = Array.isArray(saResp.data) ? saResp.data : (saResp.data.service_accounts || []);
        const loadedSa: AdminServiceAccount[] = saList.map((s: any) => ({
          id: s.id || s.token_id,
          name: s.name || 'Service Account',
          clientId: s.clientId || `akaal-sa-${s.token_prefix || 'token'}`,
          description: s.targetScope || 'API Service Account',
          targetScope: s.targetScope || 'Global Scope',
          ownerEmail: s.ownerEmail || 'ops@akaaltech.corp',
          assignedRolesCount: s.rolesCount || 1,
          status: s.status || 'ACTIVE',
          tokenExpiryDays: s.tokenExpiryDays || 90,
          createdAt: s.createdAt || new Date().toISOString(),
        }));
        this.serviceAccounts.set(loadedSa);
      }

      const jitResp = await this.adminIpc.listJitRequests();
      if (jitResp.status === 'SUCCESS' && jitResp.data) {
        const jitList = Array.isArray(jitResp.data) ? jitResp.data : (jitResp.data.requests || []);
        const loadedJit: JitRequest[] = jitList.map((j: any) => ({
          id: j.id,
          requesterName: j.requesterName || 'Akaal User',
          requesterEmail: j.requesterEmail || 'user@akaaltech.corp',
          targetRoleName: j.targetRoleName || 'Enterprise Platform Administrator',
          targetScopeName: j.targetScopeName || 'Global Corporate Root',
          durationHours: j.durationHours || 2,
          justification: j.justification || '',
          status: j.status || 'PENDING_APPROVAL',
          requestedAt: j.requestedAt || new Date().toISOString(),
          expiresAt: j.expiresAt,
        }));
        this.jitRequests.set(loadedJit);
      }

      const sessResp = await this.adminIpc.listAuditSessions();
      if (sessResp.status === 'SUCCESS' && sessResp.data) {
        const sessList = Array.isArray(sessResp.data) ? sessResp.data : (sessResp.data.sessions || []);
        const loadedSess: AdminSessionRecord[] = sessList.map((s: any) => ({
          id: s.id || s.session_id,
          principalName: s.principalName || s.principal_id || 'Active Principal',
          principalEmail: `${s.principalName || 'user'}@akaaltech.corp`,
          ipAddress: s.ipAddress || '127.0.0.1',
          deviceInfo: s.userAgent || 'Akaal Desktop Client',
          location: s.location || 'Local Session',
          startedAt: s.startedAt || s.issued_at || new Date().toISOString(),
          lastActivityAt: s.lastActive || s.last_activity_at || 'Just now',
          status: s.status || 'ACTIVE',
        }));
        this.sessions.set(loadedSess);
      }
    } catch {
      // Offline or fallback
    }
  }

  // 1. Users / Principals
  public users = signal<AdminUser[]>([]);

  // 2. Teams / Groups
  public teams = signal<AdminTeam[]>([]);

  // 3. Service Accounts
  public serviceAccounts = signal<AdminServiceAccount[]>([]);

  // 4. Roles & Permissions
  public roles = signal<AdminRole[]>([]);

  // 5. Access Assignments / RBAC
  public assignments = signal<AccessAssignment[]>([]);

  // 6. Conditional Access / ABAC
  public conditionalRules = signal<ConditionalAccessRule[]>([]);

  // 7. JIT Access
  public jitRequests = signal<JitRequest[]>([]);

  // 8. Access Conflicts / SoD Impact
  public accessConflicts = signal<AccessConflictRecord[]>([]);

  // 9. Sessions & Token Revocation
  public sessions = signal<AdminSessionRecord[]>([]);

  // 10. Access Reviews
  public accessReviews = signal<AccessReviewCampaign[]>([]);

  // ==========================================================================
  // MUTATION METHODS
  // ==========================================================================

  public createUser(data: Partial<AdminUser>): AdminUser {
    const newUser: AdminUser = {
      id: 'usr-' + Date.now().toString().slice(-6),
      name: data.name || '',
      email: data.email || '',
      title: data.title || '',
      department: data.department || 'Engineering',
      type: data.type || 'EMPLOYEE',
      status: data.status || 'ACTIVE',
      primaryOrgId: data.primaryOrgId || 'org-global-corp',
      primaryOrgName: data.primaryOrgName || 'Akaal Corporate Global',
      assignedRolesCount: 1,
      teamsCount: 1,
      lastActive: 'Just now',
      mfaEnforced: data.mfaEnforced ?? true,
      createdAt: new Date().toISOString()
    };
    this.users.update(list => [newUser, ...list]);
    if (this.adminIpc) {
      this.adminIpc.createUser({
        user_id: newUser.id,
        name: newUser.name,
        email: newUser.email,
        role: 'MEMBER',
      }).catch(() => {});
    }
    return newUser;
  }

  public updateUser(id: string, updates: Partial<AdminUser>): void {
    this.users.update(list => list.map(u => u.id === id ? { ...u, ...updates } : u));
    if (this.adminIpc) {
      this.adminIpc.updateUser({
        user_id: id,
        name: updates.name,
        status: updates.status,
      }).catch(() => {});
    }
  }

  public deleteUser(id: string): void {
    const prev = this.users();
    this.users.update(list => list.filter(u => u.id !== id));
    if (this.adminIpc) {
      this.adminIpc.deleteUser({ user_id: id }).then(res => {
        if (res && res.status !== 'SUCCESS') {
          this.users.set(prev);
        }
      }).catch(() => {
        this.users.set(prev);
      });
    }
  }

  public createTeam(data: Partial<AdminTeam>): AdminTeam {
    const newTeam: AdminTeam = {
      id: 'team-' + Date.now().toString().slice(-6),
      name: data.name || '',
      code: data.code || 'TEAM-NEW',
      description: data.description || '',
      leadOwnerName: data.leadOwnerName || '',
      leadOwnerEmail: data.leadOwnerEmail || '',
      orgId: data.orgId || 'org-global-corp',
      orgName: data.orgName || 'Akaal Corporate Global',
      membersCount: 1,
      assignedRolesCount: 1,
      status: 'ACTIVE',
      createdAt: new Date().toISOString()
    };
    this.teams.update(list => [newTeam, ...list]);
    return newTeam;
  }

  public updateTeam(id: string, updates: Partial<AdminTeam>): void {
    this.teams.update(list => list.map(t => t.id === id ? { ...t, ...updates } : t));
  }

  public updateServiceAccount(id: string, updates: Partial<AdminServiceAccount>): void {
    this.serviceAccounts.update(list => list.map(s => s.id === id ? { ...s, ...updates } : s));
  }

  public createServiceAccount(data: Partial<AdminServiceAccount>): AdminServiceAccount {
    const newSa: AdminServiceAccount = {
      id: 'sa-' + Date.now().toString().slice(-6),
      name: data.name || '',
      clientId: 'akaal-sa-' + (data.name?.toLowerCase().replace(/\s+/g, '-') || 'agent'),
      description: data.description || '',
      targetScope: data.targetScope || 'Global Scope',
      ownerEmail: data.ownerEmail || 'admin@akaaltech.corp',
      assignedRolesCount: 1,
      status: 'ACTIVE',
      tokenExpiryDays: data.tokenExpiryDays || 90,
      createdAt: new Date().toISOString()
    };
    this.serviceAccounts.update(list => [newSa, ...list]);
    return newSa;
  }

  public createRole(data: Partial<AdminRole>): AdminRole {
    const newRole: AdminRole = {
      id: 'role-' + Date.now().toString().slice(-6),
      name: data.name || '',
      code: data.code || 'ROLE-CUSTOM',
      description: data.description || '',
      domainScope: data.domainScope || 'WORKSPACE',
      isSystemRole: false,
      assignedPrincipalsCount: 0,
      permissionsCount: data.permissions?.length || 4,
      permissions: data.permissions || ['PIPELINE_READ', 'VALIDATION_READ'],
      createdAt: new Date().toISOString()
    };
    this.roles.update(list => [newRole, ...list]);
    if (this.adminIpc) {
      this.adminIpc.createRole({
        role_id: newRole.id,
        role_name: newRole.name,
        permissions: newRole.permissions,
      }).catch(() => {});
    }
    return newRole;
  }

  public updateRole(id: string, updates: Partial<AdminRole>): void {
    this.roles.update(list => list.map(r => r.id === id ? { ...r, ...updates } : r));
    if (this.adminIpc) {
      this.adminIpc.updateRole({
        role_id: id,
        permissions: updates.permissions || [],
      }).catch(() => {});
    }
  }

  public assignAccess(data: Partial<AccessAssignment>): AccessAssignment {
    const newAsg: AccessAssignment = {
      id: 'asg-' + Date.now().toString().slice(-6),
      principalId: data.principalId || 'usr-aalok-01',
      principalName: data.principalName || 'Aalok Ladwa',
      principalType: data.principalType || 'USER',
      roleId: data.roleId || 'role-migration-architect',
      roleName: data.roleName || 'Migration Initiative Architect',
      scopeType: data.scopeType || 'GLOBAL',
      scopeName: data.scopeName || 'Global Root',
      assignedBy: 'Platform Admin',
      assignedAt: new Date().toISOString(),
      status: 'ACTIVE'
    };
    this.assignments.update(list => [newAsg, ...list]);
    if (this.adminIpc) {
      this.adminIpc.assignRole({
        user_id: newAsg.principalId,
        role_name: newAsg.roleId,
      }).catch(() => {});
    }
    return newAsg;
  }

  public createConditionalRule(data: Partial<ConditionalAccessRule>): ConditionalAccessRule {
    const newRule: ConditionalAccessRule = {
      id: 'ca-' + Date.now().toString().slice(-6),
      name: data.name || '',
      description: data.description || '',
      targetRole: data.targetRole || 'ROLE-PLATFORM-ADMIN',
      enforcementMode: data.enforcementMode || 'STRICT_ENFORCED',
      ipAllowlistRequired: data.ipAllowlistRequired ?? true,
      mfaStepUpRequired: data.mfaStepUpRequired ?? true,
      timeWindowRestriction: data.timeWindowRestriction || 'All Times',
      boundPrincipalsCount: 1,
      createdAt: new Date().toISOString()
    };
    this.conditionalRules.update(list => [newRule, ...list]);
    return newRule;
  }

  public updateConditionalRule(id: string, updates: Partial<ConditionalAccessRule>): void {
    this.conditionalRules.update(list => list.map(r => r.id === id ? { ...r, ...updates } : r));
  }

  public requestJit(data: Partial<JitRequest>): JitRequest {
    const newReq: JitRequest = {
      id: 'jit-req-' + Date.now().toString().slice(-4),
      requesterName: data.requesterName || 'Akaal User',
      requesterEmail: data.requesterEmail || 'user@akaaltech.corp',
      targetRoleName: data.targetRoleName || 'Enterprise Platform Administrator',
      targetScopeName: data.targetScopeName || 'Global Corporate Root',
      durationHours: data.durationHours || 2,
      justification: data.justification || '',
      status: 'PENDING_APPROVAL',
      requestedAt: new Date().toISOString()
    };
    this.jitRequests.update(list => [newReq, ...list]);
    if (this.adminIpc) {
      this.adminIpc.requestJitElevation({
        requester_id: data.requesterEmail || 'user-admin',
        target_role_id: data.targetRoleName,
        target_scope: data.targetScopeName,
        duration_hours: data.durationHours || 2,
        justification: data.justification || '',
      }).then(res => {
        if (res && res.status === 'SUCCESS' && res.data?.approval_id) {
          this.jitRequests.update(list =>
            list.map(j => j.id === newReq.id ? { ...j, id: res.data.approval_id } : j)
          );
        }
      }).catch(() => {});
    }
    return newReq;
  }

  public approveJit(requestId: string, decision: 'APPROVED' | 'REJECTED' = 'APPROVED'): void {
    this.jitRequests.update(list =>
      list.map(j => j.id === requestId ? { ...j, status: decision === 'APPROVED' ? 'ACTIVE_ELEVATED' : 'REJECTED' } : j)
    );
    if (this.adminIpc) {
      this.adminIpc.approveJitElevation({
        request_id: requestId,
        decision: decision,
      }).catch(() => {});
    }
  }

  public terminateSession(sessionId: string): void {
    this.sessions.update(list => list.map(s => s.id === sessionId ? { ...s, status: 'TERMINATED' } : s));
  }

  public createAccessReview(data: Partial<AccessReviewCampaign>): AccessReviewCampaign {
    const newRev: AccessReviewCampaign = {
      id: 'rev-' + Date.now().toString().slice(-6),
      name: data.name || '',
      scopeType: data.scopeType || 'ROLE_TIER',
      scopeName: data.scopeName || 'Privileged Roles',
      reviewerName: data.reviewerName || 'Aalok Ladwa',
      reviewerEmail: data.reviewerEmail || 'aalok.ladwa@akaaltech.internal',
      totalEntitlements: data.totalEntitlements || 10,
      reviewedEntitlements: 0,
      status: 'IN_PROGRESS',
      deadline: data.deadline || '2026-06-30T23:59:59Z',
      createdAt: new Date().toISOString()
    };
    this.accessReviews.update(list => [newRev, ...list]);
    return newRev;
  }
}
