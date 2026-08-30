import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationUiService } from './validation-ui.service';
import { MigrationDevFixturesAdapter } from '../fixtures/migration-dev-fixtures.adapter';

describe('ValidationUiService', () => {
  let service: ValidationUiService;
  let fixtures: MigrationDevFixturesAdapter;

  beforeEach(() => {
    fixtures = new MigrationDevFixturesAdapter();
    service = new ValidationUiService(fixtures);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should initialize with zero fake validations by default', () => {
    expect(service.validationItems().length).toBe(0);
    expect(service.filteredValidations().length).toBe(0);
  });

  it('should manage Governed Repair modal state', () => {
    expect(service.isRepairModalOpen()).toBe(false);
    service.openRepairModal();
    expect(service.isRepairModalOpen()).toBe(true);
    service.closeRepairModal();
    expect(service.isRepairModalOpen()).toBe(false);
  });
});
