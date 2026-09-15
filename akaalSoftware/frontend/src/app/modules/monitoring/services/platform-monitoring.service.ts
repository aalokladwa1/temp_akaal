/**
 * AKAAL Monitoring — Part 3 of 4: Platform Operations Service
 * Signal-driven reactive store managing platform overview, runtime services,
 * connectivity, infrastructure & fleet, capacity, performance, reliability, and diagnostics.
 */

import { Injectable, signal, computed } from '@angular/core';
import { 
  PlatformOperationsDTO, 
  PlatformTabKey, 
  RuntimeServiceDTO, 
  PlatformNodeDTO, 
  PlatformConnectorDTO,
  PlatformWorkerDTO
} from '../models/platform-monitoring.models';
import { MOCK_PLATFORM_OPERATIONS } from '../fixtures/platform-monitoring.fixtures';
import { formatSnakeToTitle } from '../models/monitoring.models';

@Injectable({
  providedIn: 'root'
})
export class PlatformMonitoringService {
  // Master Signal State
  private _data = signal<PlatformOperationsDTO>(MOCK_PLATFORM_OPERATIONS);
  public data = computed(() => this._data());

  // Active Tab & Selection Signals
  public selectedTab = signal<PlatformTabKey>('overview');
  public selectedNodeId = signal<string | null>(null);
  public selectedServiceId = signal<string | null>(null);

  // Search & Filter Signals
  public serviceSearchQuery = signal<string>('');
  public serviceStatusFilter = signal<string>('ALL');

  public nodeSearchQuery = signal<string>('');
  public nodeRoleFilter = signal<string>('ALL');

  public connectorSearchQuery = signal<string>('');
  public connectorFamilyFilter = signal<string>('ALL');

  // Refresh & Freshness State
  public isRefreshing = signal<boolean>(false);
  public lastObservedAt = signal<string>(MOCK_PLATFORM_OPERATIONS.summary.observed_at);
  public telemetryConfidence = signal<string>(MOCK_PLATFORM_OPERATIONS.summary.telemetry_confidence);

  // Formatter References
  public formatText = formatSnakeToTitle;

  // Computed Projections
  public summary = computed(() => this._data().summary);
  public conditions = computed(() => this._data().conditions);
  public capacity = computed(() => this._data().capacity);
  public performance = computed(() => this._data().performance);
  public reliability = computed(() => this._data().reliability);
  public diagnostics = computed(() => this._data().diagnostics);
  public leases = computed(() => this._data().leases);

  // Filtered Services
  public filteredServices = computed<RuntimeServiceDTO[]>(() => {
    const list = this._data().runtime_services;
    const q = this.serviceSearchQuery().trim().toLowerCase();
    const status = this.serviceStatusFilter();

    return list.filter(svc => {
      if (status !== 'ALL' && svc.status !== status) return false;
      if (q && !svc.name.toLowerCase().includes(q) && !svc.subsystem.toLowerCase().includes(q) && !svc.role.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  // Selected Service Detail
  public selectedService = computed<RuntimeServiceDTO | null>(() => {
    const id = this.selectedServiceId();
    if (!id) return null;
    return this._data().runtime_services.find(s => s.id === id) || null;
  });

  // Filtered Nodes
  public filteredNodes = computed<PlatformNodeDTO[]>(() => {
    const list = this._data().nodes;
    const q = this.nodeSearchQuery().trim().toLowerCase();
    const role = this.nodeRoleFilter();

    return list.filter(node => {
      if (role !== 'ALL' && node.role !== role) return false;
      if (q && !node.host_name.toLowerCase().includes(q) && !node.node_id.toLowerCase().includes(q) && !node.region_locality.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  // Selected Node Detail
  public selectedNode = computed<PlatformNodeDTO | null>(() => {
    const id = this.selectedNodeId();
    if (!id) return null;
    return this._data().nodes.find(n => n.node_id === id) || null;
  });

  // Workers allocated to selected node
  public selectedNodeWorkers = computed<PlatformWorkerDTO[]>(() => {
    const id = this.selectedNodeId();
    if (!id) return [];
    return this._data().workers.filter(w => w.node_id === id);
  });

  // Filtered Connectors
  public filteredConnectors = computed<PlatformConnectorDTO[]>(() => {
    const list = this._data().connectors;
    const q = this.connectorSearchQuery().trim().toLowerCase();
    const family = this.connectorFamilyFilter();

    return list.filter(conn => {
      if (family !== 'ALL' && conn.family !== family) return false;
      if (q && !conn.provider.toLowerCase().includes(q) && !conn.endpoint_target.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  // State Mutators
  public selectTab(tabKey: PlatformTabKey): void {
    this.selectedTab.set(tabKey);
  }

  public selectNode(nodeId: string | null): void {
    this.selectedNodeId.set(nodeId);
  }

  public selectService(serviceId: string | null): void {
    this.selectedServiceId.set(serviceId);
  }

  public setServiceSearch(q: string): void {
    this.serviceSearchQuery.set(q);
  }

  public setServiceStatusFilter(s: string): void {
    this.serviceStatusFilter.set(s);
  }

  public setNodeSearch(q: string): void {
    this.nodeSearchQuery.set(q);
  }

  public setNodeRoleFilter(r: string): void {
    this.nodeRoleFilter.set(r);
  }

  public setConnectorSearch(q: string): void {
    this.connectorSearchQuery.set(q);
  }

  public setConnectorFamilyFilter(f: string): void {
    this.connectorFamilyFilter.set(f);
  }

  public refresh(): void {
    this.isRefreshing.set(true);
    setTimeout(() => {
      this.lastObservedAt.set(new Date().toISOString());
      this.isRefreshing.set(false);
    }, 450);
  }
}
