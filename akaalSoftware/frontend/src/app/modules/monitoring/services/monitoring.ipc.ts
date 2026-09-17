/**
 * monitoring.ipc.ts
 * ===================
 * Thin Monitoring IPC adapter. Wraps the existing generic `IpcService.invoke`
 * (read-only boundary for this campaign -- see ipc.service.ts) with typed
 * request/response members for the Monitoring capabilities that have a
 * proven, field-verified canonical backend authority reachable through
 * akaalIPC's router (akaalIPC/application/router.py ->
 * akaalPipeline/application/unified_caller.py PipelineUnifiedCaller).
 *
 * Every request_type below (`incident.*`, `alert.*`, `fleet.status`) is
 * already registered in akaalIPC/protocol/schemas.py and already dispatched
 * in PipelineUnifiedCaller.handle_command/handle_query -- this adapter adds
 * no new backend capability, it only exposes what already exists.
 *
 * This file owns no canonical state, performs no authorization, and never
 * fabricates success -- every method returns the real IPCResponse envelope
 * (SUCCESS/ERROR) for the caller to interpret; callers must fail closed on
 * ERROR/disconnected rather than substitute local fixture data.
 */

import { Injectable, inject } from '@angular/core';
import { IpcService } from '../../../core/services/ipc.service';
import type { IPCResponse } from '../../../core/models/ipc.models';

// ---------------------------------------------------------------------------
// Typed DTOs -- field names verified against real IncidentRecord.to_dict() /
// AlertRecord (akaalPipeline/operations/incidents.py, alerts.py) and the
// real fleet.status response (akaalPipeline/fleet/fleet_service.py
// NodeOperationalSnapshot), observed directly via akaalIPC/transport/
// tcp_socket_host.py dispatch during Stage 2 integration testing.
// ---------------------------------------------------------------------------

export type IncidentSeverity = 'SEV1' | 'SEV2' | 'SEV3' | 'SEV4' | 'SEV5';
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'MITIGATED' | 'RESOLVED' | 'CLOSED';

