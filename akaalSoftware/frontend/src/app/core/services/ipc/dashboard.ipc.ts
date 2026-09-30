import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';
import { DashboardSummary } from '../../models/dashboard.models';

@Injectable({
  providedIn: 'root'
})
export class DashboardIpc {
  constructor(private ipc: IpcService) {}

  public async getEstateSummary(): Promise<IPCResponse<DashboardSummary>> {
    return this.ipc.invoke<DashboardSummary>('estate', 'get_summary');
  }

  public async getSummary(): Promise<IPCResponse<DashboardSummary>> {
    return this.getEstateSummary();
  }

  public subscribeTelemetry(handler: (payload: any) => void): () => void {
    return this.ipc.subscribe('akaal:telemetry', handler);
  }
}

// Backward compatibility alias for DashboardIpcService
export type DashboardIpcService = DashboardIpc;
export const DashboardIpcService = DashboardIpc;

