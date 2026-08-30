import { Injectable, signal, computed } from '@angular/core';
import {
  MigrationHomeRow,
  ProjectHomeRow,
  ActivityHomeRow,
  MigrationHomeSummary
} from '../models/migration-home.models';

export interface RelativeTimeFormatted {
  primary: string;
  secondary: string;
}

@Injectable({
  providedIn: 'root'
})
export class MigrationHomeService {
  // Signals for state storage
  public migrations = signal<MigrationHomeRow[]>([]);
  public projects = signal<ProjectHomeRow[]>([]);
  public activities = signal<ActivityHomeRow[]>([]);
  public summary = signal<MigrationHomeSummary | null>(null);

  public isLoading = signal<boolean>(true);
  public isUnavailable = signal<boolean>(false);
  public errorMessage = signal<string>('');

  // Derived KPI Counters
  public computedCounters = computed(() => {
    const list = this.migrations();
    const sum = this.summary();

    if (sum) {
      return {
        active: sum.active_count,
        attention: sum.attention_count,
        scheduled: sum.scheduled_count,
        completed: sum.completed_count,
        total: sum.total_count
      };
    }

    return {
      active: list.filter(m => m.lifecycle_state === 'ACTIVE' || m.lifecycle_state === 'RUNNING').length,
      attention: list.filter(m => m.lifecycle_state === 'ATTENTION' || !!m.attention_level).length,
      scheduled: list.filter(m => m.lifecycle_state === 'SCHEDULED').length,
      completed: list.filter(m => m.lifecycle_state === 'COMPLETED').length,
      total: list.length
    };
  });

  // Dynamic Migration Subtext Prioritized Selector (Section 13)
  public dynamicHeadline = computed<string>(() => {
    const sum = this.summary();
    const migs = this.migrations();
    const acts = this.activities();

    if (sum?.dynamic_headline) {
      return sum.dynamic_headline;
    }

    return this.calculateDynamicHeadline(migs, acts);
  });

  constructor() {
    this.loadDeterministicPrototypeFallback();
    this.loadState();
  }

  public async loadState(): Promise<void> {
    this.isLoading.set(true);
    this.isUnavailable.set(false);
    this.errorMessage.set('');

    try {
      const wailsApp = typeof window !== 'undefined' ? (window as any).go?.main?.App : undefined;

      if (wailsApp && typeof wailsApp.GetMigrationHomeMigrations === 'function') {
        const [sum, migs, projs, acts] = await Promise.all([
          wailsApp.GetMigrationHomeSummary(),
          wailsApp.GetMigrationHomeMigrations(),
          wailsApp.GetMigrationHomeProjects(),
          wailsApp.GetMigrationHomeActivities()
        ]);

        this.summary.set(sum);
        this.migrations.set(migs || []);
        this.projects.set(projs || []);
        this.activities.set(acts || []);
      } else {
        // Fallback / in-browser prototype seed
        this.loadDeterministicPrototypeFallback();
      }
    } catch (err: any) {
      console.error('[MigrationHomeService] Failed to load prototype data:', err);
      this.isUnavailable.set(true);
      this.errorMessage.set('Prototype migration data is unavailable.');
    } finally {
      this.isLoading.set(false);
    }
  }

  public async resetPrototypeDemoState(): Promise<void> {
    const wailsApp = typeof window !== 'undefined' ? (window as any).go?.main?.App : undefined;
    if (wailsApp && typeof wailsApp.ResetMigrationHomeDemoState === 'function') {
      await wailsApp.ResetMigrationHomeDemoState();
      await this.loadState();
    } else {
      this.loadDeterministicPrototypeFallback();
    }
  }

