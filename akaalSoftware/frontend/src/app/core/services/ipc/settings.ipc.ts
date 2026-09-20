import { Injectable, inject } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

export interface SettingsConfigResponse {
  domain: string;
  settings: Record<string, any>;
  effectiveAt: string;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsIpc {
  private ipc: IpcService;

  constructor(ipcService?: IpcService) {
    try {
      this.ipc = ipcService || inject(IpcService);
    } catch {
      this.ipc = ipcService || new IpcService();
    }
  }

  public async getConfig(domain: string = 'all'): Promise<IPCResponse<Record<string, any>>> {
    return this.ipc.invoke<Record<string, any>>('settings', 'get', { domain });
  }

  public async updateConfig(domain: string, settings: Record<string, any>): Promise<IPCResponse<SettingsConfigResponse>> {
    return this.ipc.invoke<SettingsConfigResponse>('settings', 'update', { domain, settings });
  }

  public async resetConfig(domain: string): Promise<IPCResponse<SettingsConfigResponse>> {
    return this.ipc.invoke<SettingsConfigResponse>('settings', 'reset', { domain });
  }

}
