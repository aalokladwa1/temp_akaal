import { describe, it, expect, vi } from 'vitest';
import { PlatformMonitoringService } from './services/platform-monitoring.service';
import { MonitoringIpcService, FleetNodeSnapshotDTO } from '../../core/services/ipc/monitoring.ipc';

function makeNode(overrides: Partial<FleetNodeSnapshotDTO> = {}): FleetNodeSnapshotDTO {
  return {
    node_id: 'node-1',
    address: '127.0.0.1',
    port: 9000,
    liveness: 'ALIVE',
    drain_state: 'ACTIVE',
    active_executions: 0,
    assigned_workloads: 0,
    capabilities: [],
    last_heartbeat_ago_sec: 0,
    registered_at_iso: '2026-09-17T00:00:00Z',
    ...overrides
  };
}

function makeFakeIpc(overrides: Partial<MonitoringIpcService> = {}): MonitoringIpcService {
  return {
    getFleetStatus: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { nodes: [makeNode()] } }),
    listAlerts: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { alerts: [] } }),
    listIncidents: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { incidents: [] } }),
    ...overrides
  } as unknown as MonitoringIpcService;
}

describe('AKAAL Monitoring — Platform Operations (real backend integration)', () => {
  it('should compose real node/health counts from fleet.status', async () => {
    const ipc = makeFakeIpc({
      getFleetStatus: vi.fn().mockResolvedValue({
        status: 'SUCCESS',
        data: { nodes: [makeNode({ node_id: 'a', liveness: 'ALIVE' }), makeNode({ node_id: 'b', liveness: 'DEGRADED' })] }
      })
    });
    const service = new PlatformMonitoringService(ipc);
    await service.refresh();

    expect(service.summary().total_nodes).toBe(2);
    expect(service.summary().healthy_nodes).toBe(1);
    expect(service.summary().overall_health).toBe('DEGRADED');
    expect(service.summary().liveness_state).toBe('DEGRADED');
    expect(service.isUnavailable()).toBe(false);
  });

  it('should mark overall_health UNHEALTHY when any node is DEAD', async () => {
    const ipc = makeFakeIpc({
      getFleetStatus: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { nodes: [makeNode({ liveness: 'DEAD' })] } })
    });
    const service = new PlatformMonitoringService(ipc);
    await service.refresh();

    expect(service.summary().overall_health).toBe('UNHEALTHY');
    expect(service.summary().liveness_state).toBe('DEAD');
    expect(service.summary().readiness_state).toBe('NOT_READY');
  });

  it('should compose real alert/incident counts', async () => {
    const ipc = makeFakeIpc({
      listAlerts: vi.fn().mockResolvedValue({
        status: 'SUCCESS',
        data: { alerts: [{ lifecycle_state: 'OPEN' } as any, { lifecycle_state: 'RESOLVED' } as any] }
      }),
      listIncidents: vi.fn().mockResolvedValue({
        status: 'SUCCESS',
        data: { incidents: [{ status: 'OPEN' } as any, { status: 'RESOLVED' } as any] }
      })
    });
    const service = new PlatformMonitoringService(ipc);
    await service.refresh();

    expect(service.summary().active_alerts_count).toBe(1);
    expect(service.summary().unresolved_incidents_count).toBe(1);
  });

  it('should truthfully leave capability-absent detail surfaces empty rather than fabricate them', async () => {
    const service = new PlatformMonitoringService(makeFakeIpc());
    await service.refresh();

    expect(service.data().nodes).toEqual([]);
    expect(service.data().runtime_services).toEqual([]);
    expect(service.data().connectors).toEqual([]);
    expect(service.data().capacity.cpu.total_cores).toBe(0);
    expect(service.data().reliability.advisory_rca).toEqual([]);
  });

  it('should mark unavailable and not fabricate healthy state when the fleet backend errors', async () => {
    const ipc = makeFakeIpc({
      getFleetStatus: vi.fn().mockResolvedValue({ status: 'ERROR', error: 'ENGINE_DISCONNECTED' })
    });
    const service = new PlatformMonitoringService(ipc);
    await service.refresh();

    expect(service.isUnavailable()).toBe(true);
    expect(service.errorMessage()).toBe('ENGINE_DISCONNECTED');
    expect(service.summary().total_nodes).toBe(0);
  });
});
