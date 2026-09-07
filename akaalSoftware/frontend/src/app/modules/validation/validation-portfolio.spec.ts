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
});
