import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class MonitoringIpc {
  constructor(private ipc: IpcService) {}

  public async getStreamMetrics(): Promise<IPCResponse> {
    return this.ipc.invoke('monitoring', 'stream_metrics');
  }
}
