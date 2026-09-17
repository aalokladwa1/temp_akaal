import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class AdministrationIpc {
  constructor(private ipc: IpcService) {}

  public async getRoles(): Promise<IPCResponse> {
    return this.ipc.invoke('administration', 'get_roles');
  }
}
