import { Injectable, signal, computed, Optional } from '@angular/core';
import { DashboardService } from './dashboard.service';

export interface Organization {
  id: string;
  name: string;
  description?: string;
}

export interface Workspace {
  id: string;
  orgId: string;
  name: string;
  description?: string;
}

export interface Environment {
  id: string;
  workspaceId: string;
  name: string;
  isProduction?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ContextService {
  // Available Data (Loaded from backend when contracts exist, empty otherwise)
  public organizations = signal<Organization[]>([]);
  public workspaces = signal<Workspace[]>([]);
  public environments = signal<Environment[]>([]);

  // Selected State
  public selectedOrg = signal<Organization | null>(null);
  public selectedWorkspace = signal<Workspace | null>(null);
  public selectedEnvironment = signal<Environment | null>(null);

  // Computed / Derived State
  public isProduction = computed(() => this.selectedEnvironment()?.isProduction ?? false);

  public availableWorkspacesForOrg = computed(() => {
    const currentOrg = this.selectedOrg();
    if (!currentOrg) return [];
    return this.workspaces().filter(w => w.orgId === currentOrg.id);
  });

  public availableEnvironmentsForWorkspace = computed(() => {
    const currentWs = this.selectedWorkspace();
    if (!currentWs) return [];
    return this.environments().filter(e => e.workspaceId === currentWs.id);
  });

  public effectiveContextLabel = computed(() => {
    const org = this.selectedOrg()?.name || 'No Org';
    const ws = this.selectedWorkspace()?.name || 'No Workspace';
    const env = this.selectedEnvironment()?.name || 'No Env';
    return `${org} / ${ws} / ${env}`;
  });

  constructor(@Optional() private ds?: DashboardService) {}

  /**
   * Selects an Organization and invalidates any child Workspace/Environment that is no longer valid.
   */
  public selectOrganization(org: Organization | null): void {
    this.selectedOrg.set(org);

    // Child context invalidation
    if (!org) {
      this.selectedWorkspace.set(null);
      this.selectedEnvironment.set(null);
    } else {
      const validWs = this.workspaces().filter(w => w.orgId === org.id);
      const currentWs = this.selectedWorkspace();
      if (!currentWs || !validWs.some(w => w.id === currentWs.id)) {
        this.selectedWorkspace.set(null);
        this.selectedEnvironment.set(null);
      }
    }

    // Refresh context-dependent dashboard data
    this.ds?.refreshDashboard();
  }

  /**
   * Selects a Workspace and invalidates any child Environment that is no longer valid.
   */
  public selectWorkspace(ws: Workspace | null): void {
    this.selectedWorkspace.set(ws);

    // Child context invalidation
    if (!ws) {
      this.selectedEnvironment.set(null);
    } else {
      const validEnvs = this.environments().filter(e => e.workspaceId === ws.id);
      const currentEnv = this.selectedEnvironment();
      if (!currentEnv || !validEnvs.some(e => e.id === currentEnv.id)) {
        this.selectedEnvironment.set(null);
      }
    }

    // Refresh context-dependent dashboard data
    this.ds?.refreshDashboard();
  }

  /**
   * Selects an Environment.
   */
  public selectEnvironment(env: Environment | null): void {
    this.selectedEnvironment.set(env);
    this.ds?.refreshDashboard();
  }
}
