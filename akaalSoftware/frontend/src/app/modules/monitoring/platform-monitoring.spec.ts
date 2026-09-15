import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PlatformMonitoringService } from './services/platform-monitoring.service';
import { MOCK_PLATFORM_OPERATIONS } from './fixtures/platform-monitoring.fixtures';
import { PLATFORM_TABS, PlatformTabKey } from './models/platform-monitoring.models';

describe('AKAAL Monitoring — Part 3 of 4: Platform Operations Master Integrity Suite', () => {
  let service: PlatformMonitoringService;

  beforeEach(() => {
    service = new PlatformMonitoringService();
  });

  describe('1. Platform Master State & Core Projections', () => {
    it('should initialize with complete platform operations dataset', () => {
      const summary = service.summary();
      expect(summary.overall_health).toBe('HEALTHY');
      expect(summary.readiness_state).toBe('READY');
      expect(summary.liveness_state).toBe('ALIVE');
      expect(summary.total_nodes).toBe(4);
      expect(summary.healthy_nodes).toBe(4);
      expect(summary.active_workers).toBe(11);
      expect(summary.total_services).toBe(8);
      expect(summary.healthy_services).toBe(8);
      expect(summary.total_connectors).toBe(12);
    });

    it('should expose all 8 canonical platform investigation tabs in exact order', () => {
      expect(PLATFORM_TABS.length).toBe(8);
      const keys = PLATFORM_TABS.map(t => t.key);
      expect(keys).toEqual([
        'overview',
        'runtime',
        'connectivity',
        'infrastructure',
        'capacity',
        'performance',
        'reliability',
        'diagnostics'
      ]);
    });

    it('should switch selected tabs smoothly', () => {
      expect(service.selectedTab()).toBe('overview');

      PLATFORM_TABS.forEach(tab => {
        service.selectTab(tab.key);
        expect(service.selectedTab()).toBe(tab.key);
      });
    });

    it('should trigger refresh state and update observation timestamp', async () => {
      vi.useFakeTimers();
      expect(service.isRefreshing()).toBe(false);

      service.refresh();
      expect(service.isRefreshing()).toBe(true);

      vi.advanceTimersByTime(500);
      expect(service.isRefreshing()).toBe(false);
      vi.useRealTimers();
    });
  });

  describe('2. Active Conditions & Operational Metrics', () => {
    it('should project active platform conditions with severity and impact scope', () => {
      const conditions = service.conditions();
      expect(conditions.length).toBeGreaterThan(0);
      
      const warnCond = conditions.find(c => c.severity === 'WARNING');
      expect(warnCond).toBeDefined();
      expect(warnCond?.target_tab).toBe('connectivity');
    });

    it('should report correct cluster headroom and confidence', () => {
      const summary = service.summary();
      expect(summary.cpu_headroom_pct).toBe(62.4);
      expect(summary.memory_headroom_mb).toBe(24576);
      expect(service.telemetryConfidence()).toBe('HIGH');
    });
  });

  describe('3. Runtime & Services Daemons Inventory & Filtering', () => {
    it('should project all 8 internal runtime daemons', () => {
      const svcs = service.filteredServices();
      expect(svcs.length).toBe(8);

      const gateway = svcs.find(s => s.id === 'svc-core-gateway');
      expect(gateway?.name).toBe('Engine Gateway & IPC Dispatcher');
      expect(gateway?.health).toBe('HEALTHY');
      expect(gateway?.p95_latency_ms).toBeLessThan(10);
    });

    it('should filter runtime services by search query (name, subsystem, role)', () => {
      service.setServiceSearch('Schema');
      const filtered = service.filteredServices();
      expect(filtered.length).toBe(1);
      expect(filtered[0].name).toBe('Schema Mapping & DDL Transpiler');

      service.setServiceSearch('Gateway');
      expect(service.filteredServices().length).toBe(1);

      service.setServiceSearch('NonExistentDaemon');
      expect(service.filteredServices().length).toBe(0);

      service.setServiceSearch('');
      expect(service.filteredServices().length).toBe(8);
    });

    it('should filter runtime services by operational status', () => {
      service.setServiceStatusFilter('ACTIVE');
      const active = service.filteredServices();
      expect(active.length).toBe(8);

      service.setServiceStatusFilter('STOPPED');
      const stopped = service.filteredServices();
      expect(stopped.length).toBe(0);

      service.setServiceStatusFilter('ALL');
      expect(service.filteredServices().length).toBe(8);
    });

    it('should handle service selection drilldown and lazy detail retrieval', () => {
      expect(service.selectedService()).toBeNull();

      service.selectService('svc-coordinator');
      const selected = service.selectedService();
      expect(selected).not.toBeNull();
      expect(selected?.name).toBe('Pipeline Execution Coordinator');
      expect(selected?.dependencies_summary).toContain('RaftQuorum');

      service.selectService(null);
      expect(service.selectedService()).toBeNull();
    });
  });

  describe('4. Connectivity & Endpoints State & Filtering', () => {
    it('should project all registered enterprise data-path connectors', () => {
      const connectors = service.filteredConnectors();
      expect(connectors.length).toBe(6);

      const oracle = connectors.find(c => c.provider.includes('Oracle'));
      expect(oracle?.family).toBe('RELATIONAL');
      expect(oracle?.health).toBe('HEALTHY');
      expect(oracle?.active_connections).toBe(8);
    });

    it('should filter connectors by search query and family category', () => {
      service.setConnectorSearch('Snowflake');
      expect(service.filteredConnectors().length).toBe(1);
      expect(service.filteredConnectors()[0].family).toBe('WAREHOUSE');

      service.setConnectorSearch('');
      service.setConnectorFamilyFilter('STREAMING');
      expect(service.filteredConnectors().length).toBe(1);
      expect(service.filteredConnectors()[0].provider).toContain('Kafka');

      service.setConnectorFamilyFilter('ALL');
      expect(service.filteredConnectors().length).toBe(6);
    });
  });

  describe('5. Infrastructure, Compute Nodes & Distributed Leases', () => {
    it('should project compute node fleet and distributed CAS fencing leases', () => {
      const nodes = service.filteredNodes();
      expect(nodes.length).toBe(4);

      const leases = service.leases();
      expect(leases.length).toBe(3);
      expect(leases.every(l => l.state === 'ACQUIRED')).toBe(true);
    });

    it('should filter compute nodes by search query and role', () => {
      service.setNodeSearch('coord-01');
      expect(service.filteredNodes().length).toBe(1);
      expect(service.filteredNodes()[0].role).toBe('COORDINATOR');

      service.setNodeSearch('');
      service.setNodeRoleFilter('WORKER_NODE');
      expect(service.filteredNodes().length).toBe(2);

      service.setNodeRoleFilter('ALL');
      expect(service.filteredNodes().length).toBe(4);
    });

    it('should select node and project allocated workers', () => {
      expect(service.selectedNode()).toBeNull();
      expect(service.selectedNodeWorkers().length).toBe(0);

      service.selectNode('node-akaal-worker-01');
      const selected = service.selectedNode();
      expect(selected).not.toBeNull();
      expect(selected?.host_name).toBe('worker-01.us-east-1.internal');

      const workers = service.selectedNodeWorkers();
      expect(workers.length).toBe(2);
      expect(workers[0].assigned_migration_id).toBe('mig-core-banking-01');

      service.selectNode(null);
      expect(service.selectedNode()).toBeNull();
      expect(service.selectedNodeWorkers().length).toBe(0);
    });
  });

  describe('6. Capacity, Utilization & Advisory Runway', () => {
    it('should project CPU, memory, storage domain, and buffer metrics', () => {
      const capacity = service.capacity();
      expect(capacity.cpu.total_cores).toBe(64);
      expect(capacity.cpu.headroom_pct).toBe(62.4);

      expect(capacity.memory.total_mb).toBe(114688);
      expect(capacity.memory.headroom_mb).toBe(94608);

      expect(capacity.storage_domains.length).toBe(4);
      const rocksdb = capacity.storage_domains.find(d => d.domain.includes('RocksDB'));
      expect(rocksdb).toBeDefined();

      expect(capacity.forecasting.is_sufficient_samples).toBe(true);
    });
  });

  describe('7. Platform Performance & Bottlenecks Profile', () => {
    it('should project throughput rates, systemic latency profile, and concurrency skew', () => {
      const perf = service.performance();
      expect(perf.work_rate.total_rows_per_sec).toBe(90170);
      expect(perf.work_rate.total_bytes_per_sec_label).toBe('142.4 MB/s');

      expect(perf.latencies.p95_ms).toBe(18.4);
      expect(perf.latencies.sink_apply_ms).toBe(12.5);

      expect(perf.worker_skew.total_workers).toBe(11);
      expect(perf.worker_skew.balanced_workers).toBe(10);
      expect(perf.worker_skew.elevated_workers).toBe(1);

      expect(perf.systemic_bottlenecks.length).toBeGreaterThan(0);
    });
  });

  describe('8. Platform Reliability, Durability & Self-Healing', () => {
    it('should project consensus state, checkpoint integrity, uptime churn, and RCA hypotheses', () => {
      const rel = service.reliability();
      expect(rel.durability.checkpoint_store_integrity).toBe('VERIFIED_NOMINAL');
      expect(rel.durability.raft_consensus_state).toBe('QUORUM_HEALTHY');
      expect(rel.durability.cas_lease_fencing_status).toBe('PROTECTED');

      expect(rel.component_restarts.length).toBe(3);
      expect(rel.recovery_progress.successful_recoveries_24h).toBe(3);
      expect(rel.advisory_rca.length).toBe(1);
    });
  });

  describe('9. Diagnostics, Correlation Seams & Runtime Log Stream', () => {
    it('should project global correlation context, telemetry seams, and bounded log entries', () => {
      const diag = service.diagnostics();
      expect(diag.correlation_context.global_trace_id).toBe('trace-4a5b6c7d8e9f0a1b2c3d4e5f');
      expect(diag.correlation_context.engine_fingerprint).toContain('sha256');

      expect(diag.telemetry_exporters.length).toBe(2);
      expect(diag.bounded_logs.length).toBeGreaterThan(0);
      expect(diag.runtime_events.length).toBeGreaterThan(0);
    });
  });
});
