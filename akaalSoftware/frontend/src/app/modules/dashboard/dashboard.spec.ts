import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DashboardService, isValidDashboardSummary } from '../../core/services/dashboard.service';
import { DashboardSummary } from '../../core/models/dashboard.models';
import { ActiveMigrationsComponent } from './components/active-migrations.component';
import { AttentionQueueComponent } from './components/attention-queue.component';
import { PendingApprovalsComponent } from './components/pending-approvals.component';
import { AlertsIncidentsComponent } from './components/alerts-incidents.component';

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
});
