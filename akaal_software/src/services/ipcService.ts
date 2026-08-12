/**
 * Raw Tauri IPC Invocation Service Wrapper
 */
import { invoke } from '@tauri-apps/api/core';
import type { WorkspaceConfig } from '../types/workspace';
import type {
  BootstrapStatus,
  AuthResponse,
  SessionInfo,
  UserDisplayInfo,
  AuthProviderInfo,
} from '../types/auth';
import type {
  BridgeStatusDTO,
  CapabilityDTO,
  HeartbeatStatusDTO,
} from '../types/bridge';

export const ipcService = {
  // Workspace Config (Sprint 2 & 3.1)
  async loadWorkspaceConfig(): Promise<WorkspaceConfig> {
    return await invoke<WorkspaceConfig>('load_workspace_config_cmd');
  },

  async saveWorkspaceConfig(config: WorkspaceConfig): Promise<WorkspaceConfig> {
    return await invoke<WorkspaceConfig>('save_workspace_config_cmd', { config });
  },

  async createBootstrapAdmin(
    config: WorkspaceConfig,
    adminFullName: string,
    adminUsername: string,
    adminPassword: string
  ): Promise<WorkspaceConfig> {
    return await invoke<WorkspaceConfig>('create_bootstrap_admin_cmd', {
      payload: {
        config,
        adminFullName,
        adminUsername,
        adminPassword,
      },
    });
  },

  async validateWorkspacePath(path: string): Promise<boolean> {
    return await invoke<boolean>('validate_workspace_path_cmd', { path });
  },

  // Security & Authentication (Sprint 3)
  async bootstrapApp(): Promise<BootstrapStatus> {
    return await invoke<BootstrapStatus>('bootstrap_app_cmd');
  },

  async authenticateUser(
    username: string,
    password: string,
    rememberDevice: boolean
  ): Promise<AuthResponse> {
    return await invoke<AuthResponse>('authenticate_user_cmd', {
      credentials: {
        username,
        password,
        rememberDevice,
      },
    });
  },

  async validateSession(sessionId: string): Promise<SessionInfo> {
    return await invoke<SessionInfo>('validate_session_cmd', { sessionId });
  },

  async logoutSession(sessionId: string): Promise<void> {
    return await invoke<void>('logout_session_cmd', { sessionId });
  },

  async lockSession(sessionId: string): Promise<void> {
    return await invoke<void>('lock_session_cmd', { sessionId });
  },

  async unlockSession(sessionId: string, password: string): Promise<SessionInfo> {
    return await invoke<SessionInfo>('unlock_session_cmd', { sessionId, password });
  },

  async getLastKnownUser(): Promise<UserDisplayInfo | null> {
    return await invoke<UserDisplayInfo | null>('get_last_known_user_cmd');
  },

  async getAuthProviders(): Promise<AuthProviderInfo[]> {
    return await invoke<AuthProviderInfo[]>('get_auth_providers_cmd');
  },

  // Engine Bridge Foundation (Sprint 5 Milestone 1)
  async getBridgeStatus(): Promise<BridgeStatusDTO> {
    return await invoke<BridgeStatusDTO>('get_bridge_status_cmd');
  },

  async startEngineDaemon(): Promise<BridgeStatusDTO> {
    return await invoke<BridgeStatusDTO>('start_engine_daemon_cmd');
  },

  async stopEngineDaemon(): Promise<BridgeStatusDTO> {
    return await invoke<BridgeStatusDTO>('stop_engine_daemon_cmd');
  },

  async invokeEngineCapability(capabilityId: string, payload: string): Promise<string> {
    try {
      return await invoke<string>('invoke_engine_capability_cmd', {
        capabilityId,
        payload,
      });
    } catch (err: any) {
      const errMsg = typeof err === 'string' ? err : (err?.message || String(err));
      console.warn(`IPC capability '${capabilityId}' failed:`, errMsg);
      throw new Error(errMsg);
    }
  },

  async listCapabilities(): Promise<CapabilityDTO[]> {
    return await invoke<CapabilityDTO[]>('list_capabilities_cmd');
  },

  async getHeartbeatStatus(): Promise<HeartbeatStatusDTO> {
    return await invoke<HeartbeatStatusDTO>('get_heartbeat_status_cmd');
  },
};
