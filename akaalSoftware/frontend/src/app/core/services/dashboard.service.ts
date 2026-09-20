import { Injectable, inject, signal, computed } from '@angular/core';
import { IpcService } from './ipc.service';
import { DashboardSummary, DashboardStatus } from '../models/dashboard.models';
import { generateGreetingContext, GreetingContext } from '../tokens/phrase.generator';

export function isValidDashboardSummary(data: any): data is DashboardSummary {
  if (!data || typeof data !== 'object') return false;
  // If it's a generic IPC envelope fallback without domain fields, reject as non-domain
  if (data.channel && data.endpoint && data.action && !Array.isArray(data.activeMigrations) && data.runningCount === undefined) {
    return false;
  }
  // Ensure array collections are valid arrays if present
  if (data.activeMigrations !== undefined && !Array.isArray(data.activeMigrations)) return false;
  if (data.attentionItems !== undefined && !Array.isArray(data.attentionItems)) return false;
  if (data.subsystems !== undefined && !Array.isArray(data.subsystems)) return false;
  if (data.pendingApprovals !== undefined && !Array.isArray(data.pendingApprovals)) return false;
  if (data.capacityMetrics !== undefined && !Array.isArray(data.capacityMetrics)) return false;
  if (data.incidents !== undefined && !Array.isArray(data.incidents)) return false;
  if (data.recentEvents !== undefined && !Array.isArray(data.recentEvents)) return false;
  return true;
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private ipc: IpcService;

  constructor(ipc?: IpcService) {
    this.ipc = ipc || (inject(IpcService, { optional: true }) as IpcService);
  }

  public userName = signal<string>('Aalok');
  public status = signal<DashboardStatus>('initial');
  public isLoading = signal<boolean>(false);
  public lastError = signal<string | null>(null);

  // Truthful initial state: null until valid domain data arrives from authoritative engine IPC
  public dashboardData = signal<DashboardSummary | null>(null);

  // Deterministically computed greeting context
  public greetingContext = computed<GreetingContext>(() => {
    return generateGreetingContext(
      this.userName(),
      this.dashboardData(),
      this.ipc.connectionState()
    );
  });

  // Daemon takes a variable amount of time to bind its IPC socket on cold start;
  // a single ENGINE_DISCONNECTED is expected startup noise, not a real failure.
  private readonly engineStartupRetries = 5;
  private readonly engineStartupRetryDelayMs = 1000;

  public async refreshDashboard(): Promise<void> {
    this.isLoading.set(true);
    this.lastError.set(null);
    try {
      if (this.ipc.connectionState() === 'disconnected') {
        if (!this.dashboardData()) {
          this.status.set('unavailable');
        }
        this.lastError.set('IPC connection is offline');
        return;
      }

      let res = await this.ipc.invoke<DashboardSummary>('dashboard', 'get_estate_summary');
      for (
        let attempt = 0;
        attempt < this.engineStartupRetries && res.status === 'ERROR' && res.error?.startsWith('ENGINE_DISCONNECTED');
        attempt++
      ) {
        await new Promise(resolve => setTimeout(resolve, this.engineStartupRetryDelayMs));
        res = await this.ipc.invoke<DashboardSummary>('dashboard', 'get_estate_summary');
      }

      if (res.status === 'SUCCESS' && isValidDashboardSummary(res.data)) {
        const normalized: DashboardSummary = {
          runningCount: res.data.runningCount ?? null,
          scheduledCount: res.data.scheduledCount ?? null,
          attentionCount: res.data.attentionCount ?? null,
          completedTodayCount: res.data.completedTodayCount ?? null,
          activeMigrations: Array.isArray(res.data.activeMigrations) ? res.data.activeMigrations : [],
          attentionItems: Array.isArray(res.data.attentionItems) ? res.data.attentionItems : [],
          subsystems: Array.isArray(res.data.subsystems) ? res.data.subsystems : [],
          pendingApprovals: Array.isArray(res.data.pendingApprovals) ? res.data.pendingApprovals : [],
          capacityMetrics: Array.isArray(res.data.capacityMetrics) ? res.data.capacityMetrics : [],
          incidents: Array.isArray(res.data.incidents) ? res.data.incidents : [],
          fleet: res.data.fleet ?? null,
          security: res.data.security ?? null,
          recentEvents: Array.isArray(res.data.recentEvents) ? res.data.recentEvents : []
        };
        this.dashboardData.set(normalized);
        this.status.set('available');
      } else if (res.status === 'ERROR') {
        this.lastError.set(res.error || 'Failed to refresh dashboard');
        if (!this.dashboardData()) {
          this.status.set('error');
        }
      } else {
        // Non-domain or developmental mock envelope without domain telemetry
        if (!this.dashboardData()) {
          this.status.set('unavailable');
        }
      }
    } catch (err: any) {
      this.lastError.set(err?.message || 'Failed to refresh dashboard');
      if (!this.dashboardData()) {
        this.status.set('error');
      }
    } finally {
      this.isLoading.set(false);
    }
  }
}
