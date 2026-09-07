import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step1ProjectIdentityComponent } from './step1-project-identity.component';
import { Step2AccessResourcesComponent } from './step2-access-resources.component';
import { Step3ProjectReviewComponent } from './step3-project-review.component';

export interface ProjectStepRailItem {
  index: number;
  label: string;
}

@Component({
  selector: 'app-create-project',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    Step1ProjectIdentityComponent,
    Step2AccessResourcesComponent,
    Step3ProjectReviewComponent
  ],
  template: `
    <!-- Fluid Creation Shell matching Migration & Initiative Creation standard -->
    <div class="flex flex-col h-[calc(100vh-theme(spacing.16))] -m-6 lg:-m-9 bg-slate-50 overflow-hidden select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- ZONE 1: TOP SHELL BAR (Exit | Title | Context Scope | Saved Indicator)    -->
      <!-- ========================================================================= -->
      <header class="h-[52px] bg-white border-b border-slate-200 shrink-0 z-30 px-6 lg:px-8 flex items-center justify-between overflow-visible">
        
        <!-- Left: Exit Button + Breadcrumb -->
        <div class="flex items-center gap-3.5 min-w-0">
          <button
            type="button"
            (click)="handleExit()"
            class="h-8 px-3 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 flex items-center justify-center cursor-pointer transition-colors shrink-0"
            title="Exit Project Creation">
            Exit
          </button>

          <span class="h-4 w-[1px] bg-slate-200 shrink-0"></span>

          <!-- Breadcrumb tracking -->
          <h1 class="text-[10px] font-bold tracking-wider uppercase text-slate-500 shrink-0 m-0 leading-none font-heading">
            CREATE PROJECT &middot; STEP {{ ps.projectWizardStep() }} OF 3
          </h1>
        </div>

        <!-- Right Side: Auto-Save / Shell Context Indicator -->
        <div class="flex items-center gap-3 shrink-0">
          <div class="h-8 px-3 rounded-md border border-slate-200 bg-white flex items-center gap-2 text-xs font-medium text-slate-700 shadow-2xs">
            <span class="w-1.5 h-1.5 rounded-sm bg-emerald-500 shrink-0"></span>
            <span class="text-slate-600 font-medium">Draft Ready</span>
          </div>
        </div>

      </header>

      <!-- ========================================================================= -->
      <!-- ZONE 2: LOW-PROFILE 3-STEP PROCESS STEPPER                                -->
      <!-- ========================================================================= -->
      <nav aria-label="Creation Steps Progress" class="h-12 bg-white border-b border-slate-200 px-6 lg:px-8 flex items-center shrink-0 relative z-20">
        <div class="w-full max-w-4xl mx-auto flex items-center justify-between gap-4">
          @for (step of steps; track step.index) {
            
            @if (step.index === ps.projectWizardStep()) {
              <!-- Active Step -->
              <div 
                class="flex items-center gap-2 text-slate-900 font-bold text-xs shrink-0 select-none"
                aria-current="step">
                <span class="w-5 h-5 rounded-md bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </div>
            } @else if (step.index < ps.projectWizardStep()) {
              <!-- Completed Step -->
              <button
                type="button"
                (click)="goToStep(step.index)"
                class="flex items-center gap-2 text-slate-600 hover:text-slate-900 text-xs font-medium shrink-0 cursor-pointer transition-colors group">
                <span class="w-5 h-5 rounded-md bg-slate-100 group-hover:bg-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center shrink-0 border border-slate-200">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </button>
            } @else {
              <!-- Future Step -->
              <div
                class="flex items-center gap-2 text-slate-400 text-xs font-normal shrink-0 cursor-not-allowed"
                aria-disabled="true">
                <span class="w-5 h-5 rounded-md bg-slate-100 border border-slate-200 text-slate-400 text-[10px] font-medium flex items-center justify-center shrink-0">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </div>
            }

          }
        </div>
      </nav>

      <!-- ========================================================================= -->
      <!-- ZONE 3: ACTIVE STEP WORKSPACE CANVAS                                      -->
      <!-- ========================================================================= -->
      <section
        aria-label="Active Step Workspace Canvas"
        class="flex-1 min-h-0 overflow-y-auto px-6 lg:px-8 py-6">
        @switch (ps.projectWizardStep()) {
          @case (1) { <app-step1-project-identity /> }
          @case (2) { <app-step2-access-resources /> }
          @case (3) { <app-step3-project-review /> }
        }
      </section>

      <!-- ========================================================================= -->
      <!-- ZONE 4: FIXED FOOTER (Previous Step on Left, Continue/Create on Right)    -->
      <!-- ========================================================================= -->
      <footer class="h-14 border-t border-slate-200 bg-white px-6 lg:px-8 flex items-center justify-between shrink-0 z-30">
        
        <!-- Left Slot: Previous Step -->
        <div>
          @if (ps.projectWizardStep() > 1) {
            <button
              type="button"
              (click)="previousStep()"
              class="h-9 px-3.5 text-xs font-semibold text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center justify-center cursor-pointer shadow-2xs">
              Previous Step
            </button>
          }
        </div>

        <!-- Right Slot: Continue / Create Action -->
        <div class="flex items-center gap-3">
          @if (ps.projectWizardStep() < 3) {
            <button
              type="button"
              (click)="nextStep()"
              [disabled]="!canContinue()"
              class="h-9 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-md flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
              Continue
            </button>
          } @else {
            <button
              type="button"
              (click)="submitProject()"
              class="h-9 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
              Create Project
            </button>
          }
        </div>

      </footer>

      <!-- Creation Intent Acknowledged Modal (Pre-P7D) -->
      @if (isSubmittedModalOpen()) {
        <div
          class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          (click)="closeModalAndReturn()">
          <div
            class="w-full max-w-md bg-white border border-slate-200 rounded-xl shadow-2xl p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3 text-blue-600">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0">
                <app-lucide-icon name="layers" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-base font-bold text-slate-900 font-heading">Project Created</h3>
                <span class="text-[11px] text-slate-500 font-semibold">Workspace Registered</span>
              </div>
            </div>

            <p class="text-xs text-slate-700 leading-relaxed font-normal">
              Project <strong>{{ createdProjectName() }}</strong> has been initialized with 
              {{ createdAccessCount() }} access assignment{{ createdAccessCount() === 1 ? '' : 's' }} and 
              {{ createdResourceCount() }} associated connection resource{{ createdResourceCount() === 1 ? '' : 's' }}.
            </p>

            <div class="p-3 bg-blue-50/60 rounded-lg border border-blue-200/80 text-[11px] text-blue-900 leading-normal">
              You can now launch migrations and validations scoped to this project workspace.
            </div>

            <div class="pt-2 border-t border-slate-100 flex items-center justify-end gap-2.5">
              <button
                type="button"
                (click)="closeModalAndReturn()"
                class="h-9 px-3.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                Back to Projects
              </button>
              <button
                type="button"
                (click)="goToNewProjectWorkspace()"
                class="h-9 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer flex items-center justify-center">
                Go to Project Workspace
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class CreateProjectComponent {
  public ps = inject(ProjectsService);
  private router = inject(Router);

  public isSubmittedModalOpen = signal<boolean>(false);
  public createdProjectId = signal<string>('');
  public createdProjectName = signal<string>('');
  public createdAccessCount = signal<number>(0);
  public createdResourceCount = signal<number>(0);

  public steps: ProjectStepRailItem[] = [
    { index: 1, label: 'Project Identity' },
    { index: 2, label: 'Access & Resources' },
    { index: 3, label: 'Review & Create' }
  ];

  public canContinue(): boolean {
    if (this.ps.projectWizardStep() === 1) {
      return this.ps.projectDraft().name.trim().length > 0;
    }
    return true;
  }

  public nextStep(): void {
    if (this.canContinue() && this.ps.projectWizardStep() < 3) {
      this.ps.setProjectWizardStep(this.ps.projectWizardStep() + 1);
    }
  }

  public previousStep(): void {
    if (this.ps.projectWizardStep() > 1) {
      this.ps.setProjectWizardStep(this.ps.projectWizardStep() - 1);
    }
  }

  public goToStep(step: number): void {
    if (step < this.ps.projectWizardStep()) {
      this.ps.setProjectWizardStep(step);
    }
  }

  public submitProject(): void {
    const draft = this.ps.projectDraft();
    this.createdProjectName.set(draft.name);
    this.createdAccessCount.set(draft.accessAssignments.length);
    this.createdResourceCount.set(draft.selectedResourceIds.length);

    const newId = this.ps.submitCreateProject();
    this.createdProjectId.set(newId);
    this.isSubmittedModalOpen.set(true);
  }

  public goToNewProjectWorkspace(): void {
    const id = this.createdProjectId();
    this.isSubmittedModalOpen.set(false);
    this.ps.clearProjectDraft();
    if (id) {
      this.router.navigate(['/migration/projects', id]);
    } else {
      this.router.navigate(['/migration/projects']);
    }
  }

  public closeModalAndReturn(): void {
    this.isSubmittedModalOpen.set(false);
    this.ps.clearProjectDraft();
    this.router.navigate(['/migration/projects']);
  }

  public handleExit(): void {
    this.ps.clearProjectDraft();
    this.router.navigate(['/migration/projects']);
  }
}
