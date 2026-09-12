import { describe, it, expect, beforeEach, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { MonitoringService } from './services/monitoring.service';
import { IpcService } from '../../core/services/ipc.service';
import { CANONICAL_MODES, CanonicalMigrationMode } from './models/monitoring.models';

describe('AKAAL Monitoring Home (Part 1 of 4) — Master Contract & Integrity Suite', () => {
  let service: MonitoringService;
  let mockIpcService: any;

  beforeEach(() => {
    mockIpcService = {
      invoke: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: {} }),
      connectionState: { set: vi.fn() },
      lastTelemetryTimestamp: { set: vi.fn() }
    };

    service = new MonitoringService(mockIpcService);
  });

  describe('1. Architectural Boundaries & Canonical Modes (M1–M7)', () => {
    it('should define all M1–M7 canonical migration modes with exact human-readable labels', () => {
      const modes: CanonicalMigrationMode[] = [
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ];

      modes.forEach(mode => {
        expect(CANONICAL_MODES[mode]).toBeDefined();
        expect(CANONICAL_MODES[mode].tag).toMatch(/^M[1-7]$/);
        expect(CANONICAL_MODES[mode].label.length).toBeGreaterThan(0);
      });

      expect(CANONICAL_MODES['M1_BULK'].label).toBe('Bulk Snapshot');
      expect(CANONICAL_MODES['M2_BULK_CDC'].label).toBe('Bulk + CDC');
      expect(CANONICAL_MODES['M3_CDC'].label).toBe('Continuous CDC');
      expect(CANONICAL_MODES['M4_INCREMENTAL'].label).toBe('Incremental Polling');
      expect(CANONICAL_MODES['M5_STATE_SYNC'].label).toBe('State-Based Sync');
      expect(CANONICAL_MODES['M6_SCHEMA_ONLY'].label).toBe('Schema Only');
      expect(CANONICAL_MODES['M7_DATA_ONLY'].label).toBe('Data Only');
    });

    it('must strictly exclude M8 (Validation Only) from Migration Monitoring modes', () => {
      expect((CANONICAL_MODES as any)['M8_VALIDATION']).toBeUndefined();
      expect((CANONICAL_MODES as any)['M8']).toBeUndefined();
    });
  });

  describe('2. Truthful Operational State & Freshness Semantics', () => {
    it('should initialize with baseline summary and valid canonical observation timestamp', () => {
      expect(service.summary()).not.toBeNull();
      expect(service.summary()?.overall_platform_health).toBe('HEALTHY');
      expect(service.telemetryConfidence()).toBe('CURRENT');
      expect(service.lastObservedAt()).toBeTruthy();
    });

    it('should preserve unknown progress as null for continuous streaming CDC without inventing false 0%', () => {
      const streamingWorkload = service.activeMigrations().find(m => m.mode === 'M3_CDC');
      expect(streamingWorkload).toBeDefined();
      expect(streamingWorkload?.progress_percent).toBeNull();
      expect(streamingWorkload?.work_unit_label).toContain('Offset');
    });

    it('should calculate active migration count reactively from fleet state', () => {
      expect(service.activeMigrationCount()).toBeGreaterThan(0);
      expect(service.activeMigrationCount()).toBeLessThanOrEqual(service.activeMigrations().length);
    });

    it('should format relative observation time truthfully without generating IPC traffic', () => {
      const now = new Date().toISOString();
      const formatted = service.formatObservationTime(now);
      expect(formatted).toBe('Just now');

      const past = new Date(Date.now() - 35 * 1000).toISOString();
      expect(service.formatObservationTime(past)).toBe('35s ago');

      const older = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(service.formatObservationTime(older)).toBe('5m ago');
    });
  });

  describe('3. Needs Attention & Calm Healthy State Law', () => {
    it('should contain curated attention conditions with severity, duration, and direction', () => {
      const attentionItems = service.needsAttention();
      expect(attentionItems.length).toBeGreaterThan(0);
      
      const item = attentionItems[0];
      expect(item.condition_title).toBeTruthy();
      expect(item.condition_detail).toBeTruthy();
      expect(['CRITICAL', 'WARNING', 'INFO', 'UNKNOWN']).toContain(item.severity);
      expect(['improving', 'stable', 'worsening', 'unknown']).toContain(item.direction);
      expect(item.deep_link_route).toBeTruthy();
    });

    it('should support calm empty state when no attention conditions exist', () => {
      service.needsAttention.set([]);
      expect(service.needsAttention().length).toBe(0);
      expect(service.criticalAttentionCount()).toBe(0);
    });
  });

  describe('4. Platform & Data Path Health (6 Operational Areas)', () => {
    it('should represent all 6 canonical data path areas', () => {
      const areas = service.platformHealth();
      expect(areas.length).toBe(6);

      const keys = areas.map(a => a.key);
      expect(keys).toContain('SOURCES_CONNECTORS');
      expect(keys).toContain('AKAAL_RUNTIME');
      expect(keys).toContain('QUEUES_BUFFERS');
      expect(keys).toContain('STORAGE');
      expect(keys).toContain('TARGET_ENDPOINTS');
      expect(keys).toContain('SERVICES_DEPENDENCIES');
    });

    it('should maintain degraded summary specifically when a component is abnormal', () => {
      const degradedArea = service.platformHealth().find(a => a.health === 'DEGRADED');
      if (degradedArea) {
        expect(degradedArea.degraded_summary).toBeTruthy();
      }
    });
  });

  describe('5. Operational Pressure & Headroom (5 Resource Dimensions)', () => {
    it('should monitor CPU, Memory, Storage, Network, and Buffers/Queues', () => {
      const metrics = service.operationalPressure();
      expect(metrics.length).toBe(5);

      const keys = metrics.map(m => m.key);
      expect(keys).toContain('CPU');
      expect(keys).toContain('MEMORY');
      expect(keys).toContain('STORAGE');
      expect(keys).toContain('NETWORK');
      expect(keys).toContain('BUFFERS_QUEUES');
    });

    it('should decouple current utilization from trend direction', () => {
      const metrics = service.operationalPressure();
      metrics.forEach(m => {
        expect(m.utilization_percent).toBeGreaterThanOrEqual(0);
        expect(m.utilization_percent).toBeLessThanOrEqual(100);
        expect(['improving', 'stable', 'worsening', 'unknown']).toContain(m.trend);
        expect(m.threshold_warning_percent).toBeGreaterThan(0);
        expect(m.threshold_critical_percent).toBeGreaterThan(m.threshold_warning_percent);
      });
    });
  });

  describe('6. Active Workloads & Filtering', () => {
    it('should filter active migrations correctly by name, source, or target', () => {
      service.migrationSearchQuery.set('Oracle');
      expect(service.filteredActiveMigrations().length).toBe(1);
      expect(service.filteredActiveMigrations()[0].source_provider).toContain('Oracle');

      service.migrationSearchQuery.set('Snowflake');
      expect(service.filteredActiveMigrations().length).toBe(1);
      expect(service.filteredActiveMigrations()[0].target_provider).toContain('Snowflake');

      service.migrationSearchQuery.set('non-existent-query');
      expect(service.filteredActiveMigrations().length).toBe(0);

      service.migrationSearchQuery.set('');
      expect(service.filteredActiveMigrations().length).toBe(service.activeMigrations().length);
    });
  });

  describe('7. Recent Operational Events', () => {
    it('should provide a bounded list of meaningful operational transitions', () => {
      const events = service.recentEvents();
      expect(events.length).toBeGreaterThanOrEqual(5);
      expect(events.length).toBeLessThanOrEqual(8);

      events.forEach(evt => {
        expect(evt.id).toBeTruthy();
        expect(evt.timestamp).toBeTruthy();
        expect(evt.category_label).toBeTruthy();
        expect(evt.summary).toBeTruthy();
      });
    });
  });

  describe('8. Refresh Semantics & Error Handling', () => {
    it('should set isRefreshing to true during refresh and false upon completion', async () => {
      const refreshPromise = service.refresh();
      expect(service.isRefreshing()).toBe(true);
      await refreshPromise;
      expect(service.isRefreshing()).toBe(false);
    });

    it('should handle unavailable backend cleanly without throwing uncaught exceptions', async () => {
      mockIpcService.invoke.mockRejectedValueOnce(new Error('IPC socket connection refused'));
      
      await service.initializeState();
      expect(service.isLoading()).toBe(false);
    });
  });
});
