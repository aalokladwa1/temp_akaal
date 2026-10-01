import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import {
  ValidationItemRow,
  ValidationAttentionItem,
  ValidationUpcomingRow,
  ValidationRecentResultRow,
  ValidationActivityRow,
  ValidationHomeSummary
} from '../models/validation-home.models';
import { MigrationIpc } from './ipc/migration.ipc';
import { IpcService } from './ipc.service';
import { ContextService } from './context.service';

export interface RelativeTimeFormatted {
  relative: string;
  exactTime: string;
}

@Injectable({
  providedIn: 'root'
})
export class ValidationHomeService {
  private migrationIpc: MigrationIpc;

  // Signals for state storage
  public validations = signal<ValidationItemRow[]>([]);
  public attentionItems = signal<ValidationAttentionItem[]>([]);
  public upcomingValidations = signal<ValidationUpcomingRow[]>([]);
  public recentResults = signal<ValidationRecentResultRow[]>([]);
  public activities = signal<ValidationActivityRow[]>([]);
  public summary = signal<ValidationHomeSummary | null>(null);

  public isLoading = signal<boolean>(false);
  public isUnavailable = signal<boolean>(false);
  public errorMessage = signal<string>('');

  // Filter & Search Signals
  public searchQuery = signal<string>('');
  public statusFilter = signal<string>('ALL');
  public strategyFilter = signal<string>('ALL');
  public kpiFilter = signal<string>('ALL');

  // Computed KPI Counters
  public computedCounters = computed(() => {
    const sum = this.summary();
    const list = this.validations();
    const attns = this.attentionItems();
    const upcomings = this.upcomingValidations();
    const recents = this.recentResults();

    if (sum) {
      return {
        active: sum.active_count,
        attention: sum.attention_count,
        scheduled: sum.scheduled_count,
        completed: sum.completed_count,
        total: sum.total_count
      };
    }

    const activeCount = list.filter(v => v.state === 'ACTIVE' || v.state === 'RUNNING').length;
    const attentionCount = attns.length || list.filter(v => v.state === 'ATTENTION' || (v.discrepancy_count ?? 0) > 0).length;
    const scheduledCount = upcomings.length || list.filter(v => v.state === 'SCHEDULED').length;
    const completedCount = recents.length || list.filter(v => v.state === 'COMPLETED' || v.outcome === 'Validated').length;

    return {
      active: activeCount,
      attention: attentionCount,
      scheduled: scheduledCount,
      completed: completedCount,
      total: list.length
    };
  });

  // Active Validations (Home Level Only)
  public activeValidations = computed(() => {
    return this.validations().filter(v => v.state === 'ACTIVE' || v.state === 'RUNNING');
  });

  // Filtered Validations Table
  public filteredValidations = computed(() => {
    let list = this.validations();
    const query = this.searchQuery().trim().toLowerCase();
    const status = this.statusFilter();
    const strategy = this.strategyFilter();
    const kpi = this.kpiFilter();

    // KPI filter applied
    if (kpi === 'ACTIVE') {
      list = list.filter(v => v.state === 'ACTIVE' || v.state === 'RUNNING');
    } else if (kpi === 'ATTENTION') {
      list = list.filter(v => v.state === 'ATTENTION' || (v.discrepancy_count ?? 0) > 0 || v.outcome === 'Discrepancies Found');
    } else if (kpi === 'SCHEDULED') {
      list = list.filter(v => v.state === 'SCHEDULED' || !!v.next_run);
    } else if (kpi === 'COMPLETED') {
      list = list.filter(v => v.state === 'COMPLETED' || v.outcome === 'Validated');
    }

    // Status filter
    if (status !== 'ALL') {
      list = list.filter(v => {
        if (status === 'VALIDATED') return v.outcome === 'Validated';
        if (status === 'DISCREPANCIES') return v.outcome === 'Discrepancies Found' || (v.discrepancy_count ?? 0) > 0;
        if (status === 'RUNNING') return v.state === 'RUNNING' || v.state === 'ACTIVE';
        if (status === 'SCHEDULED') return v.state === 'SCHEDULED';
        if (status === 'FAILED') return v.outcome === 'Execution Failed' || v.state === 'FAILED';
        return true;
      });
    }

    // Strategy filter
    if (strategy !== 'ALL') {
      list = list.filter(v => v.strategy?.toLowerCase() === strategy.toLowerCase());
    }

    // Search query
    if (query) {
      list = list.filter(v => {
        return (
          v.name.toLowerCase().includes(query) ||
          v.source_provider.toLowerCase().includes(query) ||
          v.target_provider.toLowerCase().includes(query) ||
          (v.strategy && v.strategy.toLowerCase().includes(query)) ||
          (v.outcome && v.outcome.toLowerCase().includes(query))
        );
      });
    }

    return list;
  });

