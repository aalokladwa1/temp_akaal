/**
 * AKAAL Enterprise Identity & Security Types
 */

export type UserRole =
  | 'SuperAdministrator'
  | 'Administrator'
  | 'MigrationEngineer'
  | 'Auditor'
  | 'ReadOnly'
  | 'SupportEngineer';

export interface SessionInfo {
  sessionId: string;
  userId: string;
  username: string;
  displayName: string;
  role: UserRole;
  createdAt: number;
  lastAccessedAt: number;
  expiresAt: number;
  isLocked: boolean;
  rememberDevice: boolean;
}

export interface AuthResponse {
  session: SessionInfo;
  message: string;
}

export interface UserDisplayInfo {
  username: string;
  displayName: string;
  avatarInitials: string;
}

export interface AuthProviderInfo {
  id: string;
  name: string;
  providerType: string;
  supportsMfa: boolean;
  supportsPasswordReset: boolean;
  supportsRememberDevice: boolean;
  supportsAutoLogin: boolean;
  supportsSso: boolean;
  supportsOfflineLogin: boolean;
  isSelectable: boolean;
  statusBadge?: string;
}

export interface BootstrapStatus {
  isWorkspaceConfigured: boolean;
  isIntegrityOk: boolean;
  activeSession: SessionInfo | null;
  lastUsername: string | null;
  lastDisplayName: string | null;
  errorMessage: string | null;
}
