import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Step7ReadinessComponent } from './step7-readiness.component';
import { NewValidationWizardComponent } from '../new-validation-wizard.component';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import { Step7VisualFixture, ReadinessCheckItem } from './step7-readiness.models';

describe('Step 7 Governance & Readiness Component', () => {
  let step7: Step7ReadinessComponent;
  let wizard: NewValidationWizardComponent;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(() => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };

    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step7 = new Step7ReadinessComponent(vs);

    vs.resetDraft();
  });

  it('Mandate 1: Production Default must be NOT_EVALUATED / READINESS_NOT_CONNECTED', () => {
    expect(step7).toBeTruthy();
    const readiness = step7.activeReadiness();
    expect(readiness.status).toBe('NOT_EVALUATED');
    expect(readiness.statusLabel).toBe('Not Evaluated');
    expect(readiness.isEvaluationConnected).toBe(false);
    expect(readiness.summaryText).toContain('Readiness evaluation service is not currently connected');
    expect(readiness.domainsCount).toBe(5);
    expect(readiness.passedChecksCount).toBe(0);
    expect(readiness.totalChecksCount).toBe(10);
    expect(step7.activeActions().length).toBe(0);
  });

  it('Mandate 1: Angular is NOT the canonical readiness authority — NOT_EVALUATED does NOT block wizard', () => {
    // Populate valid steps 1-6
    vs.updateDraft({
      name: 'Production Core Settlement Validation',
      environment: 'Production',
      validationContext: 'INDEPENDENT',
      currentStep: 7,
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

    expect(vs.isStep1Valid()).toBe(true);
    expect(vs.isStep2Valid()).toBe(true);
    expect(vs.isStep3Valid()).toBe(true);
    expect(vs.isStep4Valid()).toBe(true);
    expect(vs.isStep5Valid()).toBe(true);
    expect(vs.isStep6Valid()).toBe(true);
    // Step 7 must be valid to allow operator to advance to Step 8 Review
    expect(vs.isStep7Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('Domain Categories: 5 scalable readiness domains are populated', () => {
    const domains = step7.activeDomains();
    expect(domains.length).toBe(5);
    expect(domains.map(d => d.id)).toEqual([
      'CONNECTIVITY_ACCESS',
      'SCOPE_CORRESPONDENCE',
      'BASELINE_LEGITIMACY',
      'ASSURANCE_COMPATIBILITY',
      'GOVERNANCE_OPERATIONAL'
    ]);
  });

  it('Domain Accordion: toggles domain expansion cleanly', () => {
    const domainId = 'SCOPE_CORRESPONDENCE';
    expect(step7.expandedDomainIds().has(domainId)).toBe(true);

    step7.toggleDomainExpansion(domainId);
    expect(step7.expandedDomainIds().has(domainId)).toBe(false);

    step7.toggleDomainExpansion(domainId);
    expect(step7.expandedDomainIds().has(domainId)).toBe(true);
  });

  it('Inspect Drawer: opens check details and closes drawer', () => {
    const check: ReadinessCheckItem = {
      id: 'conn-source-probe',
      domain: 'CONNECTIVITY_ACCESS',
      name: 'Source Endpoint Connectivity',
      status: 'NOT_EVALUATED',
      observation: 'Connection parameters provided; live connectivity has not been evaluated.',
      affectedResources: ['Oracle DB'],
      technicalDetail: 'TCP Handshake: Not run'
    };

    expect(step7.selectedCheck()).toBeNull();
    step7.openInspectDrawer(check);
    expect(step7.selectedCheck()).toEqual(check);

    step7.closeInspectDrawer();
    expect(step7.selectedCheck()).toBeNull();
  });

  it('Re-evaluate control: produces truthful unintegrated notice rather than fake evaluation', () => {
    vi.useFakeTimers();
    step7.handleReevaluateAll();
    expect(step7.isEvaluating()).toBe(true);

    vi.advanceTimersByTime(400);
    expect(step7.isEvaluating()).toBe(false);
    expect(step7.evaluationMessage()).toContain('Readiness evaluation service is not currently connected');
    vi.useRealTimers();
  });

  it('Check-level Re-evaluate: produces truthful unintegrated notice', () => {
    step7.handleReevaluateCheck('conn-source-probe');
    expect(step7.evaluationMessage()).toContain('Live evaluation daemon is not currently connected');
  });

  it('Visual Fixtures: READY state renders certified ready presentation', () => {
    const fixture: Step7VisualFixture = {
      status: 'READY',
      statusLabel: 'Ready for Execution',
      summaryText: 'All 5 readiness domains evaluated and certified.',
      isEvaluationConnected: true,
      domains: [
        {
          id: 'CONNECTIVITY_ACCESS',
          title: '1. Connectivity & Access Rights',
          description: 'Verified',
          checks: [],
          passedCount: 2,
          totalCount: 2,
          hasBlockers: false,
          hasWarnings: false,
          isExpanded: true
        }
      ],
      actions: [],
      acknowledgements: []
    };

    step7.visualFixture = fixture;
    const readiness = step7.activeReadiness();
    expect(readiness.status).toBe('READY');
    expect(readiness.statusLabel).toBe('Ready for Execution');
    expect(readiness.isEvaluationConnected).toBe(true);
    expect(readiness.passedChecksCount).toBe(2);
    expect(step7.getStatusIcon('READY')).toBe('check-circle-2');
  });

  it('Visual Fixtures: BLOCKED state renders blockers and upstream remediation actions', () => {
    const fixture: Step7VisualFixture = {
      status: 'BLOCKED',
      statusLabel: 'Validation Blocked',
      summaryText: '1 blocking issue prevents execution.',
      isEvaluationConnected: true,
      domains: [],
      actions: [
        {
          id: 'action-fix-target',
          severity: 'BLOCKER',
          title: 'Unresolved Target Correspondence',
          description: 'Comparison unit has unmapped target.',
          actionLabel: 'Resolve in Step 4',
          upstreamStep: 4
        }
      ],
      acknowledgements: []
    };

    step7.visualFixture = fixture;
    const readiness = step7.activeReadiness();
    expect(readiness.status).toBe('BLOCKED');
    expect(step7.activeActions().length).toBe(1);

    // Clicking action navigates to Step 4
    step7.handleActionClick(fixture.actions[0]);
    expect(vs.newValidationDraft().currentStep).toBe(4);
  });

  it('Operational Conditions: Step 5 maintenance condition requires operator acknowledgement', () => {
    vs.updateDraft({
      baselineIntent: 'MAINTENANCE_COORDINATED',
      maintenanceCondition: 'WRITES_STOPPED_DECLARED'
    });

    const acks = step7.activeAcknowledgements();
    expect(acks.length).toBe(1);
    expect(acks[0].id).toBe('ack-writes-stopped');
    expect(acks[0].isAcknowledged).toBe(false);

    // Toggle acknowledgement
    step7.toggleAcknowledgement('ack-writes-stopped');
    expect(step7.acknowledgedIds().has('ack-writes-stopped')).toBe(true);
    expect(step7.activeAcknowledgements()[0].isAcknowledged).toBe(true);
  });
});
