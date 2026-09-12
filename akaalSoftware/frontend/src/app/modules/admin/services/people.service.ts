/**
 * AKAAL Administration — 5.2 People & Access Reactive Signals Store
 */

import { Injectable, signal, computed } from '@angular/core';
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
  // 1. Users / Principals
  public users = signal<AdminUser[]>([
    {
      id: 'usr-aalok-01',
      name: 'Aalok Ladwa',
      email: 'aalok.ladwa@akaaltech.internal',
      title: 'Principal Lead Architect',
      department: 'Platform Architecture & Core Infrastructure',
      type: 'EMPLOYEE',
      status: 'ACTIVE',
      primaryOrgId: 'org-global-corp',
      primaryOrgName: 'Akaal Corporate Global',
      assignedRolesCount: 3,
      teamsCount: 2,
      lastActive: 'Active now',
      mfaEnforced: true,
      createdAt: '2026-01-01T00:00:00Z'
    },
    {
      id: 'usr-sarah-02',
      name: 'Sarah Jenkins',
      email: 's.jenkins@akaaltech.corp',
      title: 'Staff Security Engineer',
      department: 'Information Security & Compliance',
      type: 'EMPLOYEE',
      status: 'ACTIVE',
      primaryOrgId: 'org-global-corp',
      primaryOrgName: 'Akaal Corporate Global',
      assignedRolesCount: 2,
      teamsCount: 1,
      lastActive: '12m ago',
      mfaEnforced: true,
      createdAt: '2026-01-15T00:00:00Z'
    },
    {
      id: 'usr-devon-03',
      name: 'Devon Vance',
      email: 'd.vance@akaaltech.corp',
      title: 'Senior Database Migration Specialist',
      department: 'Data Engineering & Replications',
      type: 'CONTRACTOR',
      status: 'ACTIVE',
      primaryOrgId: 'org-global-corp',
      primaryOrgName: 'Akaal Corporate Global',
      assignedRolesCount: 1,
      teamsCount: 1,
      lastActive: '1h ago',
      mfaEnforced: true,
      createdAt: '2026-02-01T00:00:00Z'
    }
  ]);

  // 2. Teams / Groups
  public teams = signal<AdminTeam[]>([
    {
      id: 'team-infra-core',
      name: 'Infrastructure Platform Engineering',
      code: 'TEAM-INFRA-CORE',
      description: 'Engineers responsible for global replication clusters, network isolation perimeters, and HSM vault operations.',
      leadOwnerName: 'Aalok Ladwa',
      leadOwnerEmail: 'aalok.ladwa@akaaltech.internal',
      orgId: 'org-global-corp',
      orgName: 'Akaal Corporate Global',
      membersCount: 8,
      assignedRolesCount: 2,
      status: 'ACTIVE',
      createdAt: '2026-01-05T00:00:00Z'
    },
    {
      id: 'team-secops',
      name: 'Security Operations & Governance',
      code: 'TEAM-SECOPS-GOV',
      description: 'Custodian team overseeing SOC2 baseline enforcement, cryptographic key governance, and break-glass escrow.',
      leadOwnerName: 'Sarah Jenkins',
      leadOwnerEmail: 's.jenkins@akaaltech.corp',
      orgId: 'org-global-corp',
      orgName: 'Akaal Corporate Global',
      membersCount: 5,
      assignedRolesCount: 3,
      status: 'ACTIVE',
      createdAt: '2026-01-10T00:00:00Z'
    }
  ]);

  // 3. Service Accounts
  public serviceAccounts = signal<AdminServiceAccount[]>([
    {
      id: 'sa-pipeline-engine',
      name: 'Migration Pipeline Execution Agent',
      clientId: 'akaal-sa-pipe-core-889',
      description: 'Automated machine identity used by Wails IPC backend daemon to coordinate streaming CDC synchronization.',
      targetScope: 'All Workspaces (Global)',
      ownerEmail: 'aalok.ladwa@akaaltech.internal',
      assignedRolesCount: 2,
      status: 'ACTIVE',
      tokenExpiryDays: 90,
      createdAt: '2026-01-01T00:00:00Z'
    },
    {
      id: 'sa-audit-harvester',
      name: 'Compliance Evidence Harvester',
      clientId: 'akaal-sa-audit-harvester-102',
      description: 'Read-only administrative crawler generating immutability attestations and cryptographic receipts.',
      targetScope: 'Enterprise Root',
      ownerEmail: 's.jenkins@akaaltech.corp',
      assignedRolesCount: 1,
      status: 'ACTIVE',
      tokenExpiryDays: 180,
      createdAt: '2026-02-10T00:00:00Z'
    }
  ]);

  // 4. Roles & Permissions
  public roles = signal<AdminRole[]>([
    {
      id: 'role-super-admin',
      name: 'Enterprise Platform Administrator',
      code: 'ROLE-PLATFORM-ADMIN',
      description: 'Full administrative authority across tenancy hierarchy, security baseline, and privileged operations.',
      domainScope: 'GLOBAL',
      isSystemRole: true,
      assignedPrincipalsCount: 2,
      permissionsCount: 28,
      permissions: ['TENANT_MANAGE', 'ORGS_MANAGE', 'WORKSPACES_MANAGE', 'RBAC_WRITE', 'GOVERNANCE_EXECUTE', 'BREAK_GLASS_ESCROW'],
      createdAt: '2026-01-01T00:00:00Z'
    },
    {
      id: 'role-migration-architect',
      name: 'Migration Initiative Architect',
      code: 'ROLE-MIGRATION-ARCHITECT',
      description: 'Authority to create migration initiatives, define schema transforms, and orchestrate validation cutover.',
      domainScope: 'WORKSPACE',
      isSystemRole: false,
      assignedPrincipalsCount: 4,
      permissionsCount: 16,
      permissions: ['INITIATIVE_CREATE', 'PIPELINE_EXECUTE', 'VALIDATION_VERIFY', 'SCHEMA_MAP_WRITE'],
      createdAt: '2026-01-12T00:00:00Z'
    },
    {
      id: 'role-compliance-auditor',
      name: 'Compliance & Assurance Auditor',
      code: 'ROLE-COMPLIANCE-AUDITOR',
      description: 'Read-only access to audit logs, cryptographic receipts, report library, and historical evidence packages.',
      domainScope: 'GLOBAL',
      isSystemRole: true,
      assignedPrincipalsCount: 3,
      permissionsCount: 8,
      permissions: ['AUDIT_READ', 'REPORTS_EXPORT', 'RECEIPTS_VERIFY', 'SOD_READ'],
      createdAt: '2026-01-15T00:00:00Z'
    }
  ]);

  // 5. Access Assignments / RBAC
  public assignments = signal<AccessAssignment[]>([
    {
      id: 'asg-01',
      principalId: 'usr-aalok-01',
      principalName: 'Aalok Ladwa',
      principalType: 'USER',
      roleId: 'role-super-admin',
      roleName: 'Enterprise Platform Administrator',
      scopeType: 'GLOBAL',
      scopeName: 'Global Corporate Root',
      assignedBy: 'system.bootstrap@akaaltech.internal',
      assignedAt: '2026-01-01T00:00:00Z',
      status: 'ACTIVE'
    },
    {
      id: 'asg-02',
      principalId: 'team-infra-core',
      principalName: 'Infrastructure Platform Engineering',
      principalType: 'TEAM',
      roleId: 'role-migration-architect',
      roleName: 'Migration Initiative Architect',
      scopeType: 'WORKSPACE',
      scopeName: 'Core Banking Modernization',
      assignedBy: 'aalok.ladwa@akaaltech.internal',
      assignedAt: '2026-01-10T00:00:00Z',
      status: 'ACTIVE'
    }
  ]);

  // 6. Conditional Access / ABAC
  public conditionalRules = signal<ConditionalAccessRule[]>([
    {
      id: 'ca-prod-mfa',
      name: 'Production Environment Step-Up Authentication',
      description: 'Requires hardware-bound FIDO2 step-up verification and corporate IP allowlist for production cluster deployments.',
      targetRole: 'ROLE-PLATFORM-ADMIN',
      enforcementMode: 'STRICT_ENFORCED',
      ipAllowlistRequired: true,
      mfaStepUpRequired: true,
      timeWindowRestriction: '24/7 Monitored',
      boundPrincipalsCount: 2,
      createdAt: '2026-01-05T00:00:00Z'
    },
    {
      id: 'ca-hsm-time-window',
      name: 'HSM Cryptographic Key Rotation Window',
      description: 'Limits KMS master key operations strictly to declared Sunday maintenance window.',
      targetRole: 'ROLE-PLATFORM-ADMIN',
      enforcementMode: 'STRICT_ENFORCED',
      ipAllowlistRequired: true,
      mfaStepUpRequired: true,
      timeWindowRestriction: 'Sundays 02:00 - 06:00 UTC',
      boundPrincipalsCount: 1,
      createdAt: '2026-01-20T00:00:00Z'
    }
  ]);

  // 7. JIT Access
  public jitRequests = signal<JitRequest[]>([
    {
      id: 'jit-req-101',
      requesterName: 'Devon Vance',
      requesterEmail: 'd.vance@akaaltech.corp',
      targetRoleName: 'Enterprise Platform Administrator',
      targetScopeName: 'Core Banking Modernization',
      durationHours: 4,
      justification: 'Emergency index optimization and vacuum triage on high-throughput shard cluster 04.',
      status: 'PENDING_APPROVAL',
      requestedAt: '2026-03-10T14:30:00Z'
    },
    {
      id: 'jit-req-100',
      requesterName: 'Sarah Jenkins',
      requesterEmail: 's.jenkins@akaaltech.corp',
      targetRoleName: 'Enterprise Platform Administrator',
      targetScopeName: 'Global Corporate Root',
      durationHours: 2,
      justification: 'Quarterly SOC2 cryptographic escrow verification drill.',
      status: 'EXPIRED',
      requestedAt: '2026-02-15T09:00:00Z',
      expiresAt: '2026-02-15T11:00:00Z'
    }
  ]);

  // 8. Access Conflicts / SoD Impact
  public accessConflicts = signal<AccessConflictRecord[]>([
    {
      id: 'conf-01',
      ruleCode: 'SOD-DEV-PROD-SEPARATION',
      ruleDescription: 'Principals holding Migration Execution permissions in Production cannot hold direct Schema Mapping write access.',
      principalName: 'Devon Vance',
      principalEmail: 'd.vance@akaaltech.corp',
      conflictingRoleA: 'Migration Initiative Architect',
      conflictingRoleB: 'Core Production Operator',
      scopeName: 'Core Banking Modernization',
      detectedAt: '2026-03-01T11:20:00Z',
      resolutionStatus: 'UNRESOLVED'
    }
  ]);

  // 9. Sessions & Token Revocation
  public sessions = signal<AdminSessionRecord[]>([
    {
      id: 'sess-8891',
      principalName: 'Aalok Ladwa',
      principalEmail: 'aalok.ladwa@akaaltech.internal',
      ipAddress: '10.240.12.84 (Corporate VPN)',
      deviceInfo: 'Windows 11 Workstation (Hardware TPM 2.0)',
      location: 'London, United Kingdom',
      startedAt: '2026-03-11T18:00:00Z',
      lastActivityAt: 'Just now',
      status: 'ACTIVE'
    },
    {
      id: 'sess-8840',
      principalName: 'Sarah Jenkins',
      principalEmail: 's.jenkins@akaaltech.corp',
      ipAddress: '10.240.14.19 (Corporate VPN)',
      deviceInfo: 'macOS Sonoma Enterprise Profile',
      location: 'New York, United States',
      startedAt: '2026-03-11T17:15:00Z',
      lastActivityAt: '12m ago',
      status: 'ACTIVE'
    }
  ]);

  // 10. Access Reviews
  public accessReviews = signal<AccessReviewCampaign[]>([
    {
      id: 'rev-q1-2026',
      name: 'Q1 2026 Privilege Recertification',
      scopeType: 'ROLE_TIER',
      scopeName: 'All Elevated Administrative Roles',
      reviewerName: 'Aalok Ladwa',
      reviewerEmail: 'aalok.ladwa@akaaltech.internal',
      totalEntitlements: 14,
      reviewedEntitlements: 12,
      status: 'IN_PROGRESS',
      deadline: '2026-03-31T23:59:59Z',
      createdAt: '2026-03-01T00:00:00Z'
    }
  ]);

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
    return newUser;
  }

  public updateUser(id: string, updates: Partial<AdminUser>): void {
    this.users.update(list => list.map(u => u.id === id ? { ...u, ...updates } : u));
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
    return newRole;
  }

  public updateRole(id: string, updates: Partial<AdminRole>): void {
    this.roles.update(list => list.map(r => r.id === id ? { ...r, ...updates } : r));
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
      requesterName: data.requesterName || 'Aalok Ladwa',
      requesterEmail: data.requesterEmail || 'aalok.ladwa@akaaltech.internal',
      targetRoleName: data.targetRoleName || 'Enterprise Platform Administrator',
      targetScopeName: data.targetScopeName || 'Global Corporate Root',
      durationHours: data.durationHours || 2,
      justification: data.justification || '',
      status: 'PENDING_APPROVAL',
      requestedAt: new Date().toISOString()
    };
    this.jitRequests.update(list => [newReq, ...list]);
    return newReq;
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
