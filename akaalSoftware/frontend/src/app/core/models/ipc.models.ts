export interface IPCRequest {
  endpoint: string;
  action: string;
  payload: Record<string, any>;
}

export interface IPCResponse<T = any> {
  status: 'SUCCESS' | 'ERROR' | 'PENDING';
  data?: T;
  error?: string;
}

export interface TelemetryEvent {
  topic: string;
  timestamp: string;
  source: string;
  payload: Record<string, any>;
}

export type ConnectionState = 'connected' | 'connecting' | 'disconnected';
