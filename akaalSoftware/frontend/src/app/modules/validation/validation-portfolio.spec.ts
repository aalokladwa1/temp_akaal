import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ValidationPortfolioComponent } from './validation-portfolio.component';
import { ValidationHomeService } from '../../core/services/validation-home.service';

describe('ValidationPortfolioComponent (Validation Home 6 Visible Bands)', () => {
  let component: ValidationPortfolioComponent;
  let service: ValidationHomeService;
  let mockRouter: any;

  beforeEach(() => {
    service = new ValidationHomeService();
    mockRouter = {
      navigate: vi.fn()
    };

    component = new ValidationPortfolioComponent(service, mockRouter);
  });

  it('should initialize component with default states', () => {
    expect(component).toBeTruthy();
    expect(component.vs).toBeDefined();
    expect(component.isStatusDropdownOpen()).toBe(false);
    expect(component.isStrategyDropdownOpen()).toBe(false);
    expect(component.activeActionMenuId()).toBeNull();
  });

  it('should toggle KPI quick filter when clicked', () => {
    const mockEvent = { stopPropagation: vi.fn() } as any;
    expect(service.kpiFilter()).toBe('ALL');

    component.toggleKpiFilter('ACTIVE', mockEvent);
    expect(service.kpiFilter()).toBe('ACTIVE');

    // Clicking again should toggle back to ALL
    component.toggleKpiFilter('ACTIVE', mockEvent);
    expect(service.kpiFilter()).toBe('ALL');
  });

  it('should toggle and select status dropdown filter', () => {
    const mockEvent = { stopPropagation: vi.fn() } as any;
    expect(component.isStatusDropdownOpen()).toBe(false);

    component.toggleStatusDropdown(mockEvent);
    expect(component.isStatusDropdownOpen()).toBe(true);

    component.selectStatusFilter('VALIDATED');
    expect(service.statusFilter()).toBe('VALIDATED');
    expect(component.isStatusDropdownOpen()).toBe(false);
    expect(component.selectedStatusFilterLabel()).toBe('Validated');
  });

  it('should toggle and select strategy dropdown filter', () => {
    const mockEvent = { stopPropagation: vi.fn() } as any;
    expect(component.isStrategyDropdownOpen()).toBe(false);

    component.toggleStrategyDropdown(mockEvent);
    expect(component.isStrategyDropdownOpen()).toBe(true);

    component.selectStrategyFilter('Sync');
    expect(service.strategyFilter()).toBe('Sync');
    expect(component.isStrategyDropdownOpen()).toBe(false);
    expect(component.selectedStrategyFilterLabel()).toBe('Sync');
  });

  it('should toggle action menu for a specific row', () => {
    const mockEvent = { stopPropagation: vi.fn() } as any;
    expect(component.activeActionMenuId()).toBeNull();

    component.toggleActionMenu('val-001', mockEvent);
    expect(component.activeActionMenuId()).toBe('val-001');

    component.toggleActionMenu('val-001', mockEvent);
    expect(component.activeActionMenuId()).toBeNull();
  });

  it('should reset all filters when clearAllFilters is called', () => {
    service.kpiFilter.set('ACTIVE');
    service.statusFilter.set('VALIDATED');
    service.strategyFilter.set('Sync');
    service.searchQuery.set('Test');

    component.clearAllFilters();

    expect(service.kpiFilter()).toBe('ALL');
    expect(service.statusFilter()).toBe('ALL');
    expect(service.strategyFilter()).toBe('ALL');
    expect(service.searchQuery()).toBe('');
  });

  it('should close all popovers on document click', () => {
    component.isStatusDropdownOpen.set(true);
    component.isStrategyDropdownOpen.set(true);
    component.activeActionMenuId.set('val-001');

    component.closeAllPopovers();

    expect(component.isStatusDropdownOpen()).toBe(false);
    expect(component.isStrategyDropdownOpen()).toBe(false);
    expect(component.activeActionMenuId()).toBeNull();
  });

  it('should navigate to view history', () => {
    const item = { id: 'val-001', name: 'Test' } as any;
    component.activeActionMenuId.set('val-001');

    component.viewHistory(item);

    expect(component.activeActionMenuId()).toBeNull();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/validation', 'val-001']);
  });

  describe('ValidationHomeService Canonical Backend Integration', () => {
    it('should map missions from listValidationMissions into portfolio tables and summaries', async () => {
      const mockMigrationIpc: any = {
        listValidationMissions: vi.fn().mockResolvedValue({
          status: 'SUCCESS',
          data: {
            missions: [
              {
                mission_id: 'miss-101',
                name: 'Core Ledger Sync',
                source_provider: 'Oracle',
                target_provider: 'PostgreSQL',
                temporal_strategy: 'CONTINUOUS',
                state: 'RUNNING',
                last_result_status: 'SUCCESS',
                evaluation_count: 5,
                fail_count: 0,
                updated_at: '2026-09-23T12:00:00Z',
                last_evaluated_at: '2026-09-23T12:00:00Z'
              },
              {
                mission_id: 'miss-102',
                name: 'Customers Table Mismatch',
                source_provider: 'MySQL',
                target_provider: 'ClickHouse',
                temporal_strategy: 'EXECUTE_ON_INIT',
                state: 'FAILED',
                last_result_status: 'MISMATCH',
                evaluation_count: 1,
                fail_count: 3,
                updated_at: '2026-09-23T12:05:00Z',
                last_evaluated_at: '2026-09-23T12:05:00Z'
              }
            ]
          }
        })
      };

      const homeSvc = new ValidationHomeService(mockMigrationIpc);
      await homeSvc.loadState();

      expect(homeSvc.validations().length).toBe(2);
      expect(homeSvc.validations()[0].name).toBe('Core Ledger Sync');
      expect(homeSvc.validations()[0].outcome).toBe('Validated');
      expect(homeSvc.validations()[0].strategy).toBe('Continuous CDC');

      expect(homeSvc.validations()[1].name).toBe('Customers Table Mismatch');
      expect(homeSvc.validations()[1].outcome).toBe('Discrepancies Found');
      expect(homeSvc.validations()[1].discrepancy_count).toBe(3);

      // Attention items
      expect(homeSvc.attentionItems().length).toBe(1);
      expect(homeSvc.attentionItems()[0].validation_id).toBe('miss-102');
      expect(homeSvc.attentionItems()[0].title).toBe('Discrepancies Detected');

      // Recent results
      expect(homeSvc.recentResults().length).toBe(2);

      // Summary
      expect(homeSvc.summary()).toEqual({
        active_count: 1,
        attention_count: 1,
        scheduled_count: 0,
        completed_count: 2,
        total_count: 2
      });
      expect(homeSvc.isUnavailable()).toBe(false);
    });

    it('should fail closed with empty arrays when backend returns error', async () => {
      const mockMigrationIpc: any = {
        listValidationMissions: vi.fn().mockResolvedValue({
          status: 'ERROR',
          error: 'DAEMON_UNREACHABLE'
        })
      };

      const homeSvc = new ValidationHomeService(mockMigrationIpc);
      await homeSvc.loadState();

      expect(homeSvc.validations().length).toBe(0);
      expect(homeSvc.attentionItems().length).toBe(0);
      expect(homeSvc.summary()).toBeNull();
      expect(homeSvc.isUnavailable()).toBe(false);
    });
  });
});
