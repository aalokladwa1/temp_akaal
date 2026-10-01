import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { NewValidationWizardComponent } from './new-validation-wizard.component';
import { ValidationUiService } from '../../../core/services/validation-ui.service';

describe('P9.2 Slice 2: Validation Wizard Creation & Authoritative Migration Hydration', () => {
  let handoffWizard: NewValidationWizardComponent;
  let handoffVs: ValidationUiService;
  let mockIpc: any;
  let mockRouter: any;

  beforeEach(() => {
    handoffVs = new ValidationUiService();
    handoffVs.resetDraft();
    mockRouter = { navigate: vi.fn() };
    mockIpc = {
      getMigration: vi.fn(),
      getConnection: vi.fn()
    };
    handoffWizard = new NewValidationWizardComponent(handoffVs, mockRouter, undefined, undefined, mockIpc as any);
  });

  it('should successfully hydrate wizard draft from an authoritative COMPLETED migration', async () => {
    mockIpc.getMigration.mockResolvedValue({
      status: 'SUCCESS',
      data: {
        migration_id: 'mig-comp-1',
        name: 'Core Oracle to PG',
        state: 'COMPLETED',
        project_id: 'proj-omega',
        configuration: {
          source_connection_id: 'conn-src-1',
          target_connection_id: 'conn-tgt-1',
          comparison_units: ['users', 'orders']
        }
      }
    });

    mockIpc.getConnection.mockImplementation((id: string) => {
      if (id === 'conn-src-1') {
        return Promise.resolve({
          status: 'SUCCESS',
          data: {
            provider: 'Oracle',
            parameters: { host: 'ora.prod.internal', port: 1521, database: 'ORCL', username: 'app_user' }
          }
        });
      }
      return Promise.resolve({
        status: 'SUCCESS',
        data: {
          provider: 'PostgreSQL',
          parameters: { host: 'pg.prod.internal', port: 5432, database: 'appdb', username: 'postgres' }
        }
      });
    });

    await handoffWizard.hydrateFromMigration('mig-comp-1');

    expect(handoffWizard.handoffBlocked()).toBe(false);
    expect(handoffWizard.handoffError()).toBeNull();

    const draft = handoffVs.newValidationDraft();
    expect(draft.name).toBe('Validation: Core Oracle to PG');
    expect(draft.projectId).toBe('proj-omega');
    expect(draft.validationContext).toBe('EXISTING_PROJECT');
    expect(draft.sourceProvider).toBe('Oracle');
    expect(draft.sourceHost).toBe('ora.prod.internal');
    expect(draft.sourcePort).toBe(1521);
    expect(draft.sourceDatabase).toBe('ORCL');
    expect(draft.targetProvider).toBe('PostgreSQL');
    expect(draft.targetHost).toBe('pg.prod.internal');
    expect(draft.targetPort).toBe(5432);
    expect(draft.targetDatabase).toBe('appdb');
    expect(draft.comparisonUnits?.length).toBe(2);
    expect(draft.comparisonUnits?.map(u => u.sourceName)).toEqual(['users', 'orders']);
  });

  it('should fail closed when migration is in an ineligible lifecycle state (e.g. RUNNING or FAILED)', async () => {
    mockIpc.getMigration.mockResolvedValue({
      status: 'SUCCESS',
      data: {
        migration_id: 'mig-run-1',
        state: 'RUNNING'
      }
    });

    await handoffWizard.hydrateFromMigration('mig-run-1');

    expect(handoffWizard.handoffBlocked()).toBe(true);
    expect(handoffWizard.handoffError()).toContain('Parity validation is only permitted for completed or cutover migrations');
    expect(handoffWizard.isCurrentStepValid()).toBe(false);
  });

  it('should fail closed when migration record is not found', async () => {
    mockIpc.getMigration.mockResolvedValue({
      status: 'ERROR',
      error: 'Migration not found'
    });

    await handoffWizard.hydrateFromMigration('mig-missing');

    expect(handoffWizard.handoffBlocked()).toBe(true);
    expect(handoffWizard.handoffError()).toContain('could not be resolved');
    expect(handoffWizard.isCurrentStepValid()).toBe(false);
  });

  it('should keep handoffBlocked true even when dismissHandoffError is clicked', async () => {
    mockIpc.getMigration.mockResolvedValue({
      status: 'SUCCESS',
      data: {
        migration_id: 'mig-failed-1',
        state: 'FAILED'
      }
    });

    await handoffWizard.hydrateFromMigration('mig-failed-1');

    expect(handoffWizard.handoffBlocked()).toBe(true);
    expect(handoffWizard.handoffError()).not.toBeNull();

    handoffWizard.dismissHandoffError();

    // Error banner dismissed from view
    expect(handoffWizard.handoffError()).toBeNull();
    // BUT wizard remains strictly fail-closed blocked
    expect(handoffWizard.handoffBlocked()).toBe(true);
    expect(handoffWizard.isCurrentStepValid()).toBe(false);
  });
});
