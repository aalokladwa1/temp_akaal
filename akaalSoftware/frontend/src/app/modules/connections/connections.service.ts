import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import { ContextService } from '../../core/services/context.service';
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

  constructor(@Optional() contextService?: ContextService) {
    this.cs = contextService || new ContextService();
  }

  // Primary Data Store Signals
  public connections = signal<ConnectionRecord[]>(FIXTURE_STANDARD_CONNECTIONS);
  public availabilityState = signal<EntityAvailabilityState>('READY');
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

  // Interactive Verification Simulation (Point-in-time)
  public verifyConnection(connId: string): void {
    this.triggerPointInTimeVerification(connId);
  }

  public triggerPointInTimeVerification(connId: string): void {
    this.isVerifyingConnectionId.set(connId);
    
    // Set connection state to TESTING
    this.connections.update(list => list.map(c => {
      if (c.id === connId) {
        return {
          ...c,
          verificationState: 'TESTING',
          lastVerifiedDetails: 'Probe dispatch in progress...'
        };
      }
      return c;
    }));

    setTimeout(() => {
      const nowIso = new Date().toISOString();
      this.connections.update(list => list.map(c => {
        if (c.id === connId) {
          const updated: ConnectionRecord = {
            ...c,
            verificationState: 'VERIFIED_RECENT',
            lastVerifiedAt: nowIso,
            configChangedSinceTest: false,
            lastVerifiedDetails: 'Point-in-time probe verified · TLS 1.3 · Authentication & catalog read passed',
            updatedAt: nowIso
          };
          if (this.selectedConnection()?.id === connId) {
            this.selectedConnection.set(updated);
          }
          return updated;
        }
        return c;
      }));
      this.isVerifyingConnectionId.set(null);
    }, 600);
  }

  public setSorting(field: ConnectionSortField, dir?: SortDirection): void {
    this.setSort(field, dir);
  }

  public resetToFixtures(): void {
    this.connections.set([...FIXTURE_STANDARD_CONNECTIONS]);
    this.clearFilters();
    this.availabilityState.set('READY');
    this.errorMessage.set(null);
    this.selectedConnection.set(null);
    this.isInspectDrawerOpen.set(false);
    this.isVerifyingConnectionId.set(null);
  }

  public reload(): void {
    this.resetToFixtures();
  }

  public setMockAvailability(state: EntityAvailabilityState, msg?: string): void {
    this.availabilityState.set(state);
    this.errorMessage.set(msg || null);
  }

  public retryConnection(): void {
    this.availabilityState.set('LOADING');
    setTimeout(() => {
      this.availabilityState.set('READY');
      this.errorMessage.set(null);
    }, 400);
  }
}
