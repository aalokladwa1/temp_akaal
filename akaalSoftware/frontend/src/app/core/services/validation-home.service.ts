import { Injectable, signal, computed } from '@angular/core';
import {
  ValidationItemRow,
  ValidationAttentionItem,
  ValidationUpcomingRow,
  ValidationRecentResultRow,
  ValidationActivityRow,
  ValidationHomeSummary
} from '../models/validation-home.models';

export interface RelativeTimeFormatted {
  relative: string;
  exactTime: string;
}

@Injectable({
  providedIn: 'root'
})
export class ValidationHomeService {
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

  constructor() {
    this.loadState();
  }

  public async loadState(): Promise<void> {
    this.isLoading.set(true);
    this.isUnavailable.set(false);
    this.errorMessage.set('');

    try {
      // IPC hooks when running inside Wails environment
      const wailsApp = typeof window !== 'undefined' ? (window as any).go?.main?.App : undefined;

      if (wailsApp && typeof wailsApp.GetValidationHomeData === 'function') {
        const data = await wailsApp.GetValidationHomeData();
        if (data) {
          this.summary.set(data.summary || null);
          this.validations.set(data.validations || []);
          this.attentionItems.set(data.attention_items || []);
          this.upcomingValidations.set(data.upcoming || []);
          this.recentResults.set(data.recent_results || []);
          this.activities.set(data.activities || []);
          return;
        }
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
    const now = Date.now();
    const iso = (offsetMs: number) => new Date(now + offsetMs).toISOString();

    const sampleValidations: ValidationItemRow[] = [
      {
        id: 'val-001',
        name: 'Enterprise Customer Data Verification',
        source_provider: 'Oracle',
        target_provider: 'PostgreSQL',
        strategy: 'Sync',
        state: 'RUNNING',
        outcome: 'Running',
        last_run: iso(-15 * 60 * 1000), // 15 mins ago
        next_run: iso(6 * 3600 * 1000), // in 6 hours
        progress_percent: 68,
        discrepancy_count: 0,
        elapsed_time: '4m 12s',
        description: 'Post-migration schema and record parity check'
      },
      {
        id: 'val-002',
        name: 'Core Banking Ledger Verification',
        source_provider: 'Oracle',
        target_provider: 'PostgreSQL',
        strategy: 'Async',
        state: 'ATTENTION',
        outcome: 'Discrepancies Found',
        last_run: iso(-45 * 60 * 1000), // 45 mins ago
        next_run: iso(12 * 3600 * 1000), // in 12 hours
        discrepancy_count: 18,
        elapsed_time: '2m 08s',
        description: 'Pre-cutover ledger consistency verification'
      },
      {
        id: 'val-003',
        name: 'Product Catalog Parity Audit',
        source_provider: 'MySQL',
        target_provider: 'Snowflake',
        strategy: 'Sync',
        state: 'COMPLETED',
        outcome: 'Validated',
        last_run: iso(-4 * 3600 * 1000), // 4 hours ago
        next_run: iso(20 * 3600 * 1000), // in 20 hours
        discrepancy_count: 0,
        elapsed_time: '1m 45s',
        description: 'Scheduled structural and row parity verification'
      },
      {
        id: 'val-004',
        name: 'Global Inventory State Check',
        source_provider: 'Microsoft SQL Server',
        target_provider: 'PostgreSQL',
        strategy: 'Async',
        state: 'SCHEDULED',
        outcome: 'Scheduled',
        last_run: iso(-14 * 3600 * 1000), // 14 hours ago
        next_run: iso(8 * 3600 * 1000), // in 8 hours
        discrepancy_count: 0,
        description: 'Nightly incremental partition validation'
      },
      {
        id: 'val-005',
        name: 'Payments Archive Parity Run',
        source_provider: 'IBM Db2',
        target_provider: 'Amazon Redshift',
        strategy: 'Sync',
        state: 'COMPLETED',
        outcome: 'Validated',
        last_run: iso(-6 * 3600 * 1000), // 6 hours ago
        next_run: iso(18 * 3600 * 1000), // in 18 hours
        discrepancy_count: 0,
        elapsed_time: '6m 20s',
        description: 'Historical archive verification'
      }
    ];

    const sampleAttention: ValidationAttentionItem[] = [
      {
        id: 'attn-001',
        validation_id: 'val-002',
        validation_name: 'Core Banking Ledger Verification',
        title: 'Discrepancies Detected',
        description: '18 mismatched rows identified during ledger comparison.',
        severity: 'HIGH',
        action_label: 'Review Discrepancies',
        action_route: '/migration/validation/val-002',
        created_at: iso(-44 * 60 * 1000)
      }
    ];

    const sampleUpcoming: ValidationUpcomingRow[] = [
      {
        id: 'up-001',
        name: 'Global Inventory State Check',
        source_provider: 'Microsoft SQL Server',
        target_provider: 'PostgreSQL',
        strategy: 'Async',
        next_run: iso(8 * 3600 * 1000),
        schedule_state: 'ACTIVE'
      },
      {
        id: 'up-002',
        name: 'Product Catalog Parity Audit',
        source_provider: 'MySQL',
        target_provider: 'Snowflake',
        strategy: 'Sync',
        next_run: iso(20 * 3600 * 1000),
        schedule_state: 'ACTIVE'
      }
    ];

    const sampleRecentResults: ValidationRecentResultRow[] = [
      {
        id: 'res-001',
        validation_id: 'val-003',
        name: 'Product Catalog Parity Audit',
        source_provider: 'MySQL',
        target_provider: 'Snowflake',
        outcome: 'Validated',
        completed_at: iso(-4 * 3600 * 1000),
        discrepancies: 0
      },
      {
        id: 'res-002',
        validation_id: 'val-005',
        name: 'Payments Archive Parity Run',
        source_provider: 'IBM Db2',
        target_provider: 'Amazon Redshift',
        outcome: 'Validated',
        completed_at: iso(-6 * 3600 * 1000),
        discrepancies: 0
      },
      {
        id: 'res-003',
        validation_id: 'val-002',
        name: 'Core Banking Ledger Verification',
        source_provider: 'Oracle',
        target_provider: 'PostgreSQL',
        outcome: 'Discrepancies Found',
        completed_at: iso(-45 * 60 * 1000),
        discrepancies: 18
      }
    ];

    const sampleActivities: ValidationActivityRow[] = [
      {
        id: 'act-001',
        title: 'Validation Started',
        validation_id: 'val-001',
        validation_name: 'Enterprise Customer Data Verification',
        status_text: 'Running sync validation between Oracle and PostgreSQL',
        occurred_at: iso(-15 * 60 * 1000),
        action_type: 'OPEN',
        severity: 'INFO'
      },
      {
        id: 'act-002',
        title: 'Discrepancies Identified',
        validation_id: 'val-002',
        validation_name: 'Core Banking Ledger Verification',
        status_text: '18 row differences found during async comparison',
        occurred_at: iso(-45 * 60 * 1000),
        action_type: 'REVIEW',
        severity: 'WARNING'
      },
      {
        id: 'act-003',
        title: 'Validation Completed',
        validation_id: 'val-003',
        validation_name: 'Product Catalog Parity Audit',
        status_text: 'Completed with 0 discrepancies detected',
        occurred_at: iso(-4 * 3600 * 1000),
        action_type: 'VIEW',
        severity: 'SUCCESS'
      }
    ];

    this.validations.set(sampleValidations);
    this.attentionItems.set(sampleAttention);
    this.upcomingValidations.set(sampleUpcoming);
    this.recentResults.set(sampleRecentResults);
    this.activities.set(sampleActivities);
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
