/**
 * Raw Tauri IPC Invocation Service Wrapper
 */
import { invoke } from '@tauri-apps/api/core';
import type { WorkspaceConfig } from '../types/workspace';

export const ipcService = {
  async loadWorkspaceConfig(): Promise<WorkspaceConfig> {
    return await invoke<WorkspaceConfig>('load_workspace_config_cmd');
  },

  async saveWorkspaceConfig(config: WorkspaceConfig): Promise<WorkspaceConfig> {
    return await invoke<WorkspaceConfig>('save_workspace_config_cmd', { config });
  },

  async validateWorkspacePath(path: string): Promise<boolean> {
    return await invoke<boolean>('validate_workspace_path_cmd', { path });
  },
};
