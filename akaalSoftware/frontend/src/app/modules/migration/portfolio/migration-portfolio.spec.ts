import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MigrationPortfolioComponent } from './migration-portfolio.component';
import { MigrationHomeService } from '../../../core/services/migration-home.service';
import { MigrationHomeRow } from '../../../core/models/migration-home.models';

describe('MigrationPortfolioComponent - Post-Restart Portfolio Table & Active KPI Parity', () => {
  let component: MigrationPortfolioComponent;
  let service: MigrationHomeService;
  let mockRouter: any;

  beforeEach(() => {
    service = new MigrationHomeService();
    mockRouter = {
      navigate: vi.fn()
    };
    component = new MigrationPortfolioComponent(service, mockRouter);
  });

  it('proves post-restart parity: active migration with default project ID is included in Active KPI and renders in Independent Migrations table', () => {
    // 1. Persist active migration with default project context as restored after restart
    const restoredMigration: MigrationHomeRow = {
      id: 'mig-test-restart-parity-100',
      name: 'P8 M2 MySQL to Oracle Continuous Sync',
      source_provider: 'MySQL',
      source_label: 'MySQL Source',
      target_provider: 'Oracle',
      target_label: 'Oracle Target',
      mode: 'M2_BULK_CDC',
      lifecycle_state: 'ACTIVE',
      current_stage: 'Continuous Replication',
      progress_percent: 100,
      project_id: 'default-project',
      started_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    // 2. Load state into service as after restart
    service.migrations.set([restoredMigration]);

    // 3. Verify Active KPI count = 1
    const counters = service.computedCounters();
    expect(counters.active).toBe(1);

    // 4. Verify Independent Migrations table list contains the migration
    const filtered = component.filteredMigrations();
    expect(filtered.length).toBe(1);
    expect(filtered[0].id).toBe('mig-test-restart-parity-100');
    expect(filtered[0].name).toBe('P8 M2 MySQL to Oracle Continuous Sync');

    // 5. Verify table filter does not remove it
    component.selectedState.set('ACTIVE');
    expect(component.filteredMigrations().length).toBe(1);

    // 6. Verify operator can select/open the same migration
    component.navigateToMigration(filtered[0].id);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/cockpit', 'mig-test-restart-parity-100']);
  });
});
