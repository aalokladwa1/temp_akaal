import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationHomeService } from './migration-home.service';
import { MigrationHomeRow, ActivityHomeRow } from '../models/migration-home.models';

describe('MigrationHomeService (2.1 Migration Home Landing Hub)', () => {
  let service: MigrationHomeService;

  beforeEach(() => {
    service = new MigrationHomeService();
  });

  describe('1. Dynamic Headline Priority (Section 13 & 37)', () => {
    it('should return "Clean slate. Pick where the data goes next." when workspace is empty', () => {
      const headline = service.calculateDynamicHeadline([], []);
      expect(headline).toBe('Clean slate. Pick where the data goes next.');
    });

    it('should prioritize Critical failure over all other states', () => {
      const migs: MigrationHomeRow[] = [
        {
          id: 'm1',
          name: 'Critical Mig',
          source_provider: 'Oracle',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_ONLY',
          lifecycle_state: 'FAILED',
          current_stage: 'Failed',
          progress_percent: 10,
          started_at: '',
          updated_at: ''
        },
        {
          id: 'm2',
          name: 'Approval Mig',
          source_provider: 'MySQL',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_CDC',
          lifecycle_state: 'ATTENTION',
          current_stage: 'Cutover Approval Required',
          progress_percent: 50,
          started_at: '',
          updated_at: ''
        }
      ];
      const headline = service.calculateDynamicHeadline(migs, []);
      expect(headline).toBe('Something needs you before the fleet moves on.');
    });

    it('should prioritize Blocked readiness when no critical failure exists', () => {
      const migs: MigrationHomeRow[] = [
        {
          id: 'm1',
          name: 'Blocked Mig',
          source_provider: 'Oracle',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_ONLY',
          lifecycle_state: 'ACTIVE',
          current_stage: 'Blocked by firewall quorum',
          attention_text: 'Blocked readiness check',
          progress_percent: 10,
          started_at: '',
          updated_at: ''
        },
        {
          id: 'm2',
          name: 'Active Mig',
          source_provider: 'MySQL',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_CDC',
          lifecycle_state: 'ACTIVE',
          current_stage: 'Running',
          progress_percent: 50,
          started_at: '',
          updated_at: ''
        }
      ];
      const headline = service.calculateDynamicHeadline(migs, []);
      expect(headline).toBe('One move is ready — except for what’s holding it back.');
    });

    it('should prioritize Approval waiting when no failures or blocks exist', () => {
      const migs: MigrationHomeRow[] = [
        {
          id: 'm1',
          name: 'Approval Mig',
          source_provider: 'Oracle',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_ONLY',
          lifecycle_state: 'ATTENTION',
          current_stage: 'Approval pending at Barrier 2',
          progress_percent: 80,
          started_at: '',
          updated_at: ''
        }
      ];
      const headline = service.calculateDynamicHeadline(migs, []);
      expect(headline).toBe('The next move is waiting on a decision.');
    });

    it('should return Cutover approaching when cutover is in progress', () => {
      const migs: MigrationHomeRow[] = [
        {
          id: 'm1',
          name: 'Cutover Mig',
          source_provider: 'Oracle',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_CDC',
          lifecycle_state: 'ACTIVE',
          current_stage: 'CDC Catchup Phase for Cutover',
          progress_percent: 95,
          started_at: '',
          updated_at: ''
        }
      ];
      const headline = service.calculateDynamicHeadline(migs, []);
      expect(headline).toBe('Cutover is getting close. The important pieces are lining up.');
    });

    it('should return Heavy fleet headline when 5 or more migrations are active', () => {
      const migs: MigrationHomeRow[] = Array.from({ length: 6 }).map((_, i) => ({
        id: `m-${i}`,
        name: `Mig ${i}`,
        source_provider: 'Oracle',
        source_label: 'src',
        target_provider: 'PG',
        target_label: 'tgt',
        mode: 'BULK_ONLY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Streaming partitions',
        progress_percent: 30,
        started_at: '',
        updated_at: ''
      }));
      const headline = service.calculateDynamicHeadline(migs, []);
      expect(headline).toBe('The fleet is busy. The important bits are below.');
    });

    it('should return Normal active fleet headline when active migrations exist', () => {
      const migs: MigrationHomeRow[] = [
        {
          id: 'm1',
          name: 'Mig 1',
          source_provider: 'Oracle',
          source_label: 'src',
          target_provider: 'PG',
          target_label: 'tgt',
          mode: 'BULK_ONLY',
          lifecycle_state: 'ACTIVE',
          current_stage: 'Streaming partitions',
          progress_percent: 30,
          started_at: '',
          updated_at: ''
        }
      ];
      const headline = service.calculateDynamicHeadline(migs, []);
      expect(headline).toBe('Things are moving. Nothing important is hiding.');
    });
  });

  describe('2. Mode-Aware Operational Metric Formatter (Section 20 & 37)', () => {
    it('should format Bulk Migration correctly', () => {
      const row: MigrationHomeRow = {
        id: '1',
        name: 'Bulk',
        source_provider: 'Oracle',
        source_label: 'src',
        target_provider: 'PG',
        target_label: 'tgt',
        mode: 'BULK_ONLY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Running',
        progress_percent: 62.4,
        throughput_rows_per_sec: 88000,
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('62% · 88k rows/s');
    });

    it('should format Bulk + CDC correctly', () => {
      const row: MigrationHomeRow = {
        id: '2',
        name: 'Bulk CDC',
        source_provider: 'Oracle',
        source_label: 'src',
        target_provider: 'PG',
        target_label: 'tgt',
        mode: 'BULK_CDC',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Running',
        progress_percent: 84.1,
        cdc_lag_ms: 400,
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('84% bulk · 0.4s CDC lag');
    });

    it('should format CDC Only correctly', () => {
      const row: MigrationHomeRow = {
        id: '3',
        name: 'CDC Only',
        source_provider: 'Mongo',
        source_label: 'src',
        target_provider: 'Kafka',
        target_label: 'tgt',
        mode: 'CDC_ONLY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Running',
        progress_percent: 0,
        cdc_lag_ms: 100,
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('Streaming · 0.1s lag');
    });

    it('should format Incremental Query correctly', () => {
      const row: MigrationHomeRow = {
        id: '4',
        name: 'Incremental',
        source_provider: 'SQL Server',
        source_label: 'src',
        target_provider: 'Snowflake',
        target_label: 'tgt',
        mode: 'INCREMENTAL_QUERY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Running',
        progress_percent: 50,
        incremental_watermark: '2026-08-30 13:42',
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('Watermark · 2026-08-30 13:42');
    });

    it('should format State Synchronization correctly', () => {
      const row: MigrationHomeRow = {
        id: '5',
        name: 'State Sync',
        source_provider: 'MySQL',
        source_label: 'src',
        target_provider: 'PG',
        target_label: 'tgt',
        mode: 'STATE_SYNC',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Comparing',
        progress_percent: 98.7,
        state_sync_percent: 98.7,
        difference_count: 7,
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('98.7% compared · 7 differences');
    });

    it('should format Schema Only correctly', () => {
      const row: MigrationHomeRow = {
        id: '6',
        name: 'Schema Only',
        source_provider: 'Oracle',
        source_label: 'src',
        target_provider: 'PG',
        target_label: 'tgt',
        mode: 'SCHEMA_ONLY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Converting',
        progress_percent: 74,
        objects_completed: 184,
        objects_total: 248,
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('184 / 248 objects');
    });

    it('should format Data Only correctly', () => {
      const row: MigrationHomeRow = {
        id: '7',
        name: 'Data Only',
        source_provider: 'PostgreSQL',
        source_label: 'src',
        target_provider: 'BigQuery',
        target_label: 'tgt',
        mode: 'DATA_ONLY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Streaming',
        progress_percent: 71,
        throughput_rows_per_sec: 112000,
        started_at: '',
        updated_at: ''
      };
      expect(service.formatModeMetric(row)).toBe('71% · 112k rows/s');
    });
  });

  describe('3. Project Remaining-Time Display (Section 23 & 37)', () => {
    const refDate = new Date('2026-08-30T12:00:00Z');

    it('should format > 60 days as "<N> months left"', () => {
      const res = service.formatProjectRemainingTime('2026-11-30', refDate);
      expect(res.primary).toBe('3 months left');
      expect(res.secondary).toContain('30 Nov');
    });

    it('should format 31-60 days as "2 months left"', () => {
      const res = service.formatProjectRemainingTime('2026-10-15', refDate);
      expect(res.primary).toBe('2 months left');
      expect(res.secondary).toContain('15 Oct');
    });

    it('should format 14-30 days as "<N> days left"', () => {
      const res = service.formatProjectRemainingTime('2026-09-27', refDate);
      expect(res.primary).toBe('28 days left');
      expect(res.secondary).toContain('27 Sep');
    });

    it('should format 2-13 days as "<N> days left"', () => {
      const res = service.formatProjectRemainingTime('2026-09-07', refDate);
      expect(res.primary).toBe('8 days left');
      expect(res.secondary).toContain('7 Sep');
    });

    it('should format 1 day as "Tomorrow"', () => {
      const res = service.formatProjectRemainingTime('2026-08-31', refDate);
      expect(res.primary).toBe('Tomorrow');
      expect(res.secondary).toContain('31 Aug');
    });

    it('should format 0 days as "Due today"', () => {
      const res = service.formatProjectRemainingTime('2026-08-30', refDate);
      expect(res.primary).toBe('Due today');
      expect(res.secondary).toContain('30 Aug');
    });

    it('should format past target as "<N> days overdue"', () => {
      const res = service.formatProjectRemainingTime('2026-08-28', refDate);
      expect(res.primary).toBe('2 days overdue');
      expect(res.secondary).toContain('28 Aug');
    });

    it('should format missing target as "No target set"', () => {
      const res = service.formatProjectRemainingTime(undefined, refDate);
      expect(res.primary).toBe('No target set');
    });
  });

  describe('4. KPI Derivation from Persisted State (Section 31 & 37)', () => {
    it('should calculate accurate KPI counts from loaded migrations', () => {
      const counters = service.computedCounters();
      expect(counters.total).toBe(5);
      expect(counters.active).toBe(2);
      expect(counters.attention).toBe(1);
      expect(counters.scheduled).toBe(1);
      expect(counters.completed).toBe(1);
    });
  });
});
