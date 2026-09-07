import { Injectable, inject, signal, computed } from '@angular/core';
import {
  WorkstationViewModel,
  WorkstationWorkspaceTab,
  ValidationExecutionState,
  ValidationVerdict
} from './validation-workstation.models';
import {
  FIXTURE_NOT_CONNECTED,
  WORKSTATION_FIXTURES
} from './validation-workstation-fixtures';
import { ValidationUiService } from '../../../core/services/validation-ui.service';

@Injectable({
  providedIn: 'root'
})
export class ValidationWorkstationService {
  private validationUiService?: ValidationUiService;

  constructor(validationUiService?: ValidationUiService) {
    if (validationUiService) {
      this.validationUiService = validationUiService;
    } else {
      try {
        this.validationUiService = inject(ValidationUiService, { optional: true }) || undefined;
      } catch {
        // Injection context not available (e.g. direct test instantiation)
      }
    }
  }

  // Current view model signal, defaulting strictly to truthful NOT_CONNECTED
  private _state = signal<WorkstationViewModel>(FIXTURE_NOT_CONNECTED);
  readonly state = this._state.asReadonly();

  // Active workspace tab
  readonly activeTab = computed(() => this._state().activeTab);

  // Technical drawer state
  readonly drawerOpen = computed(() => this._state().drawerOpen);

  // Identity & Status signals
  readonly validationId = computed(() => this._state().validationId);
  readonly validationName = computed(() => this._state().validationName);
  readonly executionState = computed(() => this._state().executionState);
  readonly verdict = computed(() => this._state().verdict);
  readonly isProductionDefault = computed(() => this._state().isProductionDefault);

  // User notification/feedback for disabled actions
  private _actionFeedback = signal<string | null>(null);
  readonly actionFeedback = this._actionFeedback.asReadonly();

  // Copied indicator for Validation ID
  private _copiedId = signal<boolean>(false);
  readonly copiedId = this._copiedId.asReadonly();

  /**
   * Initializes the workstation for a given validation ID.
   * If an active validation or draft exists in the UI service matching this ID,
   * we project its identity attributes while maintaining truthful NOT_CONNECTED execution status.
   */
  loadMission(id: string): void {
    const defaultState = { ...FIXTURE_NOT_CONNECTED, validationId: id };

    if (this.validationUiService) {
      // Check activeValidation in portfolio
      const portfolioValidation = this.validationUiService.validationItems?.().find(v => v.id === id);
      if (portfolioValidation) {
        defaultState.validationName = portfolioValidation.name || defaultState.validationName;
        if (portfolioValidation.sourceEngine) {
          defaultState.source.provider = portfolioValidation.sourceEngine;
          defaultState.donut.sourceLabel = portfolioValidation.sourceEngine;
        }
        if (portfolioValidation.sourceInstance) {
          defaultState.source.label = portfolioValidation.sourceInstance;
          defaultState.donut.sourceHost = portfolioValidation.sourceInstance;
        }
        if (portfolioValidation.targetEngine) {
          defaultState.target.provider = portfolioValidation.targetEngine;
          defaultState.donut.targetLabel = portfolioValidation.targetEngine;
        }
        if (portfolioValidation.targetInstance) {
          defaultState.target.label = portfolioValidation.targetInstance;
          defaultState.donut.targetHost = portfolioValidation.targetInstance;
        }
      }

      // Check draft validation
      const draft = this.validationUiService.newValidationDraft?.();
      if (draft && draft.name) {
        defaultState.validationName = draft.name;
        if (draft.sourceProvider) {
          defaultState.source.provider = draft.sourceProvider;
          defaultState.donut.sourceLabel = draft.sourceProvider;
        }
        if (draft.targetProvider) {
          defaultState.target.provider = draft.targetProvider;
          defaultState.donut.targetLabel = draft.targetProvider;
        }
      }
    }

    this._state.set(defaultState);
  }

  /**
   * Switch active workspace tab.
   */
  setActiveTab(tab: WorkstationWorkspaceTab): void {
    this._state.update(curr => ({ ...curr, activeTab: tab }));
  }

  /**
   * Toggle slide-over technical details drawer.
   */
  toggleDrawer(open?: boolean): void {
    this._state.update(curr => ({
      ...curr,
      drawerOpen: open !== undefined ? open : !curr.drawerOpen
    }));
  }

  /**
   * Copy canonical validation ID to clipboard.
   */
  copyValidationId(): void {
    const id = this._state().validationId;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(id);
      this._copiedId.set(true);
      setTimeout(() => this._copiedId.set(false), 2000);
    }
  }

  /**
   * Isolated fixture loader for visual testing and demonstration.
   */
  setFixture(fixtureKey: string): void {
    const fixture = WORKSTATION_FIXTURES[fixtureKey];
    if (fixture) {
      this._state.set({ ...fixture, drawerOpen: this._state().drawerOpen });
    }
  }

  /**
   * Reset strictly to truthful production default.
   */
  resetToProductionDefault(): void {
    this._state.set(FIXTURE_NOT_CONNECTED);
  }

  /**
   * Safe action triggers for execution controls.
   * In production default, alerts user that controls will become active upon P7D backend integration.
   */
  triggerAction(actionName: string): void {
    if (this._state().isProductionDefault) {
      this._actionFeedback.set(
        `[P7D Authority Boundary] Action "${actionName}" is disabled: Validation engine backend integration pending.`
      );
      setTimeout(() => this._actionFeedback.set(null), 4000);
    } else {
      this._actionFeedback.set(`[Visual Fixture] Executed test trigger: ${actionName}`);
      setTimeout(() => this._actionFeedback.set(null), 3000);
    }
  }
}
