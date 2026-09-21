import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import { ContextService } from '../../core/services/context.service';
import { IpcService } from '../../core/services/ipc.service';
import { MigrationIpc } from '../../core/services/ipc/migration.ipc';
import {
  ConnectionRecord,
  ConnectionFamily,
  ConnectionVerificationState,
  ConnectionRoleApplicability,
  EntityAvailabilityState,
  ConnectionFilterState,
  ConnectionSortField,
  SortDirection,
  ConnectionSummaryCounters
} from './connections.models';
import { FIXTURE_STANDARD_CONNECTIONS } from './connections.fixtures';

@Injectable({
  providedIn: 'root'
})
export class ConnectionsService {
  public cs: ContextService;
  private ipc: IpcService;
  private migrationIpc: MigrationIpc;

  constructor(
    @Optional() contextService?: ContextService,
    migrationIpc?: MigrationIpc,
    ipc?: IpcService
  ) {
    this.cs = contextService || new ContextService();
    try { this.ipc = ipc || inject(IpcService); } catch { this.ipc = ipc || new IpcService(); }
    try { this.migrationIpc = migrationIpc || inject(MigrationIpc); } catch { this.migrationIpc = migrationIpc || new MigrationIpc(this.ipc); }
  }

  // Primary Data Store Signals (Neutral truthful production startup: B-2.2-01)
  public connections = signal<ConnectionRecord[]>([]);
  public availabilityState = signal<EntityAvailabilityState>('NOT_CONNECTED');
  public errorMessage = signal<string | null>(null);

  // Filter & Search State Signal
  public filters = signal<ConnectionFilterState>({
    searchQuery: '',
    family: 'ALL',
    verificationState: 'ALL',
    usageFilter: 'ALL',
    environment: 'ALL',
    role: 'ALL',
    sortBy: 'name',
    sortDirection: 'asc'
  });

  // Selected Connection for slide-over inspection drawer
  public selectedConnection = signal<ConnectionRecord | null>(null);
  public isInspectDrawerOpen = signal<boolean>(false);
  public isVerifyingConnectionId = signal<string | null>(null);

  // ==========================================================================
  // COMPUTED SIGNALS
  // ==========================================================================

