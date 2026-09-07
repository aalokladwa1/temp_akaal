import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Step6StrategyComponent } from './step6-strategy.component';
import { NewValidationWizardComponent } from '../new-validation-wizard.component';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import { AssuranceTierCard } from './step6-strategy.models';

describe('Step 6 Strategy & Assurance Component', () => {
  let step6: Step6StrategyComponent;
  let wizard: NewValidationWizardComponent;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(() => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };

    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step6 = new Step6StrategyComponent(vs);

    vs.resetDraft();
  });

  it('should initialize with default Partition Fingerprint and Consistent-State cadence', () => {
    expect(step6).toBeTruthy();
    expect(step6.selectedLevel()).toBe('PARTITION_FINGERPRINT');
    expect(step6.selectedCadence()).toBe('CONSISTENT_STATE');
    expect(step6.coverageMode()).toBe('EXHAUSTIVE');
    expect(step6.exceptionGroups().length).toBe(0);
    expect(step6.contextualFinding()).toBeNull();
  });

  it('STATE A — Simple Mission: valid out of the box with zero exceptions and consistent-state', () => {
    vs.updateDraft({
      currentStep: 6,
      name: 'Standard Oracle to PG Mission',
      sourceProvider: 'Oracle',
      targetProvider: 'PostgreSQL'
    });

    expect(vs.isStep6Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
    expect(step6.defaultObjectsCount()).toBe(303);
    expect(step6.escalatedObjectsCount()).toBe(0);
    expect(step6.reducedObjectsCount()).toBe(0);
  });

  it('STATE B — Strongest Assurance: Complete Attribute selected with exhaustive logical equivalence contract', () => {
    step6.selectAssuranceLevel('COMPLETE_ATTRIBUTE');

    expect(step6.selectedLevel()).toBe('COMPLETE_ATTRIBUTE');
    expect(vs.newValidationDraft().assuranceLevel).toBe('COMPLETE_ATTRIBUTE');

    const activeContract = step6.activeTier();
    expect(activeContract.level).toBe('COMPLETE_ATTRIBUTE');
    expect(activeContract.establishes.some(e => e.includes('Exhaustive attribute-by-attribute comparison'))).toBe(true);
    expect(activeContract.establishes.some(e => e.includes('Disambiguation between NULL and missing'))).toBe(true);
    expect(activeContract.doesNotEstablish.some(d => d.includes('Physical raw byte identity'))).toBe(true);
    expect(activeContract.limitations.some(l => l.includes('canonical logical value equivalence'))).toBe(true);
  });

  it('STATE C & D — Capability states & unavailable tier protection', () => {
    // Structural, Cardinality, Partition Fingerprint, Complete Attribute exist
    expect(step6.assuranceTiers.length).toBe(4);

    // Mock an unavailable tier in assuranceTiers
    const structuralTier = step6.assuranceTiers.find(t => t.level === 'STRUCTURAL');
    expect(structuralTier?.capability).toBe('AVAILABLE');

    // Simulate an unavailable tier
    (step6.assuranceTiers as any)[0].capability = 'UNAVAILABLE';
    step6.selectAssuranceLevel('STRUCTURAL');
    // Selection should be blocked and remain at default
    expect(step6.selectedLevel()).toBe('PARTITION_FINGERPRINT');

    // Restore
    (step6.assuranceTiers as any)[0].capability = 'AVAILABLE';
  });

  it('STATE F — Mixed Assurance: default with escalated and reduced exception groups', () => {
    // Add Escalated group
    step6.openAddExceptionModal();
    step6.draftExceptionType.set('ESCALATED');
    step6.draftTargetLevel.set('COMPLETE_ATTRIBUTE');
    step6.draftReason.set('Financial critical GL ledger accounts');
    step6.draftSelectedObjectIds.set(['tbl_gl_balances', 'tbl_payments']);
    step6.saveExceptionGroup();

    // Add Reduced group
    step6.openAddExceptionModal();
    step6.draftExceptionType.set('REDUCED');
    step6.draftTargetLevel.set('CARDINALITY');
    step6.draftReason.set('Archival logging audit tables');
    step6.draftSelectedObjectIds.set(['tbl_sessions']);
    step6.saveExceptionGroup();

    expect(step6.exceptionGroups().length).toBe(2);
    expect(step6.escalatedObjectsCount()).toBe(2);
    expect(step6.reducedObjectsCount()).toBe(1);
    expect(step6.defaultObjectsCount()).toBe(300); // 303 - 3

    expect(vs.isStep6Valid()).toBe(true);
  });

  it('STATE G — Large Estate Exception Management: search, filter, multi-select, and deletion', () => {
    step6.openAddExceptionModal();
    expect(step6.showExceptionModal()).toBe(true);

    // Search filter
    step6.objectSearchQuery.set('PAY');
    expect(step6.filteredScopedObjects().length).toBe(1);
    expect(step6.filteredScopedObjects()[0].name).toBe('PAYMENTS');

    // Select all filtered
    step6.selectAllFilteredObjects();
    expect(step6.draftSelectedObjectIds()).toEqual(['tbl_payments']);

    // Clear search
    step6.objectSearchQuery.set('');
    step6.toggleObjectSelection('tbl_accounts');
    expect(step6.draftSelectedObjectIds().length).toBe(2);

    step6.draftReason.set('Core banking accounts');
    step6.saveExceptionGroup();

    const group = step6.exceptionGroups()[0];
    expect(group.objectIds.length).toBe(2);

    // Delete exception
    step6.removeExceptionGroup(group.id);
    expect(step6.exceptionGroups().length).toBe(0);
  });

  it('STATE H — Continuous Validation Unavailable: selecting continuous warns and halts progression', () => {
    step6.selectTemporalCadence('CONTINUOUS');
    expect(step6.selectedCadence()).toBe('CONTINUOUS');

    // Continuous is unavailable on current platform -> fail-closed
    expect(vs.isStep6Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);

    // Switching back to Consistent-State restores validity
    step6.selectTemporalCadence('CONSISTENT_STATE');
    expect(step6.selectedCadence()).toBe('CONSISTENT_STATE');
    expect(vs.isStep6Valid()).toBe(true);
  });

  it('STATE I — Advanced Coverage: statistical sampling progressive disclosure and validation', () => {
    expect(step6.isAdvancedCoverageOpen()).toBe(false);
    step6.toggleAdvancedCoverage();
    expect(step6.isAdvancedCoverageOpen()).toBe(true);

    step6.selectCoverageMode('STATISTICAL_SAMPLE');
    expect(step6.coverageMode()).toBe('STATISTICAL_SAMPLE');
    expect(step6.samplePercentage()).toBe(5);

    step6.onSamplePercentageChange(15);
    expect(step6.samplePercentage()).toBe(15);
    expect(vs.isStep6Valid()).toBe(true);

    // Invalid percentage blocks validity
    step6.onSamplePercentageChange(0);
    expect(vs.isStep6Valid()).toBe(false);

    // Restore valid percentage
    step6.onSamplePercentageChange(10);
    expect(vs.isStep6Valid()).toBe(true);

    // Switch back to exhaustive
    step6.selectCoverageMode('EXHAUSTIVE');
    expect(step6.coverageMode()).toBe('EXHAUSTIVE');
    expect(vs.isStep6Valid()).toBe(true);
  });

  it('STATE J & K — P7C Contextual Intelligence Finding: interactive recommendation and dismissal', () => {
    // State K: No finding
    expect(step6.contextualFinding()).toBeNull();

    // State J: Finding arrives via P7C advisory seam
    step6.contextualFinding.set({
      id: 'finding-001',
      title: 'High-Risk Decimal Dialect Mapping Detected',
      body: 'Tables GL_BALANCES and PAYMENTS contain 4 currency fields mapped from Oracle NUMBER(18,4) to PostgreSQL NUMERIC. Complete Attribute Assurance recommended.',
      severity: 'ADVISORY',
      recommendedAssuranceLevel: 'COMPLETE_ATTRIBUTE',
      affectedObjectsCount: 2,
      isDismissed: false,
      isAccepted: false
    });

    expect(step6.contextualFinding()?.isDismissed).toBe(false);

    // Apply recommendation
    step6.applyContextualRecommendation(step6.contextualFinding()!);
    expect(step6.selectedLevel()).toBe('COMPLETE_ATTRIBUTE');
    expect(step6.contextualFinding()?.isAccepted).toBe(true);

    // Dismiss finding
    step6.dismissContextualFinding();
    expect(step6.contextualFinding()?.isDismissed).toBe(true);
  });

  it('STATE L — Form Validation: invalid draft reason blocks adding exception', () => {
    step6.openAddExceptionModal();
    step6.draftReason.set('   '); // whitespace only
    step6.draftSelectedObjectIds.set(['tbl_payments']);

    expect(step6.isDraftReasonInvalid()).toBe(true);

    // Save should do nothing
    step6.saveExceptionGroup();
    expect(step6.exceptionGroups().length).toBe(0);
    expect(step6.showExceptionModal()).toBe(true);

    step6.closeExceptionModal();
    expect(step6.showExceptionModal()).toBe(false);
  });

  it('Additive Assurance Law: isTierSubsumed correctly evaluates hierarchy', () => {
    // Default is PARTITION_FINGERPRINT (rank 3)
    expect(step6.isTierSubsumed('STRUCTURAL')).toBe(true);
    expect(step6.isTierSubsumed('CARDINALITY')).toBe(true);
    expect(step6.isTierSubsumed('PARTITION_FINGERPRINT')).toBe(false);
    expect(step6.isTierSubsumed('COMPLETE_ATTRIBUTE')).toBe(false);

    // Switch to COMPLETE_ATTRIBUTE (rank 4)
    step6.selectAssuranceLevel('COMPLETE_ATTRIBUTE');
    expect(step6.isTierSubsumed('STRUCTURAL')).toBe(true);
    expect(step6.isTierSubsumed('CARDINALITY')).toBe(true);
    expect(step6.isTierSubsumed('PARTITION_FINGERPRINT')).toBe(true);
    expect(step6.isTierSubsumed('COMPLETE_ATTRIBUTE')).toBe(false);

    // Switch to STRUCTURAL (rank 1)
    step6.selectAssuranceLevel('STRUCTURAL');
    expect(step6.isTierSubsumed('STRUCTURAL')).toBe(false);
    expect(step6.isTierSubsumed('CARDINALITY')).toBe(false);
    expect(step6.isTierSubsumed('PARTITION_FINGERPRINT')).toBe(false);
    expect(step6.isTierSubsumed('COMPLETE_ATTRIBUTE')).toBe(false);
  });
});
