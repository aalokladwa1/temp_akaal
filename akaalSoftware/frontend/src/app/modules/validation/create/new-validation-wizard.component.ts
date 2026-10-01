import { Component, inject, signal, computed, HostListener, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
import { IpcService } from '../../../core/services/ipc.service';
import { MigrationIpc } from '../../../core/services/ipc/migration.ipc';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { Step1DefinitionComponent } from './steps/step1-definition.component';
import { Step2SourceComponent } from './steps/step2-source.component';
import { Step3TargetComponent } from './steps/step3-target.component';
import { Step4ScopeComponent } from './steps/step4-scope.component';
import { Step5BoundaryComponent } from './steps/step5-boundary.component';
import { Step6StrategyComponent } from './steps/step6-strategy.component';
import { Step7ReadinessComponent } from './steps/step7-readiness.component';
import { Step8ReviewComponent } from './steps/step8-review.component';

export interface StepRailItem {
  index: number;
  label: string;
  nextLabel: string;
  prevLabel?: string;
}

@Component({
  selector: 'app-new-validation-wizard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    Step1DefinitionComponent,
    Step2SourceComponent,
    Step3TargetComponent,
    Step4ScopeComponent,
    Step5BoundaryComponent,
    Step6StrategyComponent,
    Step7ReadinessComponent,
    Step8ReviewComponent
  ],
  template: `
    <!-- Fluid Content Wrapper: Integrated inside Platform Main Workspace with Left Sidebar & Top Header preserved -->
    <div class="flex flex-col h-[calc(100vh-theme(spacing.16))] -m-6 lg:-m-9 bg-slate-50 overflow-hidden select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- ZONE 1: TOP SHELL BAR (Exit | Breadcrumb | Read-Only Badge)               -->
      <!-- ========================================================================= -->
      <header class="h-[52px] bg-white border-b border-slate-200 shrink-0 z-30 px-6 lg:px-8 flex items-center justify-between overflow-visible">
        
        <!-- Left: Exit Button + Breadcrumb -->
        <div class="flex items-center gap-3.5 min-w-0">
          
          <!-- Exit Action Button -->
          <button
            type="button"
            (click)="handleExit()"
            class="h-8 px-2.5 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer transition-colors shrink-0"
            title="Exit Create Validation">
            <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
            <span>Exit</span>
          </button>

          <span class="h-4 w-[1px] bg-slate-200 shrink-0"></span>

          <!-- Breadcrumb tracking -->
          <h1 class="text-[10px] font-bold tracking-wider uppercase text-slate-500 shrink-0 m-0 leading-none">
            VALIDATION WIZARD &middot; STEP {{ currentStep() }} OF 8
          </h1>

        </div>

        <!-- Right Side: Read-Only Assurance Badge (Curved Corner Rectangle) -->
        <div class="flex items-center gap-3 shrink-0">
          <span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-bold flex items-center gap-1.5 shrink-0">
            <app-lucide-icon name="shield-check" [size]="13" class="text-emerald-600"></app-lucide-icon>
            <span>READ-ONLY NON-MUTATING VERIFICATION</span>
          </span>
        </div>

      </header>

      <!-- Dismissible Migration Handoff Error Notice (B-VAL-03) -->
      @if (handoffError()) {
        <div class="bg-rose-50 border-b border-rose-200 text-rose-800 px-6 py-2.5 flex items-center justify-between shrink-0 z-20">
          <div class="flex items-center gap-2 min-w-0">
            <app-lucide-icon name="alert-circle" [size]="15" class="text-rose-600 shrink-0"></app-lucide-icon>
            <span class="text-xs font-semibold truncate">{{ handoffError() }}</span>
          </div>
          <button
            type="button"
            (click)="dismissHandoffError()"
            class="text-xs font-bold text-rose-700 hover:text-rose-900 cursor-pointer underline ml-4 shrink-0">
            Dismiss
          </button>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- ZONE 2: 8-STEP PROCESS STEPPER (Floating steps matching GDS)             -->
      <!-- ========================================================================= -->
      <nav aria-label="Validation Wizard Steps Progress" class="h-12 bg-white border-b border-slate-200 px-6 lg:px-8 flex items-center shrink-0 relative z-20">
        
        <!-- Stepper Items Flex Container -->
        <div class="w-full max-w-6xl mx-auto flex items-center justify-between gap-2 overflow-x-hidden">
          @for (step of steps; track step.index) {
            
            <!-- Stepper Item (Curved-corner rectangle indicators, clickable navigation) -->
            <button
              type="button"
              (click)="goToStep(step.index)"
              class="flex items-center gap-2 text-xs shrink-0 cursor-pointer transition-colors group"
              [ngClass]="step.index === currentStep() ? 'text-slate-900 font-bold' : 'text-slate-600 hover:text-slate-900'"
              [attr.aria-current]="step.index === currentStep() ? 'step' : null"
              [title]="'Go to Step ' + step.index + ': ' + step.label">
              <span
                class="w-5 h-5 rounded-md text-[10px] font-bold flex items-center justify-center shrink-0 transition-colors"
                [ngClass]="step.index === currentStep() 
                  ? 'bg-blue-600 text-white shadow-2xs' 
                  : (step.index < currentStep() 
                    ? 'bg-slate-100 group-hover:bg-slate-200 text-slate-700 border border-slate-200' 
                    : 'bg-slate-50 group-hover:bg-slate-100 text-slate-500 border border-slate-200')">
                {{ step.index }}
              </span>
              <span class="tracking-tight">{{ step.label }}</span>
            </button>

          }
        </div>

      </nav>

      <!-- ========================================================================= -->
      <!-- ZONE 3: ACTIVE STEP WORKSPACE CANVAS                                      -->
      <!-- ========================================================================= -->
      <section
        aria-label="Active Step Workspace Canvas"
        class="flex-1 min-h-0 overflow-y-auto px-6 lg:px-8 py-4 lg:py-5 select-none">
        <div [class]="currentStep() === 4 || currentStep() === 5 ? 'w-full max-w-7xl mx-auto' : (currentStep() === 8 ? 'w-full max-w-6xl mx-auto' : 'w-full max-w-5xl mx-auto')">
          @switch (currentStep()) {
            @case (1) {
              <app-step1-definition />
            }
            @case (2) {
              <app-step2-source />
            }
            @case (3) {
              <app-step3-target />
            }
            @case (4) {
              <app-step4-scope />
            }
            @case (5) {
              <app-step5-boundary />
            }
            @case (6) {
              <app-step6-strategy />
            }
            @case (7) {
              <app-step7-readiness />
            }
            @case (8) {
              <app-step8-review />
            }
            @default { 
              <div class="py-16 text-center text-slate-400 font-medium">
                Step {{ currentStep() }} ({{ currentStepItem().label }}) workspace ready for clean implementation
              </div> 
            }
          }
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- ZONE 4: FIXED FOOTER (Previous on Left, Continue on Right)                -->
      <!-- ========================================================================= -->
      <footer class="h-14 border-t border-slate-200 bg-white px-6 lg:px-8 flex items-center justify-between shrink-0 z-30">
        
        <!-- Left Slot: Exit (on Step 1) or Previous Step -->
        <div class="flex items-center">
          @if (currentStep() === 1) {
            <button
              type="button"
              (click)="handleExit()"
              class="h-8 px-3 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer">
              <app-lucide-icon name="arrow-left" [size]="13"></app-lucide-icon>
              <span>Exit</span>
            </button>
          } @else {
            <button
              type="button"
              (click)="previousStep()"
              class="h-8 px-3 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer">
              <app-lucide-icon name="arrow-left" [size]="13"></app-lucide-icon>
              <span>Previous Step</span>
            </button>
          }
        </div>

        <!-- Right Slot: Continue / Action Button -->
        <div class="flex items-center gap-3">
          @if (currentStep() < 8) {
            <button
              type="button"
              (click)="continueToNextStep()"
              [disabled]="!isCurrentStepValid()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 cursor-pointer transition-colors"
              [title]="'Continue to ' + nextStepLabel()">
              <span>Continue to {{ nextStepLabel() }}</span>
              <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
            </button>
          } @else {
            <button
              type="button"
              (click)="initializeValidation()"
              [disabled]="!isCurrentStepValid() || isSubmitting()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 cursor-pointer transition-colors"
              title="Initialize Validation">
              <app-lucide-icon [name]="isSubmitting() ? 'loader-2' : 'arrow-right'" [size]="13" [class.animate-spin]="isSubmitting()"></app-lucide-icon>
              <span>{{ isSubmitting() ? 'Initializing...' : 'Initialize Validation' }}</span>
            </button>
          }
        </div>

      </footer>

      @if (submitError()) {
        <div class="px-6 lg:px-8 py-2.5 bg-rose-50 border-t border-rose-200 text-rose-900 text-xs flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="alert-circle" [size]="14" class="text-rose-600 shrink-0"></app-lucide-icon>
            <span class="font-bold">Initialization Error:</span>
            <span>{{ submitError() }}</span>
          </div>
          <button type="button" (click)="submitError.set(null)" class="text-rose-600 hover:text-rose-800 font-bold cursor-pointer">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- OVERLAYS (Exit Confirmation Dialog)                                       -->
      <!-- ========================================================================= -->
      @if (showExitModal()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
          (click)="showExitModal.set(false)">
          <div
            class="w-full max-w-md rounded-xl bg-white border border-slate-200 p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">Exit Create Validation?</h3>
                <span class="text-xs text-slate-500 font-medium">Unpersisted changes detected</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-medium">
              Some draft changes have not been saved. Exiting now will discard the current draft.
            </p>

            <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
              <button
                type="button"
                (click)="showExitModal.set(false)"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer">
                Keep Editing
              </button>

              <button
                type="button"
                (click)="exitToValidationHome()"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer">
                Exit to Validation
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class NewValidationWizardComponent implements OnInit, OnDestroy {
  public vs: ValidationUiService;
  private router: Router;
  private route: ActivatedRoute;
  private routeSub?: Subscription;

  public showExitModal = signal<boolean>(false);
  public projectId = signal<string | null>(null);

  // Canonical 8 Steps
  public readonly steps: StepRailItem[] = [
    { index: 1, label: 'Definition', nextLabel: 'Source' },
    { index: 2, label: 'Source', nextLabel: 'Target', prevLabel: 'Definition' },
    { index: 3, label: 'Target', nextLabel: 'Scope', prevLabel: 'Source' },
    { index: 4, label: 'Scope', nextLabel: 'Boundary', prevLabel: 'Target' },
    { index: 5, label: 'Boundary', nextLabel: 'Strategy', prevLabel: 'Scope' },
    { index: 6, label: 'Strategy', nextLabel: 'Readiness', prevLabel: 'Boundary' },
    { index: 7, label: 'Readiness', nextLabel: 'Review', prevLabel: 'Strategy' },
    { index: 8, label: 'Review', nextLabel: 'Initialize Validation', prevLabel: 'Readiness' }
  ];

  public currentStep = computed(() => {
    const raw = this.vs.newValidationDraft().currentStep;
    const num = typeof raw === 'string' ? parseInt(raw, 10) : Number(raw);
    return isNaN(num) || num < 1 || num > 8 ? 1 : num;
  });

  public currentStepItem = computed(() => this.steps[this.currentStep() - 1] || this.steps[0]);
  public nextStepLabel = computed(() => this.currentStepItem().nextLabel);
  public previousStepLabel = computed(() => this.currentStepItem().prevLabel || 'Previous');

  public handoffBlocked = signal<boolean>(false);
  public handoffError = signal<string | null>(null);
  public originatingMigrationId = signal<string | null>(null);

  public dismissHandoffError(): void {
    this.handoffError.set(null);
  }

  public isCurrentStepValid = computed(() => {
    if (this.handoffBlocked()) {
      return false;
    }
    return this.vs.isStepValid(this.currentStep());
  });

  public ipc: IpcService;
  public migrationIpc: MigrationIpc;

  constructor(vs?: ValidationUiService, router?: Router, route?: ActivatedRoute, ipc?: IpcService, migrationIpc?: MigrationIpc) {
    if (vs) {
      this.vs = vs;
    } else {
      try { this.vs = inject(ValidationUiService); } catch { this.vs = new ValidationUiService(); }
    }

    if (router) {
      this.router = router;
    } else {
      try { this.router = inject(Router); } catch { this.router = {} as Router; }
    }

    if (route) {
      this.route = route;
    } else {
      try { this.route = inject(ActivatedRoute); } catch { this.route = undefined as any; }
    }

    if (ipc) {
      this.ipc = ipc;
    } else {
      try { this.ipc = inject(IpcService); } catch { this.ipc = new IpcService(); }
    }

    if (migrationIpc) {
      this.migrationIpc = migrationIpc;
    } else {
      try { this.migrationIpc = inject(MigrationIpc); } catch { this.migrationIpc = new MigrationIpc(this.ipc); }
    }
  }

  ngOnInit(): void {
    if (!this.route) return;

    this.routeSub = new Subscription();

    // Sync step from route path param (/validation/new/:step)
    if (this.route.paramMap) {
      const paramSub = this.route.paramMap.subscribe(params => {
        const stepParam = params?.get?.('step');
        if (stepParam) {
          this.activateStepFromParam(stepParam);
        }
      });
      this.routeSub.add(paramSub);
    }

    // Sync step and parameters from query param (?step=6, ?projectId=..., ?migrationId=...)
    if (this.route.queryParamMap) {
      const querySub = this.route.queryParamMap.subscribe(queryParams => {
        const stepQuery = queryParams?.get?.('step');
        if (stepQuery) {
          this.activateStepFromParam(stepQuery);
        }
        const proj = queryParams?.get?.('projectId');
        if (proj) {
          this.projectId.set(proj);
        }
        const migId = queryParams?.get?.('migrationId');
        if (migId) {
          this.originatingMigrationId.set(migId);
          this.hydrateFromMigration(migId);
        }
      });
      this.routeSub.add(querySub);
    }
  }

  public async hydrateFromMigration(migId: string): Promise<void> {
    if (!this.migrationIpc) {
      this.handoffBlocked.set(true);
      this.handoffError.set('Validation IPC is unavailable to hydrate migration record.');
      return;
    }

    try {
      const res = await this.migrationIpc.getMigration(migId);
      if (!res || res.status !== 'SUCCESS' || !res.data) {
        this.handoffBlocked.set(true);
        this.handoffError.set(`Migration handoff failed: migration "${migId}" could not be resolved from authoritative records.`);
        return;
      }

      const mig = res.data;
      const state = mig.state;
      // Parity validation requires an eligible completed or cutover execution state
      if (state !== 'COMPLETED' && state !== 'CUTOVER') {
        this.handoffBlocked.set(true);
        this.handoffError.set(`Migration handoff failed: migration "${migId}" is in state "${state}". Parity validation is only permitted for completed or cutover migrations.`);
        return;
      }

      // Valid and eligible migration!
      this.handoffBlocked.set(false);
      this.handoffError.set(null);

      const cfg = mig.configuration || {};
      const srcConnId = cfg.source_connection_id || cfg.sourceConnectionId;
      const tgtConnId = cfg.target_connection_id || cfg.targetConnectionId;

      let srcHost = cfg.source_host || cfg.sourceHost || '';
      let srcPort = Number(cfg.source_port || cfg.sourcePort || 0);
      let srcDb = cfg.source_database || cfg.sourceDatabase || '';
      let srcUser = cfg.source_username || cfg.sourceUsername || '';
      let srcProvider = cfg.source_provider || cfg.sourceProvider || mig.sourceProvider || mig.source_provider || '';

      let tgtHost = cfg.target_host || cfg.targetHost || '';
      let tgtPort = Number(cfg.target_port || cfg.targetPort || 0);
      let tgtDb = cfg.target_database || cfg.targetDatabase || '';
      let tgtUser = cfg.target_username || cfg.targetUsername || '';
      let tgtProvider = cfg.target_provider || cfg.targetProvider || mig.targetProvider || mig.target_provider || '';

      // If connection IDs are present, resolve authoritative connection records
      if (srcConnId) {
        try {
          const srcRes = await this.migrationIpc.getConnection(srcConnId);
          if (srcRes?.status === 'SUCCESS' && srcRes.data) {
            const sc = srcRes.data;
            const params = sc.parameters || {};
            srcProvider = srcProvider || sc.providerName || sc.providerId || sc.provider || '';
            srcHost = srcHost || params['host'] || sc.host || '';
            srcPort = srcPort || Number(params['port']) || Number(sc.port) || 0;
            srcDb = srcDb || params['database'] || params['service_name'] || sc.databaseName || '';
            srcUser = srcUser || params['username'] || sc.username || '';
          }
        } catch {
          // Keep existing values
        }
      }

      if (tgtConnId) {
        try {
          const tgtRes = await this.migrationIpc.getConnection(tgtConnId);
          if (tgtRes?.status === 'SUCCESS' && tgtRes.data) {
            const tc = tgtRes.data;
            const params = tc.parameters || {};
            tgtProvider = tgtProvider || tc.providerName || tc.providerId || tc.provider || '';
            tgtHost = tgtHost || params['host'] || tc.host || '';
            tgtPort = tgtPort || Number(params['port']) || Number(tc.port) || 0;
            tgtDb = tgtDb || params['database'] || params['service_name'] || tc.databaseName || '';
            tgtUser = tgtUser || params['username'] || tc.username || '';
          }
        } catch {
          // Keep existing values
        }
      }

      const scopeUnits = (cfg.comparison_units || cfg.comparisonUnits || cfg.selected_tables || []).map((t: any) => {
        if (typeof t === 'string') {
          return {
            id: `unit-${t}`,
            sourceName: t,
            expectedTargetName: t,
            targetName: t,
            targetStatus: 'CONFIRMED',
            status: 'VERIFIED',
            coveragePolicy: 'EXHAUSTIVE',
            discrepancyCount: 0
          };
        }
        return t;
      });

      this.vs.updateDraft({
        name: `Validation: ${mig.name || mig.migration_id || migId}`,
        environment: mig.environment || cfg.environment || 'Production',
        projectId: mig.project_id || mig.projectId,
        validationContext: (mig.project_id || mig.projectId) ? 'EXISTING_PROJECT' : 'INDEPENDENT',
        sourceConnectionMode: srcConnId ? 'SAVED' : 'NEW',
        sourceConnectionId: srcConnId,
        sourceProvider: srcProvider as any,
        sourceHost: srcHost,
        sourcePort: srcPort,
        sourceDatabase: srcDb,
        sourceUsername: srcUser,
        targetConnectionMode: tgtConnId ? 'SAVED' : 'NEW',
        targetConnectionId: tgtConnId,
        targetProvider: tgtProvider as any,
        targetHost: tgtHost,
        targetPort: tgtPort,
        targetDatabase: tgtDb,
        targetUsername: tgtUser,
        targetSchema: tgtDb || cfg.target_schema || cfg.targetSchema || '',
        comparisonUnits: scopeUnits,
        scopedPairs: scopeUnits
      });
    } catch (err: any) {
      this.handoffBlocked.set(true);
      this.handoffError.set(`Migration handoff resolution error: ${err?.message || 'Unknown resolution failure'}`);
    }
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
  }

  private activateStepFromParam(param: string): void {
    const p = param.trim().toLowerCase();
    const map: Record<string, number> = {
      '1': 1, 'definition': 1, 'step1': 1,
      '2': 2, 'source': 2, 'step2': 2,
      '3': 3, 'target': 3, 'step3': 3,
      '4': 4, 'scope': 4, 'step4': 4,
      '5': 5, 'boundary': 5, 'step5': 5,
      '6': 6, 'strategy': 6, 'step6': 6,
      '7': 7, 'readiness': 7, 'step7': 7,
      '8': 8, 'review': 8, 'step8': 8
    };
    const target = map[p];
    if (target && target >= 1 && target <= 8 && target !== this.currentStep()) {
      this.vs.updateDraft({ currentStep: target });
    }
  }

  @HostListener('window:keydown', ['$event'])
  public handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.showExitModal.set(false);
    }
  }

  public handleExit(): void {
    if (this.vs.newValidationDraft().isDirty) {
      this.showExitModal.set(true);
    } else {
      this.exitToValidationHome();
    }
  }

  public exitToValidationHome(): void {
    this.showExitModal.set(false);
    const pid = this.projectId();
    this.vs.resetDraft();
    if (pid) {
      this.router.navigate(['/migration/projects', pid, 'validations']);
    } else {
      this.router.navigate(['/migration/validation']);
    }
  }

  public goToStep(stepIndex: number): void {
    this.vs.updateDraft({ currentStep: stepIndex });
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { step: stepIndex },
      queryParamsHandling: 'merge'
    });
  }

  public goToCompletedStep(stepIndex: number): void {
    if (stepIndex < this.currentStep()) {
      this.goToStep(stepIndex);
    }
  }

  public continueToNextStep(): void {
    if (this.isCurrentStepValid() && this.currentStep() < 8) {
      const next = this.currentStep() + 1;
      this.goToStep(next);
    }
  }

  public previousStep(): void {
    if (this.currentStep() > 1) {
      const prev = this.currentStep() - 1;
      this.goToStep(prev);
    }
  }

  public isSubmitting = signal<boolean>(false);
  public submitError = signal<string | null>(null);

  public async initializeValidation(): Promise<void> {
    if (!this.isCurrentStepValid() || this.isSubmitting()) return;

    this.isSubmitting.set(true);
    this.submitError.set(null);
    const draft = this.vs.newValidationDraft();

    try {
      // Serialize Step 4 Scope & Step 6 Strategy Exception rules into canonical contracts
      const scopeUnits = (draft.comparisonUnits && draft.comparisonUnits.length > 0) ? draft.comparisonUnits : (draft.scopedPairs || []);
      const primaryTable = scopeUnits.length > 0 ? (scopeUnits[0].sourceName || scopeUnits[0].expectedTargetName) : undefined;

      const scopeConfig = {
        table_name: primaryTable,
        comparison_units: scopeUnits,
        selected_correspondence_rule: draft.selectedCorrespondenceRule || 'EXACT_IDENTIFIER_MATCH',
        step4_pathway: draft.step4Pathway || 'CHOICE',
        selected_namespaces: draft.selectedScopeNamespaces || []
      };

      const executionPolicy = {
        mode: draft.assuranceLevel || 'PARTITION_FINGERPRINT',
        temporal_cadence: draft.temporalCadence || 'CONSISTENT_STATE',
        coverage_policy: draft.coveragePolicy || 'EXHAUSTIVE',
        assurance_exceptions: draft.assuranceExceptions || [],
        advanced_coverage: draft.advancedCoverage || null
      };

      // 1. Create Mission via MigrationIpc
      const createRes = await this.migrationIpc.createValidationMission({
        name: draft.name || 'Untitled Validation Mission',
        source_id: draft.sourceDatabase || draft.sourceHost || 'src-1',
        target_id: draft.targetDatabase || draft.targetHost || 'tgt-1',
        source_provider: draft.sourceProvider || 'Oracle',
        target_provider: draft.targetProvider || 'PostgreSQL',
        temporal_strategy: draft.temporalCadence || (draft.step8TimingChoice === 'CONTINUOUS' ? 'CONTINUOUS' : (draft.step8TimingChoice === 'RECURRING' ? 'RECURRING' : (draft.step8TimingChoice === 'SCHEDULE_LATER' ? 'SCHEDULE_LATER' : 'EXECUTE_ON_INIT'))),
        assurance_level: draft.assuranceLevel || 'PARTITION_FINGERPRINT',
        environment: draft.environment || 'Production',
        project_id: draft.projectId,
        scope_config: scopeConfig,
        execution_policy: executionPolicy
      });

      if (createRes.status !== 'SUCCESS') {
        throw new Error(createRes.error || 'Failed to create validation mission via IPC');
      }

      const missionId = createRes.data?.mission_id || `miss_${Date.now()}`;

      // 2. Initialize Mission via MigrationIpc
      await this.migrationIpc.initializeValidationMission({
        mission_id: missionId
      });

      // 3. Handle Execution Timing Choice
      const choice = draft.step8TimingChoice || 'INITIALIZATION';
      if (choice === 'INITIALIZATION') {
        await this.migrationIpc.executeValidationMission({ mission_id: missionId });
      }

      this.isSubmitting.set(false);
      this.vs.resetDraft();
      this.router.navigate(['/validation', missionId]);
    } catch (err: any) {
      this.isSubmitting.set(false);
      this.submitError.set(err?.message || 'Initialization failed');
    }
  }
}