  public filteredConnections = computed<ConnectionRecord[]>(() => {
    const all = this.connections();
    const f = this.filters();
    const query = f.searchQuery.trim().toLowerCase();

    let result = all.filter((conn) => {
      // 1. Search Query (Name, Provider, Family, Endpoint, Tags, Environment, Safe Route)
      if (query) {
        const matchesName = conn.name.toLowerCase().includes(query);
        const matchesProvider = conn.providerName.toLowerCase().includes(query) || conn.providerId.toLowerCase().includes(query);
        const matchesFamily = conn.family.toLowerCase().includes(query);
        const matchesEndpoint = conn.endpointDisplay.toLowerCase().includes(query);
        const matchesEnv = conn.environment.toLowerCase().includes(query);
        const matchesRoute = conn.safeRouteInfo ? conn.safeRouteInfo.toLowerCase().includes(query) : false;
        const matchesTags = conn.tags ? conn.tags.some(t => t.toLowerCase().includes(query)) : false;
        const matchesProjects = conn.usage.projectNames ? conn.usage.projectNames.some(p => p.toLowerCase().includes(query)) : false;

        if (!matchesName && !matchesProvider && !matchesFamily && !matchesEndpoint && !matchesEnv && !matchesRoute && !matchesTags && !matchesProjects) {
          return false;
        }
      }

      // 2. Family Filter
      if (f.family !== 'ALL' && conn.family !== f.family) {
        return false;
      }

      // 3. Verification State Filter
      if (f.verificationState !== 'ALL') {
        if (f.verificationState === 'VERIFIED_GROUP') {
          if (conn.verificationState !== 'VERIFIED_RECENT' && conn.verificationState !== 'VERIFIED_POINT_IN_TIME') {
            return false;
          }
        } else if (f.verificationState === 'ATTENTION_GROUP') {
          if (conn.verificationState !== 'VERIFICATION_FAILED' &&
              conn.verificationState !== 'VERIFIED_STALE' &&
              conn.verificationState !== 'CONFIG_CHANGED_SINCE_TEST') {
            return false;
          }
        } else if (conn.verificationState !== f.verificationState) {
          return false;
        }
      }

      // 4. Usage Filter
      if (f.usageFilter !== 'ALL') {
        if (f.usageFilter === 'IN_USE') {
          if (conn.usage.activeMigrationCount === 0 && conn.usage.activeValidationCount === 0) return false;
        } else if (f.usageFilter === 'REFERENCED_PROJECTS') {
          if (conn.usage.referencedProjectCount === 0) return false;
        } else if (f.usageFilter === 'UNUSED') {
          if (!conn.usage.isUnused) return false;
        } else if (f.usageFilter === 'UNKNOWN') {
          if (conn.usage.usageAvailable) return false;
        }
      }

      // 5. Environment Filter
      if (f.environment !== 'ALL' && conn.environment !== f.environment) {
        return false;
      }

      // 6. Role Applicability Filter
      if (f.role !== 'ALL' && conn.roleApplicability !== f.role) {
        return false;
      }

      return true;
    });

    // Sort Result Deterministically
    result = [...result].sort((a, b) => {
      let cmp = 0;
      switch (f.sortBy) {
        case 'name':
          cmp = a.name.localeCompare(b.name);
          break;
        case 'provider':
          cmp = a.providerName.localeCompare(b.providerName);
          break;
        case 'family':
          cmp = a.family.localeCompare(b.family);
          break;
        case 'lastVerified': {
          const tA = a.lastVerifiedAt ? new Date(a.lastVerifiedAt).getTime() : 0;
          const tB = b.lastVerifiedAt ? new Date(b.lastVerifiedAt).getTime() : 0;
          cmp = tA - tB;
          break;
        }
        case 'updatedAt': {
          const tA = new Date(a.updatedAt).getTime();
          const tB = new Date(b.updatedAt).getTime();
          cmp = tA - tB;
          break;
        }
        case 'usageCount': {
          const uA = (a.usage.activeMigrationCount || 0) + (a.usage.activeValidationCount || 0);
          const uB = (b.usage.activeMigrationCount || 0) + (b.usage.activeValidationCount || 0);
          cmp = uA - uB;
          break;
        }
        default:
          cmp = a.name.localeCompare(b.name);
      }
      return f.sortDirection === 'desc' ? -cmp : cmp;
    });

    return result;
  });

  public summaryCounters = computed<ConnectionSummaryCounters>(() => {
    const all = this.connections();
    let verified = 0;
    let needsAttention = 0;
    let unused = 0;
    let testing = 0;

    for (const c of all) {
      if (c.verificationState === 'VERIFIED_RECENT' || c.verificationState === 'VERIFIED_POINT_IN_TIME') {
        verified++;
      } else if (c.verificationState === 'VERIFICATION_FAILED' ||
                 c.verificationState === 'VERIFIED_STALE' ||
                 c.verificationState === 'CONFIG_CHANGED_SINCE_TEST') {
        needsAttention++;
      } else if (c.verificationState === 'TESTING') {
        testing++;
      }

      if (c.usage.isUnused) {
        unused++;
      }
    }

    return {
      total: all.length,
      verified,
      needsAttention,
      unused,
      testing
    };
  });

  public activeFilterCount = computed<number>(() => {
    const f = this.filters();
    let count = 0;
    if (f.searchQuery.trim()) count++;
    if (f.family !== 'ALL') count++;
    if (f.verificationState !== 'ALL') count++;
    if (f.usageFilter !== 'ALL') count++;
    if (f.environment !== 'ALL') count++;
    if (f.role !== 'ALL') count++;
    return count;
  });

  public isFiltered = computed<boolean>(() => {
    return this.activeFilterCount() > 0;
  });

  // ==========================================================================
  // FILTER MUTATORS
  // ==========================================================================

  public setSearchQuery(q: string): void {
    this.filters.update(curr => ({ ...curr, searchQuery: q }));
  }