  // Prioritized selector implementation for dynamic subtext (Section 13)
  public calculateDynamicHeadline(migs: MigrationHomeRow[], acts: ActivityHomeRow[]): string {
    if (migs.length === 0) {
      return 'Clean slate. Pick where the data goes next.';
    }

    // 1. Critical migration failure/interruption
    const hasCriticalFailure = migs.some(m => m.lifecycle_state === 'FAILED' || m.lifecycle_state === 'INTERRUPTED' || m.attention_level === 'CRITICAL');
    if (hasCriticalFailure) {
      return 'Something needs you before the fleet moves on.';
    }

    // 2. Blocking readiness/governance issue
    const hasBlockedReadiness = migs.some(m => m.attention_text?.toLowerCase().includes('blocked') || m.current_stage?.toLowerCase().includes('blocked'));
    if (hasBlockedReadiness) {
      return 'One move is ready — except for what’s holding it back.';
    }

    // 3. Approval/gate waiting for operator
    const hasApprovalPending = migs.some(m => m.lifecycle_state === 'ATTENTION' || m.attention_text?.toLowerCase().includes('approval') || m.attention_text?.toLowerCase().includes('gate'));
    if (hasApprovalPending) {
      return 'The next move is waiting on a decision.';
    }

    // 4. Cutover approaching / cutover ready
    const hasCutoverReady = migs.some(m => m.current_stage?.toLowerCase().includes('cutover') || m.current_stage?.toLowerCase().includes('catchup'));
    if (hasCutoverReady) {
      return 'Cutover is getting close. The important pieces are lining up.';
    }

    // 5. Validation reports NOT SYNCED
    const hasValidationDiffs = migs.some(m => (m.difference_count ?? 0) > 0);
    if (hasValidationDiffs) {
      return 'The move finished. The data still has something to say.';
    }

    // 6. Heavy active fleet (>= 5)
    const activeCount = migs.filter(m => m.lifecycle_state === 'ACTIVE' || m.lifecycle_state === 'RUNNING').length;
    if (activeCount >= 5) {
      return 'The fleet is busy. The important bits are below.';
    }

    // 7. Normal active fleet
    if (activeCount > 0) {
      return 'Things are moving. Nothing important is hiding.';
    }

    // 8. Upcoming scheduled migrations
    const scheduledCount = migs.filter(m => m.lifecycle_state === 'SCHEDULED').length;
    if (scheduledCount > 0) {
      return 'The next moves are already lined up.';
    }

    // 9. Recent successful completion
    const hasRecentCompleted = migs.some(m => m.lifecycle_state === 'COMPLETED');
    if (hasRecentCompleted) {
      return 'Another one across. The next move is yours.';
    }

    // 10. Quiet fleet with existing work
    return 'Nothing urgent. Everything ready when you are.';
  }

  // Mode-Aware Operational Metric Formatter (Section 20)
  public formatModeMetric(m: MigrationHomeRow): string {
    const mode = m.mode.toUpperCase();

    if (mode === 'BULK_ONLY' || mode === 'M1_BULK') {
      const rowsSec = m.throughput_rows_per_sec ? `${Math.round(m.throughput_rows_per_sec / 1000)}k rows/s` : 'Initializing';
      return `${Math.round(m.progress_percent)}% · ${rowsSec}`;
    }

    if (mode === 'BULK_CDC' || mode === 'M2_BULK_CDC') {
      const lag = m.cdc_lag_ms !== undefined && m.cdc_lag_ms !== null ? `${(m.cdc_lag_ms / 1000).toFixed(1)}s CDC lag` : '<0.5s lag';
      return `${Math.round(m.progress_percent)}% bulk · ${lag}`;
    }

    if (mode === 'CDC_ONLY' || mode === 'M3_CDC') {
      const lag = m.cdc_lag_ms !== undefined && m.cdc_lag_ms !== null ? `${(m.cdc_lag_ms / 1000).toFixed(1)}s lag` : '0.1s lag';
      return `Streaming · ${lag}`;
    }

    if (mode === 'INCREMENTAL_QUERY' || mode === 'M4_INCREMENTAL') {
      const wm = m.incremental_watermark || '2026-08-30 13:42';
      return `Watermark · ${wm}`;
    }

    if (mode === 'STATE_SYNC' || mode === 'M5_STATE_SYNC') {
      const diffs = m.difference_count ?? 0;
      return `${(m.state_sync_percent ?? m.progress_percent).toFixed(1)}% compared · ${diffs} differences`;
    }

    if (mode === 'SCHEMA_ONLY' || mode === 'M6_SCHEMA_ONLY') {
      const completed = m.objects_completed ?? 184;
      const total = m.objects_total ?? 248;
      return `${completed} / ${total} objects`;
    }

    if (mode === 'DATA_ONLY' || mode === 'M7_DATA_ONLY') {
      const rowsSec = m.throughput_rows_per_sec ? `${Math.round(m.throughput_rows_per_sec / 1000)}k rows/s` : '112k rows/s';
      return `${Math.round(m.progress_percent)}% · ${rowsSec}`;
    }

    return `${Math.round(m.progress_percent)}%`;
  }

