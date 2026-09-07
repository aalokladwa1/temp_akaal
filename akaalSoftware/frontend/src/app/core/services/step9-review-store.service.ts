// ============================================================================
// AKAAL CREATE MIGRATION — STEP 9: REVIEW, SCHEDULE & INITIALIZE
// REACTIVE STORE SERVICE (STATE MANAGEMENT & CANONICAL ORCHESTRATION)
// ============================================================================

import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { MigrationUiService } from './migration-ui.service';
import { Step7PlanStoreService } from './step7-plan-store.service';
import { Step8GovernanceStoreService } from './step8-governance-store.service';
import { IpcService } from './ipc.service';
import { Step9ReviewAdapterService } from './step9-review-adapter.service';
import {
  MigrationIdentityPresentation,
  MigrationReviewGroup,
  BeforeYouStartPresentation,
  ExecutionTimingState,
  TimingChoice,
  ConsequencePresentation,
  TechnicalDetailsPresentation,
  Step9SubmitPhase,
  Step9OperationError
} from '../../modules/migration/create/steps/step9-review.models';

@Injectable({
  providedIn: 'root'
})
export class Step9ReviewStoreService {
  public ms: MigrationUiService;
  public step7Store: Step7PlanStoreService;
  public step8Store: Step8GovernanceStoreService;
  public ipc: IpcService;
  public adapter: Step9ReviewAdapterService;
  public router: Router;

  constructor(
    ms?: MigrationUiService,
    step7Store?: Step7PlanStoreService,
    step8Store?: Step8GovernanceStoreService,
    ipc?: IpcService,
    adapter?: Step9ReviewAdapterService,
    router?: Router
  ) {
    try { this.ms = ms || inject(MigrationUiService); } catch { this.ms = ms || new MigrationUiService(); }
    try { this.step7Store = step7Store || inject(Step7PlanStoreService); } catch { this.step7Store = step7Store || new Step7PlanStoreService(); }
    try { this.step8Store = step8Store || inject(Step8GovernanceStoreService); } catch { this.step8Store = step8Store || new Step8GovernanceStoreService(); }
    try { this.ipc = ipc || inject(IpcService); } catch { this.ipc = ipc || new IpcService(); }
    try { this.adapter = adapter || inject(Step9ReviewAdapterService); } catch { this.adapter = adapter || new Step9ReviewAdapterService(); }
    try { this.router = router || inject(Router); } catch { this.router = router as any; }
  }

  // --------------------------------------------------------------------------
  // REACTIVE STATE SIGNALS
  // --------------------------------------------------------------------------
  public timingChoice = signal<TimingChoice>('RUN_NOW');
  
