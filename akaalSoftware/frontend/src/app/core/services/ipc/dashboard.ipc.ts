import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class DashboardIpc {
  constructor(private ipc: IpcService) {}

  public async getSummary(): Promise<IPCResponse> {
    return this.ipc.invoke('dashboard', 'get_summary');
  }
}