  public setFamilyFilter(family: ConnectionFamily | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, family }));
  }

  public setVerificationFilter(verificationState: ConnectionVerificationState | 'ALL' | 'VERIFIED_GROUP' | 'ATTENTION_GROUP'): void {
    this.filters.update(curr => ({ ...curr, verificationState }));
  }

  public setUsageFilter(usageFilter: 'ALL' | 'IN_USE' | 'REFERENCED_PROJECTS' | 'UNUSED' | 'UNKNOWN'): void {
    this.filters.update(curr => ({ ...curr, usageFilter }));
  }

  public setEnvironmentFilter(environment: 'ALL' | 'Production' | 'Staging' | 'Development'): void {
    this.filters.update(curr => ({ ...curr, environment }));
  }

  public setRoleFilter(role: 'ALL' | ConnectionRoleApplicability): void {
    this.filters.update(curr => ({ ...curr, role }));
  }

  public setSort(field: ConnectionSortField, dir?: SortDirection): void {
    this.filters.update(curr => ({
      ...curr,
      sortBy: field,
      sortDirection: dir || (curr.sortBy === field && curr.sortDirection === 'asc' ? 'desc' : 'asc')
    }));
  }

  public toggleSort(field: ConnectionSortField): void {
    this.setSort(field);
  }

  public clearFilters(): void {
    this.filters.update(curr => ({
      ...curr,
      searchQuery: '',
      family: 'ALL',
      verificationState: 'ALL',
      usageFilter: 'ALL',
      environment: 'ALL',
      role: 'ALL'
    }));
  }

  // ==========================================================================
  // SELECTION & DRAWER
  // ==========================================================================

  public openInspectDrawer(conn: ConnectionRecord): void {
    this.selectedConnection.set(conn);
    this.isInspectDrawerOpen.set(true);
  }

  public closeInspectDrawer(): void {
    this.isInspectDrawerOpen.set(false);
    this.selectedConnection.set(null);
  }

  // Production IPC State Loader & Mapper
  public async loadState(): Promise<void> {
    if (this.ipc.connectionState() === 'disconnected') {
      this.availabilityState.set('NOT_CONNECTED');
      this.errorMessage.set('Connection service is currently disconnected.');
      return;
    }

    this.availabilityState.set('LOADING');
    this.errorMessage.set(null);

    try {
      const res = await this.migrationIpc.listConnections();
      if (res.status === 'SUCCESS' && res.data) {
        const rawList = Array.isArray(res.data.connections)
          ? res.data.connections
          : (Array.isArray(res.data) ? res.data : []);
        
        const mapped: ConnectionRecord[] = rawList.map((item: any) => this.mapBackendConnection(item));
        this.connections.set(mapped);
        this.availabilityState.set(mapped.length > 0 ? 'READY' : 'EMPTY');
      } else if (res.status === 'ERROR') {
        this.availabilityState.set('NOT_CONNECTED');
        this.errorMessage.set(res.error || 'Failed to fetch connections');
      } else {
        this.availabilityState.set('NOT_CONNECTED');
      }
    } catch (err: any) {
      this.availabilityState.set('NOT_CONNECTED');
      this.errorMessage.set(err?.message || 'Failed to load connections from backend IPC');
    }
  }

  private mapBackendConnection(item: any): ConnectionRecord {
    return {
      id: item.id || item.connection_id || `conn-${Math.random().toString(36).substring(2, 7)}`,
      name: item.name || item.connection_name || 'Unnamed Connection',
      description: item.description,
      providerId: item.providerId || item.provider_id || 'postgresql',
      providerName: item.providerName || item.provider_name || item.providerId || 'PostgreSQL',
      family: item.family || 'RELATIONAL',
      environment: item.environment || 'Production',
      workspaceId: item.workspaceId || item.workspace_id || 'default-workspace',
      workspaceName: item.workspaceName || item.workspace_name,
      organizationId: item.organizationId || item.organization_id || 'default-tenant',
      endpointDisplay: item.endpointDisplay || item.endpoint || item.host || '127.0.0.1:5432',
      safeRouteInfo: item.safeRouteInfo || item.route,
      tlsMode: item.tlsMode || 'TLS_1_3',
      authMethodDisplay: item.authMethodDisplay || item.auth_method || 'IAM Token / Secret Vault',
      roleApplicability: item.roleApplicability || 'SOURCE_AND_TARGET',
      verificationState: item.verificationState || (item.status === 'ACTIVE' ? 'VERIFIED_RECENT' : 'NEVER_TESTED'),
      lastVerifiedAt: item.lastVerifiedAt || item.last_verified_at || null,
      lastVerifiedDetails: item.lastVerifiedDetails || item.last_verified_details,
      createdAt: item.createdAt || item.created_at || new Date().toISOString(),
      updatedAt: item.updatedAt || item.updated_at || new Date().toISOString(),
      usage: item.usage || {
        referencedProjectCount: 0,
        activeMigrationCount: 0,
        activeValidationCount: 0,
        isUnused: true,
        usageAvailable: true
      },
      tags: item.tags || []
    };
  }

  // Truthful Verification Handling (Invokes canonical connection.test IPC)
  public verifyConnection(connId: string): void {
    this.triggerPointInTimeVerification(connId);
  }

  public async triggerPointInTimeVerification(connId: string): Promise<void> {
    this.isVerifyingConnectionId.set(connId);
    try {
      const res = await this.migrationIpc.testConnection({ connection_id: connId });
      if (res.status === 'SUCCESS') {
        this.connections.update(list => list.map(c => {
          if (c.id === connId) {
            const updated: ConnectionRecord = {
              ...c,
              verificationState: 'VERIFIED_RECENT',
              lastVerifiedAt: new Date().toISOString(),
              lastVerifiedDetails: 'Point-in-time verification succeeded through backend IPC.'
            };
            if (this.selectedConnection()?.id === connId) {
              this.selectedConnection.set(updated);
            }
            return updated;
          }
          return c;
        }));
      } else {
        this.connections.update(list => list.map(c => {
          if (c.id === connId) {
            const updated: ConnectionRecord = {
              ...c,
              verificationState: 'VERIFICATION_FAILED',
              lastVerifiedDetails: res.error || 'Connection probe failed.'
            };
            if (this.selectedConnection()?.id === connId) {
              this.selectedConnection.set(updated);
            }
            return updated;
          }
          return c;
        }));
      }
    } catch (err: any) {
      this.connections.update(list => list.map(c => {
        if (c.id === connId) {
          const updated: ConnectionRecord = {
            ...c,
            verificationState: 'VERIFICATION_FAILED',
            lastVerifiedDetails: err?.message || 'Connection test failed.'
          };
          if (this.selectedConnection()?.id === connId) {
            this.selectedConnection.set(updated);
          }
          return updated;
        }
        return c;
      }));
    } finally {
      this.isVerifyingConnectionId.set(null);
    }
  }

  public async createConnection(payload: any): Promise<boolean> {
    try {
      const res = await this.migrationIpc.createConnection(payload);
      if (res.status === 'SUCCESS') {
        await this.loadState();
        return true;
      }
      this.errorMessage.set(res.error || 'Failed to create connection');
      return false;
    } catch (err: any) {
      this.errorMessage.set(err?.message || 'Error creating connection');
      return false;
    }
  }

  public setSorting(field: ConnectionSortField, dir?: SortDirection): void {
    this.setSort(field, dir);
  }

  /**
   * Explicit test-only fixture loader for test suites & Playwright harnesses (§53)
   */
  public loadFixturesForTesting(): void {
    this.connections.set([...FIXTURE_STANDARD_CONNECTIONS]);
    this.clearFilters();
    this.availabilityState.set('READY');
    this.errorMessage.set(null);
    this.selectedConnection.set(null);
    this.isInspectDrawerOpen.set(false);
    this.isVerifyingConnectionId.set(null);
  }

  public resetToFixtures(): void {
    this.loadFixturesForTesting();
  }

  public reload(): void {
    this.loadState();
  }

  public setMockAvailability(state: EntityAvailabilityState, msg?: string): void {
    this.availabilityState.set(state);
    this.errorMessage.set(msg || null);
  }

  public retryConnection(): void {
    this.loadState();
  }
}
