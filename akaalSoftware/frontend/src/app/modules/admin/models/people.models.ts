/**
 * AKAAL Administration — 5.2 People & Access Domain Models
 */

export type PrincipalType = 'EMPLOYEE' | 'CONTRACTOR' | 'SYSTEM_OPERATOR' | 'EXTERNAL_AUDITOR';
export type PrincipalStatus = 'ACTIVE' | 'SUSPENDED' | 'PROVISIONING' | 'DEPROVISIONED';

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  title: string;
  department: string;
  type: PrincipalType;
  status: PrincipalStatus;
  primaryOrgId: string;
  primaryOrgName: string;
  assignedRolesCount: number;
  teamsCount: number;
  lastActive: string;
  mfaEnforced: boolean;
  createdAt: string;
}

export interface AdminTeam {
  id: string;
  name: string;
  code: string;
  description: string;
  leadOwnerName: string;
  leadOwnerEmail: string;
  orgId: string;
  orgName: string;
  membersCount: number;
  assignedRolesCount: number;
  status: 'ACTIVE' | 'ARCHIVED';
  createdAt: string;
}

export interface AdminServiceAccount {
  id: string;
  name: string;
  clientId: string;
  description: string;
  targetScope: string;
  ownerEmail: string;
  assignedRolesCount: number;
  status: 'ACTIVE' | 'ROTATING' | 'REVOKED';
  tokenExpiryDays: number;
  createdAt: string;
}

export interface AdminRole {
  id: string;
  name: string;
  code: string;
  description: string;
  domainScope: 'GLOBAL' | 'ORGANIZATION' | 'WORKSPACE' | 'PIPELINE';
  isSystemRole: boolean;
  assignedPrincipalsCount: number;
  permissionsCount: number;
  permissions: string[];
  createdAt: string;
}

export interface AccessAssignment {
  id: string;
  principalId: string;
  principalName: string;
  principalType: 'USER' | 'TEAM' | 'SERVICE_ACCOUNT';
  roleId: string;
  roleName: string;
  scopeType: 'GLOBAL' | 'ORGANIZATION' | 'WORKSPACE';
  scopeName: string;
  assignedBy: string;
  assignedAt: string;
  status: 'ACTIVE' | 'EXPIRED' | 'REVOKED';
}

export interface ConditionalAccessRule {
  id: string;
  name: string;
  description: string;
  targetRole: string;
  enforcementMode: 'STRICT_ENFORCED' | 'AUDIT_LOG_ONLY' | 'DISABLED';
  ipAllowlistRequired: boolean;
  mfaStepUpRequired: boolean;
  timeWindowRestriction?: string;
  boundPrincipalsCount: number;
  createdAt: string;
}

export interface JitRequest {
  id: string;
  requesterName: string;
  requesterEmail: string;
  targetRoleName: string;
  targetScopeName: string;
  durationHours: number;
  justification: string;
  status: 'PENDING_APPROVAL' | 'ACTIVE_ELEVATED' | 'EXPIRED' | 'REJECTED';
  requestedAt: string;
  expiresAt?: string;
}

export interface AccessConflictRecord {
  id: string;
  ruleCode: string;
  ruleDescription: string;
  principalName: string;
  principalEmail: string;
  conflictingRoleA: string;
  conflictingRoleB: string;
  scopeName: string;
  detectedAt: string;
  resolutionStatus: 'UNRESOLVED' | 'WAIVER_ACTIVE' | 'RESOLVED';
}

export interface AdminSessionRecord {
  id: string;
  principalName: string;
  principalEmail: string;
  ipAddress: string;
  deviceInfo: string;
  location: string;
  startedAt: string;
  lastActivityAt: string;
  status: 'ACTIVE' | 'TERMINATED' | 'EXPIRED';
}

export interface AccessReviewCampaign {
  id: string;
  name: string;
  scopeType: 'ORGANIZATION' | 'WORKSPACE' | 'ROLE_TIER';
  scopeName: string;
  reviewerName: string;
  reviewerEmail: string;
  totalEntitlements: number;
  reviewedEntitlements: number;
  status: 'IN_PROGRESS' | 'COMPLETED' | 'SCHEDULED';
  deadline: string;
  createdAt: string;
}