export interface IncidentRecordDTO {
  incident_id: string;
  tenant_id: string;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  summary: string;
  migration_id: string | null;
  node_id: string | null;
  correlation_key: string | null;
  owner_actor_id: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface IncidentTimelineRecordDTO {
  event_id: string;
  incident_id: string;
  tenant_id: string;
  event_type: 'CREATED' | 'ALERT_ATTACHED' | 'SEVERITY_CHANGED' | 'STATUS_CHANGED' | 'DIAGNOSTIC_LINKED' | 'ACTION_TAKEN';
  actor_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export type AlertSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertLifecycleState = 'OPEN' | 'ACKNOWLEDGED' | 'SUPPRESSED' | 'RESOLVED' | 'REOPENED';

export interface AlertRecordDTO {
  alert_id: string;
  tenant_id: string;
  signal_name: string;
  dedup_fingerprint: string;
  severity: AlertSeverity;
  lifecycle_state: AlertLifecycleState;
  message: string;
  rule_id: string | null;
  current_value: string | null;
  threshold_value: string | null;
  context_payload: Record<string, unknown> | null;
  observation_count: number;
  suppression_expires_at: string | null;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  first_observed_at: string;
  last_observed_at: string;
  created_at: string;
}

export interface FleetNodeSnapshotDTO {
  node_id: string;
  address: string;
  port: number;
  liveness: string;
  drain_state: string;
  active_executions: number;
  assigned_workloads: number;
  capabilities: string[];
  last_heartbeat_ago_sec: number;
  registered_at_iso: string;
}

// Field names verified against akaalPipeline/state/aggregates.py MigrationAggregate.to_dict()
// via akaalPipeline/application/unified_caller.py's migration.list dispatch.
export type BackendMigrationMode = 'M1' | 'M2' | 'M3' | 'M4' | 'M5' | 'M6' | 'M7' | 'M8';
export type BackendMigrationLifecycleState =
  | 'DRAFT' | 'CONFIGURING' | 'DISCOVERED' | 'PLANNED' | 'GOVERNANCE_PENDING' | 'AUTHORIZED'
  | 'INITIALIZED' | 'ACTIVE' | 'PAUSING' | 'PAUSED' | 'CANCELLATION_PENDING'
  | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'ARCHIVED';

export interface MigrationAggregateDTO {
  migration_id: string;
  revision: number;
  name: string;
  mode: BackendMigrationMode;
  state: BackendMigrationLifecycleState;
  tenant_id: string | null;
  workspace_id: string | null;
  project_id: string | null;
  configuration: Record<string, unknown>;
  plan_id: string | null;
  initialization_id: string | null;
  active_attempt_id: string | null;
  active_schedule_id: string | null;
  lineage: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class MonitoringIpcService {
  private ipc: IpcService;

  constructor(ipcService?: IpcService) {
    if (ipcService) {
      this.ipc = ipcService;
    } else {
      try {
        this.ipc = inject(IpcService, { optional: true }) || new IpcService();
      } catch {
        this.ipc = new IpcService();
      }
    }
  }

  // -- Queries ------------------------------------------------------------

  public async listIncidents(params: { status?: IncidentStatus; limit?: number } = {}): Promise<IPCResponse<{ incidents: IncidentRecordDTO[] }>> {
    return this.ipc.invoke<{ incidents: IncidentRecordDTO[] }>('incident', 'list', { ...params });
  }

  public async getIncident(incidentId: string): Promise<IPCResponse<{ incident: IncidentRecordDTO }>> {
    return this.ipc.invoke<{ incident: IncidentRecordDTO }>('incident', 'get', { incident_id: incidentId });
  }

  public async getIncidentTimeline(incidentId: string): Promise<IPCResponse<{ timeline: IncidentTimelineRecordDTO[] }>> {
    return this.ipc.invoke<{ timeline: IncidentTimelineRecordDTO[] }>('incident', 'timeline', { incident_id: incidentId });
  }

  public async listAlerts(params: { lifecycle_state?: AlertLifecycleState; limit?: number } = {}): Promise<IPCResponse<{ alerts: AlertRecordDTO[] }>> {
    return this.ipc.invoke<{ alerts: AlertRecordDTO[] }>('alert', 'list', { ...params });
  }

  public async getAlert(alertId: string): Promise<IPCResponse<{ alert: AlertRecordDTO }>> {
    return this.ipc.invoke<{ alert: AlertRecordDTO }>('alert', 'get', { alert_id: alertId });
  }

  public async getFleetStatus(): Promise<IPCResponse<{ nodes: FleetNodeSnapshotDTO[] }>> {
    return this.ipc.invoke<{ nodes: FleetNodeSnapshotDTO[] }>('fleet', 'status', {});
  }

  public async listMigrations(params: { limit?: number; offset?: number; status?: string; mode?: string } = {}): Promise<
    IPCResponse<{ migrations: MigrationAggregateDTO[]; limit: number; offset: number; total: number; next_offset: number | null }>
  > {
    return this.ipc.invoke('migration', 'list', { ...params });
  }

  // -- Commands -------------------------------------------------------------
  // These call the real, already-wired canonical command handlers
  // (command_handlers.handle_update_incident_status / AlertService
  // acknowledge/resolve/suppress). They are expected to legitimately fail
  // closed today with a FORBIDDEN/PERMISSION_DENIED-class error, because the
  // current desktop transport (akaalSoftware/app.go IPCRequest) carries no
  // session identity for PipelineUnifiedCaller to derive real roles/scopes
  // from -- see akaalIPC/transport/tcp_socket_host.py's "Identity note".
  // This is truthful fail-closed behavior, not a bug in this adapter, and
  // must never be papered over with a local success fallback.

  public async updateIncidentStatus(incidentId: string, statusValue: IncidentStatus, reason?: string): Promise<IPCResponse<{ incident: IncidentRecordDTO }>> {
    return this.ipc.invoke<{ incident: IncidentRecordDTO }>('incident', 'status.update', {
      incident_id: incidentId,
      status: statusValue,
      reason: reason ?? null,
    });
  }

  public async acknowledgeAlert(alertId: string): Promise<IPCResponse<{ alert: AlertRecordDTO }>> {
    return this.ipc.invoke<{ alert: AlertRecordDTO }>('alert', 'acknowledge', { alert_id: alertId });
  }

  public async resolveAlert(alertId: string): Promise<IPCResponse<{ alert: AlertRecordDTO }>> {
    return this.ipc.invoke<{ alert: AlertRecordDTO }>('alert', 'resolve', { alert_id: alertId });
  }

  public async suppressAlert(alertId: string, durationSeconds: number): Promise<IPCResponse<{ alert: AlertRecordDTO }>> {
    return this.ipc.invoke<{ alert: AlertRecordDTO }>('alert', 'suppress', { alert_id: alertId, duration_seconds: durationSeconds });
  }
}
