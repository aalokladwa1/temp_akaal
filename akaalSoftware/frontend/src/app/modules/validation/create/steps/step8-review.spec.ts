import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Step8ReviewComponent } from './step8-review.component';
import { NewValidationWizardComponent } from '../new-validation-wizard.component';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';

describe('Step 8 Review, Schedule & Initialize Component', () => {
  let step8: Step8ReviewComponent;
  let wizard: NewValidationWizardComponent;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(() => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };

    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step8 = new Step8ReviewComponent(vs);

    vs.resetDraft();
  });

  it('Mandate 6: 5 Review Groups are defined and link to correct upstream steps', () => {
    const groups = step8.reviewGroups();
    expect(groups.length).toBe(5);

    expect(groups[0].id).toBe('mission-endpoints');
    expect(groups[0].upstreamStep).toBe(1);

    expect(groups[1].id).toBe('scope-correspondence');
    expect(groups[1].upstreamStep).toBe(4);

    expect(groups[2].id).toBe('comparison-baseline');
    expect(groups[2].upstreamStep).toBe(5);

    expect(groups[3].id).toBe('assurance-strategy');
    expect(groups[3].upstreamStep).toBe(6);

    expect(groups[4].id).toBe('governance-readiness');
    expect(groups[4].upstreamStep).toBe(7);
  });

  it('Mandate 7: Draft Identity presentation uses draft ID and does not mint canonical IDs', () => {
    vs.updateDraft({
      name: 'Order Processing Settlement Verification',
      environment: 'Production',
      validationContext: 'INDEPENDENT',
      sourceProvider: 'Oracle',
      sourceHost: 'ora-cluster.internal',
      sourcePort: 1521,
      targetProvider: 'PostgreSQL',
      targetHost: 'pg-replica.internal',
      targetPort: 5432
    });

    const identity = step8.identity();
    expect(identity.validationName).toBe('Order Processing Settlement Verification');
    expect(identity.environment).toBe('Production');
    expect(identity.draftId.startsWith('dft_val_')).toBe(true);
    expect(identity.source.label).toContain('ora-cluster.internal:1521');
    expect(identity.target.label).toContain('pg-replica.internal:5432');
  });

  it('Mandate 8: Timing choice switching and continuous unavailable enforcement', () => {
    expect(step8.timingChoice()).toBe('INITIALIZATION');

    // Switch to Schedule Later
    step8.setTimingChoice('SCHEDULE_LATER');
    expect(step8.timingChoice()).toBe('SCHEDULE_LATER');
    expect(vs.newValidationDraft().step8TimingChoice).toBe('SCHEDULE_LATER');

    // Setting date and time
    step8.setScheduledDate('2026-10-15');
    step8.setScheduledTime('03:30');
    expect(step8.scheduledDate()).toBe('2026-10-15');
    expect(step8.scheduledTime()).toBe('03:30');
    expect(vs.newValidationDraft().step8ScheduledDate).toBe('2026-10-15');
    expect(vs.newValidationDraft().step8ScheduledTime).toBe('03:30');

    // Switch to Recurring
    step8.setTimingChoice('RECURRING');
    expect(step8.timingChoice()).toBe('RECURRING');
    step8.setRecurrenceFrequency('WEEKLY');
    expect(step8.recurrenceFrequency()).toBe('WEEKLY');
    expect(vs.newValidationDraft().step8RecurringFrequency).toBe('WEEKLY');

    // Continuous Validation must be unavailable
    step8.setTimingChoice('CONTINUOUS');
    // Choice remains RECURRING
    expect(step8.timingChoice()).toBe('RECURRING');
  });

  it('Mandate 10: Technical Configuration Modal toggle and inspection', () => {
    expect(step8.isTechnicalModalOpen()).toBe(false);
    step8.openTechnicalModal();
    expect(step8.isTechnicalModalOpen()).toBe(true);

    const json = step8.draftSpecificationJson();
    expect(json).toContain('draftSpecification');
    expect(json).toContain('dft_val_');

    step8.closeTechnicalModal();
    expect(step8.isTechnicalModalOpen()).toBe(false);
  });

  it('Mandate 12: Consequence Explainer confirms non-mutating execution process', () => {
    vs.updateDraft({ environment: 'Production' });
    const consequence = step8.consequence();
    expect(consequence.title).toBe('Validation Execution Process');
    expect(consequence.primaryActionDescription).toContain('read-only execution graph');
    expect(consequence.subsequentSteps.some(s => s.includes('zero mutation privileges'))).toBe(true);
    expect(consequence.productionNotice).toBeDefined();
    expect(consequence.productionNotice).toContain('Production environment');
  });

  it('Edit Group Action: routes wizard to upstream step', () => {
    step8.routeToStep(4);
    expect(vs.newValidationDraft().currentStep).toBe(4);
  });

  it('Mandate 11: Wizard completion resets draft and navigates without simulating fake runs', () => {
    // Populate valid steps 1-6
    vs.updateDraft({
      name: 'Production Core Settlement Validation',
      environment: 'Production',
      validationContext: 'INDEPENDENT',
      currentStep: 8,
      sourceConnectionMode: 'SAVED',
      sourceConnectionId: 'conn-ora-1',
      sourceVerified: true,
      targetConnectionMode: 'SAVED',
      targetConnectionId: 'conn-pg-1',
      targetVerified: true,
      step4Pathway: 'DEFINE',
      comparisonUnits: [
        {
          id: 'unit-1',
          sourceId: 'src-1',
          sourceName: 'accounts',
          targetId: 'tgt-1',
          targetName: 'accounts',
          targetStatus: 'CONFIRMED',
          disposition: 'INCLUDED'
        } as any
      ],
      baselineIntent: 'CURRENT_OPERATIONAL',
      assuranceLevel: 'PARTITION_FINGERPRINT',
      temporalCadence: 'CONSISTENT_STATE'
    });

    expect(vs.isStep8Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);

    wizard.initializeValidation();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/validation']);
  });
});
