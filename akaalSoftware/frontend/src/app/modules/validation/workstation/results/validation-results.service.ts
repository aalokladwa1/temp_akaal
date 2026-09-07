/**
 * validation-results.service.ts
 * =====================================
 * State management service for Workspace 4: Results & Evidence.
 * 
 * Strict Architectural Rules:
 * 1. Default state is strictly truthful NOT_CONNECTED / NOT_EVALUATED standby.
 * 2. Scenario fixtures are strictly isolated for testing & screenshot harnesses.
 * 3. Navigation to discrepancies reuses parent ValidationWorkstationService.
 * 4. SHA-256 Content Digest copy is explicitly a content digest utility (Digest !== Signature).
 */

import { Injectable, inject, signal, computed } from '@angular/core';
import {
  ResultsWorkspaceState,
  ResultsViewStatus,
  FinalValidationVerdict,
  ComparisonMode,
  TemporalModel,
  ValidationRunRecord
} from './validation-results.models';
import { FIXTURE_NOT_CONNECTED, RESULTS_FIXTURES } from './validation-results.fixtures';
import { ValidationWorkstationService } from '../validation-workstation.service';

@Injectable({
  providedIn: 'root'
})
export class ValidationResultsService {
  private workstationService?: ValidationWorkstationService;

  constructor(workstationService?: ValidationWorkstationService) {
    if (workstationService) {
      this.workstationService = workstationService;
    } else {
      try {
        this.workstationService = inject(ValidationWorkstationService, { optional: true }) || undefined;
      } catch {
        // Injection context not available (e.g. direct test instantiation)
      }
    }

    if (typeof window !== 'undefined') {
      (window as any).__setResultsFixture = (key: string) => this.setFixture(key);
      (window as any).__getResultsState = () => this._state();
    }
  }

  // Primary State Signal - Defaults strictly to truthful production standby
  private readonly _state = signal<ResultsWorkspaceState>(FIXTURE_NOT_CONNECTED);

  // Readonly Public Accessors
  readonly state = this._state.asReadonly();
  readonly viewStatus = computed(() => this._state().viewStatus);
  readonly isProductionDefault = computed(() => this._state().isProductionDefault);
  readonly isTechnicalDrawerOpen = computed(() => this._state().isTechnicalDrawerOpen);
  readonly activeScenarioId = computed(() => this._state().activeScenarioId);

  // Core Independent Dimensions
  readonly validationId = computed(() => this._state().validationId);
  readonly validationName = computed(() => this._state().validationName);
  readonly verdict = computed(() => this._state().verdict);
  readonly comparisonMode = computed(() => this._state().comparisonMode);
  readonly temporalModel = computed(() => this._state().temporalModel);
  readonly executionState = computed(() => this._state().executionState);
  readonly baselineState = computed(() => this._state().baselineState);
  readonly completedAt = computed(() => this._state().completedAt);
  readonly durationFormatted = computed(() => this._state().durationFormatted);
  readonly operator = computed(() => this._state().operator);
  readonly verdictSummaryNote = computed(() => this._state().verdictSummaryNote);

  // Subsections
  readonly source = computed(() => this._state().source);
  readonly target = computed(() => this._state().target);
  readonly assuranceTiers = computed(() => this._state().assuranceTiers);
  readonly unresolvedFindings = computed(() => this._state().unresolvedFindings);
  readonly remediationLineage = computed(() => this._state().remediationLineage);
  readonly runs = computed(() => this._state().runs);
  readonly selectedRunId = computed(() => this._state().selectedRunId);
  readonly evidence = computed(() => this._state().evidence);
  readonly auditTimeline = computed(() => this._state().auditTimeline);
  readonly artifacts = computed(() => this._state().artifacts);
  readonly technicalDetails = computed(() => this._state().technicalDetails);
  readonly errorMessage = computed(() => this._state().errorMessage);

  // Feedback Signals
  private readonly _copiedDigest = signal<boolean>(false);
  readonly copiedDigest = this._copiedDigest.asReadonly();

  private readonly _copiedId = signal<boolean>(false);
  readonly copiedId = this._copiedId.asReadonly();

  private readonly _actionNotice = signal<string | null>(null);
  readonly actionNotice = this._actionNotice.asReadonly();

  /**
   * Set isolated fixture for testing & screenshot harness
   */
  setFixture(fixtureKey: string): void {
    const fixture = RESULTS_FIXTURES[fixtureKey];
    if (fixture) {
      this._state.set(JSON.parse(JSON.stringify(fixture)));
    }
  }

  /**
   * Reset strictly to truthful production default
   */
  resetToDefault(): void {
    this._state.set(JSON.parse(JSON.stringify(FIXTURE_NOT_CONNECTED)));
  }

  /**
   * Toggle Slide-over Technical Provenance Drawer
   */
  toggleTechnicalDrawer(open?: boolean): void {
    this._state.update(s => ({
      ...s,
      isTechnicalDrawerOpen: open !== undefined ? open : !s.isTechnicalDrawerOpen
    }));
  }

  /**
   * Copy SHA-256 content digest to clipboard with toast feedback
   */
  copyDigest(): void {
    const digest = this._state().evidence.contentDigest;
    if (digest && navigator.clipboard) {
      navigator.clipboard.writeText(digest);
      this._copiedDigest.set(true);
      setTimeout(() => this._copiedDigest.set(false), 2200);
    }
  }

  /**
   * Copy Validation ID
   */
  copyValidationId(): void {
    const id = this._state().validationId;
    if (id && navigator.clipboard) {
      navigator.clipboard.writeText(id);
      this._copiedId.set(true);
      setTimeout(() => this._copiedId.set(false), 2000);
    }
  }

  /**
   * Select a specific historical run from the ledger
   */
  selectRun(runId: string): void {
    this._state.update(s => ({
      ...s,
      selectedRunId: runId
    }));
  }

  /**
   * Navigate to Discrepancies tab using existing Validation Mission shell authority
   */
  navigateToDiscrepancies(): void {
    if (this.workstationService) {
      this.workstationService.setActiveTab('discrepancies');
    }
  }

  /**
   * Trigger artifact action with truthful availability feedback
   */
  triggerArtifactAction(artName: string): void {
    this._actionNotice.set(
      `Artifact generation for "${artName}" is not currently available: Export service integration pending.`
    );
    setTimeout(() => this._actionNotice.set(null), 4000);
  }
}
