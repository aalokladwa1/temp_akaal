import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { Step1DefinitionComponent } from './steps/step1-definition.component';
import { Step2SourceComponent } from './steps/step2-source.component';
import { Step3TargetComponent } from './steps/step3-target.component';
import { Step4ScopeComponent } from './steps/step4-scope.component';
import { Step5MappingComponent } from './steps/step5-mapping.component';
import { Step6ConfigComponent } from './steps/step6-config.component';
import { Step7PlanComponent } from './steps/step7-plan.component';
import { Step8GovernanceComponent } from './steps/step8-governance.component';
import { Step9ReviewComponent } from './steps/step9-review.component';

@Component({
  selector: 'app-create-migration-wizard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideIconComponent,
    Step1DefinitionComponent,
    Step2SourceComponent,
    Step3TargetComponent,
    Step4ScopeComponent,
    Step5MappingComponent,
    Step6ConfigComponent,
    Step7PlanComponent,
    Step8GovernanceComponent,
    Step9ReviewComponent
  ],
  template: `
    <div class="flex flex-col gap-5 w-full max-w-[1680px] mx-auto font-sans pb-12 select-none animate-in fade-in duration-150 text-xs">
      
      <!-- =============================================================== -->
      <!-- TOP HEADER                                                      -->
      <!-- =============================================================== -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        
        <div class="flex flex-col gap-0.5">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">OPERATIONS</span>
          <div class="flex items-center gap-3">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">CREATE MIGRATION</h1>
            <span class="text-slate-300">&bull;</span>
            <span class="text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
              Step {{ ms.wizardDraft().currentStep }} of 9: {{ getStepTitle(ms.wizardDraft().currentStep) }}
            </span>
          </div>
        </div>

        <!-- Right Header Actions -->
        <div class="flex items-center gap-2.5">
          
          <!-- Auto-Save Status Pill -->
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200/90 text-xs font-semibold text-slate-800 shadow-2xs">
            @if (ms.saveStatus() === 'SAVING') {
              <app-lucide-icon name="refresh-cw" [size]="12" class="animate-spin text-blue-600"></app-lucide-icon>
              <span>Saving...</span>
            } @else {
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>Draft saved</span>
            }
          </div>

          <button
            type="button"
            (click)="manualSaveDraft()"
            class="h-9 px-3.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-bold transition-all shadow-2xs cursor-pointer flex items-center gap-1.5">
            <app-lucide-icon name="save" [size]="13" class="text-blue-600"></app-lucide-icon>
            <span>Save Draft</span>
          </button>

          <a
            routerLink="/migration"
            class="h-9 px-3.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5"
            title="Exit to Migration Home">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
            <span>Exit</span>
          </a>

        </div>

      </div>

      <!-- =============================================================== -->
      <!-- MAIN 2-COLUMN WORKSPACE: LEFT RAIL + RIGHT CONTENT              -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        <!-- LEFT VERTICAL STEPS RAIL (Col-span 3 / 240px Fixed) -->
        <div class="lg:col-span-3 xl:col-span-3 flex flex-col gap-2 p-3 rounded-2xl bg-white border border-slate-200/90 shadow-2xs sticky top-4">
          <span class="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider px-3 py-1">
            Migration Steps
          </span>

          <div class="flex flex-col gap-1">
            @for (step of steps; track step.num) {
              <button
                type="button"
                (click)="goToStep(step.num)"
                class="flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer text-left group"
                [class.bg-blue-600]="ms.wizardDraft().currentStep === step.num"
                [class.text-white]="ms.wizardDraft().currentStep === step.num"
                [class.shadow-xs]="ms.wizardDraft().currentStep === step.num"
                [class.hover:bg-slate-100]="ms.wizardDraft().currentStep !== step.num"
                [class.text-slate-700]="ms.wizardDraft().currentStep !== step.num">
                
                <div class="flex items-center gap-2.5 min-w-0">
                  <span
                    class="w-5 h-5 rounded-full flex items-center justify-center text-[10.5px] font-extrabold shrink-0"
                    [class.bg-white]="ms.wizardDraft().currentStep === step.num"
                    [class.text-blue-700]="ms.wizardDraft().currentStep === step.num"
                    [class.bg-emerald-100]="ms.wizardDraft().currentStep !== step.num && isStepCompleted(step.num)"
                    [class.text-emerald-800]="ms.wizardDraft().currentStep !== step.num && isStepCompleted(step.num)"
                    [class.bg-slate-100]="ms.wizardDraft().currentStep !== step.num && !isStepCompleted(step.num)"
                    [class.text-slate-600]="ms.wizardDraft().currentStep !== step.num && !isStepCompleted(step.num)">
                    @if (isStepCompleted(step.num) && ms.wizardDraft().currentStep !== step.num) {
                      ✓
                    } @else {
                      {{ step.num }}
                    }
                  </span>

                  <span class="truncate">{{ step.label }}</span>
                </div>

                @if (ms.wizardDraft().currentStep === step.num) {
                  <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
                }
              </button>
            }
          </div>
        </div>

        <!-- RIGHT MAIN WORKSPACE (Col-span 9 / Full Width of Grid) -->
        <div class="lg:col-span-9 xl:col-span-9 flex flex-col gap-5">
          
          <!-- Active Step View Component -->
          @switch (ms.wizardDraft().currentStep) {
            @case (1) { <app-step1-definition></app-step1-definition> }
            @case (2) { <app-step2-source></app-step2-source> }
            @case (3) { <app-step3-target></app-step3-target> }
            @case (4) { <app-step4-scope></app-step4-scope> }
            @case (5) { <app-step5-mapping></app-step5-mapping> }
            @case (6) { <app-step6-config></app-step6-config> }
            @case (7) { <app-step7-plan></app-step7-plan> }
            @case (8) { <app-step8-governance></app-step8-governance> }
            @case (9) { <app-step9-review></app-step9-review> }
          }

          <!-- Bottom Step Action Bar -->
          <div class="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-2xs flex items-center justify-between flex-wrap gap-4">
            @if (ms.wizardDraft().currentStep === 1) {
              <a
                routerLink="/migration"
                class="h-9 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all flex items-center gap-1.5">
                <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
                <span>Exit</span>
              </a>
            } @else {
              <button
                type="button"
                (click)="prevStep()"
                class="h-9 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5">
                <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
                <span>Previous Step</span>
              </button>
            }

            <div class="flex items-center gap-2.5">
              <button
                type="button"
                (click)="manualSaveDraft()"
                class="h-9 px-4 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-bold transition-all shadow-2xs cursor-pointer flex items-center gap-1.5">
                <app-lucide-icon name="save" [size]="13"></app-lucide-icon>
                <span>Save Draft</span>
              </button>

              @if (ms.wizardDraft().currentStep < 9) {
                <button
                  type="button"
                  (click)="nextStep()"
                  class="h-9 px-5 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-bold shadow-xs transition-all cursor-pointer flex items-center gap-2">
                  <span>Continue to {{ getStepTitle(ms.wizardDraft().currentStep + 1) }}</span>
                  <app-lucide-icon name="arrow-right" [size]="14"></app-lucide-icon>
                </button>
              } @else {
                <button
                  type="button"
                  (click)="initializeMigration()"
                  class="h-9 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-xs font-bold shadow-xs transition-all cursor-pointer flex items-center gap-2">
                  <app-lucide-icon name="play" [size]="14"></app-lucide-icon>
                  <span>Deploy &amp; Launch Migration Pipeline</span>
                </button>
              }
            </div>
          </div>

        </div>

      </div>

    </div>
  `
})
export class CreateMigrationWizardComponent {
  public ms = inject(MigrationUiService);
  private router = inject(Router);

