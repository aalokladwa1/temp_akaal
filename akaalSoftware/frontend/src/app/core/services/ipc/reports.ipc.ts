import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class ReportsIpc {
  constructor(private ipc: IpcService) {}

  public async generateDossier(projectId: string): Promise<IPCResponse> {
    return this.ipc.invoke('reports', 'generate_dossier', { project_id: projectId });
  }
}
