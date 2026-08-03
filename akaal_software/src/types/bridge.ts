/**
 * AKAAL Engine Bridge DTO Interfaces
 */

export type BridgeState =
  | 'disconnected'
  | 'starting'
  | 'connected'
  | 'reconnecting'
  | 'stopping'
  | 'stopped'
  | 'error';

export interface BridgeStatusDTO {
  state: BridgeState;
  enginePid?: number;
  activeSessionId?: string;
  transportType: string;
  heartbeatOk: boolean;
  uptimeSeconds: number;
  registeredCapabilitiesCount: number;
}

export interface CapabilityDTO {
  id: string;
  name: string;
  category: string;
  description: string;
  version: string;
  isAvailable: boolean;
}

export interface HeartbeatStatusDTO {
  isHealthy: boolean;
  lastPulseTimestamp: number;
  missedPulses: number;
  latencyMs: number;
  reconnectActive: boolean;
}