  public steps = [
    { num: 1, label: '1. Definition' },
    { num: 2, label: '2. Source' },
    { num: 3, label: '3. Target' },
    { num: 4, label: '4. Scope' },
    { num: 5, label: '5. Mapping' },
    { num: 6, label: '6. Config' },
    { num: 7, label: '7. DAG & Gates' },
    { num: 8, label: '8. Governance' },
    { num: 9, label: '9. Launch' }
  ];

  public getStepTitle(stepNum: number): string {
    switch (stepNum) {
      case 1: return 'Definition';
      case 2: return 'Source Connection';
      case 3: return 'Target Connection';
      case 4: return 'Scope Discovery';
      case 5: return 'Schema Mappings';
      case 6: return 'Engine Configuration';
      case 7: return 'Execution DAG & Gates';
      case 8: return 'Pre-Flight Simulation';
      case 9: return 'Final Review & Launch';
      default: return 'Workbench';
    }
  }

  public isStepCompleted(stepNum: number): boolean {
    return stepNum < this.ms.wizardDraft().currentStep;
  }

  public goToStep(stepNum: number): void {
    this.ms.updateDraft({ currentStep: stepNum });
  }

  public prevStep(): void {
    if (this.ms.wizardDraft().currentStep > 1) {
      this.ms.updateDraft({ currentStep: this.ms.wizardDraft().currentStep - 1 });
    }
  }

  public nextStep(): void {
    if (this.ms.wizardDraft().currentStep < 9) {
      this.ms.updateDraft({ currentStep: this.ms.wizardDraft().currentStep + 1 });
    }
  }

  public manualSaveDraft(): void {
    this.ms.triggerAutoSave();
  }

  public initializeMigration(): void {
    const draft = this.ms.wizardDraft();
    const newId = `mig-${Date.now().toString().slice(-4)}`;
    const newMigration: any = {
      id: newId,
      name: draft.name || `${draft.sourceProvider} to ${draft.targetProvider} Migration`,
      sourceEngine: draft.sourceProvider,
      sourceInstance: `${draft.sourceHost || 'source-db.internal'}:${draft.sourcePort}`,
      targetEngine: draft.targetProvider,
      targetInstance: `${draft.targetHost || 'target-db.internal'}:${draft.targetPort}`,
      mode: draft.mode,
      environment: draft.environment,
      lifecycleState: 'RUNNING',
      currentStage: 'Worker Partitions Initializing',
      progressPercent: 0,
      health: 'HEALTHY',
      attentionCount: 0,
      requiresApproval: draft.customBarriersCount > 0,
      planVersion: `v${draft.planVersion}.0`,
      planFingerprint: 'Pending canonical compilation',
      updatedAt: new Date().toISOString()
    };

    this.ms.portfolioMigrations.update(list => [newMigration, ...list]);
    this.ms.selectedMigrationId.set(newId);
    this.router.navigate(['/migration', newId]);
  }
}
