import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class SettingsIpc {
  constructor(private ipc: IpcService) {}

  public async getConfig(): Promise<IPCResponse> {
    return this.ipc.invoke('settings', 'get_config');
  }
}
