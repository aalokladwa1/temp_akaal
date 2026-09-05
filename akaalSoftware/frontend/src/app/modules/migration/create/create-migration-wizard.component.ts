import { Component, inject, signal, computed, HostListener, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { Step1DefinitionComponent } from './steps/step1-definition.component';
import { Step2SourceComponent } from './steps/step2-source.component';
import { Step3TargetComponent } from './steps/step3-target.component';
import { Step4ScopeComponent } from './steps/step4-scope.component';
import { Step5MappingComponent } from './steps/step5-mapping.component';
import { Step5MappingStoreService } from '../../../core/services/step5-mapping-store.service';
import { Step6ConfigurationComponent } from './steps/step6-configuration.component';
import { Step6ConfigurationStoreService } from '../../../core/services/step6-configuration-store.service';
import { Step7PlanComponent } from './steps/step7-plan.component';
import { Step7PlanStoreService } from '../../../core/services/step7-plan-store.service';
import { MigrationPortfolioItem, MigrationTemplateItem } from '../../../core/models/migration-view.models';

export interface StepRailItem {
  index: number;
  label: string;
  nextLabel: string;
  prevLabel?: string;
}

@Component({
  selector: 'app-create-migration-wizard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    Step1DefinitionComponent,
    Step2SourceComponent,
    Step3TargetComponent,
    Step4ScopeComponent,
    Step5MappingComponent,
    Step6ConfigurationComponent,
    Step7PlanComponent
  ],
  template: `
    <!-- Fluid Content Wrapper: Integrated inside Platform Main Workspace with Left Sidebar & Top Header preserved -->
    <div class="flex flex-col h-[calc(100vh-theme(spacing.16))] -m-6 lg:-m-9 bg-slate-50 overflow-hidden select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- ZONE 1: TOP SHELL BAR (Exact Order: Exit | Title | Auto-Save | Clone | Tmpl) -->
      <!-- ========================================================================= -->
      <header class="h-[52px] bg-white border-b border-slate-200 shrink-0 z-30 px-6 lg:px-8 flex items-center justify-between overflow-visible">
        
        <!-- Left: Exit Button + Breadcrumb -->
        <div class="flex items-center gap-3.5 min-w-0">
          
          <!-- Exit Action Button -->
          <button
            type="button"
            (click)="handleExit()"
            class="h-8 px-2.5 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer transition-colors shrink-0"
            title="Exit Create Migration">
            <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
            <span>Exit</span>
          </button>

          <span class="h-4 w-[1px] bg-slate-200 shrink-0"></span>

          <!-- Breadcrumb tracking -->
          <h1 class="text-[10px] font-bold tracking-wider uppercase text-slate-500 shrink-0 m-0 leading-none">
            CREATION WIZARD &middot; STEP {{ currentStep() }} OF 9
          </h1>

        </div>

        <!-- Right Side (Exact Order: [ ● Saved · {{ timeAgo }} ] -> [ Clone ▾ ] -> [ Template ▾ ]) -->
        <div class="flex items-center gap-3 shrink-0">
          
          <!-- 1. Real Auto-Save Indicator -->
          <div class="h-8 px-2.5 rounded-lg border border-slate-200 bg-white flex items-center gap-2 text-xs font-medium text-slate-700">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
            <span class="text-slate-600 font-medium">Saved &middot; {{ relativeTimeString() }}</span>
          </div>

          <!-- 2. Clone ▾ Popover Dropdown (Right-aligned, w-72, overflow-safe) -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleClonePopover($event)"
              class="h-8 px-3 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer focus:outline-none"
              [class.border-blue-500]="isClonePopoverOpen()">
              <span>Clone</span>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isClonePopoverOpen()) {
              <div 
                class="absolute right-0 top-full mt-1.5 z-50 w-72 bg-white rounded-lg border border-slate-200 p-2 flex flex-col gap-1.5 animate-in fade-in duration-100"
                (click)="$event.stopPropagation()">
                
                <div class="px-2 py-1 flex items-center justify-between border-b border-slate-100">
                  <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Clone Existing Migration</span>
                  <span class="text-[10px] text-slate-400">{{ availableCloneSources().length }} available</span>
                </div>

                <!-- Search Input for Clone -->
                <div class="px-1">
                  <input
                    type="text"
                    [(ngModel)]="cloneSearchQuery"
                    placeholder="Search past migrations..."
                    class="w-full h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500" />
                </div>

                <!-- Migrations List -->
                <div class="max-h-56 overflow-y-auto flex flex-col gap-0.5">
                  @for (item of filteredCloneSources(); track item.id) {
                    <button
                      type="button"
                      (click)="promptCloneConfirmation(item)"
                      class="w-full text-left px-2.5 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex flex-col gap-0.5 cursor-pointer border border-transparent hover:border-slate-200">
                      <div class="flex items-center justify-between">
                        <span class="font-semibold text-slate-900 truncate">{{ item.name }}</span>
                        <span class="text-[10px] font-mono text-slate-400 shrink-0">{{ item.mode }}</span>
                      </div>
                      <span class="text-[10px] text-slate-500 truncate">{{ item.sourceEngine }} &rarr; {{ item.targetEngine }}</span>
                    </button>
                  }
                  @if (filteredCloneSources().length === 0) {
                    <div class="py-4 text-center text-slate-400 text-xs font-medium">No matching migrations found</div>
                  }
                </div>

              </div>
            }
          </div>

          <!-- 3. Template ▾ Popover Dropdown (Right-aligned, w-72, overflow-safe) -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleTemplatePopover($event)"
              class="h-8 px-3 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer focus:outline-none"
              [class.border-blue-500]="isTemplatePopoverOpen()">
              <span>Template</span>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isTemplatePopoverOpen()) {
              <div 
                class="absolute right-0 top-full mt-1.5 z-50 w-72 bg-white rounded-lg border border-slate-200 p-2 flex flex-col gap-1.5 animate-in fade-in duration-100"
                (click)="$event.stopPropagation()">
                
                <div class="px-2 py-1 flex items-center justify-between border-b border-slate-100">
                  <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Enterprise Blueprints</span>
                  <span class="text-[10px] text-slate-400">{{ availableTemplates().length }} templates</span>
                </div>

                <!-- Template Items List -->
                <div class="max-h-60 overflow-y-auto flex flex-col gap-1">
                  @for (tmpl of availableTemplates(); track tmpl.id) {
                    <button
                      type="button"
                      (click)="promptTemplateConfirmation(tmpl)"
                      class="w-full text-left px-2.5 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex flex-col gap-0.5 cursor-pointer border border-transparent hover:border-slate-200">
                      <div class="flex items-center justify-between">
                        <span class="font-semibold text-slate-900">{{ tmpl.title }}</span>
                        <span class="text-[10px] font-mono px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded">{{ tmpl.compatibleModes[0] }}</span>
                      </div>
                      <span class="text-[10px] text-slate-500 leading-tight">{{ tmpl.description }}</span>
                    </button>
                  }
                </div>

              </div>
            }
          </div>

        </div>

      </header>

      <!-- ========================================================================= -->
      <!-- ZONE 2: LOW-PROFILE 9-STEP PROCESS STEPPER (Clean floating steps, no line)-->
      <!-- ========================================================================= -->
      <nav aria-label="Wizard Steps Progress" class="h-12 bg-white border-b border-slate-200 px-6 lg:px-8 flex items-center shrink-0 relative z-20">
        
        <!-- Stepper Items Flex Container: Cleanly floating with flex gap spacing, NO connecting line -->
        <div class="w-full max-w-6xl mx-auto flex items-center justify-between gap-2 overflow-x-hidden">
          @for (step of steps; track step.index) {
            
            <!-- Case 1: Active Step (Brand Primary Index & Text) -->
            @if (step.index === currentStep()) {
              <div 
                class="flex items-center gap-2 text-slate-900 font-bold text-xs shrink-0 select-none"
                aria-current="step">
                <span class="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </div>
            }

            <!-- Case 2: Completed Step (Clickable Backward Navigation) -->
            @if (step.index < currentStep()) {
              <button
                type="button"
                (click)="goToCompletedStep(step.index)"
                class="flex items-center gap-2 text-slate-600 hover:text-slate-900 text-xs font-medium shrink-0 cursor-pointer transition-colors group"
                title="Jump backward to Step {{ step.index }}: {{ step.label }}">
                <span class="w-5 h-5 rounded-full bg-slate-100 group-hover:bg-slate-200 text-slate-600 text-[10px] font-bold flex items-center justify-center shrink-0 border border-slate-200">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </button>
            }

            <!-- Case 3: Locked Future Step (Disabled with Explanatory Tooltip) -->
            @if (step.index > currentStep()) {
              <div
                class="flex items-center gap-2 text-slate-500 text-xs font-normal shrink-0 cursor-not-allowed"
                aria-disabled="true"
                [title]="'Complete Step ' + currentStep() + ' before continuing to Step ' + step.index + ' (' + step.label + ')'">
                <span class="w-5 h-5 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-[10px] font-medium flex items-center justify-center shrink-0">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </div>
            }

          }
        </div>

      </nav>

      <!-- ========================================================================= -->
      <!-- ZONE 3: ACTIVE STEP WORKSPACE CANVAS (Responsive Step Geometry)           -->
      <!-- ========================================================================= -->
      <section
        aria-label="Active Step Workspace Canvas"
        class="flex-1 min-h-0 select-none"
        [class.overflow-y-auto]="currentStep() !== 4 && currentStep() !== 5"
        [class.overflow-hidden]="currentStep() === 4 || currentStep() === 5"
        [class.px-6]="currentStep() !== 4 && currentStep() !== 5"
        [class.lg:px-8]="currentStep() !== 4 && currentStep() !== 5"
        [class.py-4]="currentStep() !== 4 && currentStep() !== 5"
        [class.lg:py-5]="currentStep() !== 4 && currentStep() !== 5"
        [class.p-3]="currentStep() === 4 || currentStep() === 5"
        [class.lg:p-4]="currentStep() === 4 || currentStep() === 5"
        [class.flex]="currentStep() === 4 || currentStep() === 5"
        [class.flex-col]="currentStep() === 4 || currentStep() === 5"
        (click)="closeAllPopovers()">
        <div
          class="w-full mx-auto"
          [class.max-w-6xl]="currentStep() <= 3 || (currentStep() === 6 && step6Store.draft().depth === 'STANDARD')"
          [class.max-w-7xl]="currentStep() === 4 || currentStep() === 7 || (currentStep() === 6 && step6Store.draft().depth === 'ADVANCED')"
          [class.max-w-[1720px]]="currentStep() === 5"
          [class.h-full]="currentStep() === 4 || currentStep() === 5"
          [class.flex]="currentStep() === 4 || currentStep() === 5"
          [class.flex-col]="currentStep() === 4 || currentStep() === 5"
          [class.min-h-0]="currentStep() === 4 || currentStep() === 5">
          @switch (currentStep()) {
            @case (1) { <app-step1-definition /> }
            @case (2) { <app-step2-source /> }
            @case (3) { <app-step3-target /> }
            @case (4) { <app-step4-scope /> }
            @case (5) { <app-step5-mapping /> }
            @case (6) { <app-step6-configuration /> }
            @case (7) { <app-step7-plan /> }
            @default { 
              <div class="py-16 text-center text-slate-400 font-medium">
                Step {{ currentStep() }} ({{ currentStepItem().label }}) workspace ready for clean implementation
              </div> 
            }
          }
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- ZONE 4: FIXED FOOTER (Previous Step on Left, Continue on Right)           -->
      <!-- ========================================================================= -->
      <footer class="h-14 border-t border-slate-200 bg-white px-6 lg:px-8 flex items-center justify-between shrink-0 z-30">
        
        <!-- Left Slot: Previous Step (Far Left) -->
        <div class="flex items-center">
          @if (currentStep() > 1) {
            <button
              type="button"
              (click)="previousStep()"
              class="h-8 px-3 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer">
              <app-lucide-icon name="arrow-left" [size]="13"></app-lucide-icon>
              <span>Previous Step</span>
            </button>
          }
        </div>

        <!-- Right Slot: Right Cluster (Lock Scope for Step 4 & Continue Action Button) -->
        <div class="flex items-center gap-3">
          @if (currentStep() === 4 && ms.wizardDraft().discoveryHash) {
            @if (!ms.wizardDraft().isScopeLocked) {
              <button
                type="button"
                (click)="ms.lockScope()"
                [disabled]="!ms.canLockScope()"
                class="h-8 px-3.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:pointer-events-none rounded-md flex items-center gap-1.5 cursor-pointer transition-colors"
                title="Lock scope to proceed to Mapping">
                <app-lucide-icon name="lock" [size]="13"></app-lucide-icon>
                <span>Lock Scope</span>
              </button>
            } @else {
              <button
                type="button"
                (click)="ms.unlockScope()"
                class="h-8 px-3.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors"
                title="Unlock scope to modify selections">
                <app-lucide-icon name="unlock" [size]="13"></app-lucide-icon>
                <span>Unlock Scope</span>
              </button>
            }
          }

          @if (currentStep() === 5) {
            <!-- Step 5 Mapping Readiness Indicator -->
            <div class="h-8 px-3 rounded-md border flex items-center gap-1.5 text-xs font-medium"
              [class.border-rose-200]="ms.wizardDraft().hasStep5Blockers"
              [class.bg-rose-50]="ms.wizardDraft().hasStep5Blockers"
              [class.text-rose-700]="ms.wizardDraft().hasStep5Blockers"
              [class.border-amber-200]="!ms.wizardDraft().hasStep5Blockers && (ms.wizardDraft().step5GovernanceCount || 0) > 0"
              [class.bg-amber-50]="!ms.wizardDraft().hasStep5Blockers && (ms.wizardDraft().step5GovernanceCount || 0) > 0"
              [class.text-amber-800]="!ms.wizardDraft().hasStep5Blockers && (ms.wizardDraft().step5GovernanceCount || 0) > 0"
              [class.border-emerald-200]="!ms.wizardDraft().hasStep5Blockers && (ms.wizardDraft().step5GovernanceCount || 0) === 0"
              [class.bg-emerald-50]="!ms.wizardDraft().hasStep5Blockers && (ms.wizardDraft().step5GovernanceCount || 0) === 0"
              [class.text-emerald-700]="!ms.wizardDraft().hasStep5Blockers && (ms.wizardDraft().step5GovernanceCount || 0) === 0">
              
              @if (ms.wizardDraft().hasStep5Blockers) {
                <app-lucide-icon name="alert-triangle" [size]="13" class="text-rose-600 shrink-0"></app-lucide-icon>
                <span>Mapping readiness: {{ ms.wizardDraft().step5BlockerCount || 1 }} blocker{{ (ms.wizardDraft().step5BlockerCount || 1) > 1 ? 's' : '' }}</span>
              } @else if ((ms.wizardDraft().step5GovernanceCount || 0) > 0) {
                <app-lucide-icon name="shield-alert" [size]="13" class="text-amber-600 shrink-0"></app-lucide-icon>
                <span>Mapping readiness: Ready &middot; {{ ms.wizardDraft().step5GovernanceCount }} governance requirement{{ (ms.wizardDraft().step5GovernanceCount || 0) > 1 ? 's' : '' }}</span>
              } @else {
                <app-lucide-icon name="check-circle" [size]="13" class="text-emerald-600 shrink-0"></app-lucide-icon>
                <span>Mapping readiness: Ready</span>
              }
            </div>
          }

          @if (currentStep() === 6) {
            <!-- Step 6 Configuration Readiness Indicator -->
            <div class="h-8 px-3 rounded-md border flex items-center gap-1.5 text-xs font-medium"
              [class.border-rose-200]="!step6Store.isStep6Valid()"
              [class.bg-rose-50]="!step6Store.isStep6Valid()"
              [class.text-rose-700]="!step6Store.isStep6Valid()"
              [class.border-emerald-200]="step6Store.isStep6Valid()"
              [class.bg-emerald-50]="step6Store.isStep6Valid()"
              [class.text-emerald-700]="step6Store.isStep6Valid()">
              
              @if (!step6Store.isStep6Valid()) {
                <app-lucide-icon name="alert-triangle" [size]="13" class="text-rose-600 shrink-0"></app-lucide-icon>
                <span>Configuration readiness: Incomplete parameters</span>
              } @else {
                <app-lucide-icon name="check-circle" [size]="13" class="text-emerald-600 shrink-0"></app-lucide-icon>
                <span>Configuration readiness: Ready</span>
              }
            </div>
          }

          @if (currentStep() < 9) {
            <button
              type="button"
              (click)="continueToNextStep()"
              [disabled]="!isCurrentStepValid()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 cursor-pointer transition-colors"
              title="Continue to next step">
              <span>Continue to {{ nextStepLabel() }}</span>
              <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
            </button>
          } @else {
            <button
              type="button"
              (click)="onStep9Action()"
              [disabled]="!isCurrentStepValid()"
              class="h-8 px-4 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 cursor-pointer transition-colors">
              <span>Initialize &amp; Launch</span>
              <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
            </button>
          }

        </div>

      </footer>

      <!-- ========================================================================= -->
      <!-- OVERLAYS (Loss-Risk Guardrail Modal & Confirmation Modals)               -->
      <!-- ========================================================================= -->

      <!-- 1. UNSAFE EXIT LOSS-RISK CONFIRMATION DIALOG -->
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
                <h3 class="text-sm font-bold text-slate-900">Exit Create Migration?</h3>
                <span class="text-xs text-slate-500 font-medium">Unpersisted changes detected</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-medium">
              Some draft changes have not been safely persisted yet. Exiting now may result in losing recent configurations.
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
                (click)="exitToMigrationHome()"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer">
                Exit to Portfolio
              </button>
            </div>

          </div>
        </div>
      }

      <!-- 2. CLONE OVERWRITE CONFIRMATION MODAL -->
      @if (pendingCloneSource()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
          (click)="pendingCloneSource.set(null)">
          <div
            class="w-full max-w-lg rounded-xl bg-white border border-slate-200 p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="copy" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">Clone Migration Configuration?</h3>
                <span class="text-xs text-slate-500 font-medium">Source: {{ pendingCloneSource()?.name }}</span>
              </div>
            </div>

            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-2 text-xs">
              <div class="flex items-center justify-between border-b border-slate-200 pb-1.5 font-semibold text-slate-800">
                <span>Configuration Transfer Contract</span>
                <span class="text-[10px] font-mono text-slate-500">{{ pendingCloneSource()?.mode }}</span>
              </div>
              <div class="grid grid-cols-2 gap-2 text-[11px]">
                <div class="flex flex-col gap-1">
                  <span class="font-bold text-emerald-700">&check; WILL BE COPIED:</span>
                  <span class="text-slate-600">&bull; Execution Mode ({{ pendingCloneSource()?.mode }})</span>
                  <span class="text-slate-600">&bull; Source: {{ pendingCloneSource()?.sourceEngine }}</span>
                  <span class="text-slate-600">&bull; Target: {{ pendingCloneSource()?.targetEngine }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <span class="font-bold text-slate-500">&cross; WILL NOT BE COPIED:</span>
                  <span class="text-slate-500">&bull; Secret Passwords / Tokens</span>
                  <span class="text-slate-500">&bull; Execution ID &amp; History</span>
                  <span class="text-slate-500">&bull; Runtime Checkpoints</span>
                </div>
              </div>
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
              <button
                type="button"
                (click)="pendingCloneSource.set(null)"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer">
                Cancel
              </button>

              <button
                type="button"
                (click)="applyCloneSource()"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer">
                Confirm &amp; Apply Clone
              </button>
            </div>

          </div>
        </div>
      }

      <!-- 3. TEMPLATE OVERWRITE CONFIRMATION MODAL -->
      @if (pendingTemplate()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
          (click)="pendingTemplate.set(null)">
          <div
            class="w-full max-w-md rounded-xl bg-white border border-slate-200 p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="layout-template" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">Apply Blueprint: {{ pendingTemplate()?.title }}?</h3>
                <span class="text-xs text-slate-500 font-medium">Enterprise Blueprint Application</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-medium">
              Applying this blueprint will overwrite existing engine, network, and tuning parameters with the enterprise preset. Current draft details will be updated.
            </p>

            <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
              <button
                type="button"
                (click)="pendingTemplate.set(null)"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer">
                Cancel
              </button>

              <button
                type="button"
                (click)="applyPendingTemplate()"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer">
                Apply Blueprint
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class CreateMigrationWizardComponent implements OnInit, OnDestroy {
  public ms = inject(MigrationUiService);
  public step5Store = inject(Step5MappingStoreService);
  public step6Store = inject(Step6ConfigurationStoreService);
  public step7Store = inject(Step7PlanStoreService);
  private router = inject(Router);

  // Canonical Draft State
  public currentStep = computed(() => this.ms.wizardDraft().currentStep);
  public draftTitle = computed(() => this.ms.wizardDraft().name.trim() || 'Untitled Migration Draft');
  public isCurrentStepValid = computed(() => {
    const step = this.currentStep();
    if (step === 4) {
      const d = this.ms.wizardDraft();
      const isLockedOrFrozen = !!(d.isScopeLocked || d.isScopeFrozen);
      return this.ms.isStepValid(4) && (isLockedOrFrozen || this.ms.canLockScope());
    }
    if (step === 5) {
      return this.ms.isStepValid(5) && this.step5Store.isUiWorkflowReady();
    }
    if (step === 6) {
      return this.ms.isStepValid(6) && this.step6Store.isStep6Valid();
    }
    if (step === 7) {
      return this.ms.isStepValid(7) && this.step7Store.isStep7Valid();
    }
    return this.ms.isStepValid(step);
  });
  public saveState = computed(() => this.ms.saveStatus());

  // Canonical Lists
  public availableTemplates = computed(() => this.ms.templates());
  public availableCloneSources = computed(() => this.ms.portfolioMigrations());

  // Popover & Modal States
  public isClonePopoverOpen = signal<boolean>(false);
  public isTemplatePopoverOpen = signal<boolean>(false);
  public showExitModal = signal<boolean>(false);

  // Pending Actions (Confirmation surfaces)
  public pendingCloneSource = signal<MigrationPortfolioItem | null>(null);
  public pendingTemplate = signal<MigrationTemplateItem | null>(null);
  public cloneSearchQuery = signal<string>('');

  // Auto-Save Relative Timer Engine
  public relativeTimeString = signal<string>('just now');
  public lastSavedClockTime = signal<string>(new Date().toLocaleTimeString());
  private timerInterval?: any;
  private secondsAgo = signal<number>(0);

  // Canonical 9 Steps
  public readonly steps: StepRailItem[] = [
    { index: 1, label: 'Definition', nextLabel: 'Source' },
    { index: 2, label: 'Source', nextLabel: 'Target', prevLabel: 'Definition' },
    { index: 3, label: 'Target', nextLabel: 'Scope', prevLabel: 'Source' },
    { index: 4, label: 'Scope', nextLabel: 'Mapping', prevLabel: 'Target' },
    { index: 5, label: 'Mapping', nextLabel: 'Configure', prevLabel: 'Scope' },
    { index: 6, label: 'Configure', nextLabel: 'Plan', prevLabel: 'Mapping' },
    { index: 7, label: 'Plan', nextLabel: 'Governance', prevLabel: 'Configure' },
    { index: 8, label: 'Governance', nextLabel: 'Review', prevLabel: 'Plan' },
    { index: 9, label: 'Review', nextLabel: 'Launch', prevLabel: 'Governance' }
  ];

  public currentStepItem = computed(() => this.steps[this.currentStep() - 1] || this.steps[0]);
  public nextStepLabel = computed(() => this.currentStepItem().nextLabel);
  public previousStepLabel = computed(() => this.currentStepItem().prevLabel || 'Previous');

  // Filtered Clone Sources
  public filteredCloneSources = computed(() => {
    const q = this.cloneSearchQuery().trim().toLowerCase();
    const list = this.availableCloneSources();
    if (!q) return list;
    return list.filter(m => 
      m.name.toLowerCase().includes(q) || 
      m.sourceEngine.toLowerCase().includes(q) || 
      m.targetEngine.toLowerCase().includes(q)
    );
  });

  public ngOnInit(): void {
    if (typeof window !== 'undefined') {
      (window as any).__wizardMs = this.ms;
      (window as any).__step5Store = this.step5Store;
      (window as any).__step6Store = this.step6Store;
      (window as any).__step7Store = this.step7Store;
    }
    this.timerInterval = setInterval(() => {
      this.secondsAgo.update(s => s + 1);
      const s = this.secondsAgo();
      if (s < 5) {
        this.relativeTimeString.set('just now');
      } else if (s < 60) {
        this.relativeTimeString.set(`${s}s ago`);
      } else {
        const mins = Math.floor(s / 60);
        this.relativeTimeString.set(`${mins}m ago`);
      }
    }, 1000);
  }

  public ngOnDestroy(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
  }

  @HostListener('document:click', ['$event'])
  public handleDocumentClick(): void {
    this.closeAllPopovers();
  }

  @HostListener('window:keydown', ['$event'])
  public handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.closeAllPopovers();
      this.showExitModal.set(false);
      this.pendingCloneSource.set(null);
      this.pendingTemplate.set(null);
    }
  }

  public closeAllPopovers(): void {
    this.isClonePopoverOpen.set(false);
    this.isTemplatePopoverOpen.set(false);
  }

  public toggleClonePopover(event: MouseEvent): void {
    event.stopPropagation();
    this.isTemplatePopoverOpen.set(false);
    this.isClonePopoverOpen.update(v => !v);
  }

  public toggleTemplatePopover(event: MouseEvent): void {
    event.stopPropagation();
    this.isClonePopoverOpen.set(false);
    this.isTemplatePopoverOpen.update(v => !v);
  }

  public handleExit(): void {
    if (this.ms.wizardDraft().isDirty) {
      this.showExitModal.set(true);
    } else {
      this.exitToMigrationHome();
    }
  }

  public exitToMigrationHome(): void {
    this.showExitModal.set(false);
    this.router.navigate(['/migration']);
  }

  public promptCloneConfirmation(m: MigrationPortfolioItem): void {
    this.isClonePopoverOpen.set(false);
    this.pendingCloneSource.set(m);
  }

  public applyCloneSource(): void {
    const source = this.pendingCloneSource();
    if (!source) return;

    this.ms.updateDraft({
      name: `${source.name} (Clone)`,
      mode: source.mode,
      sourceProvider: source.sourceEngine,
      targetProvider: source.targetEngine,
      environment: source.environment,
      currentStep: 1
    });

    this.pendingCloneSource.set(null);
    this.secondsAgo.set(0);
    this.relativeTimeString.set('just now');
  }

  public promptTemplateConfirmation(tmpl: MigrationTemplateItem): void {
    this.isTemplatePopoverOpen.set(false);
    this.pendingTemplate.set(tmpl);
  }

  public applyPendingTemplate(): void {
    const tmpl = this.pendingTemplate();
    if (!tmpl) return;

    this.ms.loadTemplateIntoDraft(tmpl);
    this.pendingTemplate.set(null);
    this.secondsAgo.set(0);
    this.relativeTimeString.set('just now');
  }

  public goToCompletedStep(stepIndex: number): void {
    if (stepIndex < this.currentStep()) {
      this.ms.updateDraft({ currentStep: stepIndex });
    }
  }

  public continueToNextStep(): void {
    if (this.currentStep() === 4 && !this.ms.wizardDraft().isScopeLocked && this.ms.canLockScope()) {
      this.ms.lockScope();
    }
    if (this.isCurrentStepValid() && this.currentStep() < 9) {
      this.ms.updateDraft({ currentStep: this.currentStep() + 1 });
    }
  }

  public previousStep(): void {
    if (this.currentStep() > 1) {
      this.ms.updateDraft({ currentStep: this.currentStep() - 1 });
    }
  }

  public onStep9Action(): void {
    if (this.isCurrentStepValid()) {
      const newId = this.ms.launchDraftMigration();
      this.router.navigate(['/migration', newId]);
    }
  }
}
