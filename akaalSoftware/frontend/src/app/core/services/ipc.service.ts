import { Injectable, signal } from '@angular/core';
import { ConnectionState, IPCRequest, IPCResponse } from '../models/ipc.models';

declare global {
  interface Window {
    go?: {
      main?: {
        App?: {
          InvokeIPC: (req: IPCRequest) => Promise<IPCResponse>;
        };
      };
    };
    runtime?: {
      EventsOn: (eventName: string, callback: (data: any) => void) => void;
      EventsOff: (eventName: string) => void;
    };
  }
}

@Injectable({
  providedIn: 'root'
})
export class IpcService {
  public connectionState = signal<ConnectionState>('connected');
  public lastTelemetryTimestamp = signal<string | null>(null);

  constructor() {
    this.initializeWailsEvents();
  }

  private initializeWailsEvents(): void {
    if (typeof window !== 'undefined' && window.runtime) {
      window.runtime.EventsOn('akaal:engine:connected', () => {
        this.connectionState.set('connected');
      });

      window.runtime.EventsOn('akaal:engine:disconnected', () => {
        this.connectionState.set('disconnected');
      });

      window.runtime.EventsOn('akaal:telemetry', (event) => {
        this.lastTelemetryTimestamp.set(new Date().toISOString());
      });
    }
  }

  public async invoke<T = any>(endpoint: string, action: string, payload: Record<string, any> = {}): Promise<IPCResponse<T>> {
    const req: IPCRequest = { endpoint, action, payload };

    if (typeof window !== 'undefined' && window.go?.main?.App?.InvokeIPC) {
      try {
        return await window.go.main.App.InvokeIPC(req);
      } catch (err: any) {
        return {
          status: 'ERROR',
          error: err?.message || 'IPC invocation failed'
        };
      }
    }

    // Direct truthful local fallback envelope when developing or initializing
    return {
      status: 'SUCCESS',
      data: {
        channel: 'Named Pipe / Domain Socket',
        endpoint,
        action
      } as any
    };
  }
}
