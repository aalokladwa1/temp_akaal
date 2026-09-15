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