  public cs?: ContextService;

  constructor(
    migrationIpc?: MigrationIpc,
    @Optional() contextService?: ContextService
  ) {
    if (migrationIpc) {
      this.migrationIpc = migrationIpc;
    } else {
      try {
        this.migrationIpc = inject(MigrationIpc, { optional: true }) || new MigrationIpc(new IpcService());
      } catch {
        this.migrationIpc = new MigrationIpc(new IpcService());
      }
    }
    try {
      this.cs = contextService || inject(ContextService, { optional: true }) || undefined;
    } catch {
      this.cs = contextService;
    }
    if (this.cs) {
      this.cs.onContextChange(() => {
        this.loadState();
      });
    }
    this.loadState();
  }

  public async loadState(): Promise<void> {
    this.isLoading.set(true);
    this.isUnavailable.set(false);
    this.errorMessage.set('');

    try {
      const res = await this.migrationIpc.listValidationMissions({ limit: 100 });
      if (res && res.status === 'SUCCESS' && res.data && Array.isArray((res.data as any).missions)) {
        const rawMissions = (res.data as any).missions as any[];
        const validations: ValidationItemRow[] = rawMissions.map(m => {
          let outcome: string | undefined = undefined;
          if (m.last_result_status === 'SUCCESS') outcome = 'Validated';
          else if (m.last_result_status === 'MISMATCH') outcome = 'Discrepancies Found';
          else if (m.state === 'FAILED') outcome = 'Execution Failed';
          else if (m.state === 'RUNNING') outcome = 'Running';
          else if (m.state === 'CANCELLED') outcome = 'Cancelled';
          else if (m.temporal_strategy === 'SCHEDULE_LATER' || m.schedule_id) outcome = 'Scheduled';

          const strategy = m.temporal_strategy === 'CONTINUOUS'
            ? 'Continuous CDC'
            : (m.temporal_strategy === 'RECURRING'
              ? 'Recurring Sync'
              : (m.execution_policy?.mode || 'Partition Fingerprint'));

          return {
            id: m.mission_id,
            name: m.name || 'Untitled Validation',
            source_provider: m.source_provider || 'Unknown',
            target_provider: m.target_provider || 'Unknown',
            strategy,
            state: m.state || 'DRAFT',
            outcome,
            last_run: m.last_evaluated_at || m.updated_at,
            next_run: (m.temporal_strategy === 'SCHEDULE_LATER' || m.temporal_strategy === 'RECURRING' || m.schedule_id) ? m.updated_at : undefined,
            discrepancy_count: m.fail_count || 0,
            description: m.scope_config?.table_name ? `Table: ${m.scope_config.table_name}` : undefined
          };
        });

        const attentionItems: ValidationAttentionItem[] = [];
        const upcomingValidations: ValidationUpcomingRow[] = [];
        const recentResults: ValidationRecentResultRow[] = [];
        const activities: ValidationActivityRow[] = [];

        rawMissions.forEach(m => {
          if (m.state === 'FAILED' || m.last_result_status === 'MISMATCH' || (m.fail_count && m.fail_count > 0)) {
            attentionItems.push({
              id: `attn-${m.mission_id}`,
              validation_id: m.mission_id,
              validation_name: m.name || m.mission_id,
              title: m.last_result_status === 'MISMATCH' ? 'Discrepancies Detected' : (m.last_result_status?.startsWith('READINESS_FAILED') ? 'Readiness Check Failed' : 'Validation Failed'),
              description: m.last_result_status || 'Validation execution encountered issues.',
              severity: m.last_result_status === 'MISMATCH' ? 'WARNING' : 'CRITICAL',
              action_label: m.last_result_status === 'MISMATCH' ? 'Review Discrepancies' : 'Investigate',
              action_route: `/migration/validation/${m.mission_id}`,
              created_at: m.last_evaluated_at || m.updated_at || new Date().toISOString()
            });
          }

          if (m.temporal_strategy === 'SCHEDULE_LATER' || m.temporal_strategy === 'RECURRING' || m.schedule_id) {
            upcomingValidations.push({
              id: m.mission_id,
              name: m.name || m.mission_id,
              source_provider: m.source_provider || 'Unknown',
              target_provider: m.target_provider || 'Unknown',
              strategy: m.temporal_strategy,
              next_run: m.updated_at || new Date().toISOString(),
              schedule_state: m.state === 'PAUSED' ? 'PAUSED' : 'SCHEDULED'
            });
          }

          if (m.last_evaluated_at) {
            recentResults.push({
              id: `res-${m.mission_id}`,
              validation_id: m.mission_id,
              name: m.name || m.mission_id,
              source_provider: m.source_provider || 'Unknown',
              target_provider: m.target_provider || 'Unknown',
              outcome: m.last_result_status === 'SUCCESS' ? 'Validated' : (m.last_result_status === 'MISMATCH' ? 'Discrepancies Found' : 'Execution Failed'),
              completed_at: m.last_evaluated_at,
              discrepancies: m.fail_count || 0
            });
          }

          activities.push({
            id: `act-${m.mission_id}`,
            title: m.state === 'COMPLETED' ? 'Validation Completed' : (m.state === 'RUNNING' ? 'Validation Running' : 'Mission Updated'),
            validation_id: m.mission_id,
            validation_name: m.name || m.mission_id,
            status_text: m.last_result_status || m.state || 'Updated',
            occurred_at: m.last_evaluated_at || m.updated_at || new Date().toISOString(),
            action_type: m.last_result_status === 'MISMATCH' ? 'REVIEW' : 'VIEW',
            severity: m.last_result_status === 'SUCCESS' ? 'SUCCESS' : (m.last_result_status === 'MISMATCH' ? 'WARNING' : (m.state === 'FAILED' ? 'ERROR' : 'INFO'))
          });
        });

        const summary: ValidationHomeSummary = {
          active_count: validations.filter(v => v.state === 'ACTIVE' || v.state === 'RUNNING').length,
          attention_count: attentionItems.length,
          scheduled_count: upcomingValidations.length,
          completed_count: recentResults.length,
          total_count: validations.length
        };

        this.validations.set(validations);
        this.attentionItems.set(attentionItems);
        this.upcomingValidations.set(upcomingValidations);
        this.recentResults.set(recentResults);
        this.activities.set(activities);
        this.summary.set(summary);
        this.isUnavailable.set(false);
        return;
      }

      // Restrained default baseline state for standalone/development mode
      this.loadBaselineState();
    } catch (err: any) {
      console.error('[ValidationHomeService] Error loading validation state:', err);
      this.isUnavailable.set(true);
      this.errorMessage.set('Validation operations data is unavailable.');
    } finally {
      this.isLoading.set(false);
    }
  }

