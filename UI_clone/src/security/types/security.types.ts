/**
 * AKAAL Enterprise Identity & Security Types & Models
 */

export type AuthProviderType = 'oidc' | 'saml' | 'ldap' | 'okta' | 'azure_ad' | 'google_workspace';

export interface UserIdentity {
  id: string;
  email: string;
  fullName: string;
  provider: AuthProviderType;
  providerId: string;
  organizationId: string;
  tenantId: string;
  projectIds: string[];
  roles: string[];
  attributes: Record<string, any>;
  mfaEnabled: boolean;
  lastLoginAt: string;
}

export interface Permission {
  id: string;
  resource: string; // e.g. 'migration', 'database', 'system_setting'
  action: 'create' | 'read' | 'update' | 'delete' | 'execute' | 'approve' | 'admin';
  tenantScope?: string;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  parentRoleIds?: string[];
}

export interface SessionContext {
  sessionId: string;
  userId: string;
  email: string;
  tenantId: string;
  organizationId: string;
  deviceId: string;
  userAgent: string;
  ipAddress: string;
  createdAt: string;
  lastActiveAt: string;
  expiresAt: string;
  isRevoked: boolean;
}

export interface AuthToken {
  accessToken: string;
  refreshToken: string;
  tokenType: 'Bearer';
  expiresIn: number;
  scope: string;
}

export interface SecurityContextState {
  user: UserIdentity | null;
  session: SessionContext | null;
  correlationId: string;
  auditId: string;
  permissions: Set<string>;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  eventType: 'AUTH_SUCCESS' | 'AUTH_FAILURE' | 'LOGOUT' | 'SESSION_REVOKED' | 'PERMISSION_DENIED' | 'ROLE_CHANGED' | 'CONFIG_MODIFIED';
  userId: string;
  userEmail: string;
  tenantId: string;
  ipAddress: string;
  userAgent: string;
  resource: string;
  action: string;
  status: 'SUCCESS' | 'FAILURE';
  details: Record<string, any>;
}
