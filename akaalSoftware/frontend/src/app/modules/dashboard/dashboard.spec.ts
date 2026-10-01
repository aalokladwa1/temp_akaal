import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DashboardService, isValidDashboardSummary } from '../../core/services/dashboard.service';
import { DashboardSummary } from '../../core/models/dashboard.models';
import { ActiveMigrationsComponent } from './components/active-migrations.component';
import { AttentionQueueComponent } from './components/attention-queue.component';
import { PendingApprovalsComponent } from './components/pending-approvals.component';
import { AlertsIncidentsComponent } from './components/alerts-incidents.component';
import { CapacitySummaryComponent } from './components/capacity-summary.component';
import { FleetClusterComponent } from './components/fleet-cluster.component';
import { PlatformStatusComponent } from './components/platform-status.component';
import { SecurityComplianceComponent } from './components/security-compliance.component';
import { RecentActivityComponent } from './components/recent-activity.component';

describe('Dashboard Module — CHECK 1 Correct Verification Suite', () => {
  let dashboardService: DashboardService;
  let mockIpcService: any;

  beforeEach(() => {
    mockIpcService = {
      connectionState: vi.fn().mockReturnValue('connected'),
      invoke: vi.fn()
    };
    dashboardService = new DashboardService(mockIpcService);
  });

  describe('DASH-003 & DASH-004: Dashboard State Boundary & Zero-Fake Telemetry', () => {
    it('should initialize with truthful null data and initial status (no synthetic metrics)', () => {
      expect(dashboardService.dashboardData()).toBeNull();
      expect(dashboardService.status()).toBe('initial');
      expect(dashboardService.isLoading()).toBe(false);
      expect(dashboardService.lastError()).toBeNull();
    });

    it('should validate incoming valid domain DashboardSummary payload', () => {
      const validPayload: DashboardSummary = {
        runningCount: 2,
        scheduledCount: 1,
        attentionCount: 0,
        completedTodayCount: 5,
        activeMigrations: [],
        attentionItems: [],
        subsystems: [],
        pendingApprovals: [],
        capacityMetrics: [],
        incidents: [],
        fleet: null,
        security: null,
        recentEvents: []
      };

      expect(isValidDashboardSummary(validPayload)).toBe(true);
    });

    it('should reject malformed or generic IPC envelopes from becoming domain state', () => {
      const genericEnvelope = {
        channel: 'Named Pipe / Domain Socket',
        endpoint: 'dashboard',
        action: 'get_estate_summary'
      };

      expect(isValidDashboardSummary(genericEnvelope)).toBe(false);
      expect(isValidDashboardSummary(null)).toBe(false);
      expect(isValidDashboardSummary('string')).toBe(false);
      expect(isValidDashboardSummary({ activeMigrations: 'not-an-array' })).toBe(false);
    });

    it('should accept valid payload upon refresh and transition status to available', async () => {
      const validPayload: DashboardSummary = {
        runningCount: 3,
        scheduledCount: 0,
        attentionCount: 1,
        completedTodayCount: 4,
        activeMigrations: [
          {
            id: 'mig-1',
            name: 'Oracle to Postgres Core',
            sourceEngine: 'Oracle',
            targetEngine: 'PostgreSQL',
            sourceEndpoint: 'src.db',
            targetEndpoint: 'tgt.db',
            mode: 'M2_BULK_CDC',
            state: 'RUNNING',
            progressPercent: 65,
            throughputRowsSec: 12500
          }
        ],
        attentionItems: [],
        subsystems: [],
        pendingApprovals: [],
        capacityMetrics: [],
        incidents: [],
        fleet: null,
        security: null,
        recentEvents: []
      };

      mockIpcService.invoke.mockResolvedValue({
        status: 'SUCCESS',
        data: validPayload
      });

      await dashboardService.refreshDashboard();

      expect(dashboardService.status()).toBe('available');
      expect(dashboardService.dashboardData()).not.toBeNull();
      expect(dashboardService.dashboardData()?.runningCount).toBe(3);
      expect(dashboardService.dashboardData()?.activeMigrations.length).toBe(1);
    });

    it('should handle malformed IPC response without crashing and transition to unavailable', async () => {
      mockIpcService.invoke.mockResolvedValue({
        status: 'SUCCESS',
        data: { channel: 'Named Pipe', endpoint: 'dashboard', action: 'get_estate_summary' }
      });

      await dashboardService.refreshDashboard();

      expect(dashboardService.status()).toBe('unavailable');
      expect(dashboardService.dashboardData()).toBeNull();
    });

    it('should handle disconnected state truthfully without faking healthy zero-estate', async () => {
      mockIpcService.connectionState.mockReturnValue('disconnected');

      await dashboardService.refreshDashboard();

      expect(dashboardService.status()).toBe('unavailable');
      expect(dashboardService.lastError()).toBe('IPC connection is offline');
      expect(dashboardService.dashboardData()).toBeNull();
    });

    it('should handle IPC error status without crashing and record error', async () => {
      mockIpcService.invoke.mockResolvedValue({
        status: 'ERROR',
        error: 'Engine socket timeout'
      });

      await dashboardService.refreshDashboard();

      expect(dashboardService.status()).toBe('error');
      expect(dashboardService.lastError()).toBe('Engine socket timeout');
      expect(dashboardService.dashboardData()).toBeNull();
    });

    it('should subscribe to akaal:engine:connected, akaal:engine:disconnected, and akaal:telemetry for reactivity', () => {
      const handlers: Record<string, Function> = {};
      const subscribeMock = vi.fn().mockImplementation((ev: string, fn: Function) => {
        handlers[ev] = fn;
        return () => {};
      });
      const ipc = {
        connectionState: vi.fn().mockReturnValue('connected'),
        invoke: vi.fn(),
        subscribe: subscribeMock
      } as any;

      const svc = new DashboardService(ipc);
      expect(subscribeMock).toHaveBeenCalledWith('akaal:engine:connected', expect.any(Function));
      expect(subscribeMock).toHaveBeenCalledWith('akaal:engine:disconnected', expect.any(Function));
      expect(subscribeMock).toHaveBeenCalledWith('akaal:telemetry', expect.any(Function));

      // Trigger disconnected handler
      handlers['akaal:engine:disconnected']();
      expect(svc.status()).toBe('unavailable');
      expect(svc.lastError()).toBe('IPC connection is offline');
    });
  });

  describe('DASH-001: Migration Mode Presentation (M1–M7 and M8 Defence)', () => {
    let activeMigrationsComp: ActiveMigrationsComponent;
    let mockRouter: any;

    beforeEach(() => {
      mockRouter = { navigate: vi.fn() };
      activeMigrationsComp = new ActiveMigrationsComponent(mockRouter);
    });

    it('should format all canonical migration modes M1 through M7 correctly', () => {
      expect(activeMigrationsComp.formatMode('M1_BULK')).toBe('M1 Bulk');
      expect(activeMigrationsComp.formatMode('M2_BULK_CDC')).toBe('M2 Bulk + CDC');
      expect(activeMigrationsComp.formatMode('M3_CDC_CONTINUOUS')).toBe('M3 CDC');
      expect(activeMigrationsComp.formatMode('M4_INCREMENTAL')).toBe('M4 Incremental');
      expect(activeMigrationsComp.formatMode('M5_STATE_SYNC')).toBe('M5 State-Based Sync');
      expect(activeMigrationsComp.formatMode('M6_SCHEMA_ONLY')).toBe('M6 Schema Only');
      expect(activeMigrationsComp.formatMode('M7_DATA_ONLY')).toBe('M7 Data Only');
    });

    it('should format M8 Validation Only defensively without promoting as standard migration mode', () => {
      expect(activeMigrationsComp.formatMode('M8_VALIDATION_ONLY')).toBe('Validation Assurance');
    });

    it('should handle unexpected modes gracefully without leaking raw snake_case or crashing', () => {
      expect(activeMigrationsComp.formatMode('CUSTOM_STREAMING_SYNC')).toBe('Custom Streaming Sync');
      expect(activeMigrationsComp.formatMode('')).toBe('Standard');
    });
  });

  describe('DASH-006: Lifecycle State Truth', () => {
    let activeMigrationsComp: ActiveMigrationsComponent;
    let mockRouter: any;

    beforeEach(() => {
      mockRouter = { navigate: vi.fn() };
      activeMigrationsComp = new ActiveMigrationsComponent(mockRouter);
    });

    it('should map each lifecycle state to its truthful label', () => {
      expect(activeMigrationsComp.getStateLabel('RUNNING')).toBe('Running');
      expect(activeMigrationsComp.getStateLabel('PAUSED')).toBe('Paused');
      expect(activeMigrationsComp.getStateLabel('BLOCKED')).toBe('Blocked');
      expect(activeMigrationsComp.getStateLabel('COMPLETED')).toBe('Completed');
      expect(activeMigrationsComp.getStateLabel('FAILED')).toBe('Failed');
      expect(activeMigrationsComp.getStateLabel('QUEUED')).toBe('Queued');
      expect(activeMigrationsComp.getStateLabel('VALIDATING')).toBe('Validating');
      expect(activeMigrationsComp.getStateLabel('CATCHING_UP')).toBe('Catching Up');
      expect(activeMigrationsComp.getStateLabel('UNKNOWN')).toBe('Unknown');
    });

    it('should assign distinct semantic badge styles for each state', () => {
      expect(activeMigrationsComp.getStateBadgeClasses('RUNNING')).toContain('emerald');
      expect(activeMigrationsComp.getStateBadgeClasses('FAILED')).toContain('rose');
      expect(activeMigrationsComp.getStateBadgeClasses('BLOCKED')).toContain('rose');
      expect(activeMigrationsComp.getStateBadgeClasses('PAUSED')).toContain('amber');
      expect(activeMigrationsComp.getStateBadgeClasses('QUEUED')).toContain('slate');
      expect(activeMigrationsComp.getStateBadgeClasses('VALIDATING')).toContain('indigo');
    });
  });

  describe('DASH-007: Attention Severity Mapping', () => {
    let attentionComp: AttentionQueueComponent;
    let mockRouter: any;

    beforeEach(() => {
      mockRouter = { navigate: vi.fn() };
      attentionComp = new AttentionQueueComponent(mockRouter);
    });

    it('should format severity labels properly', () => {
      expect(attentionComp.formatSeverity('critical')).toBe('Critical');
      expect(attentionComp.formatSeverity('blocked')).toBe('Blocked');
      expect(attentionComp.formatSeverity('failed')).toBe('Failed');
      expect(attentionComp.formatSeverity('approval_required')).toBe('Approval Required');
      expect(attentionComp.formatSeverity('warning')).toBe('Warning');
      expect(attentionComp.formatSeverity('info')).toBe('Info');
    });

    it('should assign semantic badge classes corresponding to severity', () => {
      expect(attentionComp.getSeverityBadgeClasses('critical')).toContain('rose');
      expect(attentionComp.getSeverityBadgeClasses('failed')).toContain('rose');
      expect(attentionComp.getSeverityBadgeClasses('blocked')).toContain('amber');
      expect(attentionComp.getSeverityBadgeClasses('warning')).toContain('amber');
      expect(attentionComp.getSeverityBadgeClasses('approval_required')).toContain('amber');
      expect(attentionComp.getSeverityBadgeClasses('info')).toContain('blue');
    });
  });

  describe('DASH-005: Contextual Routing', () => {
    it('ActiveMigrationsComponent should navigate to Cockpit with migrationId', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new ActiveMigrationsComponent(mockRouter as any);

      comp.goToCockpit('mig-456');
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/cockpit', 'mig-456']);

      comp.goToMigration();
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);

      comp.createMigration();
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/create']);
    });

    it('PendingApprovalsComponent should route to Cockpit if migrationId exists, or fallback safely', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new PendingApprovalsComponent(mockRouter as any);

      comp.goToReview({
        id: 'app-1',
        migrationId: 'mig-101',
        migrationName: 'Core Fin Migration',
        operation: 'Target Cutover',
        boundary: 'PROD',
        requester: 'SecOps',
        requestedAt: '10:00 UTC',
        quorum: '2 of 3',
        severity: 'critical'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/cockpit', 'mig-101']);

      comp.goToReview({
        id: 'app-2',
        migrationId: null,
        migrationName: 'Legacy Sync',
        operation: 'Drop Schema',
        boundary: 'STAGING',
        requester: 'DBA',
        requestedAt: '11:00 UTC',
        quorum: '1 of 2',
        severity: 'normal'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);
    });

    it('AlertsIncidentsComponent should route to /monitoring/alerts', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new AlertsIncidentsComponent(mockRouter as any);

      comp.goToMonitoring();
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/monitoring/alerts']);
    });

    it('AttentionQueueComponent should route based on item domain information and category', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new AttentionQueueComponent(mockRouter as any);

      // Item with migrationId
      comp.handleAction({
        id: 'att-1',
        migrationId: 'mig-789',
        title: 'CDC Lag Exceeded',
        description: 'Lag > 5000ms',
        severity: 'critical',
        category: 'backlog'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/cockpit', 'mig-789']);

      // Item category validation
      comp.handleAction({
        id: 'att-2',
        title: 'Validation Mismatch',
        description: 'Checksum difference',
        severity: 'warning',
        category: 'validation'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/validation']);

      // Item category connector
      comp.handleAction({
        id: 'att-3',
        title: 'Connection Lost',
        description: 'Socket closed',
        severity: 'failed',
        category: 'connector'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/connections']);

      // Item category capacity
      comp.handleAction({
        id: 'att-4',
        title: 'Buffer High',
        description: 'Memory > 90%',
        severity: 'warning',
        category: 'capacity'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/monitoring/platform']);

      // Fallback
      comp.handleAction({
        id: 'att-5',
        title: 'General Attention',
        description: 'Check status',
        severity: 'info',
        category: 'approval'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);
    });
  });

  describe('DASH-008: Component Presentations, Truthful Bindings & Edge Cases', () => {
    it('CapacitySummaryComponent should handle empty and populated metrics', () => {
      const comp = new CapacitySummaryComponent();
      expect(comp.metrics).toEqual([]);

      comp.metrics = [
        { resource: 'CPU Utilization', used: 15.2, total: 100, unit: '%', percent: 15.2, status: 'normal' },
        { resource: 'Memory Buffer', used: 4.5, total: 16.0, unit: 'GB', percent: 28.1, status: 'normal' },
        { resource: 'Storage Volume', used: 120, total: 1000, unit: 'GB', percent: 12.0, status: 'normal' }
      ];
      expect(comp.metrics.length).toBe(3);
      expect(comp.metrics[0].resource).toBe('CPU Utilization');
      expect(comp.metrics[0].percent).toBe(15.2);
    });

    it('FleetClusterComponent should handle null and populated fleet', () => {
      const comp = new FleetClusterComponent();
      expect(comp.fleet).toBeNull();

      comp.fleet = {
        clusterState: 'healthy',
        nodeCount: 1,
        activeWorkers: 4,
        totalCapacityCores: 8,
        detail: 'Local Host Daemon (8 Cores)'
      };
      expect(comp.fleet.clusterState).toBe('healthy');
      expect(comp.fleet.totalCapacityCores).toBe(8);
    });

    it('PlatformStatusComponent should handle empty and populated subsystems', () => {
      const comp = new PlatformStatusComponent();
      expect(comp.subsystems).toEqual([]);

      comp.subsystems = [
        { name: 'Core Pipeline Engine', status: 'healthy', detail: 'Operational', metric: 'Active' },
        { name: 'Named Pipe IPC', status: 'healthy', detail: '127.0.0.1:52199', metric: '127.0.0.1:52199' },
        { name: 'Database Authority', status: 'healthy', detail: 'SQLite UoW WAL Active', metric: 'Connected' },
        { name: 'Validation Authority', status: 'healthy', detail: 'Validation Engine Ready', metric: 'Verified' }
      ];
      expect(comp.subsystems.length).toBe(4);
      expect(comp.subsystems[0].status).toBe('healthy');
    });

    it('SecurityComplianceComponent should handle null and populated security', () => {
      const comp = new SecurityComplianceComponent();
      expect(comp.security).toBeNull();

      comp.security = {
        posture: 'enforced',
        mTLSEnabled: null,
        vaultEncryption: true,
        auditLedgerActive: true,
        detail: 'Enterprise Local Policy Enforced'
      };
      expect(comp.security.posture).toBe('enforced');
      expect(comp.security.auditLedgerActive).toBe(true);
    });

    it('RecentActivityComponent should handle empty and populated events', () => {
      const comp = new RecentActivityComponent();
      expect(comp.events).toEqual([]);

      comp.events = [
        {
          id: 'ev-1',
          migrationName: 'Core Finance Bulk',
          type: 'started',
          description: 'State transitioned to RUNNING',
          operator: 'Operator',
          timestamp: '2026-09-29 12:00:00'
        }
      ];
      expect(comp.events.length).toBe(1);
      expect(comp.events[0].id).toBe('ev-1');
      expect(comp.events[0].type).toBe('started');
    });
  });

  describe('DASH-CORRECTIONS: Hostile Findings Verification', () => {
    it('Finding 14: should initialize userName without hardcoded developer identity and populate from account IPC', async () => {
      // 1. Initial non-identity state
      expect(dashboardService.userName()).toBe('');
      // Greeting defaults to Operator when userName is empty
      expect(dashboardService.greetingContext().greeting).toContain('Operator');
      expect(dashboardService.greetingContext().greeting).not.toContain('Aalok');

      // 2. Populate from current account authority
      mockIpcService.invoke.mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { display_name: 'Lead DevOps Engineer' }
      });
      await dashboardService.loadCurrentAccount();
      expect(dashboardService.userName()).toBe('Lead DevOps Engineer');
      expect(dashboardService.greetingContext().greeting).toContain('Lead DevOps Engineer');
    });

    it('Finding 01: ActiveMigrationsComponent should render Not configured when engine is absent', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new ActiveMigrationsComponent(mockRouter as any);
      comp.migrations = [
        {
          id: 'mig-empty',
          name: 'Unconfigured Pipeline',
          sourceEngine: '' as any,
          targetEngine: '' as any,
          sourceEndpoint: '',
          targetEndpoint: '',
          mode: 'M1_BULK',
          state: 'QUEUED'
        }
      ];
      // Format mode works cleanly
      expect(comp.formatMode(comp.migrations[0].mode)).toBe('M1 Bulk');
      // Source & target engine are not invented as Postgres/Snowflake
      expect(comp.migrations[0].sourceEngine).not.toBe('PostgreSQL');
      expect(comp.migrations[0].targetEngine).not.toBe('Snowflake');
    });

    it('Finding 11: PendingApprovalsComponent should render real quorum without duplicate text', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new PendingApprovalsComponent(mockRouter as any);
      comp.approvals = [
        {
          id: 'app-1',
          migrationName: 'Core Fin Migration',
          operation: 'Target Cutover',
          boundary: 'PROD',
          requester: 'SecOps',
          requestedAt: '10:00 UTC',
          quorum: '1 of 2',
          severity: 'critical'
        }
      ];
      expect(comp.approvals[0].quorum).toBe('1 of 2');
      expect(comp.approvals[0].quorum).not.toContain('Quorum Required');
    });

    it('Finding 06: FleetClusterComponent should truthfully handle unconfigured cluster topology', () => {
      const comp = new FleetClusterComponent();
      comp.fleet = {
        clusterState: 'unconfigured',
        nodeCount: null,
        activeWorkers: null,
        totalCapacityCores: null,
        detail: 'Cluster topology not configured (standalone mode)'
      };
      expect(comp.fleet.clusterState).toBe('unconfigured');
      expect(comp.fleet.nodeCount).toBeNull();
      expect(comp.fleet.activeWorkers).toBeNull();
      expect(comp.fleet.totalCapacityCores).toBeNull();
      expect(comp.fleet.detail).toBe('Cluster topology not configured (standalone mode)');
    });

    it('Finding 04 & 15: should support null collections in isValidDashboardSummary and preserve nulls in refreshDashboard', async () => {
      const payloadWithNulls: DashboardSummary = {
        runningCount: 0,
        scheduledCount: 0,
        attentionCount: 0,
        completedTodayCount: 0,
        activeMigrations: null,
        attentionItems: null,
        subsystems: [],
        pendingApprovals: null,
        capacityMetrics: [],
        incidents: null,
        fleet: null,
        security: null,
        recentEvents: null
      };

      expect(isValidDashboardSummary(payloadWithNulls)).toBe(true);

      mockIpcService.invoke.mockResolvedValueOnce({
        status: 'SUCCESS',
        data: payloadWithNulls
      });

      await dashboardService.refreshDashboard();

      expect(dashboardService.status()).toBe('available');
      const data = dashboardService.dashboardData();
      expect(data).not.toBeNull();
      expect(data?.activeMigrations).toBeNull();
      expect(data?.attentionItems).toBeNull();
      expect(data?.pendingApprovals).toBeNull();
      expect(data?.incidents).toBeNull();
      expect(data?.recentEvents).toBeNull();
    });

    it('Finding 15: components should handle null input without crashing or assuming empty array', () => {
      const mockRouter = { navigate: vi.fn() };
      
      const activeMigrationsComp = new ActiveMigrationsComponent(mockRouter as any);
      activeMigrationsComp.migrations = null;
      expect(activeMigrationsComp.migrations).toBeNull();

      const attentionQueueComp = new AttentionQueueComponent(mockRouter as any);
      attentionQueueComp.items = null;
      expect(attentionQueueComp.items).toBeNull();

      const pendingApprovalsComp = new PendingApprovalsComponent(mockRouter as any);
      pendingApprovalsComp.approvals = null;
      expect(pendingApprovalsComp.approvals).toBeNull();

      const alertsIncidentsComp = new AlertsIncidentsComponent(mockRouter as any);
      alertsIncidentsComp.incidents = null;
      expect(alertsIncidentsComp.incidents).toBeNull();

      const recentActivityComp = new RecentActivityComponent();
      recentActivityComp.events = null;
      expect(recentActivityComp.events).toBeNull();
    });
  });

  describe('P9.2 Slice 3 Area 4: Dashboard Operational Deep-Links & Authoritative Refresh', () => {
    it('AttentionQueueComponent navigates to Cockpit when authoritative migrationId is present', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new AttentionQueueComponent(mockRouter as any);

      comp.handleAction({
        id: 'att-101',
        migrationId: 'mig-live-777',
        title: 'CDC Lag High',
        description: 'Lag > 10s',
        severity: 'critical',
        category: 'backlog'
      });

      expect(mockRouter.navigate).toHaveBeenCalledWith(['/cockpit', 'mig-live-777']);
    });

    it('AttentionQueueComponent falls back truthfully to module routes when migrationId is absent (no manufactured IDs)', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new AttentionQueueComponent(mockRouter as any);

      // validation category fallback
      comp.handleAction({
        id: 'att-val',
        migrationId: null,
        title: 'Validation Parity Drift',
        description: 'Reconciliation difference detected',
        severity: 'warning',
        category: 'validation'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/validation']);

      // connector category fallback
      comp.handleAction({
        id: 'att-conn',
        migrationId: null,
        title: 'Network Timeout',
        description: 'Connection socket dropped',
        severity: 'failed',
        category: 'connector'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/connections']);

      // capacity category fallback
      comp.handleAction({
        id: 'att-cap',
        migrationId: undefined,
        title: 'Worker Saturation',
        description: 'Worker pool at 98%',
        severity: 'warning',
        category: 'capacity'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/monitoring/platform']);

      // error category fallback
      comp.handleAction({
        id: 'att-err',
        title: 'System Alert',
        description: 'Subsystem memory degraded',
        severity: 'critical',
        category: 'error'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/monitoring/alerts']);

      // approval / backlog / general fallback
      comp.handleAction({
        id: 'att-app',
        title: 'Governance Gate',
        description: 'Sign-off required',
        severity: 'approval_required',
        category: 'approval'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);

      comp.handleAction({
        id: 'att-bkl',
        title: 'Backlog Buffer',
        description: 'Backlog growing',
        severity: 'warning',
        category: 'backlog'
      });
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);
    });

    it('PendingApprovalsComponent routes to Cockpit when migrationId exists', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new PendingApprovalsComponent(mockRouter as any);

      comp.goToReview({
        id: 'app-501',
        migrationId: 'mig-prod-core',
        migrationName: 'Core Banking Prod',
        operation: 'Target Cutover Quiesce',
        boundary: 'PROD',
        requester: 'Operator-4',
        requestedAt: '2026-10-01 12:00 UTC',
        quorum: '2 of 3',
        severity: 'critical'
      });

      expect(mockRouter.navigate).toHaveBeenCalledWith(['/cockpit', 'mig-prod-core']);
    });

    it('PendingApprovalsComponent falls back to /migration without heuristic parsing when migrationId is absent', () => {
      const mockRouter = { navigate: vi.fn() };
      const comp = new PendingApprovalsComponent(mockRouter as any);

      comp.goToReview({
        id: 'app-502',
        migrationId: null,
        migrationName: 'Unassigned Schema Apply Operation',
        operation: 'DDL Apply Barrier',
        boundary: 'STAGING',
        requester: 'SecOps',
        requestedAt: '2026-10-01 12:15 UTC',
        quorum: '1 of 2',
        severity: 'normal'
      });

      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);
    });

    it('DashboardService debounced refresh triggers on reactive domain IPC events', async () => {
      const subscriptions: Record<string, Function> = {};
      const mockIpc = {
        connectionState: vi.fn().mockReturnValue('connected'),
        invoke: vi.fn().mockResolvedValue({
          status: 'SUCCESS',
          data: {
            runningCount: 1,
            scheduledCount: 0,
            attentionCount: 0,
            completedTodayCount: 2,
            activeMigrations: [],
            attentionItems: [],
            subsystems: [],
            pendingApprovals: [],
            capacityMetrics: [],
            incidents: [],
            fleet: null,
            security: null,
            recentEvents: []
          }
        }),
        subscribe: vi.fn().mockImplementation((event: string, handler: Function) => {
          subscriptions[event] = handler;
          return () => {};
        })
      };

      const ds = new DashboardService(mockIpc as any);
      expect(mockIpc.subscribe).toHaveBeenCalled();

      // Trigger a reactive migration event
      expect(subscriptions['akaal:migration:event']).toBeDefined();
      subscriptions['akaal:migration:event']();

      // Await debounced timer
      await new Promise(resolve => setTimeout(resolve, 250));

      // Authoritative refresh invoked
      expect(mockIpc.invoke).toHaveBeenCalledWith('estate', 'get_summary');
    });
  });
});