  public loadBaselineState(): void {
    this.validations.set([]);
    this.attentionItems.set([]);
    this.upcomingValidations.set([]);
    this.recentResults.set([]);
    this.activities.set([]);
    this.summary.set(null);
  }

  // Time formatting helper utilities
  public formatRelativeTime(isoString?: string): RelativeTimeFormatted {
    if (!isoString) return { relative: '—', exactTime: '—' };
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return { relative: isoString, exactTime: isoString };

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHours = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHours / 24);

    let relative = '';
    if (diffMs < 0) {
      const futureMin = Math.abs(Math.floor(diffMs / 60000));
      const futureHours = Math.floor(futureMin / 60);
      if (futureMin < 60) relative = `in ${futureMin}m`;
      else if (futureHours < 24) relative = `in ${futureHours}h`;
      else relative = `in ${Math.floor(futureHours / 24)}d`;
    } else if (diffSec < 60) {
      relative = 'just now';
    } else if (diffMin < 60) {
      relative = `${diffMin}m ago`;
    } else if (diffHours < 24) {
      relative = `${diffHours}h ago`;
    } else {
      relative = `${diffDays}d ago`;
    }

    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');
    const exactTime = `${hours}:${minutes}:${seconds} UTC`;

    return { relative, exactTime };
  }

  public formatDate(isoString?: string): string {
    if (!isoString) return '—';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  }
}