  // Dynamic Relative Time for Projects (Section 23)
  public formatProjectRemainingTime(targetDateStr?: string, referenceDate: Date = new Date()): RelativeTimeFormatted {
    if (!targetDateStr) {
      return {
        primary: 'No target set',
        secondary: 'Open-ended milestone'
      };
    }

    const target = new Date(targetDateStr);
    if (isNaN(target.getTime())) {
      return {
        primary: 'No target set',
        secondary: 'Invalid date'
      };
    }

    const targetDay = new Date(target.getFullYear(), target.getMonth(), target.getDate());
    const refDay = new Date(referenceDate.getFullYear(), referenceDate.getMonth(), referenceDate.getDate());

    const diffTime = targetDay.getTime() - refDay.getTime();
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));

    const monthsShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const formattedTarget = `Target · ${target.getDate()} ${monthsShort[target.getMonth()]}`;

    if (diffDays < 0) {
      const overdue = Math.abs(diffDays);
      return {
        primary: `${overdue} day${overdue === 1 ? '' : 's'} overdue`,
        secondary: formattedTarget
      };
    }

    if (diffDays === 0) {
      return {
        primary: 'Due today',
        secondary: formattedTarget
      };
    }

    if (diffDays === 1) {
      return {
        primary: 'Tomorrow',
        secondary: formattedTarget
      };
    }

    if (diffDays <= 30) {
      return {
        primary: `${diffDays} days left`,
        secondary: formattedTarget
      };
    }

    if (diffDays <= 60) {
      return {
        primary: '2 months left',
        secondary: formattedTarget
      };
    }

    const months = Math.round(diffDays / 30);
    return {
      primary: `${months} months left`,
      secondary: formattedTarget
    };
  }

  // Relative Time Display for Activities (Section 26)
  public formatRelativeTime(isoString: string): { relative: string; exactTime: string } {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) {
      return { relative: 'Recently', exactTime: '—' };
    }

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    const exactTime = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (diffMins < 1) {
      return { relative: 'Just now', exactTime };
    }
    if (diffMins < 60) {
      return { relative: `${diffMins} min ago`, exactTime };
    }
    if (diffHours < 24) {
      return { relative: `${diffHours} hr${diffHours === 1 ? '' : 's'} ago`, exactTime };
    }
    if (diffDays === 1) {
      return { relative: 'Yesterday', exactTime };
    }
    if (diffDays < 30) {
      return { relative: `${diffDays} days ago`, exactTime };
    }

    return { relative: date.toLocaleDateString([], { month: 'short', day: 'numeric' }), exactTime };
  }

  private loadDeterministicPrototypeFallback(): void {
    const now = new Date();

    const targetDate1 = new Date(now);
    targetDate1.setDate(now.getDate() + 46);

    const targetDate2 = new Date(now);
    targetDate2.setDate(now.getDate() + 8);

    const targetDate3 = new Date(now);
    targetDate3.setMonth(now.getMonth() + 3);

    const fallbackMigrations: MigrationHomeRow[] = [
      {
        id: 'mig-001',
        name: 'Core Accounts Ledger Migration',
        source_provider: 'Oracle',
        source_label: 'prod-oracle-01.internal:1521/ORCL',
        target_provider: 'PostgreSQL',
        target_label: 'aurora-pg.cluster-ro.internal:5432/finance',
        mode: 'BULK_CDC',
        lifecycle_state: 'ACTIVE',
        current_stage: 'CDC Catchup Phase',
        progress_percent: 84.2,
        throughput_rows_per_sec: 142500,
        cdc_lag_ms: 400,
        started_at: new Date(Date.now() - 3600000).toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: 'mig-002',
        name: 'Customer Analytics Warehouse Load',
        source_provider: 'PostgreSQL',
        source_label: 'rds-pg-analytics.internal:5432/reporting',
        target_provider: 'Snowflake',
        target_label: 'xy12345.us-east-1.snowflakecomputing.com',
        mode: 'BULK_ONLY',
        lifecycle_state: 'ACTIVE',
        current_stage: 'Direct-Path COPY Worker 4/8',
        progress_percent: 62.0,
        throughput_rows_per_sec: 88000,
        started_at: new Date(Date.now() - 7200000).toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: 'mig-003',
        name: 'Payment Gateway State Reconciliation',
        source_provider: 'MySQL',
        source_label: 'mysql-primary-02.internal:3306/payments',
        target_provider: 'PostgreSQL',
        target_label: 'pg-payments-dr.internal:5432/payments',
        mode: 'STATE_SYNC',
        lifecycle_state: 'ATTENTION',
        current_stage: 'Merkle Discrepancy Localization',
        progress_percent: 98.7,
        state_sync_percent: 98.7,
        difference_count: 7,
        attention_level: 'WARNING',
        attention_text: '7 cell differences detected in settlement partition',
        started_at: new Date(Date.now() - 14400000).toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: 'mig-004',
        name: 'Inventory Stream Replication',
        source_provider: 'MongoDB',
        source_label: 'mongo-shard-01.internal:27017/catalog',
        target_provider: 'Kafka',
        target_label: 'kafka-broker-01.internal:9092',
        mode: 'CDC_ONLY',
        lifecycle_state: 'SCHEDULED',
        current_stage: 'Pending Window Authorization',
        progress_percent: 0.0,
        scheduled_at: new Date(Date.now() + 43200000).toISOString(),
        started_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: 'mig-005',
        name: 'Customer Master Archive',
        source_provider: 'Oracle',
        source_label: 'oracle-legacy.internal:1521/ARCH',
        target_provider: 'PostgreSQL',
        target_label: 'pg-archive.internal:5432/public',
        mode: 'BULK_ONLY',
        lifecycle_state: 'COMPLETED',
        current_stage: 'Verified 100% Certified',
        progress_percent: 100.0,
        difference_count: 0,
        started_at: new Date(Date.now() - 86400000).toISOString(),
        updated_at: new Date().toISOString()
      }
    ];

    const fallbackProjects: ProjectHomeRow[] = [
      {
        id: 'proj-001',
        name: 'Core Banking Modernization',
        environment: 'Production',
        health: 'HEALTHY',
        migration_count: 12,
        active_count: 7,
        attention_count: 0,
        scheduled_count: 1,
        delivery_percent: 74.0,
        target_date: targetDate1.toISOString().slice(0, 10),
        owner: 'Aalok Ladwa',
        updated_at: new Date().toISOString()
      },
      {
        id: 'proj-002',
        name: 'Payment Gateway Sharding',
        environment: 'Staging',
        health: 'ATTENTION',
        migration_count: 6,
        active_count: 2,
        attention_count: 2,
        scheduled_count: 0,
        delivery_percent: 42.0,
        target_date: targetDate2.toISOString().slice(0, 10),
        owner: 'Sarah Jenkins',
        updated_at: new Date().toISOString()
      },
      {
        id: 'proj-003',
        name: 'Data Lake Consolidation',
        environment: 'Development',
        health: 'HEALTHY',
        migration_count: 8,
        active_count: 3,
        attention_count: 0,
        scheduled_count: 2,
        delivery_percent: 88.0,
        target_date: targetDate3.toISOString().slice(0, 10),
        owner: 'Dev Ops Team',
        updated_at: new Date().toISOString()
      }
    ];

    const fallbackActivities: ActivityHomeRow[] = [
      {
        id: 'act-001',
        activity_type: 'cutover',
        title: 'Cutover approved',
        subject_type: 'migration',
        subject_id: 'mig-001',
        subject_name: 'ERP Core',
        status_text: 'Source quiesced · Write authority transferred',
        occurred_at: new Date(Date.now() - 4 * 60000).toISOString(),
        action_type: 'VIEW',
        severity: 'INFO'
      },
      {
        id: 'act-002',
        activity_type: 'validation',
        title: 'Validation certified',
        subject_type: 'validation',
        subject_id: 'val-002',
        subject_name: 'Customer Archive',
        status_text: 'Merkle root hash sealed · 0 discrepancies',
        occurred_at: new Date(Date.now() - 30 * 60000).toISOString(),
        action_type: 'VIEW',
        severity: 'SUCCESS'
      },
      {
        id: 'act-003',
        activity_type: 'approval',
        title: 'Approval requested',
        subject_type: 'migration',
        subject_id: 'mig-003',
        subject_name: 'Finance CDC',
        status_text: 'Waiting for SecOps maker-checker sign-off',
        occurred_at: new Date(Date.now() - 48 * 60000).toISOString(),
        action_type: 'REVIEW',
        severity: 'WARNING'
      },
      {
        id: 'act-004',
        activity_type: 'execution',
        title: 'Migration completed',
        subject_type: 'migration',
        subject_id: 'mig-005',
        subject_name: 'Customer Master',
        status_text: '10.4M rows committed across 64 partitions',
        occurred_at: new Date(Date.now() - 60 * 60000).toISOString(),
        action_type: 'VIEW',
        severity: 'INFO'
      }
    ];

    this.migrations.set(fallbackMigrations);
    this.projects.set(fallbackProjects);
    this.activities.set(fallbackActivities);
    this.summary.set({
      active_count: 2,
      attention_count: 1,
      scheduled_count: 1,
      completed_count: 1,
      total_count: 5,
      dynamic_headline: 'The next move is waiting on a decision.'
    });
  }
}