  // Default scheduled date to tomorrow
  private tomorrowStr = (() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split('T')[0];
  })();

  public scheduledDate = signal<string>(this.tomorrowStr);
  public scheduledTime = signal<string>('22:00');
  public selectedTimezone = signal<string>(
    typeof Intl !== 'undefined' && Intl.DateTimeFormat().resolvedOptions().timeZone
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : 'UTC'
  );
  public isAdvancedRecurring = signal<boolean>(false);
  public recurrenceFrequency = signal<'DAILY' | 'WEEKLY' | 'MONTHLY'>('DAILY');

  // Modal State
  public isTechnicalModalOpen = signal<boolean>(false);

  // Submission / Orchestration State
  public submitPhase = signal<Step9SubmitPhase>('IDLE');
  public operationError = signal<Step9OperationError | null>(null);

  // --------------------------------------------------------------------------
  // REACTIVE COMPUTED PROJECTIONS
  // --------------------------------------------------------------------------
  public migrationIdentity = computed<MigrationIdentityPresentation>(() => {
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    return this.adapter.adaptMigrationIdentity(draft, plan);
  });

  public reviewGroups = computed<MigrationReviewGroup[]>(() => {
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    const overall = this.step8Store.overallReadiness();
    return this.adapter.adaptReviewGroups(draft, plan, overall);
  });

  public beforeYouStart = computed<BeforeYouStartPresentation>(() => {
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    const overall = this.step8Store.overallReadiness();
    return this.adapter.adaptBeforeYouStart(draft, plan, overall);
  });

  public timingState = computed<ExecutionTimingState>(() => {
    const choice = this.timingChoice();
    const date = this.scheduledDate();
    const time = this.scheduledTime();
    const tz = this.selectedTimezone();
    const isRec = this.isAdvancedRecurring();
    const freq = this.recurrenceFrequency();
    const mode = this.ms.wizardDraft().mode || 'M2_BULK_CDC';
    const isRecPermitted = this.adapter.isRecurrencePermittedForMode(mode);

    // Resolve date/time presentation
    let resolvedLocalDisplay = `${date} at ${time}`;
    let resolvedUtcDisplay = 'UTC Resolved';
    let isValid = true;
    let validationError: string | undefined = undefined;

    if (choice === 'SCHEDULE_LATER') {
      if (!date || !time) {
        isValid = false;
        validationError = 'Please select a valid date and time for scheduled execution.';
      } else {
        try {
          const targetIso = `${date}T${time}:00`;
          const parsedDate = new Date(targetIso);
          if (isNaN(parsedDate.getTime())) {
            isValid = false;
            validationError = 'Invalid date or time format.';
          } else {
            // Format readable local display
            const options: Intl.DateTimeFormatOptions = {
              day: 'numeric',
              month: 'short',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              hour12: true
            };
            resolvedLocalDisplay = parsedDate.toLocaleDateString(undefined, options);
            resolvedUtcDisplay = parsedDate.toUTCString();
          }
        } catch {
          isValid = false;
          validationError = 'Could not parse scheduled execution timestamp.';
        }
      }
    }

    return {
      choice,
      scheduledDate: date,
      scheduledTime: time,
      selectedTimezone: tz,
      isAdvancedRecurring: isRec,
      recurrenceFrequency: freq,
      isRecurrencePermittedForMode: isRecPermitted,
      resolvedLocalDisplay,
      resolvedUtcDisplay,
      isValid,
      validationError
    };
  });

  public consequence = computed<ConsequencePresentation>(() => {
    const timing = this.timingState();
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    return this.adapter.adaptConsequencePresentation(timing, draft, plan);
  });

  public technicalDetails = computed<TechnicalDetailsPresentation>(() => {
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    const overall = this.step8Store.overallReadiness();
    return this.adapter.adaptTechnicalDetails(draft, plan, overall);
  });

  public primaryCtaLabel = computed<string>(() => {
    return this.timingChoice() === 'RUN_NOW' ? 'Initialize & Launch' : 'Schedule Migration';
  });

  public isSubmitEligible = computed<boolean>(() => {
    const phase = this.submitPhase();
    if (phase === 'INITIALIZING' || phase === 'STARTING' || phase === 'SCHEDULING') {
      return false; // Prevent double submit
    }
    const timing = this.timingState();
    return timing.isValid;
  });

  // --------------------------------------------------------------------------
  // STORE ACTIONS
  // --------------------------------------------------------------------------

  public setTimingChoice(choice: TimingChoice): void {
    this.timingChoice.set(choice);
    this.operationError.set(null);
  }

  public setScheduledDate(date: string): void {
    this.scheduledDate.set(date);
  }

  public setScheduledTime(time: string): void {
    this.scheduledTime.set(time);
  }

  public setTimezone(tz: string): void {
    this.selectedTimezone.set(tz);
  }

  public toggleAdvancedRecurring(): void {
    this.isAdvancedRecurring.update(v => !v);
  }

  public setRecurrenceFrequency(freq: 'DAILY' | 'WEEKLY' | 'MONTHLY'): void {
    this.recurrenceFrequency.set(freq);
  }

  public openTechnicalModal(): void {
    this.isTechnicalModalOpen.set(true);
  }

  public closeTechnicalModal(): void {
    this.isTechnicalModalOpen.set(false);
  }

  public routeToUpstreamStep(stepNum: number): void {
    if (stepNum >= 1 && stepNum <= 8) {
      this.ms.updateDraft({ currentStep: stepNum });
    }
  }

  // --------------------------------------------------------------------------
  // FINAL ACTION ORCHESTRATION (INITIALIZE / START / SCHEDULE)
  // --------------------------------------------------------------------------
  public async executeFinalAction(): Promise<void> {
    if (!this.isSubmitEligible()) return;

    this.operationError.set(null);
    const identity = this.migrationIdentity();
    const timing = this.timingState();

    // 1. Orchestrate Canonical Plan Initialization
    this.submitPhase.set('INITIALIZING');

    try {
      const initRes = await this.ipc.invoke('engine/migration', 'initialize', {
        migrationId: identity.migrationId,
        planId: identity.planId,
        environment: identity.environment,
        mode: identity.mode,
        timingMode: timing.choice
      });

      if (initRes && initRes.status === 'ERROR') {
        this.submitPhase.set('ERROR');
        this.operationError.set({
          phase: 'INITIALIZATION',
          title: 'Migration Plan Initialization Failed',
          message: initRes.error || 'The backend engine could not initialize the governed plan.',
          isRetryable: true,
          recoveryGuidance: 'Verify backend connection and click Initialize & Launch again.'
        });
        return;
      }
    } catch (err: any) {
      this.submitPhase.set('ERROR');
      this.operationError.set({
        phase: 'IPC',
        title: 'IPC Connection Error',
        message: err?.message || 'Could not communicate with the local migration engine.',
        isRetryable: true,
        recoveryGuidance: 'Check the backend service status and retry.'
      });
      return;
    }

    // 2. Fork based on timing choice
    if (timing.choice === 'RUN_NOW') {
      // 2A: Immediate Execution Dispatch
      this.submitPhase.set('STARTING');

      try {
        const startRes = await this.ipc.invoke('engine/migration', 'start', {
          migrationId: identity.migrationId,
          planId: identity.planId
        });

        if (startRes && startRes.status === 'ERROR') {
          this.submitPhase.set('ERROR');
          this.operationError.set({
            phase: 'START',
            title: 'Execution Dispatch Failed',
            message: startRes.error || 'Plan was initialized, but worker dispatch could not start.',
            isRetryable: true,
            recoveryGuidance: 'Plan is safely initialized. You can retry dispatch or inspect the portfolio.'
          });
          return;
        }

        // Register in portfolio and navigate to Mission Control
        const newId = this.ms.launchDraftMigration();
        this.submitPhase.set('SUCCESS');
        if (this.router) {
          this.router.navigate(['/migration', newId]);
        }
      } catch (err: any) {
        this.submitPhase.set('ERROR');
        this.operationError.set({
          phase: 'START',
          title: 'Dispatch Interrupted',
          message: err?.message || 'Failed to dispatch migration workers.',
          isRetryable: true
        });
      }
    } else {
      // 2B: Schedule Creation & Arming
      this.submitPhase.set('SCHEDULING');

      try {
        const schedRes = await this.ipc.invoke('engine/schedule', 'create', {
          migrationId: identity.migrationId,
          planId: identity.planId,
          scheduledTimestamp: `${timing.scheduledDate}T${timing.scheduledTime}:00`,
          timezone: timing.selectedTimezone,
          isRecurring: timing.isAdvancedRecurring,
          recurrenceFrequency: timing.isAdvancedRecurring ? timing.recurrenceFrequency : undefined
        });

        if (schedRes && schedRes.status === 'ERROR') {
          this.submitPhase.set('ERROR');
          this.operationError.set({
            phase: 'SCHEDULING',
            title: 'Schedule Arming Failed',
            message: schedRes.error || 'Plan initialized, but schedule trigger registration failed.',
            isRetryable: true,
            recoveryGuidance: 'You can retry arming the schedule or navigate to Portfolio.'
          });
          return;
        }

        // Record schedule and navigate to Portfolio
        this.ms.updateDraft({
          scheduleChoice: 'SCHEDULE',
          scheduledTime: `${timing.scheduledDate}T${timing.scheduledTime}:00`
        });
        this.ms.launchDraftMigration();
        this.submitPhase.set('SUCCESS');
        if (this.router) {
          this.router.navigate(['/migration/portfolio']);
        }
      } catch (err: any) {
        this.submitPhase.set('ERROR');
        this.operationError.set({
          phase: 'SCHEDULING',
          title: 'Schedule Registration Interrupted',
          message: err?.message || 'Failed to register schedule trigger.',
          isRetryable: true
        });
      }
    }
  }
}
