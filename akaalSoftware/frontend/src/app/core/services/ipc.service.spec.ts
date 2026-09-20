import { describe, it, expect, beforeEach, vi } from 'vitest';
import { IpcService } from './ipc.service';
import { DashboardIpc } from './ipc/dashboard.ipc';
import { MigrationIpc } from './ipc/migration.ipc';
import { SettingsIpc } from './ipc/settings.ipc';
import { MonitoringIpc } from './ipc/monitoring.ipc';
import { ReportsIpc } from './ipc/reports.ipc';
import { AdministrationIpc } from './ipc/administration.ipc';

describe('IpcService — Master Frontend IPC Transport & Signal Router', () => {
  let ipcService: IpcService;

  beforeEach(() => {
    // Reset window.runtime mocks
    (globalThis as any).window = {
      runtime: {
        EventsOn: vi.fn(),
        EventsOff: vi.fn(),
      },
    };
    ipcService = new IpcService();
  });

  describe('A. Six-Adapter Transport Uniformity', () => {
    it('should inject and share the same master IpcService instance across all six domain adapters', () => {
      const dashboard = new DashboardIpc(ipcService);
      const migration = new MigrationIpc(ipcService);
      const settings = new SettingsIpc(ipcService);
      const monitoring = new MonitoringIpc(ipcService);
      const reports = new ReportsIpc(ipcService);
      const admin = new AdministrationIpc(ipcService);

      expect((dashboard as any).ipc).toBe(ipcService);
      expect((migration as any).ipc).toBe(ipcService);
      expect((settings as any).ipc).toBe(ipcService);
      expect((monitoring as any).ipc).toBe(ipcService);
      expect((reports as any).ipc).toBe(ipcService);
      expect((admin as any).ipc).toBe(ipcService);
    });
  });

  describe('B. Single Underlying Listener & Listener Deduplication', () => {
    it('should attach only ONE underlying Wails listener when multiple subscribers register for the same signal', () => {
      const mockEventsOn = (globalThis as any).window.runtime.EventsOn;

      const handler1 = vi.fn();
      const handler2 = vi.fn();

      ipcService.subscribe('akaal:telemetry', handler1);
      ipcService.subscribe('akaal:telemetry', handler2);

      // EventsOn should be called only ONCE for 'akaal:telemetry' despite 2 subscribers
      const callsForTelemetry = mockEventsOn.mock.calls.filter((c: any) => c[0] === 'akaal:telemetry');
      expect(callsForTelemetry.length).toBe(1);
      expect(ipcService.getSubscriberCount('akaal:telemetry')).toBe(3); // 1 internal + 2 custom
    });
  });

  describe('C. Fan-out to Active Subscribers', () => {
    it('should fan-out inbound signal payload to all active subscribers exactly once', () => {
      const handlerA = vi.fn();
      const handlerB = vi.fn();

      ipcService.subscribe('custom:signal', handlerA);
      ipcService.subscribe('custom:signal', handlerB);

      const payload = { timestamp: '2026-09-19T16:00:00Z', metric: 'cpu', value: 42 };
      ipcService.dispatchSignal('custom:signal', payload);

      expect(handlerA).toHaveBeenCalledTimes(1);
      expect(handlerA).toHaveBeenCalledWith(payload);
      expect(handlerB).toHaveBeenCalledTimes(1);
      expect(handlerB).toHaveBeenCalledWith(payload);
    });
  });

  describe('D. Selective Unsubscribe', () => {
    it('should stop delivering events to unsubscribed handler while keeping other subscribers active', () => {
      const handlerA = vi.fn();
      const handlerB = vi.fn();

      const unsubscribeA = ipcService.subscribe('akaal:telemetry', handlerA);
      ipcService.subscribe('akaal:telemetry', handlerB);

      unsubscribeA();

      const payload = { type: 'metrics', count: 10 };
      ipcService.dispatchSignal('akaal:telemetry', payload);

      expect(handlerA).not.toHaveBeenCalled();
      expect(handlerB).toHaveBeenCalledTimes(1);
      expect(handlerB).toHaveBeenCalledWith(payload);
    });
  });

  describe('E. Final Cleanup', () => {
    it('should detach underlying Wails listener when subscriber count drops to zero', () => {
      const mockEventsOff = (globalThis as any).window.runtime.EventsOff;
      const handler = vi.fn();

      const unsubscribe = ipcService.subscribe('unique:event', handler);
      expect(ipcService.getSubscriberCount('unique:event')).toBe(1);

      unsubscribe();

      expect(ipcService.getSubscriberCount('unique:event')).toBe(0);
      expect(mockEventsOff).toHaveBeenCalledWith('unique:event');
    });
  });

  describe('F. Re-subscription Safety', () => {
    it('should attach Wails listener cleanly on re-subscription after cleanup without duplicate callbacks', () => {
      const mockEventsOn = (globalThis as any).window.runtime.EventsOn;
      const handler1 = vi.fn();

      const unsub1 = ipcService.subscribe('resub:event', handler1);
      unsub1();

      const handler2 = vi.fn();
      ipcService.subscribe('resub:event', handler2);

      const calls = mockEventsOn.mock.calls.filter((c: any) => c[0] === 'resub:event');
      expect(calls.length).toBe(2);

      const payload = { status: 'reconnected' };
      ipcService.dispatchSignal('resub:event', payload);

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledWith(payload);
    });
  });

  describe('G. Payload Preservation', () => {
    it('should pass exact inbound payload without fabrication or mutation', () => {
      const handler = vi.fn();
      ipcService.subscribe('raw:event', handler);

      const rawPayload = { nested: { array: [1, 2, 3] }, flag: true, nullField: null };
      ipcService.dispatchSignal('raw:event', rawPayload);

      expect(handler).toHaveBeenCalledWith(rawPayload);
      expect(handler.mock.calls[0][0]).toBe(rawPayload);
    });
  });

  describe('H. Error Truth & Transport Failure Handling', () => {
    it('should capture transport invocation exception and return truthful ERROR status envelope', async () => {
      (globalThis as any).window.go = {
        main: {
          App: {
            InvokeIPC: vi.fn().mockRejectedValue(new Error('IPC socket connection refused')),
          },
        },
      };

      const response = await ipcService.invoke('test', 'action', {});
      expect(response.status).toBe('ERROR');
      expect(response.error).toContain('IPC socket connection refused');
    });
  });
});
