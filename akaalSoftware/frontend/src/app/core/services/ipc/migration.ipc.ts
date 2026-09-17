import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class MigrationIpc {
  constructor(private ipc: IpcService) {}

  public async startMigration(projectId: string): Promise<IPCResponse> {
    return this.ipc.invoke('migration', 'start_job', { project_id: projectId });
  }

  public async getPipelineState(jobId: string): Promise<IPCResponse> {
    return this.ipc.invoke('migration', 'get_pipeline_state', { job_id: jobId });
  }
}
