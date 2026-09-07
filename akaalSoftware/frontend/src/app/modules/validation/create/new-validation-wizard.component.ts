import { Component, inject, signal, computed, HostListener, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
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
              [disabled]="!isCurrentStepValid()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 cursor-pointer transition-colors"
              title="Initialize Validation">
              <span>Initialize Validation</span>
              <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
            </button>
          }
        </div>

      </footer>

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

  public isCurrentStepValid = computed(() => {
    return this.vs.isStepValid(this.currentStep());
  });

  constructor(vs?: ValidationUiService, router?: Router, route?: ActivatedRoute) {
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

    // Sync step from query param (?step=6 or ?step=strategy)
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
      });
      this.routeSub.add(querySub);
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

  public initializeValidation(): void {
    if (this.isCurrentStepValid()) {
      const pid = this.projectId();
      this.vs.resetDraft();
      if (pid) {
        this.router.navigate(['/migration/projects', pid, 'validations']);
      } else {
        this.router.navigate(['/migration/validation']);
      }
    }
  }
}
